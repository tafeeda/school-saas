from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from core.decorators import school_admin_required
from django import forms
from django.contrib.auth.password_validation import validate_password
from .forms import TeacherAllocationForm, TeacherCreationForm
from .models import StaffProfile, TeacherSubjectAllocation
from django.db.models import Prefetch
from academics.models import SchoolClass, Subject, AcademicSession, AcademicTerm
from django.http import JsonResponse

User = get_user_model()


@login_required
@school_admin_required
def teacher_list(request):
    school = request.user.school

    teachers = User.objects.filter(
        school=school,
        role="TEACHER",
    ).prefetch_related(
        Prefetch(
            "teaching_allocations",
            queryset=TeacherSubjectAllocation.objects.filter(
                school=school,
                is_active=True,
            ).select_related(
                "school_class",
                "subject",
                "session",
                "term",
            ),
            to_attr="active_allocations",
        )
    ).order_by("first_name", "last_name")

    for teacher in teachers:
        grouped_allocations = {}

        for allocation in teacher.active_allocations:
            class_name = allocation.school_class.name

            if class_name not in grouped_allocations:
                grouped_allocations[class_name] = []

            grouped_allocations[class_name].append({
                "subject": allocation.subject.name,
                "term": allocation.term.get_name_display(),
                "session": allocation.session.name,
            })

        teacher.grouped_allocations = grouped_allocations

    return render(request, "staffs/teacher_list.html", {
        "page_title": "Teachers",
        "teachers": teachers,
    })

@login_required
@school_admin_required
def teacher_create(request):
    school = request.user.school
    if request.method == "POST":
        form = TeacherCreationForm(request.POST, request.FILES)
        if form.is_valid():
            teacher = form.save(commit=False)
            teacher.school = school
            teacher.role = "TEACHER"
            teacher.is_staff = False
            teacher.must_change_password = True
            teacher.set_password(form.cleaned_data["password"])
            teacher.save()

            StaffProfile.objects.create(
                school=school,
                user=teacher,
                staff_id=form.cleaned_data["staff_id"],
                designation=form.cleaned_data.get("designation"),
                qualification=form.cleaned_data.get("qualification"),
                date_joined=form.cleaned_data.get("date_joined"),
                created_by=request.user,
            )
            messages.success(request, "Teacher account created successfully.")
            return redirect("teacher_list")
    else:
        form = TeacherCreationForm()

    return render(request, "staffs/teacher_form.html", {"page_title": "Create Teacher", "form": form})


@login_required
@school_admin_required
def teacher_update(request, pk):
    school = request.user.school
    teacher = get_object_or_404(User, pk=pk, school=school, role="TEACHER")
    profile = get_object_or_404(StaffProfile, user=teacher, school=school)

    if request.method == "POST":
        form = TeacherCreationForm(request.POST, request.FILES, instance=teacher)
        if form.is_valid():
            teacher_obj = form.save(commit=False)
            teacher_obj.school = school
            teacher_obj.role = "TEACHER"
            if form.cleaned_data.get("password"):
                teacher_obj.set_password(form.cleaned_data["password"])
            teacher_obj.save()

            profile.staff_id = form.cleaned_data["staff_id"]
            profile.designation = form.cleaned_data.get("designation")
            profile.qualification = form.cleaned_data.get("qualification")
            profile.date_joined = form.cleaned_data.get("date_joined")
            profile.save()

            messages.success(request, "Teacher updated successfully.")
            return redirect("teacher_list")
    else:
        initial = {
            "staff_id": profile.staff_id,
            "designation": profile.designation,
            "qualification": profile.qualification,
            "date_joined": profile.date_joined,
        }
        form = TeacherCreationForm(instance=teacher, initial=initial)

    return render(request, "staffs/teacher_form.html", {"page_title": "Edit Teacher", "form": form})


@login_required
@school_admin_required
def teacher_delete(request, pk):
    school = request.user.school
    teacher = get_object_or_404(User, pk=pk, school=school, role="TEACHER")
    if request.method == "POST":
        teacher.delete()
        messages.success(request, "Teacher deleted successfully.")
        return redirect("teacher_list")
    return render(request, "includes/confirm_delete.html", {
        "object": teacher,
        "page_title": "Delete Teacher",
        "cancel_url": "/staffs/teachers/",
    })


@login_required
@school_admin_required
def allocation_list(request):
    school = request.user.school
    allocations = TeacherSubjectAllocation.objects.filter(school=school).select_related(
        "teacher", "school_class", "subject", "session", "term"
    )
    return render(request, "staffs/allocation_list.html", {"page_title": "Teaching Allocations", "allocations": allocations})


@login_required
@school_admin_required
def allocation_create(request):
    school = request.user.school
    if request.method == "POST":
        form = TeacherAllocationForm(request.POST, school=school)
        if form.is_valid():
            allocation = form.save(commit=False)
            allocation.school = school
            allocation.created_by = request.user
            allocation.save()
            messages.success(request, "Teaching allocation created successfully.")
            return redirect("allocation_list")
    else:
        initial = {}

        # Get from URL
        class_id = request.GET.get("class")
        subject_id = request.GET.get("subject")

        if class_id:
            initial["school_class"] = class_id

        if subject_id:
            initial["subject"] = subject_id

        form = TeacherAllocationForm(school=school, initial=initial)

    return render(request, "staffs/allocation_form.html", {"page_title": "Assign Teacher to Subject/Class", "form": form})


