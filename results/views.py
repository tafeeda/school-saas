from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from io import BytesIO
from django.http import FileResponse, HttpResponseForbidden
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
import json
from django.db.models import Avg, Count
from core.decorators import school_admin_required, teacher_required
from .forms import (
    AssessmentComponentForm,
    AssessmentTemplateForm,
    BehaviorRatingForm,
    GradeBoundaryForm,
    GradingSchemeForm,
    ResultSheetForm,
    SubjectResultForm,
)
from .models import (
    AssessmentComponent,
    AssessmentTemplate,
    BehaviorRating,
    GradeBoundary,
    GradingScheme,
    ResultSheet,
    ResultAccessToken,
    SubjectResult,
)

from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.utils import timezone
from .utils import fully_recalculate_result_sheet
from django.db import models
from django.http import HttpResponse
from academics.models import SchoolClass, AcademicSession, AcademicTerm, ClassSubject
import qrcode
import base64
from schools.models import School
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics import renderPDF
from students.models import Student
from django.http import FileResponse, HttpResponseForbidden, HttpResponse, JsonResponse
from .comment_utils import (
    generate_headteacher_comment,
    generate_performance_summary,
    generate_teacher_comment,
)




@login_required
@school_admin_required
def grading_scheme_list(request):
    schemes = GradingScheme.objects.filter(
        school=request.user.school
    ).order_by("name")

    return render(request, "results/grading_scheme_list.html", {"page_title": "Grading Schemes", "schemes": schemes})


@login_required
@school_admin_required
def grading_scheme_create(request):
    school = request.user.school

    if request.method == "POST":
        form = GradingSchemeForm(request.POST)

        if form.is_valid():
            scheme = form.save(commit=False)
            scheme.school = school
            scheme.created_by = request.user
            scheme.save()

            # If this scheme is default, remove default from other schemes
            if scheme.is_default:
                GradingScheme.objects.filter(
                    school=school,
                    is_default=True,
                ).exclude(pk=scheme.pk).update(is_default=False)

                # Auto-create default boundaries only if none exist yet
                if not GradeBoundary.objects.filter(grading_scheme=scheme).exists():
                    default_boundaries = [
                        ("A", 70, 100, "Excellent", "#16a34a", 5),
                        ("B", 60, 69, "Very Good", "#22c55e", 4),
                        ("C", 50, 59, "Good", "#eab308", 3),
                        ("D", 40, 49, "Pass", "#f97316", 2),
                        ("F", 0, 39, "Fail", "#ef4444", 1),
                    ]

                    for grade, min_score, max_score, remark, color, point in default_boundaries:
                        GradeBoundary.objects.create(
                            school=school,
                            grading_scheme=scheme,
                            grade=grade,
                            min_score=min_score,
                            max_score=max_score,
                            remark=remark,
                            color=color,
                            point=point,
                            created_by=request.user,
                        )

            messages.success(request, "Grading scheme created successfully.")
            return redirect("grading_scheme_list")
    else:
        form = GradingSchemeForm()

    return render(
        request,
        "results/grading_scheme_form.html",
        {
            "page_title": "Create Grading Scheme",
            "form": form,
        },
    )


@login_required
@school_admin_required
def grade_boundary_list(request):
    boundaries = GradeBoundary.objects.filter(
        school=request.user.school
    ).select_related("grading_scheme").order_by("grading_scheme__name", "-max_score")

    return render(request, "results/grade_boundary_list.html", {"page_title": "Grade Boundaries", "boundaries": boundaries})


@login_required
@school_admin_required
def grade_boundary_create(request):
    school = request.user.school
    if request.method == "POST":
        form = GradeBoundaryForm(request.POST, school=school)
        if form.is_valid():
            boundary = form.save(commit=False)
            boundary.school = school
            boundary.created_by = request.user
            boundary.save()
            messages.success(request, "Grade boundary created successfully.")
            return redirect("grade_boundary_list")
    else:
        form = GradeBoundaryForm(school=school)

    return render(request, "results/grade_boundary_form.html", {"page_title": "Create Grade Boundary", "form": form})


@login_required
@school_admin_required
def assessment_template_list(request):
    templates = AssessmentTemplate.objects.filter(
        school=request.user.school
    ).order_by("name")

    return render(request, "results/assessment_template_list.html", {"page_title": "Assessment Templates", "templates": templates})


@login_required
@school_admin_required
def assessment_template_create(request):
    school = request.user.school

    if request.method == "POST":
        form = AssessmentTemplateForm(request.POST)

        if form.is_valid():
            template = form.save(commit=False)
            template.school = school
            template.created_by = request.user
            template.save()

            if template.is_default:
                AssessmentTemplate.objects.filter(
                    school=school,
                    is_default=True,
                ).exclude(pk=template.pk).update(is_default=False)

                if not template.components.exists():
                    AssessmentComponent.objects.create(
                        school=school,
                        assessment_template=template,
                        name="CA",
                        max_score=30,
                        order=1,
                        created_by=request.user,
                    )

                    AssessmentComponent.objects.create(
                        school=school,
                        assessment_template=template,
                        name="Exam",
                        max_score=70,
                        order=2,
                        created_by=request.user,
                    )

            messages.success(request, "Assessment template created successfully.")
            return redirect("assessment_template_list")

    else:
        form = AssessmentTemplateForm()

    return render(
        request,
        "results/assessment_template_form.html",
        {
            "page_title": "Create Assessment Template",
            "form": form,
        },
    )


    
@login_required
@school_admin_required
def assessment_component_list(request):
    components = AssessmentComponent.objects.filter(
        school=request.user.school
    ).select_related("assessment_template").order_by("assessment_template__name", "order")

    return render(request, "results/assessment_component_list.html", {"page_title": "Assessment Components", "components": components})


@login_required
@school_admin_required
def assessment_component_create(request):
    school = request.user.school
    if request.method == "POST":
        form = AssessmentComponentForm(request.POST, school=school)
        if form.is_valid():
            component = form.save(commit=False)
            component.school = school
            component.created_by = request.user
            component.save()
            messages.success(request, "Assessment component created successfully.")
            return redirect("assessment_component_list")
    else:
        form = AssessmentComponentForm(school=school)

    return render(request, "results/assessment_component_form.html", {"page_title": "Create Assessment Component", "form": form})


@login_required
@school_admin_required
def result_sheet_list(request):
    sheets = ResultSheet.objects.filter(
        school=request.user.school
    ).select_related(
        "student",
        "school_class",
        "session",
        "term",
    ).order_by("student__surname", "student__first_name")

    return render(request, "results/result_sheet_list.html", {"page_title": "Result Sheets", "sheets": sheets})


@login_required
@school_admin_required
def result_sheet_create(request):
    school = request.user.school
    if request.method == "POST":
        form = ResultSheetForm(request.POST, school=school)
        if form.is_valid():
           sheet = form.save(commit=False)
           sheet.school = school
           sheet.created_by = request.user
           sheet.save()

           ResultAccessToken.objects.get_or_create(result_sheet=sheet)

           messages.success(request, "Result sheet created successfully.")
           return redirect("result_sheet_list")
    else:
        form = ResultSheetForm(school=school)

    return render(request, "results/result_sheet_form.html", {"page_title": "Create Result Sheet", "form": form})




