from django.db import models

from schools.models import School
from students.models import Student
from academics.models import SchoolClass, Subject, AcademicSession, AcademicTerm


class CBTExam(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    instructions = models.TextField(blank=True, null=True)

    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)

    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE)
    term = models.ForeignKey(AcademicTerm, on_delete=models.CASCADE)

    duration_minutes = models.IntegerField(default=60)

    ALLOW_ATTEMPT_CHOICES = [
        ("ONE", "One Attempt Only"),
        ("MULTIPLE", "Multiple Attempts / Practice Mode"),
    ]

    attempt_rule = models.CharField(
        max_length=20,
        choices=ALLOW_ATTEMPT_CHOICES,
        default="ONE",
    )

    start_datetime = models.DateTimeField(null=True, blank=True)
    end_datetime = models.DateTimeField(null=True, blank=True)

    show_in_student_portal = models.BooleanField(default=True)

    RESULT_TRANSFER_CHOICES = [
        ("NONE", "Do Not Transfer"),
        ("CA", "Transfer to CA Score"),
        ("EXAM", "Transfer to Exam Score"),
    ]

    transfer_to_result = models.CharField(
        max_length=20,
        choices=RESULT_TRANSFER_CHOICES,
        default="NONE",
    )

    result_score_max = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100,
    )

    total_questions = models.IntegerField(default=0)

    # New real Question Bank link.
    # Do NOT name this "questions" because exam.questions is already used by CBTQuestion.
    question_bank_items = models.ManyToManyField(
        "QuestionBank",
        blank=True,
        related_name="exams",
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.school.name}"


class CBTQuestion(models.Model):
    exam = models.ForeignKey(
        CBTExam,
        on_delete=models.CASCADE,
        related_name="questions",
    )

    question_text = models.TextField()
    question_image = models.ImageField(upload_to="cbt_questions/", null=True, blank=True)

    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255)
    option_d = models.CharField(max_length=255)

    correct_option = models.CharField(max_length=1)  # A, B, C, D

    def __str__(self):
        return f"Question for {self.exam.title}"


class QuestionBank(models.Model):
    school = models.ForeignKey("schools.School", on_delete=models.CASCADE)

    subject = models.ForeignKey("academics.Subject", on_delete=models.CASCADE)
    school_class = models.ForeignKey("academics.SchoolClass", on_delete=models.CASCADE)

    question_text = models.TextField()
    question_image = models.ImageField(upload_to="cbt_bank/", null=True, blank=True)

    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255)
    option_d = models.CharField(max_length=255)

    correct_option = models.CharField(max_length=1)  # A, B, C, D

    DIFFICULTY_CHOICES = [
        ("EASY", "Easy"),
        ("MEDIUM", "Medium"),
        ("HARD", "Hard"),
    ]

    difficulty = models.CharField(
        max_length=10,
        choices=DIFFICULTY_CHOICES,
        default="MEDIUM",
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject.name} - {self.school_class.name}"


class CBTAttempt(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    exam = models.ForeignKey(CBTExam, on_delete=models.CASCADE)

    score = models.IntegerField(default=0)
    total = models.IntegerField(default=0)

    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    result_transferred = models.BooleanField(default=False)
    result_transferred_at = models.DateTimeField(null=True, blank=True)

    question_order = models.JSONField(default=list, blank=True)
    option_order = models.JSONField(default=dict, blank=True)

    tab_switch_count = models.IntegerField(default=0)
    was_auto_submitted = models.BooleanField(default=False)
    auto_submit_reason = models.CharField(max_length=255, blank=True, null=True)


    def __str__(self):
        return f"{self.student} - {self.exam}"


class CBTResultTransferLog(models.Model):
    STATUS_CHOICES = [
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
    ]

    school = models.ForeignKey("schools.School", on_delete=models.CASCADE)
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE)
    exam = models.ForeignKey("CBTExam", on_delete=models.CASCADE)
    attempt = models.ForeignKey("CBTAttempt", on_delete=models.CASCADE)

    transfer_type = models.CharField(max_length=10)  # CA or EXAM

    raw_score = models.DecimalField(max_digits=6, decimal_places=2)
    converted_score = models.DecimalField(max_digits=6, decimal_places=2)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    message = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student} - {self.exam} - {self.transfer_type} - {self.status}"


class CBTAnswer(models.Model):
    attempt = models.ForeignKey(
        CBTAttempt,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(CBTQuestion, on_delete=models.CASCADE)

    selected_option = models.CharField(max_length=1)
    is_correct = models.BooleanField(default=False)