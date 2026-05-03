from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from .decorators import cbt_enabled_required
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from students.models import Student
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Avg, Count, Max, Min
import pandas as pd
from .forms import CBTExamForm, CBTQuestionForm, CBTBulkUploadForm, QuestionBankForm
import random
import csv
from django.http import HttpResponse
from decimal import Decimal
from results.models import ResultSheet, SubjectResult
from .models import CBTAttempt, CBTAnswer, CBTExam, CBTQuestion, CBTResultTransferLog, QuestionBank
from core.utils import user_is_super_admin
from schools.models import School
from academics.models import SchoolClass, Subject




def check_exam_access_rules(exam):
    now = timezone.now()

    if not exam.is_active:
        return False, "This exam is not active."

    if not exam.show_in_student_portal:
        return False, "This exam is not available in the student portal."

    if exam.start_datetime and now < exam.start_datetime:
        return False, f"This exam will open on {exam.start_datetime}."

    if exam.end_datetime and now > exam.end_datetime:
        return False, "This exam has closed."

    return True, ""


def finalize_cbt_attempt(attempt, *, auto_submitted=False, reason=""):
    questions = attempt.exam.questions.all()

    correct_count = attempt.answers.filter(is_correct=True).count()
    attempt.score = correct_count
    attempt.total = questions.count()
    attempt.submitted_at = timezone.now()
    attempt.was_auto_submitted = auto_submitted
    attempt.auto_submit_reason = reason if auto_submitted else ""
    attempt.save(update_fields=[
        "score",
        "total",
        "submitted_at",
        "was_auto_submitted",
        "auto_submit_reason",
    ])
    transfer_cbt_score_to_result(attempt)


@cbt_enabled_required
def cbt_dashboard(request):
    school = request.user.school
    exams = CBTExam.objects.filter(school=school).order_by("-created_at")[:5]

    return render(
        request,
        "cbt/dashboard.html",
        {
            "page_title": "CBT Dashboard",
            "exams": exams,
        },
    )


@cbt_enabled_required
def cbt_exam_list(request):
    school = request.user.school
    exams = CBTExam.objects.filter(school=school).order_by("-created_at")

    return render(
        request,
        "cbt/exam_list.html",
        {
            "page_title": "CBT Exams",
            "exams": exams,
        },
    )


@cbt_enabled_required
def cbt_exam_create(request):
    school = request.user.school

    if request.method == "POST":
        form = CBTExamForm(request.POST, school=school)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.school = school
            exam.total_questions = 0
            exam.save()

            messages.success(request, "CBT exam created successfully.")
            return redirect("cbt_exam_list")
    else:
        form = CBTExamForm(school=school)

    return render(
        request,
        "cbt/exam_form.html",
        {
            "page_title": "Create CBT Exam",
            "form": form,
        },
    )


@cbt_enabled_required
def cbt_exam_update(request, exam_id):
    school = request.user.school
    exam = get_object_or_404(CBTExam, pk=exam_id, school=school)

    if request.method == "POST":
        form = CBTExamForm(request.POST, instance=exam, school=school)
        if form.is_valid():
            form.save()
            messages.success(request, "CBT exam updated successfully.")
            return redirect("cbt_exam_list")
    else:
        form = CBTExamForm(instance=exam, school=school)

    return render(
        request,
        "cbt/exam_form.html",
        {
            "page_title": "Edit CBT Exam",
            "form": form,
            "exam": exam,
        },
    )


@cbt_enabled_required
def cbt_exam_delete(request, exam_id):
    school = request.user.school
    exam = get_object_or_404(CBTExam, pk=exam_id, school=school)

    if request.method == "POST":
        exam.delete()
        messages.success(request, "CBT exam deleted successfully.")
        return redirect("cbt_exam_list")

    return render(
        request,
        "cbt/exam_confirm_delete.html",
        {
            "page_title": "Delete CBT Exam",
            "exam": exam,
        },
    )


@cbt_enabled_required
def cbt_exam_toggle_status(request, exam_id):
    school = request.user.school
    exam = get_object_or_404(CBTExam, pk=exam_id, school=school)

    exam.is_active = not exam.is_active
    exam.save(update_fields=["is_active"])

    messages.success(
        request,
        f'CBT exam {"activated" if exam.is_active else "deactivated"} successfully.'
    )
    return redirect("cbt_exam_list")


