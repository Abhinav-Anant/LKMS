from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("heads", views.FeeHeadViewSet)
router.register("installments", views.InstallmentViewSet)
router.register("amounts", views.FeeAmountViewSet)
router.register("invoices", views.InvoiceViewSet, basename="invoice")
router.register("payments", views.PaymentViewSet, basename="payment")
router.register("concessions", views.ConcessionViewSet, basename="concession")
router.register("upi-submissions", views.UpiSubmissionViewSet, basename="upi-submission")

urlpatterns = [
    path("reports/daily-collection/", views.DailyCollectionView.as_view()),
    path("reports/defaulters/", views.DefaultersView.as_view()),
    path("public/pay/<str:token>/", views.PublicInvoiceView.as_view()),
    path("public/pay/<str:token>/upi/", views.PublicUpiSubmitView.as_view()),
    path("public/pay/<str:token>/receipts/<str:receipt_number>/", views.PublicReceiptView.as_view()),
] + router.urls
