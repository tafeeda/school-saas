from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from core.decorators import school_admin_required
from .models import AcademicSession, AcademicTerm, SchoolClass, Subject, ClassSubject
from .forms import SessionForm, TermForm, ClassForm, SubjectForm, ClassSubjectForm


@login_required
@school_admin_required
def session_list(request):
    sessions = AcademicSession.objects.filter(school=request.user.school)
    return render(request, "academics/session_list.html", {"sessions": sessions, "page_title": "Sessions"})


@login_required
@school_admin_required
def session_create(request):
    form = SessionForm(request.POST or None)
    if form.is_valid():
        session = form.save(commit=False)
        session.school = request.user.school
        session.created_by = request.user
        if session.is_current:
            AcademicSession.objects.filter(school=request.user.school, is_current=True).update(is_current=False)
        session.save()
        messages.success(request, "Session created successfully.")
        return redirect("session_list")
    return render(request, "academics/session_form.html", {"form": form, "page_title": "Create Session"})


@login_required
@school_admin_required
def session_update(request, pk):
    session = get_object_or_404(AcademicSession, pk=pk, school=request.user.school)
    form = SessionForm(request.POST or None, instance=session)
    if form.is_valid():
        session_obj = form.save(commit=False)
        session_obj.school = request.user.school
        if session_obj.is_current:
            AcademicSession.objects.filter(school=request.user.school, is_current=True).exclude(pk=session.pk).update(is_current=False)
        session_obj.save()
        messages.success(request, "Session updated successfully.")
        return redirect("session_list")
    return render(request, "academics/session_form.html", {"form": form, "page_title": "Edit Session"})


@login_required
@school_admin_required
def session_delete(request, pk):
    session = get_object_or_404(AcademicSession, pk=pk, school=request.user.school)
    if request.method == "POST":
        session.delete()
        messages.success(request, "Session deleted successfully.")
        return redirect("session_list")
    return render(request, "includes/confirm_delete.html", {
        "object": session,
        "page_title": "Delete Session",
        "cancel_url": "/academics/sessions/",
    })


@login_required
@school_admin_required
def term_list(request):
    terms = AcademicTerm.objects.filter(school=request.user.school).select_related("session").order_by("-session__name", "name")
    return render(request, "academics/term_list.html", {"terms": terms, "page_title": "Terms"})


@login_required
@school_admin_required
def term_create(request):
    form = TermForm(request.POST or None)
    form.fields["session"].queryset = AcademicSession.objects.filter(school=request.user.school, is_active=True).order_by("-name")
    if form.is_valid():
        term = form.save(commit=False)
        term.school = request.user.school
        term.created_by = request.user
        if term.is_current:
            AcademicTerm.objects.filter(school=request.user.school, is_current=True).update(is_current=False)
        term.save()
        messages.success(request, "Term created successfully.")
        return redirect("term_list")
    return render(request, "academics/term_form.html", {"form": form, "page_title": "Create Term"})


@login_required
@school_admin_required
def term_update(request, pk):
    term = get_object_or_404(AcademicTerm, pk=pk, school=request.user.school)
    form = TermForm(request.POST or None, instance=term)
    form.fields["session"].queryset = AcademicSession.objects.filter(school=request.user.school, is_active=True).order_by("-name")
    if form.is_valid():
        term_obj = form.save(commit=False)
        term_obj.school = request.user.school
        if term_obj.is_current:
            AcademicTerm.objects.filter(school=request.user.school, is_current=True).exclude(pk=term.pk).update(is_current=False)
        term_obj.save()
        messages.success(request, "Term updated successfully.")
        return redirect("term_list")
    return render(request, "academics/term_form.html", {"form": form, "page_title": "Edit Term"})


@login_required
@school_admin_required
def term_delete(request, pk):
    term = get_object_or_404(AcademicTerm, pk=pk, school=request.user.school)
    if request.method == "POST":
        term.delete()
        messages.success(request, "Term deleted successfully.")
        return redirect("term_list")
    return render(request, "includes/confirm_delete.html", {
        "object": term,
        "page_title": "Delete Term",
        "cancel_url": "/academics/terms/",
    })