@login_required
@school_admin_required
def available_students_for_result_sheet(request):
    school = request.user.school

    class_id = request.GET.get("class_id")
    session_id = request.GET.get("session_id")
    term_id = request.GET.get("term_id")

    if not all([class_id, session_id, term_id]):
        return JsonResponse({"students": []})

    used_student_ids = ResultSheet.objects.filter(
        school=school,
        school_class_id=class_id,
        session_id=session_id,
        term_id=term_id,
        is_active=True,
    ).values_list("student_id", flat=True)

    students = Student.objects.filter(
        school=school,
        current_class_id=class_id,
        is_active=True,
    ).exclude(
        id__in=used_student_ids
    ).order_by("surname", "first_name")

    data = [
        {
            "id": student.id,
            "name": f"{student.full_name} ({student.admission_number})"
        }
        for student in students
    ]

    return JsonResponse({"students": data})



@login_required
@school_admin_required
def result_sheet_detail(request, pk):
    sheet = get_object_or_404(
        ResultSheet.objects.select_related(
            "student", "school_class", "session", "term", "grading_scheme", "assessment_template", "school"
        ).prefetch_related("subject_results__subject", "behavior_ratings"),
        pk=pk,
        school=request.user.school,
    )

    class_sheets = ResultSheet.objects.filter(
        school=sheet.school,
        school_class=sheet.school_class,
        session=sheet.session,
        term=sheet.term,
        is_active=True,
    )

    class_highest_total = class_sheets.order_by("-total_obtained").first()
    class_lowest_total = class_sheets.order_by("total_obtained").first()

    class_average_total = 0
    if class_sheets.exists():
        total_sum = sum(item.total_obtained for item in class_sheets)
        class_average_total = total_sum / class_sheets.count()

    return render(
        request,
        "results/result_sheet_detail.html",
        {
            "page_title": "Result Sheet Detail",
            "sheet": sheet,
            "class_highest_total": class_highest_total.total_obtained if class_highest_total else 0,
            "class_lowest_total": class_lowest_total.total_obtained if class_lowest_total else 0,
            "class_average_total": class_average_total,
        },
    )



@login_required
@teacher_required
def teacher_subject_result_list(request):
    sheets = ResultSheet.objects.filter(
        school=request.user.school,
        school_class__teacher_allocations__teacher=request.user,
        school_class__teacher_allocations__is_active=True,
    ).distinct().select_related("student", "school_class", "session", "term")

    entered_results = SubjectResult.objects.filter(
        school=request.user.school,
        teacher=request.user,
    ).select_related(
        "result_sheet",
        "result_sheet__student",
        "result_sheet__school_class",
        "result_sheet__session",
        "result_sheet__term",
        "subject",
    ).order_by("-created_at")

    # Build progress data per sheet
    sheet_progress = {}

    for sheet in sheets:
        total_subjects = ClassSubject.objects.filter(
            school=request.user.school,
            school_class=sheet.school_class,
            is_active=True,
        ).count()

        entered_count = SubjectResult.objects.filter(
            result_sheet=sheet,
            teacher=request.user
        ).count()

        sheet_progress[sheet.id] = {
            "entered": entered_count,
            "total": total_subjects,
            "remaining": max(total_subjects - entered_count, 0),
        }

    return render(
        request,
        "results/teacher_subject_result_list.html",
        {
            "page_title": "My Result Entries",
            "sheets": sheets,
            "entered_results": entered_results,
            "sheet_progress": sheet_progress,
        },
    )


@login_required
@teacher_required
def teacher_subject_result_create(request, sheet_id):
    sheet = get_object_or_404(
        ResultSheet,
        id=sheet_id,
        school=request.user.school,
    )

    if not sheet.school_class.teacher_allocations.filter(
        teacher=request.user,
        is_active=True,
    ).exists():
        messages.error(request, "You are not assigned to this class.")
        return redirect("teacher_subject_result_list")

    if request.method == "POST":
        form = SubjectResultForm(
            request.POST,
            school=request.user.school,
            teacher=request.user,
            school_class=sheet.school_class,
            sheet=sheet,
        )
        if form.is_valid():
            subject_result = form.save(commit=False)
            subject_result.school = request.user.school
            subject_result.result_sheet = sheet
            subject_result.teacher = request.user
            subject_result.created_by = request.user
            subject_result.save()
            fully_recalculate_result_sheet(sheet)

            messages.success(request, "Subject score saved successfully.")
            return redirect(f"/results/teacher/result-entries/{sheet.id}/create/")
    else:
        form = SubjectResultForm(
            school=request.user.school,
            teacher=request.user,
            school_class=sheet.school_class,
            sheet=sheet,
        )

    return render(
        request,
        "results/teacher_subject_result_form.html",
        {
            "page_title": "Enter Subject Score",
            "form": form,
            "sheet": sheet,
        },
    )


@login_required
@school_admin_required
def grading_scheme_update(request, pk):
    school = request.user.school
    obj = get_object_or_404(GradingScheme, pk=pk, school=school)
    if request.method == "POST":
        form = GradingSchemeForm(request.POST, instance=obj)
        if form.is_valid():
            edited = form.save(commit=False)
            edited.school = school
            edited.save()
            messages.success(request, "Grading scheme updated successfully.")
            return redirect("grading_scheme_list")
    else:
        form = GradingSchemeForm(instance=obj)
    return render(request, "results/grading_scheme_form.html", {"page_title": "Edit Grading Scheme", "form": form})


@login_required
@school_admin_required
def grading_scheme_delete(request, pk):
    school = request.user.school
    obj = get_object_or_404(GradingScheme, pk=pk, school=school)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Grading scheme deleted successfully.")
        return redirect("grading_scheme_list")
    return render(request, "includes/confirm_delete.html", {"object": obj, "page_title": "Delete Grading Scheme", "cancel_url": "/results/grading-schemes/"})


@login_required
@school_admin_required
def grade_boundary_update(request, pk):
    school = request.user.school
    obj = get_object_or_404(GradeBoundary, pk=pk, school=school)
    if request.method == "POST":
        form = GradeBoundaryForm(request.POST, instance=obj, school=school)
        if form.is_valid():
            edited = form.save(commit=False)
            edited.school = school
            edited.save()
            messages.success(request, "Grade boundary updated successfully.")
            return redirect("grade_boundary_list")
    else:
        form = GradeBoundaryForm(instance=obj, school=school)
    return render(request, "results/grade_boundary_form.html", {"page_title": "Edit Grade Boundary", "form": form})


@login_required
@school_admin_required
def grade_boundary_delete(request, pk):
    school = request.user.school
    obj = get_object_or_404(GradeBoundary, pk=pk, school=school)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Grade boundary deleted successfully.")
        return redirect("grade_boundary_list")
    return render(request, "includes/confirm_delete.html", {"object": obj, "page_title": "Delete Grade Boundary", "cancel_url": "/results/grade-boundaries/"})


