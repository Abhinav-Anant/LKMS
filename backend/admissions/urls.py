from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("applications", views.ApplicationViewSet, basename="application")
router.register("documents", views.DocumentViewSet, basename="application-document")
router.register("document-types", views.DocumentTypeViewSet, basename="document-type")

urlpatterns = [
    path("public/document-types/", views.PublicDocumentTypesView.as_view(), name="public-document-types"),
    path("public/apply/", views.PublicApplyView.as_view(), name="public-apply"),
    path("public/track/", views.PublicTrackView.as_view(), name="public-track"),
    path("public/<str:application_number>/documents/", views.PublicDocumentUploadView.as_view(), name="public-upload"),
] + router.urls
