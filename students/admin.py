from django.contrib import admin

from .models import Student, StudentClassHistory



@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        "admission_number",
        "surname",
        "first_name",
        "gender",
        "school",
        "current_class",
        "current_session",
        "user",
        "is_active",
    )
    list_filter = (
        "school",
        "gender",
        "current_class",
        "current_session",
        "is_active",
    )
    search_fields = (
        "admission_number",
        "surname",
        "first_name",
        "other_name",
        "guardian_name",
        "guardian_phone",
    )


@admin.register(StudentClassHistory)
class StudentClassHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "school",
        "old_class",
        "new_class",
        "movement_type",
        "movement_date",
    )
    list_filter = (
        "school",
        "movement_type",
        "movement_date",
    )
    search_fields = (
        "student__surname",
        "student__first_name",
        "student__admission_number",
    )