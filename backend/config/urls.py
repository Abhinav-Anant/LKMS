from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from core import seo

admin.site.site_header = "LKMS administration"
admin.site.site_title = "LKMS"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/v1/", include("core.urls")),
    path("api/v1/auth/", include("users.urls")),
    path("api/v1/academics/", include("academics.urls")),
    path("api/v1/students/", include("students.urls")),
    path("api/v1/admissions/", include("admissions.urls")),
    path("api/v1/fees/", include("fees.urls")),
    path("api/v1/attendance/", include("attendance.urls")),
    path("api/v1/assessments/", include("assessments.urls")),
    path("api/v1/notices/", include("notices.urls")),
    path("api/v1/parent/", include("portal.urls")),
    path("api/v1/reports/", include("portal.reports")),
    path("api/v1/whatsapp/", include("messaging.urls")),
    path("api/v1/exams/", include("exams.urls")),
    path("api/v1/certificates/", include("certificates.urls")),
    path("api/v1/backups/", include("core.backup_urls")),
    path("robots.txt", seo.robots),
    path("sitemap.xml", seo.sitemap),
    path("", seo.page),
    path("<str:path>", seo.page),
]