@login_required
@school_admin_required
def assessment_template_update(request, pk):
    school = request.user.school
    obj = get_object_or_404(AssessmentTemplate, pk=pk, school=school)
    if request.method == "POST":
        form = AssessmentTemplateForm(request.POST, instance=obj)
        if form.is_valid():
            edited = form.save(commit=False)
            edited.school = school
            edited.save()
            messages.success(request, "Assessment template updated successfully.")
            return redirect("assessment_template_list")
    else:
        form = AssessmentTemplateForm(instance=obj)
    return render(request, "results/assessment_template_form.html", {"page_title": "Edit Assessment Template", "form": form})


@login_required
@school_admin_required
def assessment_template_delete(request, pk):
    school = request.user.school
    obj = get_object_or_404(AssessmentTemplate, pk=pk, school=school)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Assessment template deleted successfully.")
        return redirect("assessment_template_list")
    return render(request, "includes/confirm_delete.html", {"object": obj, "page_title": "Delete Assessment Template", "cancel_url": "/results/assessment-templates/"})


@login_required
@school_admin_required
def assessment_component_update(request, pk):
    school = request.user.school
    obj = get_object_or_404(AssessmentComponent, pk=pk, school=school)
    if request.method == "POST":
        form = AssessmentComponentForm(request.POST, instance=obj, school=school)
        if form.is_valid():
            edited = form.save(commit=False)
            edited.school = school
            edited.save()
            messages.success(request, "Assessment component updated successfully.")
            return redirect("assessment_component_list")
    else:
        form = AssessmentComponentForm(instance=obj, school=school)
    return render(request, "results/assessment_component_form.html", {"page_title": "Edit Assessment Component", "form": form})


@login_required
@school_admin_required
def assessment_component_delete(request, pk):
    school = request.user.school
    obj = get_object_or_404(AssessmentComponent, pk=pk, school=school)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Assessment component deleted successfully.")
        return redirect("assessment_component_list")
    return render(request, "includes/confirm_delete.html", {"object": obj, "page_title": "Delete Assessment Component", "cancel_url": "/results/assessment-components/"})


@login_required
@school_admin_required
def result_sheet_update(request, pk):
    school = request.user.school
    obj = get_object_or_404(ResultSheet, pk=pk, school=school)
    if request.method == "POST":
        form = ResultSheetForm(request.POST, instance=obj, school=school)
        if form.is_valid():
            edited = form.save(commit=False)
            edited.school = school
            edited.save()
            messages.success(request, "Result sheet updated successfully.")
            return redirect("result_sheet_list")
    else:
        form = ResultSheetForm(instance=obj, school=school)

    return render(request, "results/result_sheet_form.html", {"page_title": "Edit Result Sheet", "form": form})


@login_required
@school_admin_required
def result_sheet_delete(request, pk):
    school = request.user.school
    obj = get_object_or_404(ResultSheet, pk=pk, school=school)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Result sheet deleted successfully.")
        return redirect("result_sheet_list")
    return render(request, "includes/confirm_delete.html", {"object": obj, "page_title": "Delete Result Sheet", "cancel_url": "/results/result-sheets/"})

@login_required
@school_admin_required
def result_sheet_recalculate(request, pk):
    sheet = get_object_or_404(ResultSheet, pk=pk, school=request.user.school)
    fully_recalculate_result_sheet(sheet)
    messages.success(request, "Result sheet recalculated successfully.")
    return redirect("result_sheet_detail", pk=sheet.pk)


@login_required
@school_admin_required
def result_sheet_publish(request, pk):
    sheet = get_object_or_404(ResultSheet, pk=pk, school=request.user.school)
    fully_recalculate_result_sheet(sheet)
    sheet.is_published = True
    sheet.published_at = timezone.now()
    sheet.save(update_fields=["is_published", "published_at", "updated_at"])
    messages.success(request, "Result sheet published successfully.")
    return redirect("result_sheet_detail", pk=sheet.pk)


@login_required
@school_admin_required
def result_sheet_unpublish(request, pk):
    sheet = get_object_or_404(ResultSheet, pk=pk, school=request.user.school)
    sheet.is_published = False
    sheet.published_at = None
    sheet.save(update_fields=["is_published", "published_at", "updated_at"])
    messages.success(request, "Result sheet unpublished successfully.")
    return redirect("result_sheet_detail", pk=sheet.pk)



@login_required
@teacher_required
def teacher_subject_result_detail(request, pk):
    subject_result = get_object_or_404(
        SubjectResult.objects.select_related(
            "result_sheet",
            "result_sheet__student",
            "result_sheet__school_class",
            "result_sheet__session",
            "result_sheet__term",
            "subject",
        ),
        pk=pk,
        school=request.user.school,
        teacher=request.user,
    )

    return render(
        request,
        "results/teacher_subject_result_detail.html",
        {
            "page_title": "Subject Result Detail",
            "subject_result": subject_result,
        },
    )


@login_required
@teacher_required
def teacher_subject_result_update(request, pk):
    subject_result = get_object_or_404(
        SubjectResult,
        pk=pk,
        school=request.user.school,
        teacher=request.user,
    )

    if subject_result.result_sheet.is_published:
        messages.error(request, "You cannot edit a published result.")
        return redirect("teacher_subject_result_list")

    if request.method == "POST":
        form = SubjectResultForm(
            request.POST,
            instance=subject_result,
            school=request.user.school,
            teacher=request.user,
            school_class=subject_result.result_sheet.school_class,
        )
        if form.is_valid():
            updated_result = form.save(commit=False)
            updated_result.school = request.user.school
            updated_result.teacher = request.user
            updated_result.save()
            fully_recalculate_result_sheet(subject_result.result_sheet)

            messages.success(request, "Subject result updated successfully.")
            return redirect("teacher_subject_result_list")
    else:
        form = SubjectResultForm(
            instance=subject_result,
            school=request.user.school,
            teacher=request.user,
            school_class=subject_result.result_sheet.school_class,
        )

    return render(
        request,
        "results/teacher_subject_result_form.html",
        {
            "page_title": "Edit Subject Score",
            "form": form,
            "sheet": subject_result.result_sheet,
        },
    )


@login_required
@teacher_required
def teacher_subject_result_delete(request, pk):
    subject_result = get_object_or_404(
        SubjectResult,
        pk=pk,
        school=request.user.school,
        teacher=request.user,
    )

    if subject_result.result_sheet.is_published:
        messages.error(request, "You cannot delete a published result.")
        return redirect("teacher_subject_result_list")

    if request.method == "POST":
        sheet = subject_result.result_sheet
        subject_result.delete()
        fully_recalculate_result_sheet(sheet)
        messages.success(request, "Subject result deleted successfully.")
        return redirect("teacher_subject_result_list")

    return render(
        request,
        "includes/confirm_delete.html",
        {
            "object": subject_result,
            "page_title": "Delete Subject Result",
            "cancel_url": "/results/teacher/result-entries/",
        },
    )
    