@cbt_enabled_required
def cbt_question_update(request, question_id):
    school = request.user.school
    question = get_object_or_404(
        CBTQuestion.objects.select_related("exam"),
        pk=question_id,
        exam__school=school,
    )

    if request.method == "POST":
        form = CBTQuestionForm(request.POST, request.FILES, instance=question)
        if form.is_valid():
            form.save()
            messages.success(request, "Question updated successfully.")
            return redirect("cbt_question_list", exam_id=question.exam.id)
    else:
        form = CBTQuestionForm(instance=question)

    return render(
        request,
        "cbt/question_form.html",
        {
            "page_title": "Edit CBT Question",
            "exam": question.exam,
            "form": form,
            "question": question,
        },
    )


@cbt_enabled_required
def cbt_question_delete(request, question_id):
    school = request.user.school
    question = get_object_or_404(
        CBTQuestion.objects.select_related("exam"),
        pk=question_id,
        exam__school=school,
    )
    exam = question.exam

    if request.method == "POST":
        question.delete()
        exam.total_questions = exam.questions.count()
        exam.save(update_fields=["total_questions"])

        messages.success(request, "Question deleted successfully.")
        return redirect("cbt_question_list", exam_id=exam.id)

    return render(
        request,
        "cbt/question_confirm_delete.html",
        {
            "page_title": "Delete CBT Question",
            "question": question,
            "exam": exam,
        },
    )


@cbt_enabled_required
def cbt_question_list(request, exam_id):
    school = request.user.school
    exam = get_object_or_404(CBTExam, pk=exam_id, school=school)
    questions = exam.questions.all().order_by("id")

    return render(
        request,
        "cbt/question_list.html",
        {
            "page_title": "CBT Questions",
            "exam": exam,
            "questions": questions,
        },
    )


@cbt_enabled_required
def cbt_question_create(request, exam_id):
    school = request.user.school
    exam = get_object_or_404(CBTExam, pk=exam_id, school=school)

    if request.method == "POST":
        form = CBTQuestionForm(request.POST, request.FILES)
        if form.is_valid():
            question = form.save(commit=False)
            question.exam = exam
            question.save()

            exam.total_questions = exam.questions.count()
            exam.save(update_fields=["total_questions"])

            messages.success(request, "Question added successfully.")
            return redirect("cbt_question_list", exam_id=exam.id)
    else:
        form = CBTQuestionForm()

    return render(
        request,
        "cbt/question_form.html",
        {
            "page_title": "Add CBT Question",
            "exam": exam,
            "form": form,
        },
    )


@cbt_enabled_required
def cbt_analytics_dashboard(request):
    school = request.user.school

    attempts = CBTAttempt.objects.filter(
        exam__school=school,
        submitted_at__isnull=False,
    ).select_related("student", "exam")

    total_attempts = attempts.count()
    average_score = attempts.aggregate(avg=Avg("score"))["avg"] or 0
    highest_score = attempts.aggregate(max_score=Max("score"))["max_score"] or 0
    lowest_score = attempts.aggregate(min_score=Min("score"))["min_score"] or 0

    passed_attempts = 0
    for attempt in attempts:
        if attempt.total and ((attempt.score / attempt.total) * 100) >= 50:
            passed_attempts += 1

    pass_rate = 0
    if total_attempts:
        pass_rate = round((passed_attempts / total_attempts) * 100, 2)

    exam_stats = (
        CBTExam.objects.filter(school=school)
        .annotate(
            attempt_count=Count("cbtattempt"),
            average_score=Avg("cbtattempt__score"),
            highest_score=Max("cbtattempt__score"),
            lowest_score=Min("cbtattempt__score"),
        )
        .order_by("-created_at")
    )

    top_attempts = attempts.order_by("-score")[:10]

    return render(
        request,
        "cbt/analytics_dashboard.html",
        {
            "page_title": "CBT Analytics",
            "total_attempts": total_attempts,
            "average_score": round(average_score, 2),
            "highest_score": highest_score,
            "lowest_score": lowest_score,
            "pass_rate": pass_rate,
            "exam_stats": exam_stats,
            "top_attempts": top_attempts,
        },
    )


@cbt_enabled_required
def cbt_exam_attempts(request, exam_id):
    school = request.user.school
    exam = get_object_or_404(CBTExam, pk=exam_id, school=school)

    attempts = CBTAttempt.objects.filter(
        exam=exam,
    ).select_related(
        "student",
        "exam",
    ).order_by("-submitted_at", "-started_at")

    return render(
        request,
        "cbt/exam_attempts.html",
        {
            "page_title": "CBT Attempts",
            "exam": exam,
            "attempts": attempts,
        },
    )


@cbt_enabled_required
def cbt_attempt_detail(request, attempt_id):
    school = request.user.school

    attempt = get_object_or_404(
        CBTAttempt.objects.select_related("student", "exam"),
        pk=attempt_id,
        exam__school=school,
    )

    answers = attempt.answers.select_related("question").all()

    percentage = 0
    if attempt.total:
        percentage = round((attempt.score / attempt.total) * 100, 2)

    return render(
        request,
        "cbt/attempt_detail.html",
        {
            "page_title": "Attempt Detail",
            "attempt": attempt,
            "answers": answers,
            "percentage": percentage,
        },
    )


