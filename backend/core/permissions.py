from rest_framework.permissions import BasePermission

# What each role may do. Superusers may do everything.
CAPABILITIES = {
    "admissions.view": {"admin", "principal", "office"},
    "admissions.review": {"admin", "principal", "office"},
    "admissions.decide": {"admin", "principal"},
    "students.view": {"admin", "principal", "office"},
    "students.edit": {"admin", "principal", "office"},
    "students.view_sensitive": {"admin", "principal"},
    "academics.view": {"admin", "principal", "office", "accountant", "teacher"},
    "academics.manage": {"admin", "principal"},
    "school.manage": {"admin"},
    "fees.view": {"admin", "principal", "accountant", "office"},
    "fees.collect": {"admin", "principal", "accountant"},
    "fees.manage": {"admin", "principal", "accountant"},
    "fees.request_concession": {"admin", "principal", "accountant", "office"},
    "fees.approve": {"admin", "principal"},
    "audit.view": {"admin", "principal"},
    # Phase 3: portals. Teachers are further limited to their own sections (academics.scope).
    "attendance.view": {"admin", "principal", "office", "teacher"},
    "attendance.mark": {"admin", "principal", "teacher"},
    "marks.view": {"admin", "principal", "teacher"},
    "marks.enter": {"admin", "principal", "teacher"},
    "notices.post": {"admin", "principal", "office", "teacher"},
    "notices.manage": {"admin", "principal", "office"},
    "users.manage": {"admin", "principal"},
    "reports.view": {"admin", "principal"},
    # Phase 4: WhatsApp
    "messaging.view": {"admin", "principal", "office"},
    "messaging.manage": {"admin", "principal"},
    # Phase 5: transfer certificates and backups
    "tc.view": {"admin", "principal", "office"},
    "tc.request": {"admin", "principal", "office"},
    "tc.issue": {"admin", "principal"},
    "backups.view": {"admin", "principal"},
}


def roles_for(capability):
    """The roles holding a capability, including the school's own choices in its profile."""
    roles = CAPABILITIES.get(capability, set())
    if capability == "fees.collect":
        from .models import SchoolProfile

        if SchoolProfile.get().office_can_collect_fees:
            roles = roles | {"office"}
    return roles


def has_capability(user, capability):
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser:
        return True
    return user.role in roles_for(capability)


def Can(capability):
    """DRF permission class factory: permission_classes = [Can("students.view")]."""

    class _Can(BasePermission):
        message = "You do not have permission to do this."

        def has_permission(self, request, view):
            return has_capability(request.user, capability)

    _Can.__name__ = f"Can_{capability.replace('.', '_')}"
    return _Can


class ReadOrManage(BasePermission):
    """Read needs `view_capability`, writes need `manage_capability` (set on the view)."""

    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return has_capability(request.user, view.view_capability)
        return has_capability(request.user, view.manage_capability)
