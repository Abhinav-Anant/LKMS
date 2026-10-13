from django.urls import path

from . import views

urlpatterns = [
    path("children/", views.children, name="parent-children"),
    path("children/<int:pk>/attendance/", views.child_attendance, name="parent-child-attendance"),
    path("children/<int:pk>/fees/", views.child_fees, name="parent-child-fees"),
    path("children/<int:pk>/receipts/<int:payment_id>/", views.child_receipt, name="parent-child-receipt"),
    path("children/<int:pk>/marks/", views.child_marks, name="parent-child-marks"),
    path("children/<int:pk>/timetable/", views.child_timetable, name="parent-child-timetable"),
    path("notices/", views.notices, name="parent-notices"),
    path("whatsapp/", views.whatsapp_alerts, name="parent-whatsapp"),
]
