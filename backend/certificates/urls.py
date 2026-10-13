from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("tc", views.TransferCertificateViewSet, basename="tc")

urlpatterns = router.urls
