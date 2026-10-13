from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from academics.models import SchoolClass
from core import audit
from core.errors import as_api_errors
from core.permissions import Can, has_capability
from core.storage import private_file_response, validate_upload
from students.serializers import StudentDetailSerializer
from students.validators import normalise_mobile

from . import services
from .models import AdmissionApplication, ApplicationDocument, DocumentType
from .serializers import (
    AdmitSerializer, ApplicationDetailSerializer, ApplicationFormSerializer, ApplicationListSerializer,
    ApproveSerializer, DocumentSerializer, DocumentTypeSerializer, DocumentUploadSerializer,
    PublicDocumentSerializer, TrackSerializer, TransitionSerializer, VerifySerializer,
)


def _upload(request, application):
    serializer = DocumentUploadSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    document_type = serializer.validated_data["document_type"]
    uploaded = serializer.validated_data["file"]
    with as_api_errors():
        try:
            info = validate_upload(uploaded, document_type.allowed_formats)
        except DjangoValidationError as exc:
            raise DjangoValidationError({"file": exc.messages}) from exc
        return services.add_document(request, application, document_type, uploaded, info)


# ---------- Public (parents, no login) ----------

class PublicDocumentTypesView(APIView):
    permission_classes = [AllowAny]
    serializer_class = DocumentTypeSerializer

    def get(self, request):
        school_class = SchoolClass.objects.filter(pk=request.query_params.get("class")).first()
        types = DocumentType.for_class(school_class) if school_class else DocumentType.objects.filter(is_active=True)
        return Response(DocumentTypeSerializer(types, many=True).data)


class PublicApplyView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public_application"
    serializer_class = ApplicationFormSerializer

    def post(self, request):
        # "website" is a hidden field on the form. People never fill it in; spam bots do.
        if request.data.get("website"):
            return Response({"detail": "The application could not be submitted."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = ApplicationFormSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with as_api_errors():
            application, token = services.create_application(request, serializer.validated_data)
        return Response(
            {
                "application_number": application.application_number,
                "access_token": token,
                "required_documents": DocumentTypeSerializer(application.required_document_types(), many=True).data,
                "message": "Keep the application number and access code safe. You need them to upload documents.",
            },
            status=status.HTTP_201_CREATED,
        )


class PublicDocumentUploadView(APIView):
    """Parents upload documents with the access code they got when applying."""

    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public_tracking"
    serializer_class = DocumentUploadSerializer

    def post(self, request, application_number):
        application = AdmissionApplication.objects.filter(application_number=application_number).first()
        if application is None or not application.check_token(request.headers.get("X-Application-Token", "")):
            raise NotFound("Application not found or access code is wrong.")
        document = _upload(request, application)
        return Response(PublicDocumentSerializer(document).data, status=status.HTTP_201_CREATED)


class PublicTrackView(APIView):
    """Status lookup with application number + child's date of birth + a registered mobile number."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public_tracking"
    serializer_class = TrackSerializer

    def post(self, request):
        serializer = TrackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        phone = normalise_mobile(data["phone"])
        application = AdmissionApplication.objects.filter(
            application_number=data["application_number"].strip(), date_of_birth=data["date_of_birth"]
        ).first()
        if application is None or phone not in {application.father_phone, application.mother_phone, application.guardian_phone} - {""}:
            raise NotFound("No application matches these details.")
        from .services import missing_or_unverified

        return Response({
            "application_number": application.application_number,
            "child_first_name": application.first_name,
            "class_applied": application.class_applied.name,
            "session": application.session.name,
            "status": application.status,
            "status_label": application.get_status_display(),
            "message": application.status_message,
            "documents": PublicDocumentSerializer(application.current_documents(), many=True).data,
            "documents_still_needed": missing_or_unverified(application),
            "submitted_at": application.submitted_at,
        })


# ---------- Staff ----------

class ApplicationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = [Can("admissions.view")]
    filterset_fields = ["status", "session", "class_applied"]
    search_fields = ["application_number", "first_name", "last_name", "father_name", "mother_name",
                     "father_phone", "mother_phone", "guardian_phone"]
    ordering_fields = ["submitted_at", "first_name", "date_of_birth"]

    def get_queryset(self):
        return AdmissionApplication.objects.select_related("session", "class_applied", "reviewed_by")

    def get_serializer_class(self):
        if self.action == "list":
            return ApplicationListSerializer
        if self.action in ("update", "partial_update"):
            return ApplicationFormSerializer
        return ApplicationDetailSerializer

    def retrieve(self, request, *args, **kwargs):
        application = self.get_object()
        audit.record(request, "admission.viewed", application)
        return Response(ApplicationDetailSerializer(application, context={"request": request}).data)

    def perform_update(self, serializer):
        if not has_capability(self.request.user, "admissions.review"):
            raise PermissionDenied()
        if serializer.instance.status not in AdmissionApplication.OPEN_STATUSES:
            raise ValidationError("A decided application cannot be edited.")
        changed = sorted(k for k, v in serializer.validated_data.items() if getattr(serializer.instance, k) != v)
        application = serializer.save()
        audit.record(self.request, "admission.edited", application, fields=changed)

    def _require(self, capability):
        if not has_capability(self.request.user, capability):
            raise PermissionDenied("Only the principal or an administrator can do this.")

    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        self._require("admissions.review")
        serializer = TransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with as_api_errors():
            application = services.transition(
                request, self.get_object(), serializer.validated_data["status"],
                serializer.validated_data["message"], serializer.validated_data.get("internal_notes"),
            )
        return Response(ApplicationDetailSerializer(application, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        self._require("admissions.decide")
        serializer = ApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with as_api_errors():
            application = services.approve(request, self.get_object(), serializer.validated_data["message"])
        return Response(ApplicationDetailSerializer(application, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def admit(self, request, pk=None):
        self._require("admissions.decide")
        serializer = AdmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with as_api_errors():
            student = services.admit(request, self.get_object(), **serializer.validated_data)
        return Response(StudentDetailSerializer(student, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def documents(self, request, pk=None):
        """Office staff upload a document for a walk-in parent."""
        self._require("admissions.review")
        document = _upload(request, self.get_object())
        return Response(DocumentSerializer(document).data, status=status.HTTP_201_CREATED)


class DocumentViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = ApplicationDocument.objects.select_related("application", "document_type", "verified_by")
    serializer_class = DocumentSerializer
    permission_classes = [Can("admissions.view")]
    parser_classes = [JSONParser]

    @action(detail=True, methods=["get"])
    def file(self, request, pk=None):
        document = self.get_object()
        audit.record(request, "admission.document_viewed", document.application, document=document.document_type.code)
        name = f"{document.application.application_number}-{document.document_type.code}.{document.extension}"
        return private_file_response(document.file, document.content_type, name)

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        if not has_capability(request.user, "admissions.review"):
            raise PermissionDenied()
        serializer = VerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with as_api_errors():
            document = services.verify_document(request, self.get_object(), **serializer.validated_data)
        return Response(DocumentSerializer(document).data)


class DocumentTypeViewSet(viewsets.ModelViewSet):
    queryset = DocumentType.objects.all()
    serializer_class = DocumentTypeSerializer

    def get_permissions(self):
        capability = "admissions.view" if self.request.method in ("GET", "HEAD", "OPTIONS") else "academics.manage"
        return [Can(capability)()]
