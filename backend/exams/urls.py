from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("terms", views.ExamTermViewSet, basename="exam-term")
router.register("grades", views.GradeBandViewSet, basename="grade-band")

urlpatterns = router.urls
