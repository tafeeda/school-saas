from decimal import Decimal
import uuid

from django.db import models

from core.models import SchoolAwareModel, ActiveStatusMixin




class GradingScheme(SchoolAwareModel, ActiveStatusMixin):
    name = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)

    class Meta:
        unique_together = ("school", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} - {self.school.name}"


class GradeBoundary(SchoolAwareModel, ActiveStatusMixin):
    grading_scheme = models.ForeignKey(
        GradingScheme,
        on_delete=models.CASCADE,
        related_name="boundaries",
    )
    grade = models.CharField(max_length=5)
    min_score = models.DecimalField(max_digits=5, decimal_places=2)
    max_score = models.DecimalField(max_digits=5, decimal_places=2)
    remark = models.CharField(max_length=100, blank=True, null=True)
    color = models.CharField(max_length=20, blank=True, null=True)
    point = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    class Meta:
        unique_together = ("grading_scheme", "grade", "min_score", "max_score")
        ordering = ["-max_score"]

    def __str__(self):
        return f"{self.grade} ({self.min_score}-{self.max_score})"


class AssessmentTemplate(SchoolAwareModel, ActiveStatusMixin):
    name = models.CharField(max_length=100)
    total_score = models.DecimalField(max_digits=6, decimal_places=2, default=100)
    is_default = models.BooleanField(default=False)

    class Meta:
        unique_together = ("school", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} - {self.school.name}"


class AssessmentComponent(SchoolAwareModel, ActiveStatusMixin):
    assessment_template = models.ForeignKey(
        AssessmentTemplate,
        on_delete=models.CASCADE,
        related_name="components",
    )
    name = models.CharField(max_length=100)
    max_score = models.DecimalField(max_digits=6, decimal_places=2)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("assessment_template", "name", "order")
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.name} ({self.max_score}) - {self.assessment_template.name}"


class ResultSheet(SchoolAwareModel, ActiveStatusMixin):
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="result_sheets",
    )
    school_class = models.ForeignKey(
        "academics.SchoolClass",
        on_delete=models.CASCADE,
        related_name="result_sheets",
    )
    session = models.ForeignKey(
        "academics.AcademicSession",
        on_delete=models.CASCADE,
        related_name="result_sheets",
    )
    term = models.ForeignKey(
        "academics.AcademicTerm",
        on_delete=models.CASCADE,
        related_name="result_sheets",
    )
    grading_scheme = models.ForeignKey(
        GradingScheme,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="result_sheets",
    )
    assessment_template = models.ForeignKey(
        AssessmentTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="result_sheets",
    )

    total_obtained = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_possible = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    percentage = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    average_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    average_grade = models.CharField(max_length=10, blank=True, null=True)

    class_position = models.PositiveIntegerField(default=0)
    class_size = models.PositiveIntegerField(default=0)

    attendance_present = models.PositiveIntegerField(default=0)
    attendance_total = models.PositiveIntegerField(default=0)

    next_resumption_date = models.DateField(blank=True, null=True)

    teacher_comment = models.TextField(blank=True, null=True)
    headteacher_comment = models.TextField(blank=True, null=True)
    is_result_blocked = models.BooleanField(default=False)
    block_reason = models.TextField(blank=True, null=True)

    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(blank=True, null=True)
    verification_code = models.CharField(max_length=30, unique=True, blank=True, null=True)

    class Meta:
        unique_together = ("school", "student", "school_class", "session", "term")
        ordering = ["student__surname", "student__first_name"]

    def __str__(self):
        return f"{self.student.full_name} - {self.term.get_name_display()} - {self.session.name}"

    def generate_verification_code(self):
        return str(uuid.uuid4()).replace("-", "")[:12].upper()

    def save(self, *args, **kwargs):
        if not self.verification_code:
            self.verification_code = self.generate_verification_code()
        super().save(*args, **kwargs)

    def recalculate(self):
        subject_results = self.subject_results.all()
        total_obtained = sum([item.total_score for item in subject_results], Decimal("0"))

        if subject_results.exists():
            if self.assessment_template:
                total_possible = self.assessment_template.total_score * subject_results.count()
            else:
                total_possible = Decimal("100") * subject_results.count()
        else:
            total_possible = Decimal("0")

        average_score = total_obtained / subject_results.count() if subject_results.exists() else Decimal("0")
        percentage = (total_obtained / total_possible * Decimal("100")) if total_possible > 0 else Decimal("0")

        self.total_obtained = total_obtained
        self.total_possible = total_possible
        self.average_score = average_score
        self.percentage = percentage

        if self.grading_scheme:
            boundary = self.grading_scheme.boundaries.filter(
                min_score__lte=average_score,
                max_score__gte=average_score,
                is_active=True,
            ).first()
            self.average_grade = boundary.grade if boundary else None

        self.save(update_fields=[
            "total_obtained",
            "total_possible",
            "average_score",
            "percentage",
            "average_grade",
            "updated_at",
        ])

