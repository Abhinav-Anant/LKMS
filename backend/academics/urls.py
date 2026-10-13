from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("sessions", views.AcademicSessionViewSet, basename="session")
router.register("classes", views.SchoolClassViewSet, basename="class")
router.register("sections", views.SectionViewSet, basename="section")
router.register("subjects", views.SubjectViewSet, basename="subject")
router.register("teaching-assignments", views.TeachingAssignmentViewSet, basename="teaching-assignment")
router.register("periods", views.PeriodSlotViewSet, basename="period")
router.register("timetable", views.TimetableEntryViewSet, basename="timetable")

urlpatterns = [
    path("admission-options/", views.admission_options, name="admission-options"),
    path("my-sections/", views.my_sections, name="my-sections"),
    path("my-timetable/", views.my_timetable, name="my-timetable"),
] + router.urls