@login_required
@school_admin_required
def class_list(request):
    classes = SchoolClass.objects.filter(school=request.user.school)
    return render(request, "academics/class_list.html", {"classes": classes, "page_title": "Classes"})


@login_required
@school_admin_required
def class_create(request):
    form = ClassForm(request.POST or None)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.school = request.user.school
        obj.created_by = request.user
        obj.save()
        messages.success(request, "Class created successfully.")
        return redirect("class_list")
    return render(request, "academics/class_form.html", {"form": form, "page_title": "Create Class"})


@login_required
@school_admin_required
def class_update(request, pk):
    obj = get_object_or_404(SchoolClass, pk=pk, school=request.user.school)
    form = ClassForm(request.POST or None, instance=obj)
    if form.is_valid():
        edited = form.save(commit=False)
        edited.school = request.user.school
        edited.save()
        messages.success(request, "Class updated successfully.")
        return redirect("class_list")
    return render(request, "academics/class_form.html", {"form": form, "page_title": "Edit Class"})


@login_required
@school_admin_required
def class_delete(request, pk):
    obj = get_object_or_404(SchoolClass, pk=pk, school=request.user.school)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Class deleted successfully.")
        return redirect("class_list")
    return render(request, "includes/confirm_delete.html", {
        "object": obj,
        "page_title": "Delete Class",
        "cancel_url": "/academics/classes/",
    })


@login_required
@school_admin_required
def subject_list(request):
    subjects = Subject.objects.filter(school=request.user.school)
    return render(request, "academics/subject_list.html", {"subjects": subjects, "page_title": "Subjects"})


@login_required
@school_admin_required
def subject_create(request):
    form = SubjectForm(request.POST or None)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.school = request.user.school
        obj.created_by = request.user
        obj.save()
        messages.success(request, "Subject created successfully.")
        return redirect("subject_list")
    return render(request, "academics/subject_form.html", {"form": form, "page_title": "Create Subject"})


@login_required
@school_admin_required
def subject_update(request, pk):
    obj = get_object_or_404(Subject, pk=pk, school=request.user.school)
    form = SubjectForm(request.POST or None, instance=obj)
    if form.is_valid():
        edited = form.save(commit=False)
        edited.school = request.user.school
        edited.save()
        messages.success(request, "Subject updated successfully.")
        return redirect("subject_list")
    return render(request, "academics/subject_form.html", {"form": form, "page_title": "Edit Subject"})


@login_required
@school_admin_required
def subject_delete(request, pk):
    obj = get_object_or_404(Subject, pk=pk, school=request.user.school)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Subject deleted successfully.")
        return redirect("subject_list")
    return render(request, "includes/confirm_delete.html", {
        "object": obj,
        "page_title": "Delete Subject",
        "cancel_url": "/academics/subjects/",
    })


@login_required
@school_admin_required
def assign_subject(request):
    school = request.user.school

    if request.method == "POST":
        form = ClassSubjectForm(request.POST, school=school)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.school = school
            obj.created_by = request.user
            obj.save()
            messages.success(request, "Subject assigned to class successfully.")
            return redirect("class_list")
    else:
        form = ClassSubjectForm(school=school)

    return render(request, "academics/assign_subject.html", {
        "form": form,
        "page_title": "Assign Subject",
    })



@login_required
@school_admin_required
def available_subjects_for_class(request):
    school = request.user.school
    class_id = request.GET.get("class_id")

    assigned_subject_ids = ClassSubject.objects.filter(
        school=school,
        school_class_id=class_id,
    ).values_list("subject_id", flat=True)

    subjects = Subject.objects.filter(
        school=school,
        is_active=True,
    ).exclude(
        id__in=assigned_subject_ids
    ).order_by("name")

    data = [
        {"id": subject.id, "name": subject.name}
        for subject in subjects
    ]

    return JsonResponse({"subjects": data})