@login_required
@cbt_enabled_required
def student_cbt_exam_list(request):
    student = getattr(request.user, "student_profile", None)

    if not student:
        messages.error(request, "Student profile not found.")
        return redirect("dashboard_redirect")

    exams = CBTExam.objects.filter(
        school=student.school,
        school_class=student.current_class,
        is_active=True,
        show_in_student_portal=True,
    ).order_by("-created_at")

    return render(
        request,
        "cbt/student_exam_list.html",
        {
            "page_title": "Available CBT Exams",
            "exams": exams,
            "student": student,
        },
    )


@login_required
@cbt_enabled_required
def student_cbt_exam_start(request, exam_id):
    student = getattr(request.user, "student_profile", None)

    if not student:
        messages.error(request, "Student profile not found.")
        return redirect("dashboard_redirect")

    exam = get_object_or_404(
        CBTExam,
        pk=exam_id,
        school=student.school,
        school_class=student.current_class,
        is_active=True,
    )

    # PART 6 — Check exam access rules
    allowed, message = check_exam_access_rules(exam)
    if not allowed:
        messages.error(request, message)
        return redirect("student_cbt_exam_list")

    # PART 7 — Handle one attempt vs multiple attempts
    if exam.attempt_rule == "ONE":
        attempt, created = CBTAttempt.objects.get_or_create(
            student=student,
            exam=exam,
            defaults={"total": exam.questions.count()},
        )

        if attempt.submitted_at:
            messages.warning(request, "You have already submitted this exam.")
            return redirect("student_cbt_exam_result", attempt_id=attempt.id)

    else:
        attempt = CBTAttempt.objects.create(
            student=student,
            exam=exam,
            total=exam.questions.count(),
        )
        created = True

    if created or not attempt.question_order:
        question_ids = list(exam.questions.values_list("id", flat=True))

        if exam.school.shuffle_cbt_questions:
            random.shuffle(question_ids)

        attempt.question_order = question_ids
        attempt.total = len(question_ids)
        attempt.save(update_fields=["question_order", "total"])

    if created or not attempt.option_order:
        option_order = {}

        for question in exam.questions.all():
            options = ["A", "B", "C", "D"]

            if exam.school.shuffle_cbt_options:
                random.shuffle(options)

            option_order[str(question.id)] = options

        attempt.option_order = option_order
        attempt.save(update_fields=["option_order"])

    return redirect("student_cbt_take_exam", attempt_id=attempt.id)

@login_required
@cbt_enabled_required
def student_cbt_take_exam(request, attempt_id):
    student = getattr(request.user, "student_profile", None)

    if not student:
        messages.error(request, "Student profile not found.")
        return redirect("dashboard_redirect")

    attempt = get_object_or_404(
        CBTAttempt.objects.select_related("exam", "student"),
        pk=attempt_id,
        student=student,
    )

    if attempt.submitted_at:
        return redirect("student_cbt_exam_result", attempt_id=attempt.id)

    exam = attempt.exam
    if attempt.question_order:
        questions_map = {
            q.id: q for q in exam.questions.filter(id__in=attempt.question_order)
        }
        questions = [
            questions_map[qid]
            for qid in attempt.question_order
            if qid in questions_map
        ]
    else:
        questions = list(exam.questions.all().order_by("id"))

    end_time = attempt.started_at + timezone.timedelta(minutes=exam.duration_minutes)
    remaining_seconds = max(int((end_time - timezone.now()).total_seconds()), 0)

    if request.method == "POST":
        for question in questions:
            selected = request.POST.get(f"question_{question.id}")
            if selected:
                answer, _ = CBTAnswer.objects.get_or_create(
                    attempt=attempt,
                    question=question,
                    defaults={"selected_option": selected},
                )
                answer.selected_option = selected
                answer.is_correct = (selected == question.correct_option)
                answer.save()

        if "submit_exam" in request.POST or remaining_seconds <= 0:
            finalize_cbt_attempt(
                attempt,
                auto_submitted=(remaining_seconds <= 0),
                reason="Exam time elapsed." if remaining_seconds <= 0 else "",
            )

            messages.success(request, "Exam submitted successfully.")
            return redirect("student_cbt_exam_result", attempt_id=attempt.id)

        return redirect("student_cbt_take_exam", attempt_id=attempt.id)

    question_display_data = []

    for question in questions:
        order = attempt.option_order.get(str(question.id), ["A", "B", "C", "D"])

        option_map = {
            "A": question.option_a,
            "B": question.option_b,
            "C": question.option_c,
            "D": question.option_d,
        }

        display_labels = ["A", "B", "C", "D"]

        display_options = [
            {
                "key": option_key,          # real/original answer key for scoring
                "label": display_labels[index],  # displayed label only
                "text": option_map.get(option_key, ""),
            }
            for index, option_key in enumerate(order)
        ]

        question_display_data.append({
            "question": question,
            "display_options": display_options,
        })

    existing_answers = {
        answer.question_id: answer.selected_option
        for answer in attempt.answers.all()
    }

    return render(
        request,
        "cbt/student_take_exam.html",
        {
            "page_title": exam.title,
            "attempt": attempt,
            "exam": exam,
            "questions": questions,
            "question_display_data": question_display_data,
            "existing_answers": existing_answers,
            "remaining_seconds": remaining_seconds,
        },
    )


