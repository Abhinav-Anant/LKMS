from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("", views.AssessmentViewSet, basename="assessment")

urlpatterns = router.urls
