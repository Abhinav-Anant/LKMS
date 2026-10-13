"""Which sections a staff member may work with.

Admin and principal may work with every section. A teacher works with the
sections where they are class teacher (attendance) or teach a subject (marks).
"""

from django.db.models import Q

from .models import AcademicSession, Section, TeachingAssignment

ALL_SECTIONS_ROLES = {"admin", "principal"}


def sees_all(user):
    return user.is_superuser or user.role in ALL_SECTIONS_ROLES


def teacher_sections(user, session=None):
    """Sections the user teaches in (as class teacher or subject teacher), current session by default."""
    session = session or AcademicSession.current()
    qs = Section.objects.filter(session=session).select_related("school_class", "session")
    if sees_all(user):
        return qs
    return qs.filter(Q(class_teacher=user) | Q(teaching_assignments__teacher=user)).distinct()


def can_take_attendance(user, section):
    return sees_all(user) or section.class_teacher_id == user.pk


def can_enter_marks(user, section, subject):
    if sees_all(user):
        return True
    return TeachingAssignment.objects.filter(teacher=user, section=section, subject=subject).exists()