@login_required
@cbt_enabled_required
def student_cbt_exam_result(request, attempt_id):
    student = getattr(request.user, "student_profile", None)

    if not student:
        messages.error(request, "Student profile not found.")
        return redirect("dashboard_redirect")

    attempt = get_object_or_404(
        CBTAttempt.objects.select_related("exam", "student"),
        pk=attempt_id,
        student=student,
    )

    if not attempt.submitted_at:
        messages.warning(request, "You have not submitted this exam yet.")
        return redirect("student_cbt_take_exam", attempt_id=attempt.id)

    answers = attempt.answers.select_related("question")

    correct_count = 0
    wrong_count = 0
    unanswered_count = 0

    for answer in answers:
        if not answer.selected_option:
            unanswered_count += 1
        elif answer.selected_option == answer.question.correct_option:
            correct_count += 1
        else:
            wrong_count += 1

    total_questions = attempt.total

    percentage = round((correct_count / total_questions) * 100) if total_questions else 0

    if percentage >= 90:
        performance = "Excellent"
    elif percentage >= 70:
        performance = "Very Good"
    elif percentage >= 50:
        performance = "Good"
    else:
        performance = "Needs Improvement"

    return render(
        request,
        "cbt/student_exam_result.html",
        {
            "page_title": "CBT Result",
            "attempt": attempt,
            "percentage": percentage,
            "show_score": attempt.exam.school.show_cbt_score_immediately,
            "correct_count": correct_count,
            "wrong_count": wrong_count,
            "unanswered_count": unanswered_count,
            "performance": performance,
            "answers": answers,
        },
    )

@login_required
@cbt_enabled_required
@require_POST
def student_cbt_record_tab_switch(request, attempt_id):
    student = getattr(request.user, "student_profile", None)

    if not student:
        return JsonResponse({"status": "error", "message": "Student profile not found."}, status=400)

    attempt = get_object_or_404(CBTAttempt, pk=attempt_id, student=student)

    if attempt.submitted_at:
        return JsonResponse({"status": "submitted", "redirect_url": ""})

    attempt.tab_switch_count += 1
    attempt.save(update_fields=["tab_switch_count"])

    max_switches = 3
    if attempt.tab_switch_count >= max_switches:
        finalize_cbt_attempt(
            attempt,
            auto_submitted=True,
            reason="Too many tab switches detected.",
        )
        return JsonResponse({
            "status": "auto_submitted",
            "redirect_url": reverse("student_cbt_exam_result", args=[attempt.id]),
        })

    return JsonResponse({
        "status": "warning",
        "count": attempt.tab_switch_count,
        "remaining": max_switches - attempt.tab_switch_count,
    })


@login_required
@cbt_enabled_required
@require_POST
def student_cbt_force_submit(request, attempt_id):
    student = getattr(request.user, "student_profile", None)

    if not student:
        return JsonResponse({"status": "error", "message": "Student profile not found."}, status=400)

    attempt = get_object_or_404(CBTAttempt, pk=attempt_id, student=student)

    if attempt.submitted_at:
        return JsonResponse({
            "status": "submitted",
            "redirect_url": reverse("student_cbt_exam_result", args=[attempt.id]),
        })

    questions = attempt.exam.questions.all()
    for question in questions:
        selected = request.POST.get(f"question_{question.id}")
        if selected:
            answer, _ = CBTAnswer.objects.get_or_create(
                attempt=attempt,
                question=question,
                defaults={"selected_option": selected},
            )
            answer.selected_option = selected
            answer.is_correct = (selected == question.correct_option)
            answer.save()

    finalize_cbt_attempt(
        attempt,
        auto_submitted=True,
        reason="Exam time elapsed.",
    )

    return JsonResponse({
        "status": "submitted",
        "redirect_url": reverse("student_cbt_exam_result", args=[attempt.id]),
    })


