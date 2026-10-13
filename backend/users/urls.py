from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

router = DefaultRouter()
router.register("users", views.StaffUserViewSet, basename="staff-user")

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("me/", views.MeView.as_view(), name="me"),
    path("change-password/", views.ChangePasswordView.as_view(), name="change-password"),
    path("parent/request-code/", views.ParentCodeRequestView.as_view(), name="parent-request-code"),
    path("parent/verify-code/", views.ParentCodeVerifyView.as_view(), name="parent-verify-code"),
    path("parent/issue-code/", views.IssueParentCodeView.as_view(), name="parent-issue-code"),
    path("permissions/", views.permission_matrix, name="permission-matrix"),
] + router.urls
