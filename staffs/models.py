from django.conf import settings
from django.db import models

from core.models import SchoolAwareModel, ActiveStatusMixin
from core.image_utils import compress_uploaded_image


class StaffProfile(SchoolAwareModel, ActiveStatusMixin):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="staff_profile",
    )
    staff_id = models.CharField(max_length=50, unique=True)
    designation = models.CharField(max_length=100, blank=True, null=True)
    qualification = models.CharField(max_length=255, blank=True, null=True)
    date_joined = models.DateField(blank=True, null=True)
    passport = models.ImageField(upload_to="staff_passports/", blank=True, null=True)

    class Meta:
        ordering = ["user__first_name", "user__last_name"]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.staff_id}"

    def save(self, *args, **kwargs):
        if self.passport:
            self.passport = compress_uploaded_image(
                self.passport,
                max_size=(350, 350),
                quality=70,
            )
        super().save(*args, **kwargs)


class TeacherSubjectAllocation(SchoolAwareModel, ActiveStatusMixin):
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="teaching_allocations",
        limit_choices_to={"role": "TEACHER"},
    )
    school_class = models.ForeignKey(
        "academics.SchoolClass",
        on_delete=models.CASCADE,
        related_name="teacher_allocations",
    )
    subject = models.ForeignKey(
        "academics.Subject",
        on_delete=models.CASCADE,
        related_name="teacher_allocations",
    )
    session = models.ForeignKey(
        "academics.AcademicSession",
        on_delete=models.CASCADE,
        related_name="teacher_allocations",
    )
    term = models.ForeignKey(
        "academics.AcademicTerm",
        on_delete=models.CASCADE,
        related_name="teacher_allocations",
    )

    class Meta:
        unique_together = (
            "school",
            "teacher",
            "school_class",
            "subject",
            "session",
            "term",
        )
        ordering = ["teacher__first_name", "school_class__name", "subject__name"]

    def __str__(self):
        return f"{self.teacher.get_full_name()} - {self.subject.name} - {self.school_class.name}"