@cbt_enabled_required
def cbt_bulk_upload_questions(request, exam_id):
    school = request.user.school
    exam = get_object_or_404(CBTExam, pk=exam_id, school=school)

    if request.method == "POST":
        form = CBTBulkUploadForm(request.POST, request.FILES)

        if form.is_valid():
            file = form.cleaned_data["file"]

            try:
                df = pd.read_excel(file)

                required_columns = [
                    "question",
                    "option_a",
                    "option_b",
                    "option_c",
                    "option_d",
                    "correct_option",
                ]

                for col in required_columns:
                    if col not in df.columns:
                        messages.error(request, f"Missing column: {col}")
                        return redirect("cbt_bulk_upload_questions", exam_id=exam.id)

                created_count = 0

                for _, row in df.iterrows():
                    CBTQuestion.objects.create(
                        exam=exam,
                        question_text=row["question"],
                        option_a=row["option_a"],
                        option_b=row["option_b"],
                        option_c=row["option_c"],
                        option_d=row["option_d"],
                        correct_option=row["correct_option"],
                    )
                    created_count += 1

                exam.total_questions = exam.questions.count()
                exam.save(update_fields=["total_questions"])

                messages.success(request, f"{created_count} questions uploaded successfully.")
                return redirect("cbt_question_list", exam_id=exam.id)

            except Exception as e:
                messages.error(request, f"Upload failed: {str(e)}")

    else:
        form = CBTBulkUploadForm()

    return render(
        request,
        "cbt/bulk_upload.html",
        {
            "page_title": "Bulk Upload Questions",
            "exam": exam,
            "form": form,
        },
    )


@cbt_enabled_required
def cbt_export_attempts_csv(request, exam_id):
    school = request.user.school
    exam = get_object_or_404(CBTExam, pk=exam_id, school=school)

    attempts = CBTAttempt.objects.filter(
        exam=exam,
        submitted_at__isnull=False,
    ).select_related("student")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{exam.title}_attempts.csv"'

    writer = csv.writer(response)

    writer.writerow([
        "Student Name",
        "Score",
        "Total",
        "Percentage",
        "Submitted At",
        "Auto Submitted",
        "Tab Switch Count",
    ])

    for attempt in attempts:
        percentage = 0
        if attempt.total:
            percentage = round((attempt.score / attempt.total) * 100, 2)

        writer.writerow([
            attempt.student.full_name,
            attempt.score,
            attempt.total,
            f"{percentage}%",
            attempt.submitted_at,
            "Yes" if attempt.was_auto_submitted else "No",
            attempt.tab_switch_count,
        ])

    return response


def transfer_cbt_score_to_result(attempt, force=False):
    exam = attempt.exam
    
    if attempt.result_transferred and not force:
        return

    if exam.transfer_to_result == "NONE":
        return

    if not attempt.submitted_at or not attempt.total:
        return

    try:
        result_sheet, _ = ResultSheet.objects.get_or_create(
            school=exam.school,
            student=attempt.student,
            school_class=exam.school_class,
            session=exam.session,
            term=exam.term,
        )

        subject_result, _ = SubjectResult.objects.get_or_create(
            result_sheet=result_sheet,
            subject=exam.subject,
            defaults={
                "ca_score": 0,
                "exam_score": 0,
            },
        )

        percentage = Decimal(attempt.score) / Decimal(attempt.total)
        converted_score = round(percentage * Decimal(exam.result_score_max), 2)

        if exam.transfer_to_result == "CA":
            subject_result.ca_score = converted_score
        elif exam.transfer_to_result == "EXAM":
            subject_result.exam_score = converted_score

        subject_result.total_score = subject_result.ca_score + subject_result.exam_score
        subject_result.save()

        # ✅ LOG SUCCESS
        CBTResultTransferLog.objects.create(
            school=exam.school,
            student=attempt.student,
            exam=exam,
            attempt=attempt,
            transfer_type=exam.transfer_to_result,
            raw_score=attempt.score,
            converted_score=converted_score,
            status="SUCCESS",
            message="Score transferred successfully",
        )

        attempt.result_transferred = True
        attempt.result_transferred_at = timezone.now()
        attempt.save(update_fields=["result_transferred", "result_transferred_at"])

    except Exception as e:
        # ❌ LOG FAILURE
        CBTResultTransferLog.objects.create(
            school=exam.school,
            student=attempt.student,
            exam=exam,
            attempt=attempt,
            transfer_type=exam.transfer_to_result,
            raw_score=attempt.score,
            converted_score=0,
            status="FAILED",
            message=str(e),
        )