@login_required
def result_sheet_print(request, pk):
    sheet = get_object_or_404(
        ResultSheet.objects.select_related(
            "student",
            "school_class",
            "session",
            "term",
            "grading_scheme",
            "assessment_template",
            "school",
        ).prefetch_related("subject_results__subject", "behavior_ratings"),
        pk=pk,
    )

    user = request.user

    # Access control
    if getattr(user, "role", None) in ["SUPER_ADMIN", "SCHOOL_ADMIN"]:
        if getattr(user, "role", None) == "SCHOOL_ADMIN" and user.school != sheet.school:
            messages.error(request, "You do not have permission to view this result.")
            return redirect("dashboard_redirect")

    elif getattr(user, "role", None) == "TEACHER":
        if user.school != sheet.school:
            messages.error(request, "You do not have permission to view this result.")
            return redirect("dashboard_redirect")

    else:
        messages.error(request, "You do not have permission to view this result.")
        return redirect("dashboard_redirect")

    class_sheets = ResultSheet.objects.filter(
        school=sheet.school,
        school_class=sheet.school_class,
        session=sheet.session,
        term=sheet.term,
        is_active=True,
    )

    class_highest_total = class_sheets.order_by("-total_obtained").first()
    class_lowest_total = class_sheets.order_by("total_obtained").first()

    class_average_total = 0
    if class_sheets.exists():
        total_sum = sum(item.total_obtained for item in class_sheets)
        class_average_total = total_sum / class_sheets.count()

    verification_url = request.build_absolute_uri(f"/results/view/{sheet.pk}/")

    return render(
        request,
        "results/public_result.html",
        {
            "page_title": "Print Result Sheet",
            "sheet": sheet,
            "class_highest_total": class_highest_total.total_obtained if class_highest_total else 0,
            "class_lowest_total": class_lowest_total.total_obtained if class_lowest_total else 0,
            "class_average_total": class_average_total,
            "verification_url": verification_url,
        },
    )



@login_required
@school_admin_required
def bulk_class_result_print_select(request):
    school = request.user.school

    classes = SchoolClass.objects.filter(
        school=school,
        is_active=True
    ).order_by("position_order", "name")

    sessions = AcademicSession.objects.filter(
        school=school,
        is_active=True
    ).order_by("-id")

    terms = AcademicTerm.objects.filter(
        school=school,
        is_active=True
    ).order_by("name")

    return render(request, "results/bulk_class_result_print_select.html", {
        "page_title": "Bulk Print Class Results",
        "classes": classes,
        "sessions": sessions,
        "terms": terms,
    })


@login_required
@school_admin_required
def bulk_class_result_print(request):
    school = request.user.school

    class_id = request.GET.get("class_id")
    session_id = request.GET.get("session_id")
    term_id = request.GET.get("term_id")

    if not class_id or not session_id or not term_id:
        messages.error(request, "Please select class, session, and term.")
        return redirect("bulk_class_result_print_select")

    school_class = get_object_or_404(SchoolClass, id=class_id, school=school)
    session = get_object_or_404(AcademicSession, id=session_id, school=school)
    term = get_object_or_404(AcademicTerm, id=term_id, school=school)

    sheets = ResultSheet.objects.filter(
        school=school,
        school_class=school_class,
        session=session,
        term=term,
        is_active=True,
        is_published=True,
        is_result_blocked=False,
    ).select_related(
        "student",
        "school",
        "school_class",
        "session",
        "term",
        "grading_scheme",
        "assessment_template",
    ).prefetch_related(
        "subject_results__subject",
        "behavior_ratings",
        "grading_scheme__boundaries",
    ).order_by(
        "student__surname",
        "student__first_name",
    )

    return render(request, "results/bulk_public_result.html", {
        "page_title": "Bulk Class Result Print",
        "sheets": sheets,
        "school_class": school_class,
        "session": session,
        "term": term,
    })


@login_required
@school_admin_required
def behavior_rating_create(request, sheet_id):
    sheet = get_object_or_404(ResultSheet, pk=sheet_id, school=request.user.school)

    if request.method == "POST":
        form = BehaviorRatingForm(request.POST, sheet=sheet)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.school = request.user.school
            obj.result_sheet = sheet
            obj.created_by = request.user
            obj.save()
            messages.success(request, "Behavior rating added successfully.")
            return redirect("result_sheet_detail", pk=sheet.pk)
    else:
        form = BehaviorRatingForm(sheet=sheet)

    return render(
        request,
        "results/behavior_rating_form.html",
        {
            "page_title": "Add Behavior Rating",
            "form": form,
            "sheet": sheet,
        },
    )


@login_required
@school_admin_required
def behavior_rating_update(request, pk):
    obj = get_object_or_404(BehaviorRating, pk=pk, school=request.user.school)

    if request.method == "POST":
        form = BehaviorRatingForm(request.POST, instance=obj, sheet=obj.result_sheet)
        if form.is_valid():
            form.save()
            messages.success(request, "Behavior rating updated successfully.")
            return redirect("result_sheet_detail", pk=obj.result_sheet.pk)
    else:
        form = BehaviorRatingForm(instance=obj, sheet=obj.result_sheet)

    return render(
        request,
        "results/behavior_rating_form.html",
        {
            "page_title": "Edit Behavior Rating",
            "form": form,
            "sheet": obj.result_sheet,
        },
    )


@login_required
@school_admin_required
def behavior_rating_delete(request, pk):
    obj = get_object_or_404(BehaviorRating, pk=pk, school=request.user.school)
    sheet_id = obj.result_sheet.pk

    if request.method == "POST":
        obj.delete()
        messages.success(request, "Behavior rating deleted successfully.")
        return redirect("result_sheet_detail", pk=sheet_id)

    return render(
        request,
        "includes/confirm_delete.html",
        {
            "object": obj,
            "page_title": "Delete Behavior Rating",
            "cancel_url": f"/results/result-sheets/{sheet_id}/",
        },
    )


@login_required
@school_admin_required
def regenerate_passkey(request, pk):
    sheet = get_object_or_404(ResultSheet, pk=pk, school=request.user.school)

    token_obj, _ = ResultAccessToken.objects.get_or_create(result_sheet=sheet)

    token_obj.token = token_obj.generate_token()
    token_obj.save()

    messages.success(request, "Passkey regenerated successfully.")
    return redirect("result_sheet_detail", pk=sheet.pk)


def check_result(request):
    school_name = None
    result_error = None

    if request.method == "POST":
        surname = (request.POST.get("surname") or "").strip()
        token = (request.POST.get("token") or "").strip().upper()

        if not surname or not token:
            result_error = "Please enter both surname and passkey."
        else:
            try:
                access = ResultAccessToken.objects.select_related(
                    "result_sheet",
                    "result_sheet__student",
                    "result_sheet__school",
                ).get(token=token, is_active=True)

                school_name = access.result_sheet.school.name

                if access.result_sheet.is_result_blocked:
                    result_error = access.result_sheet.block_reason or "Result access is blocked."
                elif not access.result_sheet.is_published:
                    result_error = "This result has not been published yet."
                elif access.result_sheet.student.surname.lower() != surname.lower():
                    result_error = "Surname and passkey do not match."
                else:
                    return redirect("public_result_view", pk=access.result_sheet.pk)

            except ResultAccessToken.DoesNotExist:
                result_error = "Invalid passkey."

    return render(
        request,
        "results/public_check.html",
        {
            "school_name": school_name,
            "result_error": result_error,
        },
    )



