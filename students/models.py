from django.db import models

from core.models import SchoolAwareModel, ActiveStatusMixin


class Student(SchoolAwareModel, ActiveStatusMixin):
    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_profile",
    )

    GENDER_CHOICES = [
        ("MALE", "Male"),
        ("FEMALE", "Female"),
    ]

    admission_number = models.CharField(max_length=50)
    portal_initial_password = models.CharField(max_length=128, blank=True, null=True)
    surname = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    other_name = models.CharField(max_length=100, blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    date_of_birth = models.DateField(blank=True, null=True)
    passport = models.ImageField(upload_to="student_passports/", blank=True, null=True)

    current_class = models.ForeignKey(
        "academics.SchoolClass",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
    )
    current_session = models.ForeignKey(
        "academics.AcademicSession",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
    )

    date_admitted = models.DateField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    guardian_name = models.CharField(max_length=255, blank=True, null=True)
    guardian_phone = models.CharField(max_length=30, blank=True, null=True)
    guardian_email = models.EmailField(blank=True, null=True)
    guardian_address = models.TextField(blank=True, null=True)
    guardian_relationship = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        unique_together = ("school", "admission_number")
        ordering = ["surname", "first_name", "admission_number"]

    def __str__(self):
        return f"{self.surname} {self.first_name} ({self.admission_number})"

    @property
    def full_name(self):
        names = [self.surname, self.first_name, self.other_name or ""]
        return " ".join([name for name in names if name]).strip()


class StudentClassHistory(SchoolAwareModel, ActiveStatusMixin):
    MOVEMENT_TYPE_CHOICES = [
        ("PROMOTION", "Promotion"),
        ("DEMOTION", "Demotion"),
        ("TRANSFER", "Transfer"),
        ("CORRECTION", "Correction"),
    ]

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="class_history",
    )
    old_class = models.ForeignKey(
        "academics.SchoolClass",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="old_class_histories",
    )
    new_class = models.ForeignKey(
        "academics.SchoolClass",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="new_class_histories",
    )
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPE_CHOICES)
    movement_date = models.DateField()
    reason = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-movement_date", "-created_at"]

    def __str__(self):
        return f"{self.student.full_name} - {self.get_movement_type_display()}"