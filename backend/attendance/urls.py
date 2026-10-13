from django.urls import path

from . import views

urlpatterns = [
    path("sheet/", views.SheetView.as_view(), name="attendance-sheet"),
    path("month/", views.MonthSummaryView.as_view(), name="attendance-month"),
]