@xframe_options_sameorigin
def public_result_view(request, pk):
    sheet = get_object_or_404(
        ResultSheet.objects.select_related(
            "student",
            "school",
            "school_class",
            "session",
            "term",
            "grading_scheme",
        ).prefetch_related(
            "subject_results__subject",
            "behavior_ratings",
            "grading_scheme__boundaries",
        ),
        pk=pk,
        is_published=True,
    )

    class_sheets = ResultSheet.objects.filter(
        school=sheet.school,
        school_class=sheet.school_class,
        session=sheet.session,
        term=sheet.term,
        is_active=True,
    )

    class_highest_total = class_sheets.order_by("-total_obtained").first()
    class_lowest_total = class_sheets.order_by("total_obtained").first()

    class_average_total = 0
    if class_sheets.exists():
        total_sum = sum(item.total_obtained for item in class_sheets)
        class_average_total = total_sum / class_sheets.count()

    verification_url = request.build_absolute_uri()

    return render(
        request,
        "results/public_result.html",
        {
            "sheet": sheet,
            "class_highest_total": class_highest_total.total_obtained if class_highest_total else 0,
            "class_lowest_total": class_lowest_total.total_obtained if class_lowest_total else 0,
            "class_average_total": class_average_total,
            "verification_url": verification_url,
        },
    )


@login_required
@school_admin_required
def print_class_passkeys(request, class_id, session_id, term_id):
    sheets = ResultSheet.objects.filter(
        school=request.user.school,
        school_class_id=class_id,
        session_id=session_id,
        term_id=term_id,
        is_active=True,
    ).select_related(
        "student",
        "school",
        "school_class",
        "term",
        "session",
    ).prefetch_related("access_token")

    cards = []
    for sheet in sheets:
        url = f"http://{request.get_host()}/results/check/"
        qr = qrcode.make(url)
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()
        cards.append({
            "sheet": sheet,
            "qr": qr_base64,
        })

    return render(
        request,
        "results/print_passkeys.html",
        {
            "cards": cards,
        },
    )


@login_required
@school_admin_required
def select_passkey_print(request):
    school = request.user.school

    classes = SchoolClass.objects.filter(school=school, is_active=True).order_by("position_order", "name")
    sessions = AcademicSession.objects.filter(school=school, is_active=True).order_by("-name")
    terms = AcademicTerm.objects.filter(school=school, is_active=True).order_by("session__name", "name")

    class_id = request.GET.get("class_id")
    session_id = request.GET.get("session_id")
    term_id = request.GET.get("term_id")

    if class_id and session_id and term_id:
        return redirect(
            "print_class_passkeys",
            class_id=class_id,
            session_id=session_id,
            term_id=term_id,
        )

    return render(
        request,
        "results/select_passkey_print.html",
        {
            "classes": classes,
            "sessions": sessions,
            "terms": terms,
        },
    )



@login_required
def result_sheet_download_pdf(request, pk):
    sheet = get_object_or_404(
        ResultSheet.objects.select_related(
            "student",
            "school",
            "school_class",
            "session",
            "term",
            "grading_scheme",
        ).prefetch_related("subject_results__subject", "behavior_ratings"),
        pk=pk,
    )

    user_role = getattr(request.user, "role", None)

    if user_role == "SUPER_ADMIN":
        pass

    elif user_role == "SCHOOL_ADMIN":
        if request.user.school != sheet.school:
            return HttpResponseForbidden("You are not allowed to download this PDF.")

    elif user_role == "STUDENT":
        student = getattr(request.user, "student_profile", None)

        if not student:
            return HttpResponseForbidden("Student profile not found.")

        if sheet.student != student or sheet.school != student.school:
            return HttpResponseForbidden("You are not allowed to download this PDF.")

        if not sheet.is_published:
            return HttpResponseForbidden("This result has not been published yet.")

    else:
        return HttpResponseForbidden("You are not allowed to download this PDF.")

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4
    left = 12 * mm
    right = width - 12 * mm
    top = height - 12 * mm

    y = top

    # Header
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawCentredString(width / 2, y, sheet.school.name.upper())
    y -= 6 * mm

    pdf.setFont("Helvetica", 8)
    school_address = sheet.school.address if sheet.school.address else ""
    school_contact = ""
    if sheet.school.phone:
        school_contact += str(sheet.school.phone)
    if sheet.school.email:
        if school_contact:
            school_contact += " | "
        school_contact += str(sheet.school.email)

    pdf.drawCentredString(width / 2, y, school_address)
    y -= 4 * mm
    pdf.drawCentredString(width / 2, y, school_contact)
    y -= 5 * mm

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawCentredString(width / 2, y, "ACADEMIC REPORT SHEET")
    y -= 8 * mm

    # Student information
    pdf.setFont("Helvetica", 8)
    info_left_x = left
    info_right_x = width / 2 + 5 * mm

    def safe_text(value):
        return str(value) if value is not None else "-"

    student_info_left = [
        f"Admission No: {safe_text(sheet.student.admission_number)}",
        f"Name: {safe_text(sheet.student.full_name)}",
        f"Gender: {safe_text(sheet.student.get_gender_display())}",
        f"Date of Birth: {safe_text(sheet.student.date_of_birth)}",
        f"Attendance: {safe_text(sheet.attendance_present)}/{safe_text(sheet.attendance_total)}",
    ]

    position_text = "-"
    if sheet.class_position and sheet.class_size:
        position_text = f"{sheet.class_position}/{sheet.class_size}"

    student_info_right = [
        f"Session: {safe_text(sheet.session.name)}",
        f"Term: {safe_text(sheet.term.get_name_display())}",
        f"Class: {safe_text(sheet.school_class.name)}",
        f"Position: {position_text}",
        f"Next Resumption: {safe_text(sheet.next_resumption_date)}",
        f"Verification Code: {safe_text(sheet.verification_code)}",
    ]

    for i, line in enumerate(student_info_left):
        pdf.drawString(info_left_x, y - (i * 4 * mm), line)

    for i, line in enumerate(student_info_right):
        pdf.drawString(info_right_x, y - (i * 4 * mm), line)

    y -= 24 * mm

    # Summary line
    pdf.setFont("Helvetica-Bold", 8)
    summary = (
        f"Total: {safe_text(sheet.total_obtained)}    "
        f"Average: {safe_text(sheet.average_score)}    "
        f"Percentage: {safe_text(sheet.percentage)}%    "
        f"Grade: {safe_text(sheet.average_grade)}"
    )
    pdf.drawString(left, y, summary)
    y -= 6 * mm

    # Subject table
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(left, y, "SUBJECT PERFORMANCE")
    y -= 5 * mm

    col_x = [
        left,
        left + 12 * mm,
        left + 58 * mm,
        left + 73 * mm,
        left + 88 * mm,
        left + 103 * mm,
        left + 121 * mm,
        left + 140 * mm,
        left + 156 * mm,
    ]

    headers = ["S/N", "Subject", "CA", "Exam", "Total", "Highest", "Average", "Grade", "Remark"]

    pdf.setFont("Helvetica-Bold", 7)
    for x, header in zip(col_x, headers):
        pdf.drawString(x, y, header)

    y -= 4 * mm
    pdf.line(left, y, right, y)
    y -= 3 * mm

    pdf.setFont("Helvetica", 7)

    for idx, item in enumerate(sheet.subject_results.all(), start=1):
        if y < 65 * mm:
            pdf.showPage()
            y = top
            pdf.setFont("Helvetica", 7)

        row = [
            str(idx),
            safe_text(item.subject.name)[:22],
            safe_text(item.ca_score),
            safe_text(item.exam_score),
            safe_text(item.total_score),
            safe_text(item.class_highest),
            safe_text(item.class_average),
            safe_text(item.grade),
            safe_text(item.remark)[:14],
        ]

        for x, value in zip(col_x, row):
            pdf.drawString(x, y, str(value))

        y -= 4 * mm

    y -= 2 * mm

    # Behavior / Skills
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(left, y, "BEHAVIOR / SKILLS")
    y -= 5 * mm

    pdf.setFont("Helvetica", 7)
    behavior_items = list(sheet.behavior_ratings.all())
    half = (len(behavior_items) + 1) // 2
    left_items = behavior_items[:half]
    right_items = behavior_items[half:]

    max_rows = max(len(left_items), len(right_items))

    for i in range(max_rows):
        if y < 35 * mm:
            break

        if i < len(left_items):
            item = left_items[i]
            pdf.drawString(left, y, f"{item.get_trait_name_display()[:28]}: {item.score}")

        if i < len(right_items):
            item = right_items[i]
            pdf.drawString(width / 2 + 5 * mm, y, f"{item.get_trait_name_display()[:28]}: {item.score}")

        y -= 4 * mm

    y -= 2 * mm

    # Comments
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(left, y, "Teacher's Comment:")
    pdf.setFont("Helvetica", 7)
    pdf.drawString(left + 35 * mm, y, safe_text(sheet.teacher_comment)[:90])
    y -= 5 * mm

    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(left, y, "Head Teacher's Comment:")
    pdf.setFont("Helvetica", 7)
    pdf.drawString(left + 42 * mm, y, safe_text(sheet.headteacher_comment)[:82])
    y -= 10 * mm

    # Signatures
    pdf.setFont("Helvetica", 8)
    pdf.line(left, y, left + 45 * mm, y)
    pdf.line(width / 2 - 22 * mm, y, width / 2 + 23 * mm, y)
    pdf.line(right - 45 * mm, y, right, y)

    y -= 4 * mm
    pdf.drawString(left + 7 * mm, y, "Class Teacher")
    pdf.drawString(width / 2 - 10 * mm, y, "Principal")
    pdf.drawString(right - 25 * mm, y, "School Stamp")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    filename = f"{sheet.student.full_name} Result.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename)



