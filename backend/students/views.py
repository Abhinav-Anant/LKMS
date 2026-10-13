from django.db.models import Prefetch
from django.http import Http404
from rest_framework import mixins, viewsets
from rest_framework.decorators import action

from academics.models import Enrollment
from core import audit
from core.permissions import ReadOrManage
from core.storage import private_file_response

from .models import Student
from .serializers import StudentDetailSerializer, StudentListSerializer


class StudentViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """Students are created only by admitting an application; they are never deleted."""

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
