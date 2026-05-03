from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, AuditLog


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "username",
        "first_name",
        "last_name",
        "email",
        "role",
        "school",
        "is_active",
        "is_staff",
    )
    list_filter = ("role", "school", "is_active", "is_staff")
    search_fields = ("username", "first_name", "last_name", "email")

    fieldsets = UserAdmin.fieldsets + (
        (
            "Additional Info",
            {
                "fields": (
                    "school",
                    "role",
                    "phone",
                    "gender",
                    "passport",
                    "must_change_password",
                )
            },
        ),
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "action",
        "actor",
        "affected_user",
        "school",
        "ip_address",
        "created_at",
    )
    list_filter = ("action", "school", "created_at")
    search_fields = (
        "actor__username",
        "affected_user__username",
        "description",
        "ip_address",
    )
    readonly_fields = (
        "actor",
        "affected_user",
        "school",
        "action",
        "description",
        "ip_address",
        "user_agent",
        "created_at",
    )