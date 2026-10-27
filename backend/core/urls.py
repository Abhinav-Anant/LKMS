from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("audit-log", views.AuditLogViewSet, basename="audit-log")
router.register("school/gallery", views.GalleryViewSet, basename="gallery")

urlpatterns = [
    path("health/", views.health, name="health"),
    path("school/", views.public_school, name="public-school"),
    path("school/logo/", views.school_logo, name="school-logo"),
    path("school/upi-qr/", views.school_upi_qr, name="school-upi-qr"),
    path("captcha/", views.CaptchaView.as_view(), name="captcha"),
    path("school/settings/", views.SchoolProfileView.as_view(), name="school-settings"),
] + router.urls
