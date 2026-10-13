from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("", views.StudentViewSet, basename="student")

urlpatterns = router.urls
