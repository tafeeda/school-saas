from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django import forms
from django.shortcuts import get_object_or_404, redirect, render
from core.decorators import school_admin_required
from cbt.models import CBTAttempt
from .forms import StudentForm, StudentMovementForm
from .models import Student, StudentClassHistory
from academics.models import SchoolClass
from results.models import ResultSheet, SubjectResult
from django.db.models import Avg
import pandas as pd
from django.contrib.auth.models import User
import json
from django.contrib.auth import get_user_model
from django.utils.text import slugify

User = get_user_model()


class StudentPasswordResetForm(forms.Form):
    new_password = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={
            "class": "w-full rounded-xl border border-slate-300 px-4 py-3"
        })
    )
    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            "class": "w-full rounded-xl border border-slate-300 px-4 py-3"
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and confirm_password:
            if new_password != confirm_password:
                raise forms.ValidationError("Passwords do not match.")

            validate_password(new_password)

        return cleaned_data


@login_required
@school_admin_required
def student_list(request):
    school = request.user.school
    students = Student.objects.filter(school=school).select_related("current_class", "current_session").order_by("surname", "first_name")
    return render(request, "students/student_list.html", {"page_title": "Students", "students": students})



def create_student_login_if_missing(student):
    if student.user:
        return student.user

    raw_admission = student.admission_number or f"student-{student.id}"
    clean_admission = slugify(raw_admission)

    base_username = f"student-{student.school.id}-{clean_admission}"
    username = base_username
    counter = 1

    while User.objects.filter(username=username).exists():
        username = f"{base_username}-{counter}"
        counter += 1

    user = User.objects.create_user(
        username=username,
        password=raw_admission,
    )

    user.role = "STUDENT"
    user.school = student.school
    user.save(update_fields=["role", "school"])

    student.user = user
    student.save(update_fields=["user"])

    return user



@login_required
@school_admin_required
def student_create(request):
    school = request.user.school
    if request.method == "POST":
        form = StudentForm(request.POST, request.FILES, school=school)
        if form.is_valid():
            student = form.save(commit=False)
            student.school = school
            student.created_by = request.user
            student.save()

            login_user = student.user

            messages.success(
                request,
                f"Student created successfully. Login Username: {login_user.username if login_user else 'Not created'}"
            )
            return redirect("student_list")
    else:
        form = StudentForm(school=school)

    return render(request, "students/student_form.html", {"page_title": "Create Student", "form": form})

@login_required
@school_admin_required
def student_update(request, pk):
    school = request.user.school
    student = get_object_or_404(Student, pk=pk, school=school)
    if request.method == "POST":
        form = StudentForm(request.POST, request.FILES, instance=student, school=school)
        if form.is_valid():
            student_obj = form.save(commit=False)
            student_obj.school = school
            student_obj.save()
            messages.success(request, "Student updated successfully.")
            return redirect("student_list")
    else:
        form = StudentForm(instance=student, school=school)

    return render(request, "students/student_form.html", {"page_title": "Edit Student", "form": form})


@login_required
@school_admin_required
def student_delete(request, pk):
    school = request.user.school
    student = get_object_or_404(Student, pk=pk, school=school)
    if request.method == "POST":
        student.delete()
        messages.success(request, "Student deleted successfully.")
        return redirect("student_list")
    return render(request, "includes/confirm_delete.html", {
        "object": student,
        "page_title": "Delete Student",
        "cancel_url": "/students/",
    })


@login_required
@school_admin_required
def student_detail(request, pk):
    school = request.user.school
    student = get_object_or_404(
        Student.objects.select_related("current_class", "current_session"),
        pk=pk,
        school=school,
    )
    return render(request, "students/student_detail.html", {"page_title": "Student Profile", "student": student})


@login_required
@school_admin_required
def student_move(request, pk):
    school = request.user.school
    student = get_object_or_404(Student, pk=pk, school=school)

    if request.method == "POST":
        form = StudentMovementForm(request.POST, school=school)
        if form.is_valid():
            old_class = student.current_class
            new_class = form.cleaned_data["new_class"]

            StudentClassHistory.objects.create(
                school=school,
                student=student,
                old_class=old_class,
                new_class=new_class,
                movement_type=form.cleaned_data["movement_type"],
                movement_date=form.cleaned_data["movement_date"],
                reason=form.cleaned_data.get("reason"),
                created_by=request.user,
            )

            student.current_class = new_class
            student.save(update_fields=["current_class"])

            messages.success(request, "Student movement recorded successfully.")
            return redirect("student_detail", pk=student.pk)
    else:
        form = StudentMovementForm(school=school)

    return render(
        request,
        "students/student_move_form.html",
        {
            "page_title": "Move Student",
            "student": student,
            "form": form,
        },
    )


