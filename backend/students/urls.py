from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("", views.StudentViewSet, basename="student")

# Before the router, whose detail route would otherwise take "import" for a student id.
urlpatterns = [
    path("import/", views.StudentImportView.as_view(), name="student-import"),
    path("import/photos/", views.StudentPhotoImportView.as_view(), name="student-photo-import"),
    *router.urls,
]
