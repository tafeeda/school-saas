from django.contrib import admin
from .models import (
    AcademicSession,
    AcademicTerm,
    SchoolClass,
    Subject,
    ClassSubject
)


@admin.register(AcademicSession)
class AcademicSessionAdmin(admin.ModelAdmin):
    list_display = ("name", "school", "is_current", "is_active")
    list_filter = ("is_current", "is_active")


@admin.register(AcademicTerm)
class AcademicTermAdmin(admin.ModelAdmin):
    list_display = ("name", "session", "school", "is_current")
    list_filter = ("name", "is_current")


@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ("name", "school", "category", "is_active")
    search_fields = ("name",)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "school", "code")
    search_fields = ("name",)


@admin.register(ClassSubject)
class ClassSubjectAdmin(admin.ModelAdmin):
    list_display = ("school_class", "subject", "school")