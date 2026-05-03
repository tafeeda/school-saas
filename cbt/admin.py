from django.contrib import admin
from .models import CBTExam, CBTQuestion, CBTAttempt, CBTAnswer
from .models import CBTResultTransferLog


@admin.register(CBTExam)
class CBTExamAdmin(admin.ModelAdmin):
    list_display = ("title", "school", "subject", "school_class", "duration_minutes", "is_active")


@admin.register(CBTQuestion)
class CBTQuestionAdmin(admin.ModelAdmin):
    list_display = ("exam", "question_text")


@admin.register(CBTAttempt)
class CBTAttemptAdmin(admin.ModelAdmin):
    list_display = ("student", "exam", "score", "submitted_at")


@admin.register(CBTAnswer)
class CBTAnswerAdmin(admin.ModelAdmin):
    list_display = ("attempt", "question", "selected_option", "is_correct")


@admin.register(CBTResultTransferLog)
class CBTResultTransferLogAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "exam",
        "transfer_type",
        "raw_score",
        "converted_score",
        "status",
        "created_at",
    )
    list_filter = ("status", "transfer_type", "exam")
    search_fields = ("student__first_name", "student__surname")