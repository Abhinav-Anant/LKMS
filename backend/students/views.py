import json

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Prefetch
from django.http import Http404, HttpResponse
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from academics.models import Enrollment
from core import audit
from core.permissions import Can, ReadOrManage
from core.storage import private_file_response

from . import bulk_import
from .models import Student
from .serializers import StudentDetailSerializer, StudentListSerializer


XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class StudentViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """Students are created by admitting an application or by a bulk import; they are never deleted."""

    permission_classes = [ReadOrManage]
    view_capability = "students.view"
    manage_capability = "students.edit"
    filterset_fields = {
        "status": ["exact"],
        "enrollments__section": ["exact"],
        "enrollments__section__school_class": ["exact"],
        "enrollments__session": ["exact"],
    }
    search_fields = ["first_name", "last_name", "admission_number", "guardians__phone", "guardians__full_name"]
    ordering_fields = ["first_name", "admission_number", "admission_date"]

    def get_queryset(self):
        current = Enrollment.objects.filter(session__is_current=True).select_related("section__school_class")
        return (
            Student.objects.all()
            .prefetch_related(Prefetch("enrollments", queryset=current, to_attr="current_enrollments"))
            .distinct()
        )

    def get_serializer_class(self):
        return StudentListSerializer if self.action == "list" else StudentDetailSerializer

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        audit.record(request, "student.viewed", self.get_object())
        return response

    def perform_update(self, serializer):
        before = {f: getattr(serializer.instance, f) for f in serializer.validated_data}
        student = serializer.save()
        changed = {f: [str(before[f]), str(getattr(student, f))] for f in before if before[f] != getattr(student, f)}
        audit.record(self.request, "student.updated", student, changed=sorted(changed))

    @action(detail=True, methods=["get"])
    def photo(self, request, pk=None):
        student = self.get_object()
        if not student.photo:
            raise Http404
        audit.record(request, "student.photo_viewed", student)
        mime = "image/png" if student.photo.name.endswith(".png") else "image/jpeg"
        return private_file_response(student.photo, mime, f"{student.admission_number}-photo")


def _json_list(value):
    """The browser sends the names of the photos it holds as a JSON list."""
    try:
        names = json.loads(value) if value else None
    except ValueError:
        return None
    return [str(n) for n in names] if isinstance(names, list) else None


class StudentImportView(APIView):
    """Bulk import from the sample sheet. POST with commit=false checks only; commit=true imports (all or nothing)."""

    permission_classes = [Can("students.import")]
    parser_classes = [MultiPartParser]

    def get(self, request):
        content = bulk_import.template_workbook()
        response = HttpResponse(content, content_type=XLSX)
        response["Content-Disposition"] = 'attachment; filename="student-import-sample.xlsx"'
        return response

    def post(self, request):
        sheet = request.FILES.get("file")
        if sheet is None:
            raise ValidationError({"file": ["Choose the filled-in sheet (.xlsx or .csv)."]})
        if sheet.size > 10 * 1024 * 1024:
            raise ValidationError({"file": ["The sheet is larger than 10 MB."]})
        try:
            rows = bulk_import.read_sheet(sheet)
            photos = bulk_import.photos_from_zip(request.FILES["photos"]) if request.FILES.get("photos") else None
            names = _json_list(request.data.get("photo_names"))
            commit = str(request.data.get("commit", "")).lower() in ("1", "true", "yes")
            if commit:
                report = bulk_import.run(request, rows, photos=photos, photo_names=names)
            else:
                report, _ = bulk_import.check(rows, photo_names=list(photos) if photos else names)
        except DjangoValidationError as exc:
            raise ValidationError({"file": exc.messages}) from exc
        data = report.as_dict()
        data["imported"] = commit and report.ok
        return Response(data, status=400 if commit and not report.ok else 200)


class StudentPhotoImportView(APIView):
    """Photos for students already in LKMS, named by admission number (0101.jpg). Several files or a ZIP."""

    permission_classes = [Can("students.import")]
    parser_classes = [MultiPartParser]

    def post(self, request):
        photos = {}
        try:
            for upload in request.FILES.getlist("photos"):
                upload.seek(0)
                if upload.read(2) == b"PK":
                    upload.seek(0)
                    photos.update(bulk_import.photos_from_zip(upload))
                else:
                    upload.seek(0)
                    photos[upload.name.lower()] = upload.read()
        except DjangoValidationError as exc:
            raise ValidationError({"photos": exc.messages}) from exc
        if not photos:
            raise ValidationError({"photos": ["Choose the photos (JPEG or PNG) or a ZIP of them."]})
        replace = str(request.data.get("replace", "true")).lower() not in ("0", "false", "no")
        return Response(bulk_import.attach_photos(request, photos, replace=replace))
