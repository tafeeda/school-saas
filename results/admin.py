from django.contrib import admin

from .models import (
    AssessmentComponent,
    AssessmentTemplate,
    BehaviorRating,
    GradeBoundary,
    GradingScheme,
    ResultSheet,
    SubjectResult,
    ResultAccessToken,
)


@admin.register(GradingScheme)
class GradingSchemeAdmin(admin.ModelAdmin):
    list_display = ("name", "school", "is_default", "is_active")
    list_filter = ("school", "is_default", "is_active")
    search_fields = ("name", "school__name")


@admin.register(GradeBoundary)
class GradeBoundaryAdmin(admin.ModelAdmin):
    list_display = (
        "grading_scheme",
        "grade",
        "min_score",
        "max_score",
        "remark",
        "is_active",
    )
    list_filter = ("school", "grading_scheme", "is_active")
    search_fields = ("grade", "remark", "grading_scheme__name")


@admin.register(AssessmentTemplate)
class AssessmentTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "school", "total_score", "is_default", "is_active")
    list_filter = ("school", "is_default", "is_active")
    search_fields = ("name", "school__name")


@admin.register(AssessmentComponent)
class AssessmentComponentAdmin(admin.ModelAdmin):
    list_display = (
        "assessment_template",
        "name",
        "max_score",
        "order",
        "school",
        "is_active",
    )
    list_filter = ("school", "assessment_template", "is_active")
    search_fields = ("name", "assessment_template__name")


@admin.register(BehaviorRating)
class BehaviorRatingAdmin(admin.ModelAdmin):
    list_display = ("result_sheet", "category", "trait_name", "score", "remark", "is_active")
    list_filter = ("school", "category", "is_active")
    search_fields = ("trait_name", "remark", "result_sheet__student__surname", "result_sheet__student__first_name")


@admin.register(ResultAccessToken)
class ResultAccessTokenAdmin(admin.ModelAdmin):
    list_display = ("result_sheet", "token", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = (
        "token",
        "result_sheet__student__surname",
        "result_sheet__student__first_name",
        "result_sheet__student__admission_number",
    )