@login_required
@school_admin_required
def student_history(request, pk):
    school = request.user.school
    student = get_object_or_404(Student, pk=pk, school=school)

    history = student.class_history.select_related(
        "old_class",
        "new_class",
    ).order_by("-movement_date", "-created_at")

    return render(
        request,
        "students/student_history.html",
        {
            "page_title": "Student Movement History",
            "student": student,
            "history": history,
        },
    )


@login_required
@school_admin_required
def bulk_student_move(request):
    school = request.user.school
    classes = SchoolClass.objects.filter(
        school=school,
        is_active=True,
    ).order_by("position_order", "name")

    students = Student.objects.none()

    selected_class_id = request.GET.get("class_id") or request.POST.get("class_id")
    if selected_class_id:
        students = Student.objects.filter(
            school=school,
            current_class_id=selected_class_id,
            is_active=True,
        ).order_by("surname", "first_name")

    if request.method == "POST":
        student_ids = request.POST.getlist("student_ids")
        new_class_id = request.POST.get("new_class")
        movement_type = request.POST.get("movement_type")
        movement_date = request.POST.get("movement_date")
        reason = request.POST.get("reason")

        if not student_ids:
            messages.error(request, "Please select at least one student.")
            return redirect(f"{request.path}?class_id={selected_class_id}")

        if not new_class_id:
            messages.error(request, "Please select the new class.")
            return redirect(f"{request.path}?class_id={selected_class_id}")

        new_class = get_object_or_404(SchoolClass, pk=new_class_id, school=school)

        selected_students = Student.objects.filter(
            school=school,
            id__in=student_ids,
            is_active=True,
        )

        moved_count = 0

        for student in selected_students:
            old_class = student.current_class

            StudentClassHistory.objects.create(
                school=school,
                student=student,
                old_class=old_class,
                new_class=new_class,
                movement_type=movement_type,
                movement_date=movement_date,
                reason=reason,
                created_by=request.user,
            )

            student.current_class = new_class
            student.save(update_fields=["current_class"])
            moved_count += 1

        messages.success(request, f"{moved_count} student(s) moved successfully.")
        return redirect("student_list")

    return render(
        request,
        "students/bulk_student_move.html",
        {
            "page_title": "Bulk Student Movement",
            "classes": classes,
            "students": students,
            "selected_class_id": selected_class_id,
        },
    )


@login_required
def student_dashboard(request):
    student = getattr(request.user, "student_profile", None)

    if not student:
        messages.error(request, "Student profile not found.")
        return redirect("dashboard_redirect")

    return render(
        request,
        "students/student_dashboard.html",
        {
            "page_title": "Student Dashboard",
            "student": student,
        },
    )


@login_required
def student_results(request):
    student = getattr(request.user, "student_profile", None)

    if not student:
        messages.error(request, "Student profile not found.")
        return redirect("dashboard_redirect")

    result_sheets = ResultSheet.objects.filter(
        student=student,
        school=student.school,
        is_published=True,
    ).order_by("-session__name", "-term__name")

    latest_result = result_sheets.first()

    return render(
        request,
        "students/student_results.html",
        {
            "student": student,
            "result_sheets": result_sheets,
            "latest_result": latest_result,
        },
    )



@login_required
def student_cbt_history(request):
    student = getattr(request.user, "student_profile", None)

    if not student:
        messages.error(request, "Student profile not found.")
        return redirect("dashboard_redirect")

    attempts = CBTAttempt.objects.filter(
        student=student,
        exam__school=student.school,
        submitted_at__isnull=False,
    ).select_related("exam").order_by("-submitted_at")

    return render(
        request,
        "students/student_cbt_history.html",
        {
            "student": student,
            "attempts": attempts,
        },
    )



@login_required
def student_result_download_pdf(request, result_id):
    student = getattr(request.user, "student_profile", None)

    if not student:
        messages.error(request, "Student profile not found.")
        return redirect("dashboard_redirect")

    result = get_object_or_404(
        ResultSheet,
        pk=result_id,
        student=student,
        school=student.school,
        is_published=True,
    )

    return redirect("result_sheet_download_pdf", pk=result.id)




