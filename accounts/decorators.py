from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect


def login_required_custom(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please login first.")
            return redirect("login")
        return view_func(request, *args, **kwargs)
    return wrapper


def super_admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please login first.")
            return redirect("login")

        if not request.user.is_superuser:
            messages.error(request, "You are not allowed to access this page.")
            return redirect("dashboard")

        return view_func(request, *args, **kwargs)
    return wrapper


def school_admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please login first.")
            return redirect("login")

        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        if not hasattr(request.user, "schooladminprofile"):
            messages.error(request, "Only school admins can access this page.")
            return redirect("dashboard")

        return view_func(request, *args, **kwargs)
    return wrapper


def teacher_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please login first.")
            return redirect("login")

        if not hasattr(request.user, "teacherprofile"):
            messages.error(request, "Only teachers can access this page.")
            return redirect("dashboard")

        return view_func(request, *args, **kwargs)
    return wrapper


def student_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please login first.")
            return redirect("login")

        if not hasattr(request.user, "studentprofile"):
            messages.error(request, "Only students can access this page.")
            return redirect("dashboard")

        return view_func(request, *args, **kwargs)
    return wrapper