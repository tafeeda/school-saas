from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.text import slugify
from datetime import timedelta
from django.utils import timezone
from core.models import TimeStampedModel, ActiveStatusMixin


class School(TimeStampedModel, ActiveStatusMixin):
    PAYMENT_METHOD_CHOICES = [
        ("OFFLINE", "Offline / Physical Payment"),
        ("ONLINE", "Online Payment"),
    ]

    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    code = models.CharField(max_length=30, unique=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    logo = models.ImageField(upload_to="school_logos/", blank=True, null=True)
    portal_subpath = models.CharField(max_length=100, unique=True)
    allow_result_checking = models.BooleanField(default=True)
    is_on_trial = models.BooleanField(default=True)
    trial_start_date = models.DateTimeField(auto_now_add=True)
    trial_end_date = models.DateTimeField(null=True, blank=True)
    is_subscription_active = models.BooleanField(default=True)
    is_suspended = models.BooleanField(default=False)
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default="OFFLINE",
    )
    online_payment_enabled = models.BooleanField(default=False)
    enable_cbt = models.BooleanField(default=False)
    show_cbt_score_immediately = models.BooleanField(default=True)
    shuffle_cbt_questions = models.BooleanField(default=True)
    shuffle_cbt_options = models.BooleanField(default=True)
    subscription_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subscription_start_date = models.DateField(null=True, blank=True)
    subscription_end_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="schools_created",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.trial_end_date:
            self.trial_end_date = timezone.now() + timedelta(days=30)
        super().save(*args, **kwargs)


class SchoolSetting(TimeStampedModel):
    GRADING_MODE_CHOICES = [
        ("PERCENTAGE", "Percentage"),
        ("CUSTOM", "Custom"),
    ]

    THEME_MODE_CHOICES = [
        ("LIGHT", "Light"),
        ("DARK", "Dark"),
        ("SYSTEM", "System"),
    ]

    school = models.OneToOneField(
        School,
        on_delete=models.CASCADE,
        related_name="settings",
    )
    result_header_text = models.CharField(max_length=255, blank=True, null=True)
    grading_mode = models.CharField(
        max_length=20,
        choices=GRADING_MODE_CHOICES,
        default="CUSTOM",
    )
    passkey_length = models.PositiveIntegerField(default=8)
    enable_parent_portal = models.BooleanField(default=True)
    enable_cbt = models.BooleanField(default=False)
    enable_sms = models.BooleanField(default=False)
    enable_email = models.BooleanField(default=False)
    theme_mode = models.CharField(
        max_length=20,
        choices=THEME_MODE_CHOICES,
        default="SYSTEM",
    )
    primary_color = models.CharField(max_length=20, default="#1d4ed8")
    secondary_color = models.CharField(max_length=20, default="#0f172a")

    def __str__(self):
        return f"{self.school.name} Settings"


@receiver(post_save, sender=School)
def create_default_school_settings(sender, instance, created, **kwargs):
    if created:
        SchoolSetting.objects.get_or_create(school=instance)


class SchoolSubscriptionRecord(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("PAID", "Paid"),
        ("FAILED", "Failed"),
        ("CANCELLED", "Cancelled"),
    ]

    PAYMENT_METHOD_CHOICES = [
        ("OFFLINE", "Offline / Physical Payment"),
        ("ONLINE", "Online Payment"),
    ]

    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="subscription_records",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default="PENDING")
    reference = models.CharField(max_length=100, blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    subscription_start_date = models.DateField()
    subscription_end_date = models.DateField()

    note = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.school.name} - {self.amount} - {self.payment_status}"