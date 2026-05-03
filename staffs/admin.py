from django.contrib import admin

from .models import StaffProfile, TeacherSubjectAllocation


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "school",
        "staff_id",
        "designation",
        "qualification",
        "is_active",
    )
    list_filter = ("school", "designation", "is_active")
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "staff_id",
    )


@admin.register(TeacherSubjectAllocation)
class TeacherSubjectAllocationAdmin(admin.ModelAdmin):
    list_display = (
        "teacher",
        "school",
        "school_class",
        "subject",
        "session",
        "term",
        "is_active",
    )
    list_filter = ("school", "session", "term", "is_active")
    search_fields = (
        "teacher__username",
        "teacher__first_name",
        "teacher__last_name",
        "school_class__name",
        "subject__name",
    )