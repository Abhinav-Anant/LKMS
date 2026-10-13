from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from academics.scope import teacher_sections
from core import audit
from core.permissions import Can, has_capability

from .models import Notice
from .serializers import NoticeSerializer


class NoticeViewSet(viewsets.ModelViewSet):
    """Staff notice board. Managers (admin, principal, office) post to anyone; teachers to parents of their sections."""

    serializer_class = NoticeSerializer
    permission_classes = [IsAuthenticated, Can("academics.view")]
    filterset_fields = ["audience", "is_published"]

    queryset = Notice.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Notice.objects.none()
        qs = Notice.objects.select_related("created_by").prefetch_related("sections__school_class")
        user = self.request.user
        if has_capability(user, "notices.manage"):
            return qs
        mine = teacher_sections(user)
        return qs.filter(
            Q(created_by=user)
            | Q(is_published=True, audience__in=[Notice.Audience.EVERYONE, Notice.Audience.STAFF])
            | Q(is_published=True, sections__in=mine)
        ).distinct()

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method not in ("GET", "HEAD", "OPTIONS") and not has_capability(request.user, "notices.post"):
            raise PermissionDenied("You may not post notices.")

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        if request.method not in ("GET", "HEAD", "OPTIONS") and not has_capability(request.user, "notices.manage"):
            if obj.created_by_id != request.user.pk:
                raise PermissionDenied("You can only change your own notices.")

    def perform_create(self, serializer):
        published = serializer.validated_data.get("is_published", True)
        notice = serializer.save(created_by=self.request.user, published_at=timezone.now() if published else None)
        audit.record(self.request, "notice.created", notice)

    def perform_update(self, serializer):
        extra = {}
        if serializer.validated_data.get("is_published") and not serializer.instance.published_at:
            extra["published_at"] = timezone.now()
        notice = serializer.save(**extra)
        audit.record(self.request, "notice.updated", notice)

    def perform_destroy(self, instance):
        audit.record(self.request, "notice.deleted", instance)
        instance.delete()


def parent_notices(sections):
    """Published notices a parent with children in `sections` should see."""
    return (
        Notice.objects.filter(is_published=True, audience__in=[Notice.Audience.EVERYONE, Notice.Audience.PARENTS])
        .filter(Q(sections__isnull=True) | Q(sections__in=sections))
        .distinct()
    )