@cbt_enabled_required
def cbt_retry_transfer(request, attempt_id):
    school = request.user.school

    attempt = get_object_or_404(
        CBTAttempt,
        pk=attempt_id,
        exam__school=school,
    )

    transfer_cbt_score_to_result(attempt, force=True)

    messages.success(request, "CBT result transfer retried successfully.")

    return redirect("cbt_attempt_detail", attempt_id=attempt.id)


@cbt_enabled_required
def question_bank_list(request):
    school = request.user.school

    questions = QuestionBank.objects.filter(
        school=school
    ).order_by("-created_at")

    return render(
        request,
        "cbt/question_bank_list.html",
        {
            "page_title": "Question Bank",
            "questions": questions,
        },
    )


@cbt_enabled_required
def question_bank_create(request):
    school = request.user.school

    if request.method == "POST":
        form = QuestionBankForm(request.POST, request.FILES, school=school)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.school = school
            obj.save()

            messages.success(request, "Question added to bank successfully.")
            return redirect("question_bank_list")
    else:
        form = QuestionBankForm(school=school)

    return render(
        request,
        "cbt/question_bank_form.html",
        {
            "page_title": "Add Question to Bank",
            "form": form,
        },
    )


@cbt_enabled_required
def question_bank_update(request, pk):
    school = request.user.school
    obj = get_object_or_404(QuestionBank, pk=pk, school=school)

    if request.method == "POST":
        form = QuestionBankForm(request.POST, request.FILES, instance=obj, school=school)
        if form.is_valid():
            form.save()
            messages.success(request, "Question updated successfully.")
            return redirect("question_bank_list")
    else:
        form = QuestionBankForm(instance=obj, school=school)

    return render(
        request,
        "cbt/question_bank_form.html",
        {
            "page_title": "Edit Question",
            "form": form,
            "question": obj,
        },
    )


@cbt_enabled_required
def question_bank_delete(request, pk):
    school = request.user.school
    obj = get_object_or_404(QuestionBank, pk=pk, school=school)

    if request.method == "POST":
        obj.delete()
        messages.success(request, "Question deleted successfully.")
        return redirect("question_bank_list")

    return render(
        request,
        "cbt/question_bank_confirm_delete.html",
        {
            "page_title": "Delete Question",
            "question": obj,
        },
    )



@cbt_enabled_required
def cbt_add_from_bank(request, exam_id):
    school = request.user.school
    exam = get_object_or_404(CBTExam, pk=exam_id, school=school)

    questions = QuestionBank.objects.filter(
        school=school,
        school_class=exam.school_class,
        subject=exam.subject,
        is_active=True,
    ).order_by("-created_at")

    already_added_ids = set(
        exam.question_bank_items.values_list("id", flat=True)
    )

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add_selected":
            selected_ids = request.POST.getlist("question_ids")

            if not selected_ids:
                messages.error(request, "Please select at least one question.")
                return redirect("cbt_add_from_bank", exam_id=exam.id)

            selected_questions = QuestionBank.objects.filter(
                id__in=selected_ids,
                school=school,
                school_class=exam.school_class,
                subject=exam.subject,
                is_active=True,
            ).exclude(id__in=already_added_ids)

            created_count = 0

            for bank_question in selected_questions:
                CBTQuestion.objects.create(
                    exam=exam,
                    question_text=bank_question.question_text,
                    question_image=bank_question.question_image,
                    option_a=bank_question.option_a,
                    option_b=bank_question.option_b,
                    option_c=bank_question.option_c,
                    option_d=bank_question.option_d,
                    correct_option=bank_question.correct_option,
                )

                exam.question_bank_items.add(bank_question)
                created_count += 1

            exam.total_questions = exam.questions.count()
            exam.save(update_fields=["total_questions"])

            if created_count:
                messages.success(request, f"{created_count} question(s) added from question bank.")
            else:
                messages.warning(request, "No new questions were added. They may already exist in this exam.")

            return redirect("cbt_question_list", exam_id=exam.id)

        if action == "random_generate":
            difficulty = request.POST.get("difficulty")
            number_of_questions = int(request.POST.get("number_of_questions") or 0)

            if number_of_questions <= 0:
                messages.error(request, "Enter a valid number of questions.")
                return redirect("cbt_add_from_bank", exam_id=exam.id)

            pool = questions.exclude(id__in=already_added_ids)

            if difficulty:
                pool = pool.filter(difficulty=difficulty)

            available_count = pool.count()

            if available_count == 0:
                messages.error(request, "No available questions found for this random selection.")
                return redirect("cbt_add_from_bank", exam_id=exam.id)

            selected_questions = list(pool.order_by("?")[:number_of_questions])

            created_count = 0

            for bank_question in selected_questions:
                CBTQuestion.objects.create(
                    exam=exam,
                    question_text=bank_question.question_text,
                    question_image=bank_question.question_image,
                    option_a=bank_question.option_a,
                    option_b=bank_question.option_b,
                    option_c=bank_question.option_c,
                    option_d=bank_question.option_d,
                    correct_option=bank_question.correct_option,
                )

                exam.question_bank_items.add(bank_question)
                created_count += 1

            exam.total_questions = exam.questions.count()
            exam.save(update_fields=["total_questions"])

            messages.success(request, f"{created_count} random question(s) added to exam.")
            return redirect("cbt_question_list", exam_id=exam.id)

    return render(
        request,
        "cbt/add_from_bank.html",
        {
            "page_title": "Add Questions From Bank",
            "exam": exam,
            "questions": questions,
            "already_added_ids": already_added_ids,
        },
    )