@login_required
@school_admin_required
def allocation_update(request, pk):
    school = request.user.school
    allocation = get_object_or_404(TeacherSubjectAllocation, pk=pk, school=school)
    if request.method == "POST":
        form = TeacherAllocationForm(request.POST, instance=allocation, school=school)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.school = school
            obj.save()
            messages.success(request, "Teaching allocation updated successfully.")
            return redirect("allocation_list")
    else:
        form = TeacherAllocationForm(instance=allocation, school=school)

    return render(request, "staffs/allocation_form.html", {"page_title": "Edit Teaching Allocation", "form": form})


@login_required
@school_admin_required
def allocation_delete(request, pk):
    school = request.user.school
    allocation = get_object_or_404(TeacherSubjectAllocation, pk=pk, school=school)
    if request.method == "POST":
        allocation.delete()
        messages.success(request, "Teaching allocation deleted successfully.")
        return redirect("allocation_list")
    return render(request, "includes/confirm_delete.html", {
        "object": allocation,
        "page_title": "Delete Teaching Allocation",
        "cancel_url": "/staffs/allocations/",
    })


@login_required
@school_admin_required
def allocation_matrix(request):
    school = request.user.school

    classes = SchoolClass.objects.filter(
        school=school,
        is_active=True
    ).order_by("position_order", "name")

    subjects = Subject.objects.filter(
        school=school,
        is_active=True
    ).order_by("name")

    # 🔥 NEW: Get selected filters
    session_id = request.GET.get("session")
    term_id = request.GET.get("term")

    allocations = TeacherSubjectAllocation.objects.filter(
        school=school,
        is_active=True
    ).select_related("teacher", "school_class", "subject", "session", "term")

    # Apply filters if selected
    if session_id:
        allocations = allocations.filter(session_id=session_id)

    if term_id:
        allocations = allocations.filter(term_id=term_id)

    # Build matrix
    matrix = {}

    for cls in classes:
        matrix[cls.id] = {}
        for subject in subjects:
            matrix[cls.id][subject.id] = None

    for alloc in allocations:
        matrix[alloc.school_class.id][alloc.subject.id] = alloc.teacher.get_full_name()

    # 🔥 NEW: send filters to template

    context = {
        "classes": classes,
        "subjects": subjects,
        "matrix": matrix,
        "sessions": AcademicSession.objects.filter(school=school, is_active=True).order_by("-name"),
        "terms": AcademicTerm.objects.filter(school=school, is_active=True).order_by("session__name", "name"),
        "selected_session": session_id,
        "selected_term": term_id,
        "page_title": "Allocation Matrix",
    }

    return render(request, "staffs/allocation_matrix.html", context)


class TeacherPasswordResetForm(forms.Form):
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "w-full rounded-xl border border-slate-300 px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:outline-none"
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "w-full rounded-xl border border-slate-300 px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:outline-none"
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("new_password")
        p2 = cleaned_data.get("confirm_password")

        if p1 and p2:
            if p1 != p2:
                raise forms.ValidationError("Passwords do not match.")

        return cleaned_data


@login_required
@school_admin_required
def teacher_reset_password(request, pk):
    school = request.user.school
    teacher = get_object_or_404(User, pk=pk, school=school, role="TEACHER")

    if request.method == "POST":
        form = TeacherPasswordResetForm(request.POST)

        if form.is_valid():
            teacher.set_password(form.cleaned_data["new_password"])
            teacher.save(update_fields=["password"])

            messages.success(request, "Teacher password reset successfully.")
            return redirect("teacher_list")
    else:
        form = TeacherPasswordResetForm()

    return render(request, "staffs/teacher_reset_password.html", {
        "teacher": teacher,
        "form": form,
        "page_title": "Reset Teacher Password"
    })


@login_required
@school_admin_required
def available_subjects_for_teacher(request):
    school = request.user.school

    teacher_id = request.GET.get("teacher_id")
    class_id = request.GET.get("class_id")
    session_id = request.GET.get("session_id")
    term_id = request.GET.get("term_id")

    if not all([teacher_id, class_id, session_id, term_id]):
        return JsonResponse({"subjects": []})

    # Get already assigned subject IDs
    assigned_subject_ids = TeacherSubjectAllocation.objects.filter(
        school=school,
        teacher_id=teacher_id,
        school_class_id=class_id,
        session_id=session_id,
        term_id=term_id,
    ).values_list("subject_id", flat=True)

    # Get available subjects
    subjects = Subject.objects.filter(
        school=school,
        is_active=True
    ).exclude(
        id__in=assigned_subject_ids
    ).order_by("name")

    data = [
        {"id": s.id, "name": s.name}
        for s in subjects
    ]

    return JsonResponse({"subjects": data})