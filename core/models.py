from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CreatedByMixin(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created_records",
    )

    class Meta:
        abstract = True


class SchoolAwareModel(TimeStampedModel, CreatedByMixin):
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="%(class)s_records",
        null=True,
        blank=True,
    )

    class Meta:
        abstract = True


class ActiveStatusMixin(models.Model):
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True