@login_required
def student_analytics(request):
    student = getattr(request.user, "student_profile", None)

    if not student:
        messages.error(request, "Student profile not found.")
        return redirect("dashboard_redirect")

    sheets = ResultSheet.objects.filter(
        student=student,
        school=student.school,
        is_published=True,
        is_active=True,
    ).select_related("session", "term")

    # 📈 Trend (term/session performance)
    trend_labels = []
    trend_scores = []

    for sheet in sheets.order_by("session__name", "term__name"):
        trend_labels.append(f"{sheet.session.name} - {sheet.term.name}")
        trend_scores.append(float(sheet.average_score or 0))

    # 📊 Subject Performance
    subject_stats = (
        SubjectResult.objects.filter(result_sheet__in=sheets)
        .values("subject__name")
        .annotate(avg_score=Avg("total_score"))
        .order_by("-avg_score")
    )

    subject_labels = [item["subject__name"] for item in subject_stats]
    subject_scores = [float(item["avg_score"] or 0) for item in subject_stats]

    # 🔝 Top subjects
    top_subjects = subject_stats[:5]

    # ⚠️ Weak subjects
    weak_subjects = subject_stats.order_by("avg_score")[:5]

    ai_insights = generate_student_insight(
        student,
        trend_scores,
        list(top_subjects),
        list(weak_subjects),
    )

    return render(
        request,
        "students/student_analytics.html",
        {
            "student": student,
            "trend_labels": json.dumps(trend_labels),
            "trend_scores": json.dumps(trend_scores),
            "subject_labels": json.dumps(subject_labels),
            "subject_scores": json.dumps(subject_scores),
            "top_subjects": top_subjects,
            "weak_subjects": weak_subjects,
            "ai_insights": ai_insights,
        },
    )


def generate_student_insight(student, trend_scores, top_subjects, weak_subjects):
    insights = []

    if trend_scores:
        latest_score = trend_scores[-1]

        if len(trend_scores) >= 2:
            previous_score = trend_scores[-2]

            if latest_score > previous_score:
                insights.append("Your performance is improving. Keep up the good work.")
            elif latest_score < previous_score:
                insights.append("Your latest performance dropped slightly. Try to revise weak areas before the next assessment.")
            else:
                insights.append("Your performance is stable. Push harder to improve your next result.")
        else:
            insights.append("This is your first available performance record. Keep building from here.")

        if latest_score >= 80:
            insights.append("Excellent overall performance. Maintain your study routine.")
        elif latest_score >= 60:
            insights.append("Good performance. With more consistency, you can move into the excellent range.")
        elif latest_score >= 50:
            insights.append("Fair performance. Focus more on your weak subjects.")
        else:
            insights.append("You need serious improvement. Create a study plan and ask your teachers for support.")

    if top_subjects:
        best = top_subjects[0]
        insights.append(f"Your strongest subject appears to be {best['subject__name']}.")

    if weak_subjects:
        weakest = weak_subjects[0]
        insights.append(f"You should pay more attention to {weakest['subject__name']}.")

    return insights



@login_required
@school_admin_required
def student_login_slips(request):
    school = request.user.school

    classes = SchoolClass.objects.filter(
        school=school,
        is_active=True,
    ).order_by("position_order", "name")

    selected_class_id = request.GET.get("class_id")

    students = Student.objects.filter(
        school=school,
        is_active=True,
        user__isnull=False,
    ).select_related("user", "current_class").order_by("surname", "first_name")

    if selected_class_id:
        students = students.filter(current_class_id=selected_class_id)

    return render(
        request,
        "students/student_login_slips.html",
        {
            "page_title": "Student Login Slips",
            "classes": classes,
            "students": students,
            "selected_class_id": selected_class_id,
        },
    )




@login_required
def student_academic_info(request):
    student = getattr(request.user, "student_profile", None)

    if not student:
        messages.error(request, "Student profile not found.")
        return redirect("dashboard_redirect")

    return render(
        request,
        "students/student_academic_info.html",
        {
            "page_title": "My Academic Info",
            "student": student,
        },
    )


