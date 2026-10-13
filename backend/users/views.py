import secrets

from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import generics, mixins, serializers, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from core import audit
from core.permissions import CAPABILITIES, Can

from . import parent_login
from .models import User
from .serializers import (
    STAFF_ROLES,
    ChangePasswordSerializer,
    IssuedCodeSerializer,
    LoginSerializer,
    MeSerializer,
    ParentCodeRequestSerializer,
    ParentCodeVerifySerializer,
    PermissionMatrixSerializer,
    StaffUserSerializer,
    TemporaryPasswordSerializer,
    TokenPairSerializer,
)


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class LogoutView(APIView):
    serializer_class = LogoutSerializer

    def post(self, request):
        try:
            RefreshToken(request.data.get("refresh", "")).blacklist()
        except TokenError:
            return Response({"detail": "Invalid refresh token."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = MeSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    serializer_class = ChangePasswordSerializer

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password"])
        audit.record(request, "user.password_changed", user)
        return Response({"detail": "Password changed."})


def tokens_for(user):
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh), "user": MeSerializer(user).data}


class ParentCodeRequestView(APIView):
    """Step 1 of parent sign-in: send a one-time code to the parent's WhatsApp."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "parent_code"

    @extend_schema(request=ParentCodeRequestSerializer, responses=inline_serializer("ParentCodeSent", {"detail": serializers.CharField()}))
    def post(self, request):
        data = ParentCodeRequestSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        parent_login.request_code(data.validated_data["phone"])
        return Response({"detail": (
            "If this number is registered with the school, a 6-digit code has been sent to it. "
            "You can also ask the school office for a code."
        )})


class ParentCodeVerifyView(APIView):
    """Step 2 of parent sign-in: exchange the code for tokens."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @extend_schema(request=ParentCodeVerifySerializer, responses=TokenPairSerializer)
    def post(self, request):
        data = ParentCodeVerifySerializer(data=request.data)
        data.is_valid(raise_exception=True)
        user = parent_login.verify(data.validated_data["phone"], data.validated_data["code"])
        if user is None:
            return Response({"detail": "The code is wrong or has expired. Ask for a new one."}, status=status.HTTP_400_BAD_REQUEST)
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])
        return Response(tokens_for(user))


class IssueParentCodeView(APIView):
    """The office issues a sign-in code for a parent who has no WhatsApp yet. Shown once."""

    permission_classes = [IsAuthenticated, Can("students.edit")]

    @extend_schema(request=ParentCodeRequestSerializer, responses=IssuedCodeSerializer)
    def post(self, request):
        data = ParentCodeRequestSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        phone = data.validated_data["phone"]
        children = list(parent_login.children_for_phone(phone))
        if not children:
            return Response({"phone": ["No studying child has a guardian with this number."]}, status=status.HTTP_400_BAD_REQUEST)
        code, record = parent_login.issue_code(request.user, phone)
        audit.record(request, "parent.login_code_issued", record, phone=phone)
        return Response({"phone": phone, "code": code, "expires_at": record.expires_at,
                         "children": [c.full_name for c in children]})


def temporary_password():
    return f"Lotus-{secrets.token_hex(3)}-{secrets.randbelow(90) + 10}"


class StaffUserViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                       mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """Staff accounts. New accounts and resets get a temporary password that must be changed at first sign-in."""

    serializer_class = StaffUserSerializer
    permission_classes = [IsAuthenticated, Can("users.manage")]
    filterset_fields = ["role", "is_active"]
    search_fields = ["username", "first_name", "last_name", "phone", "email"]
    pagination_class = None

    def get_queryset(self):
        return User.objects.filter(role__in=STAFF_ROLES).order_by("-is_active", "role", "first_name", "username")

    @extend_schema(responses={201: TemporaryPasswordSerializer})
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = temporary_password()
        user = serializer.save(must_change_password=True)
        user.set_password(password)
        user.save(update_fields=["password"])
        audit.record(request, "user.created", user, role=user.role)
        return Response({"username": user.username, "temporary_password": password}, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        if serializer.instance.is_superuser and not self.request.user.is_superuser:
            raise PermissionDenied("This account can only be changed from the Django admin.")
        before = {f: getattr(serializer.instance, f) for f in ("role", "is_active")}
        user = serializer.save()
        changes = {f: [before[f], getattr(user, f)] for f in before if before[f] != getattr(user, f)}
        audit.record(self.request, "user.updated", user, **changes)

    @extend_schema(request=None, responses=TemporaryPasswordSerializer)
    @action(detail=True, methods=["post"], url_path="reset-password")
    def reset_password(self, request, pk=None):
        user = self.get_object()
        if user.pk == request.user.pk:
            raise PermissionDenied("Use Change password for your own account.")
        if user.is_superuser and not request.user.is_superuser:
            raise PermissionDenied("This account can only be changed from the Django admin.")
        if user.role == User.Role.ADMIN and not (request.user.is_superuser or request.user.role == User.Role.ADMIN):
            raise PermissionDenied("Only an administrator can reset an administrator's password.")
        password = temporary_password()
        user.set_password(password)
        user.must_change_password = True
        user.save(update_fields=["password", "must_change_password"])
        audit.record(request, "user.password_reset", user)
        return Response({"username": user.username, "temporary_password": password})


@extend_schema(responses=PermissionMatrixSerializer)
@api_view(["GET"])
@permission_classes([IsAuthenticated, Can("users.manage")])
def permission_matrix(request):
    """Which role may do what. Read-only: changing it is a code change."""
    return Response({
        "roles": [{"value": r.value, "label": r.label} for r in STAFF_ROLES],
        "capabilities": [{"key": key, "roles": sorted(roles)} for key, roles in CAPABILITIES.items()],
    })