@login_required
def super_admin_transfer_question_bank(request):
    if not user_is_super_admin(request.user):
        messages.error(request, "You are not allowed to access this page.")
        return redirect("dashboard_redirect")

    schools = School.objects.filter(is_active=True).order_by("name")

    source_school_id = request.POST.get("source_school") if request.method == "POST" else request.GET.get("source_school")
    destination_school_id = request.POST.get("destination_school") if request.method == "POST" else request.GET.get("destination_school")

    source_classes = SchoolClass.objects.filter(school_id=source_school_id, is_active=True).order_by("position_order", "name") if source_school_id else SchoolClass.objects.none()
    source_subjects = Subject.objects.filter(school_id=source_school_id, is_active=True).order_by("name") if source_school_id else Subject.objects.none()

    destination_classes = SchoolClass.objects.filter(school_id=destination_school_id, is_active=True).order_by("position_order", "name") if destination_school_id else SchoolClass.objects.none()
    destination_subjects = Subject.objects.filter(school_id=destination_school_id, is_active=True).order_by("name") if destination_school_id else Subject.objects.none()

    if request.method == "POST":
        source_class_id = request.POST.get("source_class")
        source_subject_id = request.POST.get("source_subject")
        destination_class_id = request.POST.get("destination_class")
        destination_subject_id = request.POST.get("destination_subject")

        if not all([source_school_id, source_class_id, source_subject_id, destination_school_id, destination_class_id, destination_subject_id]):
            messages.error(request, "Please complete all fields.")
            return redirect("super_admin_transfer_question_bank")

        if source_school_id == destination_school_id:
            messages.error(request, "Source school and destination school cannot be the same.")
            return redirect("super_admin_transfer_question_bank")

        destination_school = get_object_or_404(School, id=destination_school_id, is_active=True)
        destination_class = get_object_or_404(SchoolClass, id=destination_class_id, school=destination_school, is_active=True)
        destination_subject = get_object_or_404(Subject, id=destination_subject_id, school=destination_school, is_active=True)

        source_questions = QuestionBank.objects.filter(
            school_id=source_school_id,
            school_class_id=source_class_id,
            subject_id=source_subject_id,
            is_active=True,
        )

        if not source_questions.exists():
            messages.error(request, "No active questions found for the selected source school, class, and subject.")
            return redirect("super_admin_transfer_question_bank")

        copied_count = 0
        skipped_count = 0

        for question in source_questions:
            duplicate_exists = QuestionBank.objects.filter(
                school=destination_school,
                school_class=destination_class,
                subject=destination_subject,
                question_text=question.question_text,
                option_a=question.option_a,
                option_b=question.option_b,
                option_c=question.option_c,
                option_d=question.option_d,
            ).exists()

            if duplicate_exists:
                skipped_count += 1
                continue

            QuestionBank.objects.create(
                school=destination_school,
                school_class=destination_class,
                subject=destination_subject,
                question_text=question.question_text,
                question_image=question.question_image,
                option_a=question.option_a,
                option_b=question.option_b,
                option_c=question.option_c,
                option_d=question.option_d,
                correct_option=question.correct_option,
                difficulty=question.difficulty,
                is_active=True,
            )

            copied_count += 1

        messages.success(
            request,
            f"{copied_count} question(s) copied successfully. {skipped_count} duplicate question(s) skipped."
        )
        return redirect("super_admin_transfer_question_bank")

    return render(request, "cbt/super_admin_transfer_question_bank.html", {
        "page_title": "Transfer CBT Questions",
        "schools": schools,
        "source_classes": source_classes,
        "source_subjects": source_subjects,
        "destination_classes": destination_classes,
        "destination_subjects": destination_subjects,
        "source_school_id": source_school_id,
        "destination_school_id": destination_school_id,
    })



