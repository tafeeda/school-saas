from django.contrib import admin

from .models import LessonNote


@admin.register(LessonNote)
class LessonNoteAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "school",
        "school_class",
        "subject",
        "session",
        "term",
        "week",
        "status",
        "is_active",
    )
    list_filter = (
        "school",
        "school_class",
        "subject",
        "session",
        "term",
        "status",
        "is_active",
    )
    search_fields = (
        "title",
        "topic",
        "subtopic",
        "description",
        "school__name",
        "school_class__name",
        "subject__name",
    )