from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("sessions", views.AcademicSessionViewSet, basename="session")
router.register("classes", views.SchoolClassViewSet, basename="class")
router.register("sections", views.SectionViewSet, basename="section")

urlpatterns = [path("admission-options/", views.admission_options, name="admission-options")] + router.urls
