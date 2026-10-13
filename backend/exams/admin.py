from django.contrib import admin

from .models import ExamTerm, GradeBand, ReportCardEntry

admin.site.register(ExamTerm)
admin.site.register(GradeBand)
admin.site.register(ReportCardEntry)
