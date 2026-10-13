from .models import AuditLog


def client_ip(request):
    if request is None:
        return None
    # Behind Nginx the real client address is the first entry of X-Forwarded-For.
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    return request.META.get("REMOTE_ADDR")


def record(request, action, obj, **details):
    """Write an audit entry for `obj`. `request` may be None for system actions."""
    user = getattr(request, "user", None)
    actor = user if user is not None and user.is_authenticated else None
    return AuditLog.objects.create(
        actor=actor,
        action=action,
        object_type=obj._meta.label_lower,
        object_id=str(obj.pk),
        object_repr=str(obj)[:200],
        details=details,
        ip_address=client_ip(request),
    )