@login_required
@school_admin_required
def student_reset_password(request, pk):
    school = request.user.school
    student = get_object_or_404(Student, pk=pk, school=school)

    if not student.user:
        messages.error(request, "This student does not have a login account.")
        return redirect("student_detail", pk=student.pk)

    if request.method == "POST":
        form = StudentPasswordResetForm(request.POST)

        if form.is_valid():
            user = student.user

            user.set_password(form.cleaned_data["new_password"])

            # ✅ ENSURE ACCOUNT IS VALID EVERY TIME
            user.role = "STUDENT"
            user.school = student.school
            user.is_active = True

            user.save(update_fields=["password", "role", "school", "is_active"])

            messages.success(
                request,
                f"Password reset successfully for {student.full_name}. Username remains: {student.user.username}"
            )
            return redirect("student_detail", pk=student.pk)
    else:
        form = StudentPasswordResetForm()

    return render(
        request,
        "students/student_reset_password.html",
        {
            "page_title": "Reset Student Password",
            "student": student,
            "form": form,
        },
    )




@login_required
@school_admin_required
def bulk_student_upload(request):
    if request.method == "POST":
        file = request.FILES.get("file")

        if not file:
            messages.error(request, "Please upload a file.")
            return redirect("bulk_student_upload")

        try:
            if file.name.endswith(".csv"):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)

            created = 0
            errors = []

            for index, row in df.iterrows():
                try:
                    admission_number = str(row.get("admission_number")).strip()

                    if StudentProfile.objects.filter(
                        admission_number=admission_number,
                        school=request.user.school
                    ).exists():
                        continue

                    class_name = str(row.get("class")).strip()

                    school_class = SchoolClass.objects.filter(
                        school=request.user.school,
                        name__iexact=class_name,
                        is_active=True,
                    ).first()

                    if not school_class:
                        errors.append(f"Row {index + 2}: Class '{class_name}' was not found.")
                        continue

                    student = Student.objects.create(
                        school=request.user.school,
                        admission_number=admission_number,
                        surname=str(row.get("surname")).strip(),
                        first_name=str(row.get("first_name")).strip(),
                        other_name=str(row.get("other_name") or "").strip(),
                        gender=str(row.get("gender")).strip().upper(),
                        current_class=school_class,
                    )

                    # Optional login creation
                    username = row.get("username")
                    password = row.get("password")

                    if username and password:
                        user = User.objects.create_user(
                            username=username,
                            password=password
                        )
                        user.role = "STUDENT"
                        user.school = request.user.school
                        user.save()

                        student.user = user
                        student.save()

                    created += 1

                except Exception as e:
                    errors.append(f"Row {index + 1}: {str(e)}")

            messages.success(request, f"{created} students uploaded successfully.")

            if errors:
                messages.warning(request, f"Some rows failed: {errors[:5]}")

            return redirect("student_list")

        except Exception as e:
            messages.error(request, f"Invalid file: {str(e)}")
            return redirect("bulk_student_upload")

    return render(request, "students/bulk_upload.html")



import pandas as pd
from django.http import HttpResponse

@login_required
@school_admin_required
def download_student_template(request):
    data = [{
        "admission_number": "IMAC001",
        "surname": "Ahmed",
        "first_name": "Ali",
        "other_name": "",
        "gender": "Male",
        "class": "JSS1A",
        "username": "ali01",
        "password": "123456"
    }]

    df = pd.DataFrame(data)

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="student_upload_template.xlsx"'

    df.to_excel(response, index=False)

    return response



@login_required
@school_admin_required
def student_create_login_account(request, pk):
    school = request.user.school
    student = get_object_or_404(Student, pk=pk, school=school)

    if student.user:
        messages.warning(request, "This student already has a login account.")
        return redirect("student_detail", pk=student.pk)

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        User = get_user_model()

        if not username or not password or not confirm_password:
            messages.error(request, "All login fields are required.")
            return redirect("student_create_login_account", pk=student.pk)

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("student_create_login_account", pk=student.pk)

        if User.objects.filter(username=username).exists():
            messages.error(request, "This username already exists.")
            return redirect("student_create_login_account", pk=student.pk)

        user = User.objects.create_user(username=username, password=password)
        user.role = "STUDENT"
        user.school = school
        user.is_active = True
        user.must_change_password = True
        user.save(update_fields=["role", "school", "is_active", "must_change_password"])

        student.user = user
        student.portal_initial_password = password
        student.save(update_fields=["user", "portal_initial_password"])

        messages.success(request, f"Login account created successfully. Username: {username}")
        return redirect("student_detail", pk=student.pk)

    return render(request, "students/student_create_login_account.html", {
        "page_title": "Create Student Login Account",
        "student": student,
    })