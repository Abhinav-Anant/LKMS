"""Parent sign-in with mobile number and a one-time code.

A parent account is keyed by the mobile number recorded for a guardian. Every
child whose guardian has that number appears under the one account, so a
parent with several children at the school signs in once.
"""

import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac

from core.notify import notify
from students.models import Guardian, Student

from .models import LoginCode, User

REQUESTED_CODE_MINUTES = 10
STAFF_CODE_HOURS = 24
MAX_ATTEMPTS = 5
MAX_CODES_PER_WINDOW = 3
CODE_WINDOW_MINUTES = 15


def _hash(phone, code):
    return salted_hmac("lkms.parent-login", f"{phone}:{code}", secret=settings.SECRET_KEY).hexdigest()


def children_for_phone(phone):
    return Student.objects.filter(guardians__phone=phone, status=Student.Status.ACTIVE).distinct()


def has_children(phone):
    return bool(phone) and children_for_phone(phone).exists()


def _new_code(phone, source, lifetime, issued_by=None):
    code = f"{secrets.randbelow(10**6):06d}"
    # A new code replaces any earlier unused one.
    LoginCode.objects.filter(phone=phone, used_at__isnull=True).update(expires_at=timezone.now())
    record = LoginCode.objects.create(
        phone=phone, code_hash=_hash(phone, code), source=source, expires_at=timezone.now() + lifetime, issued_by=issued_by,
    )
    return code, record


def request_code(phone):
    """Send a code if the number belongs to a parent. Says nothing either way, so numbers can't be probed."""
    if not has_children(phone):
        return
    recent = LoginCode.objects.filter(
        phone=phone, source=LoginCode.Source.REQUESTED,
        created_at__gte=timezone.now() - timedelta(minutes=CODE_WINDOW_MINUTES),
    ).count()
    if recent >= MAX_CODES_PER_WINDOW:
        return
    code, _ = _new_code(phone, LoginCode.Source.REQUESTED, timedelta(minutes=REQUESTED_CODE_MINUTES))
    notify("parent_login_code", phone=phone, code=code, minutes=REQUESTED_CODE_MINUTES)


def issue_code(staff_user, phone):
    """A code the office reads out to a parent, valid for a day. Returns (code, LoginCode)."""
    return _new_code(phone, LoginCode.Source.STAFF, timedelta(hours=STAFF_CODE_HOURS), issued_by=staff_user)


def verify(phone, code):
    """Return the parent's User if the code is right, else None."""
    record = LoginCode.objects.filter(phone=phone, used_at__isnull=True, expires_at__gt=timezone.now()).first()
    if record is None or record.attempts >= MAX_ATTEMPTS:
        return None
    if not constant_time_compare(record.code_hash, _hash(phone, code)):
        record.attempts += 1
        record.save(update_fields=["attempts"])
        return None
    if not has_children(phone):
        return None
    record.used_at = timezone.now()
    record.save(update_fields=["used_at"])
    return parent_user(phone)


def parent_user(phone):
    user, created = User.objects.get_or_create(
        username=f"parent-{phone}", defaults={"role": User.Role.PARENT, "phone": phone},
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])
        guardian = Guardian.objects.filter(phone=phone, user__isnull=True).first()
        if guardian:
            guardian.user = user
            guardian.save(update_fields=["user"])
        user.first_name = guardian.full_name if guardian else ""
        user.save(update_fields=["first_name"])
    if user.role != User.Role.PARENT or not user.is_active:
        return None
    return user