@login_required
@school_admin_required
def toggle_passkey(request, pk):
    sheet = get_object_or_404(ResultSheet, pk=pk, school=request.user.school)

    token = sheet.access_token
    token.is_active = not token.is_active
    token.save()

    messages.success(request, "Passkey status updated.")
    return redirect("result_sheet_detail", pk=pk)


def school_portal_check_result(request, portal_subpath):
    school = get_object_or_404(School, portal_subpath=portal_subpath, is_active=True)

    result_error = None

    if request.method == "POST":
        surname = (request.POST.get("surname") or "").strip()
        token = (request.POST.get("token") or "").strip().upper()

        if not surname or not token:
            result_error = "Please enter both surname and passkey."
        else:
            try:
                access = ResultAccessToken.objects.select_related(
                    "result_sheet",
                    "result_sheet__student",
                    "result_sheet__school",
                ).get(
                    token=token,
                    is_active=True,
                    result_sheet__school=school,
                )

                if access.result_sheet.is_result_blocked:
                    result_error = access.result_sheet.block_reason or "Result access is blocked."
                elif not access.result_sheet.is_published:
                    result_error = "This result has not been published yet."
                elif access.result_sheet.student.surname.lower() != surname.lower():
                    result_error = "Surname and passkey do not match."
                else:
                    return redirect(
                        "school_portal_result_view",
                        portal_subpath=portal_subpath,
                        pk=access.result_sheet.pk,
                    )

            except ResultAccessToken.DoesNotExist:
                result_error = "Invalid passkey."

    return render(
        request,
        "results/school_portal_check.html",
        {
            "school": school,
            "result_error": result_error,
        },
    )


def school_portal_result_view(request, portal_subpath, pk):
    school = get_object_or_404(School, portal_subpath=portal_subpath, is_active=True)

    sheet = get_object_or_404(
        ResultSheet.objects.select_related(
            "student",
            "school",
            "school_class",
            "session",
            "term",
            "grading_scheme",
        ).prefetch_related(
            "subject_results__subject",
            "behavior_ratings",
            "grading_scheme__boundaries",
        ),
        pk=pk,
        school=school,
        is_published=True,
    )

    class_sheets = ResultSheet.objects.filter(
        school=sheet.school,
        school_class=sheet.school_class,
        session=sheet.session,
        term=sheet.term,
        is_active=True,
    )

    class_highest_total = class_sheets.order_by("-total_obtained").first()
    class_lowest_total = class_sheets.order_by("total_obtained").first()

    class_average_total = 0
    if class_sheets.exists():
        total_sum = sum(item.total_obtained for item in class_sheets)
        class_average_total = total_sum / class_sheets.count()

    verification_url = request.build_absolute_uri()

    return render(
        request,
        "results/public_result.html",
        {
            "school": school,
            "sheet": sheet,
            "class_highest_total": class_highest_total.total_obtained if class_highest_total else 0,
            "class_lowest_total": class_lowest_total.total_obtained if class_lowest_total else 0,
            "class_average_total": class_average_total,
            "verification_url": verification_url,
        },
    )


@login_required
@school_admin_required
def toggle_result_block(request, pk):
    sheet = get_object_or_404(ResultSheet, pk=pk, school=request.user.school)

    sheet.is_result_blocked = not sheet.is_result_blocked

    if sheet.is_result_blocked:
        sheet.block_reason = "Access restricted by school management."
    else:
        sheet.block_reason = ""

    sheet.save()

    messages.success(request, "Result access updated successfully.")
    return redirect("result_sheet_detail", pk=pk)


