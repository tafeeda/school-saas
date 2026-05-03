from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings



class User(AbstractUser):
    ROLE_CHOICES = [
        ("SUPER_ADMIN", "Super Admin"),
        ("SCHOOL_ADMIN", "School Admin"),
        ("TEACHER", "Teacher"),
        ("STUDENT", "Student"),
        ("PARENT", "Parent"),
        ("ACCOUNTANT", "Accountant"),
        ("LIBRARIAN", "Librarian"),
    ]

    school = models.ForeignKey(
        "schools.School",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    role = models.CharField(max_length=30, choices=ROLE_CHOICES)
    phone = models.CharField(max_length=20, blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    passport = models.ImageField(upload_to="user_passports/", blank=True, null=True)
    must_change_password = models.BooleanField(default=False)

    def __str__(self):
        full_name = self.get_full_name().strip()
        return full_name if full_name else self.username

    @property
    def is_super_admin(self):
        return self.role == "SUPER_ADMIN"

    @property
    def is_school_admin(self):
        return self.role == "SCHOOL_ADMIN"

    @property
    def is_teacher(self):
        return self.role == "TEACHER"

    @property
    def is_student(self):
        return self.role == "STUDENT"

    @property
    def is_parent(self):
        return self.role == "PARENT"



class AuditLog(models.Model):
    ACTION_CHOICES = [
        ("PROFILE_UPDATED", "Profile Updated"),
        ("PASSWORD_CHANGED", "Password Changed"),
        ("SUPER_ADMIN_CREATED", "Super Admin Created"),
        ("LOGIN", "Login"),
        ("LOGOUT", "Logout"),
        ("FAILED_LOGIN", "Failed Login"),
    ]

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs_performed"
    )

    affected_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs_received"
    )

    school = models.ForeignKey(
        "schools.School",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    description = models.TextField(blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} by {self.actor} at {self.created_at}"