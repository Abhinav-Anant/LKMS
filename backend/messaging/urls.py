from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("messages", views.OutgoingMessageViewSet, basename="whatsapp-message")
router.register("opt-outs", views.OptOutViewSet, basename="whatsapp-opt-out")

urlpatterns = [
    path("status/", views.status_view, name="whatsapp-status"),
    path("qr/", views.qr_view, name="whatsapp-qr"),
    path("reconnect/", views.reconnect_view, name="whatsapp-reconnect"),
] + router.urls
