from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from staffs.models import TeacherSubjectAllocation

from .forms import LessonNoteForm
from .models import LessonNote


@login_required
def lesson_note_list(request):
    if request.user.role == "SUPER_ADMIN":
        notes = LessonNote.objects.select_related(
            "school", "school_class", "subject", "session", "term"
        ).order_by("-created_at")

    elif request.user.role == "SCHOOL_ADMIN":
        notes = LessonNote.objects.filter(
            school=request.user.school
        ).select_related(
            "school", "school_class", "subject", "session", "term"
        ).order_by("-created_at")

    elif request.user.role == "TEACHER":
        allocations = TeacherSubjectAllocation.objects.filter(
            school=request.user.school,
            teacher=request.user,
            is_active=True,
        ).values("school_class_id", "subject_id")

        class_ids = [a["school_class_id"] for a in allocations]
        subject_ids = [a["subject_id"] for a in allocations]

        notes = LessonNote.objects.filter(
            school=request.user.school,
            school_class_id__in=class_ids,
            subject_id__in=subject_ids,
            is_active=True,
            status="PUBLISHED",
        ).select_related(
            "school", "school_class", "subject", "session", "term"
        ).order_by("-created_at")

    else:
        return HttpResponseForbidden("You are not allowed to view this page.")

    return render(
        request,
        "lessons/lesson_note_list.html",
        {
            "page_title": "Lesson Notes",
            "notes": notes,
        },
    )


@login_required
def lesson_note_create(request):
    if request.user.role not in ["SUPER_ADMIN", "SCHOOL_ADMIN"]:
        return HttpResponseForbidden("You are not allowed to create lesson notes.")

    if request.method == "POST":
        form = LessonNoteForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            note = form.save(commit=False)

            if request.user.role == "SCHOOL_ADMIN":
                note.school = request.user.school

            note.created_by = request.user
            note.save()

            messages.success(request, "Lesson note uploaded successfully.")
            return redirect("lesson_note_list")
    else:
        form = LessonNoteForm(user=request.user)

    return render(
        request,
        "lessons/lesson_note_form.html",
        {
            "page_title": "Upload Lesson Note",
            "form": form,
        },
    )


@login_required
def lesson_note_update(request, pk):
    note = get_object_or_404(LessonNote, pk=pk)

    if request.user.role == "SUPER_ADMIN":
        pass
    elif request.user.role == "SCHOOL_ADMIN":
        if note.school != request.user.school:
            return HttpResponseForbidden("Not allowed.")
    else:
        return HttpResponseForbidden("Not allowed.")

    if request.method == "POST":
        form = LessonNoteForm(request.POST, request.FILES, instance=note, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Lesson note updated successfully.")
            return redirect("lesson_note_detail", pk=note.pk)
    else:
        form = LessonNoteForm(instance=note, user=request.user)

    return render(
        request,
        "lessons/lesson_note_form.html",
        {
            "page_title": "Edit Lesson Note",
            "form": form,
        },
    )


@login_required
def lesson_note_delete(request, pk):
    note = get_object_or_404(LessonNote, pk=pk)

    if request.user.role == "SUPER_ADMIN":
        pass
    elif request.user.role == "SCHOOL_ADMIN":
        if note.school != request.user.school:
            return HttpResponseForbidden("Not allowed.")
    else:
        return HttpResponseForbidden("Not allowed.")

    if request.method == "POST":
        note.delete()
        messages.success(request, "Lesson note deleted successfully.")
        return redirect("lesson_note_list")

    return render(
        request,
        "lessons/lesson_note_confirm_delete.html",
        {"note": note},
    )


@login_required
def lesson_note_toggle_status(request, pk):
    note = get_object_or_404(LessonNote, pk=pk)

    if request.user.role == "SUPER_ADMIN":
        pass
    elif request.user.role == "SCHOOL_ADMIN":
        if note.school != request.user.school:
            return HttpResponseForbidden("Not allowed.")
    else:
        return HttpResponseForbidden("Not allowed.")

    if note.status == "DRAFT":
        note.status = "PUBLISHED"
    elif note.status == "PUBLISHED":
        note.status = "ARCHIVED"
    else:
        note.status = "DRAFT"

    note.save()

    messages.success(request, f"Lesson note status changed to {note.get_status_display()}.")
    return redirect("lesson_note_detail", pk=note.pk)


@login_required
def lesson_note_detail(request, pk):
    if request.user.role == "SUPER_ADMIN":
        note = get_object_or_404(
            LessonNote.objects.select_related("school", "school_class", "subject", "session", "term"),
            pk=pk,
        )

    elif request.user.role == "SCHOOL_ADMIN":
        note = get_object_or_404(
            LessonNote.objects.select_related("school", "school_class", "subject", "session", "term"),
            pk=pk,
            school=request.user.school,
        )

    elif request.user.role == "TEACHER":
        note = get_object_or_404(
            LessonNote.objects.select_related("school", "school_class", "subject", "session", "term"),
            pk=pk,
            school=request.user.school,
            status="PUBLISHED",
            is_active=True,
        )

        allowed = TeacherSubjectAllocation.objects.filter(
            school=request.user.school,
            teacher=request.user,
            school_class=note.school_class,
            subject=note.subject,
            is_active=True,
        ).exists()

        if not allowed:
            return HttpResponseForbidden("You are not allowed to view this lesson note.")

    else:
        return HttpResponseForbidden("You are not allowed to view this page.")

    return render(
        request,
        "lessons/lesson_note_detail.html",
        {
            "page_title": "Lesson Note Detail",
            "note": note,
        },
    )