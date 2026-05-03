from django.contrib import messages
from django.shortcuts import redirect


def cbt_enabled_required(view_func):
    def wrapper(request, *args, **kwargs):
        school = getattr(request.user, "school", None)

        # For students, get school from linked student profile
        if not school and getattr(request.user, "role", None) == "STUDENT":
            student = getattr(request.user, "student_profile", None)
            if student:
                school = student.school

        if not school:
            messages.error(
                request,
                "Your school account is not properly linked. Please contact your school administrator."
            )
            return redirect("dashboard_redirect")

        if not getattr(school, "enable_cbt", False):
            messages.warning(
                request,
                "CBT exams have not been activated for your school. Please contact your school administrator."
            )
            return redirect("dashboard_redirect")

        return view_func(request, *args, **kwargs)

    return wrapper