@login_required
@school_admin_required
def bulk_result_controls(request):
    school = request.user.school

    classes = SchoolClass.objects.filter(school=school, is_active=True).order_by("position_order", "name")
    sessions = AcademicSession.objects.filter(school=school, is_active=True).order_by("-name")
    terms = AcademicTerm.objects.filter(school=school, is_active=True).order_by("session__name", "name")

    if request.method == "POST":
        class_id = request.POST.get("class_id")
        session_id = request.POST.get("session_id")
        term_id = request.POST.get("term_id")
        action = request.POST.get("action")

        sheets = ResultSheet.objects.filter(
            school=school,
            school_class_id=class_id,
            session_id=session_id,
            term_id=term_id,
            is_active=True,
        )

        if not sheets.exists():
            messages.error(request, "No result sheets found for the selected class, session, and term.")
            return redirect("bulk_result_controls")

        if action == "publish":
            sheets.update(is_published=True, published_at=timezone.now())
            messages.success(request, f"{sheets.count()} result sheet(s) published successfully.")

        elif action == "unpublish":
            sheets.update(is_published=False, published_at=None)
            messages.success(request, f"{sheets.count()} result sheet(s) unpublished successfully.")

        elif action == "block":
            sheets.update(
                is_result_blocked=True,
                block_reason="Access restricted by school management."
            )
            messages.success(request, f"{sheets.count()} result sheet(s) blocked successfully.")

        elif action == "unblock":
            sheets.update(
                is_result_blocked=False,
                block_reason=""
            )
            messages.success(request, f"{sheets.count()} result sheet(s) unblocked successfully.")

        elif action == "regenerate_passkeys":
            updated = 0
            for sheet in sheets:
                token_obj, _ = ResultAccessToken.objects.get_or_create(result_sheet=sheet)
                token_obj.token = token_obj.generate_token()
                token_obj.save()
                updated += 1

            messages.success(request, f"{updated} passkey(s) regenerated successfully.")

        elif action == "print_passkeys":
            return redirect(
                "print_class_passkeys",
                class_id=class_id,
                session_id=session_id,
                term_id=term_id,
            )

        else:
            messages.error(request, "Invalid bulk action.")

        return redirect("bulk_result_controls")

    return render(
        request,
        "results/bulk_result_controls.html",
        {
            "classes": classes,
            "sessions": sessions,
            "terms": terms,
        },
    )


@login_required
@school_admin_required
def result_sheet_generate_comments(request, pk):
    sheet = get_object_or_404(ResultSheet, pk=pk, school=request.user.school)

    sheet.teacher_comment = generate_teacher_comment(sheet)
    sheet.headteacher_comment = generate_headteacher_comment(sheet)
    sheet.save(update_fields=["teacher_comment", "headteacher_comment", "updated_at"])

    messages.success(request, "Comments generated successfully.")
    return redirect("result_sheet_detail", pk=sheet.pk)


@login_required
@school_admin_required
def bulk_generate_result_comments(request):
    school = request.user.school

    classes = SchoolClass.objects.filter(school=school, is_active=True).order_by("position_order", "name")
    sessions = AcademicSession.objects.filter(school=school, is_active=True).order_by("-name")
    terms = AcademicTerm.objects.filter(school=school, is_active=True).order_by("session__name", "name")

    if request.method == "POST":
        class_id = request.POST.get("class_id")
        session_id = request.POST.get("session_id")
        term_id = request.POST.get("term_id")

        sheets = ResultSheet.objects.filter(
            school=school,
            school_class_id=class_id,
            session_id=session_id,
            term_id=term_id,
            is_active=True,
        )

        if not sheets.exists():
            messages.error(request, "No result sheets found for the selected class, session, and term.")
            return redirect("bulk_generate_result_comments")

        updated = 0
        for sheet in sheets:
            sheet.teacher_comment = generate_teacher_comment(sheet)
            sheet.headteacher_comment = generate_headteacher_comment(sheet)
            sheet.save(update_fields=["teacher_comment", "headteacher_comment", "updated_at"])
            updated += 1

        messages.success(request, f"{updated} result sheet comment(s) generated successfully.")
        return redirect("bulk_generate_result_comments")

    return render(
        request,
        "results/bulk_generate_comments.html",
        {
            "classes": classes,
            "sessions": sessions,
            "terms": terms,
        },
    )


@login_required
@school_admin_required
def result_analytics_dashboard(request):
    school = request.user.school

    sessions = AcademicSession.objects.filter(school=school, is_active=True).order_by("-name")
    terms = AcademicTerm.objects.filter(school=school, is_active=True).order_by("session__name", "name")
    classes = SchoolClass.objects.filter(school=school, is_active=True).order_by("position_order", "name")

    session_id = request.GET.get("session")
    term_id = request.GET.get("term")
    class_id = request.GET.get("class")

    sheets = ResultSheet.objects.filter(
        school=school,
        is_published=True,
        is_active=True,
    ).select_related("student", "school_class", "session", "term")

    if session_id:
        sheets = sheets.filter(session_id=session_id)

    if term_id:
        sheets = sheets.filter(term_id=term_id)

    if class_id:
        sheets = sheets.filter(school_class_id=class_id)

    top_students = sheets.order_by("-average_score")[:10]

    class_performance = (
        sheets.values("school_class__name")
        .annotate(avg_score=Avg("average_score"))
        .order_by("-avg_score")
    )

    grade_distribution = (
        sheets.values("average_grade")
        .annotate(count=Count("id"))
        .order_by("average_grade")
    )

    subject_performance = (
        SubjectResult.objects.filter(
            result_sheet__in=sheets,
        )
        .values("subject__name")
        .annotate(avg_score=Avg("total_score"), entries=Count("id"))
        .order_by("-avg_score")
    )

    trend_data = (
        sheets.values("session__name", "term__name")
        .annotate(avg_score=Avg("average_score"))
        .order_by("session__name", "term__name")
    )

    return render(
        request,
        "results/analytics_dashboard.html",
        {
            "top_students": top_students,

            "class_labels": json.dumps([item["school_class__name"] for item in class_performance]),
            "class_avg_scores": json.dumps([float(item["avg_score"] or 0) for item in class_performance]),

            "grade_labels": json.dumps([item["average_grade"] or "N/A" for item in grade_distribution]),
            "grade_counts": json.dumps([item["count"] for item in grade_distribution]),

            "subject_labels": json.dumps([item["subject__name"] for item in subject_performance]),
            "subject_avg_scores": json.dumps([float(item["avg_score"] or 0) for item in subject_performance]),
            "subject_entries": subject_performance,

            "trend_labels": json.dumps([
                f'{item["session__name"]} - {item["term__name"]}'
                for item in trend_data
            ]),
            "trend_scores": json.dumps([float(item["avg_score"] or 0) for item in trend_data]),

            "sessions": sessions,
            "terms": terms,
            "classes": classes,
            "selected_session": session_id,
            "selected_term": term_id,
            "selected_class": class_id,
        },
    )



