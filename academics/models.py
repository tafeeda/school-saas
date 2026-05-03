from django.db import models
from core.models import SchoolAwareModel, ActiveStatusMixin


class AcademicSession(SchoolAwareModel, ActiveStatusMixin):
    name = models.CharField(max_length=20)  # e.g. 2024/2025
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    is_current = models.BooleanField(default=False)

    class Meta:
        unique_together = ("school", "name")
        ordering = ["-name"]

    def __str__(self):
        return f"{self.name} ({self.school.name})"


class AcademicTerm(SchoolAwareModel, ActiveStatusMixin):
    TERM_CHOICES = [
        ("FIRST", "First Term"),
        ("SECOND", "Second Term"),
        ("THIRD", "Third Term"),
    ]

    session = models.ForeignKey(
        AcademicSession,
        on_delete=models.CASCADE,
        related_name="terms"
    )
    name = models.CharField(max_length=10, choices=TERM_CHOICES)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    is_current = models.BooleanField(default=False)
    result_locked = models.BooleanField(default=False)

    class Meta:
        unique_together = ("school", "session", "name")

    def __str__(self):
        return f"{self.get_name_display()} - {self.session.name}"


class SchoolClass(SchoolAwareModel, ActiveStatusMixin):
    name = models.CharField(max_length=50)  # SS1A, JSS1 Berry
    category = models.CharField(max_length=20, blank=True, null=True)
    position_order = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("school", "name")
        ordering = ["position_order", "name"]

    def __str__(self):
        return f"{self.name} ({self.school.name})"


class Subject(SchoolAwareModel, ActiveStatusMixin):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, blank=True, null=True)
    short_name = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        unique_together = ("school", "name")

    def __str__(self):
        return self.name


class ClassSubject(SchoolAwareModel, ActiveStatusMixin):
    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.CASCADE,
        related_name="class_subjects"
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="subject_classes"
    )

    class Meta:
        unique_together = ("school", "school_class", "subject")

    def __str__(self):
        return f"{self.subject.name} - {self.school_class.name}"