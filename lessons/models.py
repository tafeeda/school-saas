import os

from django.core.exceptions import ValidationError
from django.db import models

from core.models import SchoolAwareModel, ActiveStatusMixin


def lesson_note_upload_path(instance, filename):
    school_code = instance.school.code if instance.school and instance.school.code else "school"
    return f"lesson_notes/{school_code}/{filename}"


def validate_lesson_note_file(value):
    allowed_extensions = [
        ".pdf",
        ".doc",
        ".docx",
        ".ppt",
        ".pptx",
        ".txt",
        ".csv",
        ".xlsx",
    ]

    ext = os.path.splitext(value.name)[1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(
            "Unsupported file type. Allowed formats: pdf, doc, docx, ppt, pptx, txt, csv, xlsx."
        )


class LessonNote(SchoolAwareModel, ActiveStatusMixin):
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("PUBLISHED", "Published"),
        ("ARCHIVED", "Archived"),
    ]

    school_class = models.ForeignKey(
        "academics.SchoolClass",
        on_delete=models.CASCADE,
        related_name="lesson_notes",
    )
    subject = models.ForeignKey(
        "academics.Subject",
        on_delete=models.CASCADE,
        related_name="lesson_notes",
    )
    session = models.ForeignKey(
        "academics.AcademicSession",
        on_delete=models.CASCADE,
        related_name="lesson_notes",
    )
    term = models.ForeignKey(
        "academics.AcademicTerm",
        on_delete=models.CASCADE,
        related_name="lesson_notes",
    )

    SCOPE_CHOICES = [
        ("WEEKLY", "Weekly"),
        ("TERMLY", "Entire Term"),
        ("SESSION", "Entire Session"),
    ]

    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES, default="WEEKLY")
    week = models.PositiveIntegerField(blank=True, null=True)
    title = models.CharField(max_length=255)
    topic = models.CharField(max_length=255)
    subtopic = models.CharField(max_length=255, blank=True, null=True)

    lesson_file = models.FileField(
        upload_to=lesson_note_upload_path,
        validators=[validate_lesson_note_file],
        blank=True,
        null=True
    )

    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="DRAFT")

    class Meta:
        ordering = ["school", "school_class", "subject", "week", "-created_at"]
        unique_together = ("school", "school_class", "subject", "session", "term", "scope", "week", "title")

    def __str__(self):
        return f"{self.title} - {self.school_class.name} - {self.subject.name}"

    @property
    def file_extension(self):
        return os.path.splitext(self.lesson_file.name)[1].lower() if self.lesson_file else ""