@login_required
def super_admin_cbt_question_manager(request):
    if not user_is_super_admin(request.user):
        messages.error(request, "You are not allowed to access this page.")
        return redirect("dashboard_redirect")

    schools = School.objects.filter(is_active=True).order_by("name")

    selected_school_id = request.GET.get("school") or request.POST.get("school")
    selected_exam_id = request.GET.get("exam") or request.POST.get("exam")

    exam_search = request.GET.get("exam_search", "").strip()
    bank_search = request.GET.get("bank_search", "").strip()

    exams = CBTExam.objects.none()
    exam_questions = CBTQuestion.objects.none()
    bank_questions = QuestionBank.objects.none()
    selected_exam = None

    if selected_school_id:
        exams = CBTExam.objects.filter(
            school_id=selected_school_id
        ).select_related("school_class", "subject").order_by("-created_at")

        bank_questions = QuestionBank.objects.filter(
            school_id=selected_school_id
        ).select_related("school_class", "subject").order_by("-created_at")

        if bank_search:
            bank_questions = bank_questions.filter(
                question_text__icontains=bank_search
            )

    if selected_exam_id:
        selected_exam = get_object_or_404(
            CBTExam.objects.select_related("school", "school_class", "subject"),
            id=selected_exam_id,
        )

        exam_questions = CBTQuestion.objects.filter(
            exam=selected_exam
        ).order_by("id")

        if exam_search:
            exam_questions = exam_questions.filter(
                question_text__icontains=exam_search
            )

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "exam_to_bank":
            question_ids = request.POST.getlist("exam_question_ids")

            if not selected_exam:
                messages.error(request, "Please select a CBT exam.")
                return redirect("super_admin_cbt_question_manager")

            copied_count = 0
            skipped_count = 0

            questions = CBTQuestion.objects.filter(id__in=question_ids, exam=selected_exam)

            for question in questions:
                duplicate_exists = QuestionBank.objects.filter(
                    school=selected_exam.school,
                    school_class=selected_exam.school_class,
                    subject=selected_exam.subject,
                    question_text=question.question_text,
                    option_a=question.option_a,
                    option_b=question.option_b,
                    option_c=question.option_c,
                    option_d=question.option_d,
                ).exists()

                if duplicate_exists:
                    skipped_count += 1
                    continue

                QuestionBank.objects.create(
                    school=selected_exam.school,
                    school_class=selected_exam.school_class,
                    subject=selected_exam.subject,
                    question_text=question.question_text,
                    question_image=question.question_image,
                    option_a=question.option_a,
                    option_b=question.option_b,
                    option_c=question.option_c,
                    option_d=question.option_d,
                    correct_option=question.correct_option,
                    difficulty="MEDIUM",
                    is_active=True,
                )
                copied_count += 1

            messages.success(request, f"{copied_count} copied to bank. {skipped_count} duplicate(s) skipped.")
            return redirect(f"{request.path}?school={selected_exam.school.id}&exam={selected_exam.id}")

        if action == "bank_to_exam":
            bank_question_ids = request.POST.getlist("bank_question_ids")

            if not selected_exam:
                messages.error(request, "Please select a CBT exam.")
                return redirect("super_admin_cbt_question_manager")

            copied_count = 0
            skipped_count = 0

            questions = QuestionBank.objects.filter(
                id__in=bank_question_ids,
                school=selected_exam.school,
            )

            for question in questions:
                duplicate_exists = CBTQuestion.objects.filter(
                    exam=selected_exam,
                    question_text=question.question_text,
                    option_a=question.option_a,
                    option_b=question.option_b,
                    option_c=question.option_c,
                    option_d=question.option_d,
                ).exists()

                if duplicate_exists:
                    skipped_count += 1
                    continue

                CBTQuestion.objects.create(
                    exam=selected_exam,
                    question_text=question.question_text,
                    question_image=question.question_image,
                    option_a=question.option_a,
                    option_b=question.option_b,
                    option_c=question.option_c,
                    option_d=question.option_d,
                    correct_option=question.correct_option,
                )
                copied_count += 1

            selected_exam.total_questions = selected_exam.questions.count()
            selected_exam.save(update_fields=["total_questions"])

            messages.success(request, f"{copied_count} copied to exam. {skipped_count} duplicate(s) skipped.")
            return redirect(f"{request.path}?school={selected_exam.school.id}&exam={selected_exam.id}")

    return render(request, "cbt/super_admin_cbt_question_manager.html", {
        "page_title": "Super Admin CBT Question Manager",
        "schools": schools,
        "exams": exams,
        "selected_school_id": selected_school_id,
        "selected_exam_id": selected_exam_id,
        "selected_exam": selected_exam,
        "exam_questions": exam_questions,
        "bank_questions": bank_questions,
        "exam_search": exam_search,
        "bank_search": bank_search,
    })