@login_required
@school_admin_required
def analytics_export_pdf(request):
    school = request.user.school

    sheets = ResultSheet.objects.filter(
        school=school,
        is_published=True,
        is_active=True,
    ).select_related("student", "school_class", "session", "term")

    session_id = request.GET.get("session")
    term_id = request.GET.get("term")
    class_id = request.GET.get("class")

    if session_id == "None":
        session_id = None
    if term_id == "None":
        term_id = None
    if class_id == "None":
        class_id = None

    if session_id:
        sheets = sheets.filter(session_id=session_id)

    if term_id:
        sheets = sheets.filter(term_id=term_id)

    if class_id:
        sheets = sheets.filter(school_class_id=class_id)

    avg_score = sheets.aggregate(avg=models.Avg("average_score"))["avg"] or 0
    top_students = sheets.order_by("-average_score")[:10]

    class_performance = (
        sheets.values("school_class__name")
        .annotate(avg_score=models.Avg("average_score"))
        .order_by("-avg_score")
    )

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 40

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(width / 2, y, f"{school.name.upper()} ANALYTICS REPORT")
    y -= 30

    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, y, f"Total Published Results: {sheets.count()}")
    y -= 18
    pdf.drawString(40, y, f"Average Score: {round(avg_score, 2)}")
    y -= 30

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, y, "Top Students")
    y -= 18

    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(40, y, "Name")
    pdf.drawString(330, y, "Class")
    pdf.drawString(450, y, "Average")
    y -= 12

    pdf.setFont("Helvetica", 9)
    for item in top_students:
        if y < 60:
            pdf.showPage()
            y = height - 40

        pdf.drawString(40, y, item.student.full_name[:35])
        pdf.drawString(330, y, item.school_class.name[:18])
        pdf.drawString(450, y, str(item.average_score))
        y -= 15

    y -= 20

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, y, "Class Performance")
    y -= 18

    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(40, y, "Class")
    pdf.drawString(250, y, "Average Score")
    y -= 12

    pdf.setFont("Helvetica", 9)
    for item in class_performance:
        if y < 60:
            pdf.showPage()
            y = height - 40

        pdf.drawString(40, y, str(item["school_class__name"])[:30])
        pdf.drawString(250, y, str(round(item["avg_score"] or 0, 2)))
        y -= 15

    # =========================
    # CHART PAGE
    # =========================
    pdf.showPage()

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(width / 2, height - 40, "ANALYTICS CHARTS")

    # Class Performance Bar Chart
    class_names = []
    class_scores = []

    for item in class_performance:
        class_names.append(str(item["school_class__name"])[:10])
        class_scores.append(float(item["avg_score"] or 0))

    if class_scores:
        drawing = Drawing(500, 250)
        chart = VerticalBarChart()
        chart.x = 50
        chart.y = 50
        chart.height = 150
        chart.width = 400
        chart.data = [class_scores]
        chart.categoryAxis.categoryNames = class_names
        chart.valueAxis.valueMin = 0
        chart.valueAxis.valueMax = 100
        chart.valueAxis.valueStep = 10
        chart.barSpacing = 4

        drawing.add(chart)
        renderPDF.draw(drawing, pdf, 40, height - 330)

        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(40, height - 80, "Class Average Performance")

    # Grade Distribution Pie Chart
    grade_distribution = (
        sheets.values("average_grade")
        .annotate(count=models.Count("id"))
        .order_by("average_grade")
    )

    grade_labels = []
    grade_counts = []

    for item in grade_distribution:
        grade_labels.append(item["average_grade"] or "N/A")
        grade_counts.append(item["count"])

    if grade_counts:
        drawing2 = Drawing(500, 250)
        pie = Pie()
        pie.x = 120
        pie.y = 40
        pie.width = 150
        pie.height = 150
        pie.data = grade_counts
        pie.labels = grade_labels

        drawing2.add(pie)
        renderPDF.draw(drawing2, pdf, 40, height - 570)

        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(40, height - 350, "Grade Distribution")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    return FileResponse(buffer, as_attachment=True, filename="analytics_report.pdf")



@login_required
@school_admin_required
def bulk_result_sheet_create(request):
    school = request.user.school

    classes = SchoolClass.objects.filter(school=school, is_active=True).order_by("position_order", "name")
    sessions = AcademicSession.objects.filter(school=school, is_active=True).order_by("-name")
    terms = AcademicTerm.objects.filter(school=school, is_active=True).order_by("session__name", "name")
    grading_schemes = GradingScheme.objects.filter(school=school, is_active=True).order_by("name")
    assessment_templates = AssessmentTemplate.objects.filter(school=school, is_active=True).order_by("name")

    if request.method == "POST":
        class_id = request.POST.get("school_class")
        session_id = request.POST.get("session")
        term_id = request.POST.get("term")
        grading_scheme_id = request.POST.get("grading_scheme")
        assessment_template_id = request.POST.get("assessment_template")
        attendance_present = request.POST.get("attendance_present") or 0
        attendance_total = request.POST.get("attendance_total") or 0
        next_resumption_date = request.POST.get("next_resumption_date") or None

        school_class = get_object_or_404(SchoolClass, pk=class_id, school=school)
        session = get_object_or_404(AcademicSession, pk=session_id, school=school)
        term = get_object_or_404(AcademicTerm, pk=term_id, school=school)

        grading_scheme = None
        if grading_scheme_id:
            grading_scheme = get_object_or_404(GradingScheme, pk=grading_scheme_id, school=school)

        assessment_template = None
        if assessment_template_id:
            assessment_template = get_object_or_404(AssessmentTemplate, pk=assessment_template_id, school=school)

        existing_student_ids = ResultSheet.objects.filter(
            school=school,
            school_class=school_class,
            session=session,
            term=term,
            is_active=True,
        ).values_list("student_id", flat=True)

        students = Student.objects.filter(
            school=school,
            current_class=school_class,
            is_active=True,
        ).exclude(id__in=existing_student_ids)

        created_count = 0

        for student in students:
            sheet = ResultSheet.objects.create(
                school=school,
                student=student,
                school_class=school_class,
                session=session,
                term=term,
                grading_scheme=grading_scheme,
                assessment_template=assessment_template,
                attendance_present=attendance_present,
                attendance_total=attendance_total,
                next_resumption_date=next_resumption_date,
                created_by=request.user,
            )

            ResultAccessToken.objects.get_or_create(result_sheet=sheet)
            created_count += 1

        if created_count:
            messages.success(request, f"{created_count} result sheet(s) created successfully.")
        else:
            messages.info(request, "No new result sheets created. All students may already have result sheets for this class, session, and term.")

        return redirect("result_sheet_list")

    return render(request, "results/bulk_result_sheet_create.html", {
        "page_title": "Bulk Create Result Sheets",
        "classes": classes,
        "sessions": sessions,
        "terms": terms,
        "grading_schemes": grading_schemes,
        "assessment_templates": assessment_templates,
    })



@login_required
@school_admin_required
def behavior_rating_bulk_create(request, sheet_id):
    sheet = get_object_or_404(ResultSheet, pk=sheet_id, school=request.user.school)

    existing_traits = set(
        BehaviorRating.objects.filter(result_sheet=sheet)
        .values_list("trait_name", flat=True)
    )

    available_traits = [
        choice for choice in BehaviorRating.TRAIT_CHOICES
        if choice[0] not in existing_traits
    ]

    if request.method == "POST":
        created_count = 0

        for order, (trait_code, trait_label) in enumerate(available_traits, start=1):
            selected = request.POST.get(f"selected_{trait_code}")

            if not selected:
                continue

            score = request.POST.get(f"score_{trait_code}")
            remark = request.POST.get(f"remark_{trait_code}", "").strip()
            category = request.POST.get(f"category_{trait_code}") or "GENERAL"

            if not score:
                continue

            BehaviorRating.objects.create(
                school=request.user.school,
                result_sheet=sheet,
                category=category,
                trait_name=trait_code,
                score=score,
                remark=remark,
                order=order,
                created_by=request.user,
            )
            created_count += 1

        if created_count:
            messages.success(request, f"{created_count} behavior rating(s) added successfully.")
        else:
            messages.info(request, "No behavior ratings were added.")

        return redirect("result_sheet_detail", pk=sheet.pk)

    return render(
        request,
        "results/behavior_rating_bulk_form.html",
        {
            "page_title": "Bulk Add Behavior Ratings",
            "sheet": sheet,
            "available_traits": available_traits,
            "category_choices": BehaviorRating.CATEGORY_CHOICES,
        },
    )