class SubjectResult(SchoolAwareModel, ActiveStatusMixin):
    result_sheet = models.ForeignKey(
        ResultSheet,
        on_delete=models.CASCADE,
        related_name="subject_results",
    )
    subject = models.ForeignKey(
        "academics.Subject",
        on_delete=models.CASCADE,
        related_name="subject_results",
    )
    teacher = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entered_subject_results",
    )

    ca_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    exam_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    total_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    grade = models.CharField(max_length=10, blank=True, null=True)
    remark = models.CharField(max_length=100, blank=True, null=True)

    class_highest = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    class_average = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    class_lowest = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    approved = models.BooleanField(default=False)

    class Meta:
        unique_together = ("result_sheet", "subject")
        ordering = ["subject__name"]

    def __str__(self):
        return f"{self.result_sheet.student.full_name} - {self.subject.name}"

    def recalculate(self):
        self.total_score = (self.ca_score or Decimal("0")) + (self.exam_score or Decimal("0"))

        grading_scheme = self.result_sheet.grading_scheme
        if grading_scheme:
            boundary = grading_scheme.boundaries.filter(
                min_score__lte=self.total_score,
                max_score__gte=self.total_score,
                is_active=True,
            ).first()
            if boundary:
                self.grade = boundary.grade
                self.remark = boundary.remark

        self.save(update_fields=["total_score", "grade", "remark", "updated_at"])


class BehaviorRating(SchoolAwareModel, ActiveStatusMixin):
    CATEGORY_CHOICES = [
        ("AFFECTIVE", "Affective"),
        ("PSYCHOMOTOR", "Psychomotor"),
        ("GENERAL", "General"),
    ]

    result_sheet = models.ForeignKey(
        ResultSheet,
        on_delete=models.CASCADE,
        related_name="behavior_ratings",
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="GENERAL")
    TRAIT_CHOICES = [
        ("ATTENDANCE", "Attendance of Class"),
        ("ATTENTIVENESS", "Attentiveness"),
        ("CRAFTS", "Crafts"),
        ("DRAWING", "Drawing & Painting"),
        ("FLUENCY", "Fluency"),
        ("GAMES", "Games"),
        ("GYMNASTICS", "Gymnastics"),
        ("TOOLS", "Handling of Tools / Lab / Workshops"),
        ("HANDWRITING", "Handwriting"),
        ("HONESTY", "Honesty"),
        ("INITIATIVE", "Initiative"),
        ("MUSIC", "Musical Skills"),
        ("NEATNESS", "Neatness"),
        ("ORGANISATION", "Organisation Ability"),
        ("PERSEVERANCE", "Perseverance"),
        ("POLITENESS", "Politeness"),
        ("PUNCTUALITY", "Punctuality"),
        ("REL_STUDENTS", "Relationship with Students"),
        ("REL_STAFF", "Relationship with Staff"),
        ("RELIABILITY", "Reliability"),
        ("SELF_CONTROL", "Self Control"),
        ("RESPONSIBILITY", "Sense of Responsibility"),
        ("COOPERATION", "Spirit of Co-operation"),
        ("SPORTS", "Sports"),
        ("OTHERS", "Others"),
    ]

    trait_name = models.CharField(max_length=100, choices=TRAIT_CHOICES)
    custom_trait_name = models.CharField(max_length=100, blank=True, null=True)


    score = models.PositiveIntegerField(default=0)
    remark = models.CharField(max_length=100, blank=True, null=True)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("result_sheet", "trait_name", "category")
        ordering = ["category", "order", "trait_name"]

    def __str__(self):
        return f"{self.trait_name} - {self.score} ({self.result_sheet.student.full_name})"


class ResultAccessToken(models.Model):
    result_sheet = models.OneToOneField(
        ResultSheet,
        on_delete=models.CASCADE,
        related_name="access_token"
    )
    token = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def generate_token(self):
        return str(uuid.uuid4()).replace("-", "")[:10].upper()

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = self.generate_token()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.result_sheet.student.full_name} - {self.token}"