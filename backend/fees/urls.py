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
router.register("issues", views.PaymentIssueViewSet)

urlpatterns = [
    path("reports/daily-collection/", views.DailyCollectionView.as_view()),
    path("reports/defaulters/", views.DefaultersView.as_view()),
    path("cashfree/webhook/", views.CashfreeWebhookView.as_view()),
    path("public/pay/<str:token>/", views.PublicInvoiceView.as_view()),
    path("public/pay/<str:token>/start/", views.PublicStartPaymentView.as_view()),
    path("public/pay/<str:token>/orders/<str:order_id>/", views.PublicOrderStatusView.as_view()),
    path("public/pay/<str:token>/receipts/<str:receipt_number>/", views.PublicReceiptView.as_view()),
] + router.urls
