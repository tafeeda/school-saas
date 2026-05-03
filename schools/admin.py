from django.contrib import admin
from .models import School, SchoolSubscriptionRecord, SchoolSetting


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "portal_subpath",
        "is_active",
        "allow_result_checking",
        "is_on_trial",
        "enable_cbt",
    )
    list_filter = ("is_active", "allow_result_checking", "is_on_trial")
    search_fields = ("name", "code", "portal_subpath", "enable_cbt")


@admin.register(SchoolSetting)
class SchoolSettingAdmin(admin.ModelAdmin):
    list_display = (
        "school",
        "grading_mode",
        "passkey_length",
        "enable_parent_portal",
        "enable_cbt",
        "theme_mode",
    )


@admin.register(SchoolSubscriptionRecord)
class SchoolSubscriptionRecordAdmin(admin.ModelAdmin):
    list_display = (
        "school",
        "amount",
        "payment_method",
        "payment_status",
        "subscription_start_date",
        "subscription_end_date",
        "paid_at",
    )
    list_filter = (
        "payment_method",
        "payment_status",
        "subscription_start_date",
        "subscription_end_date",
    )
    search_fields = (
        "school__name",
        "reference",
    )