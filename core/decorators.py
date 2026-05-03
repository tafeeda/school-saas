from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from .utils import (
    user_is_parent,
    user_is_school_admin,
    user_is_student,
    user_is_super_admin,
    user_is_teacher,
)


def super_admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")

        if not user_is_super_admin(request.user):
            messages.error(request, "You do not have permission to access that page.")
            return redirect("dashboard_redirect")
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def school_admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")

        if not user_is_school_admin(request.user) and not user_is_super_admin(request.user):
            messages.error(request, "You do not have permission to access that page.")
            return redirect("dashboard_redirect")
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def teacher_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")

        if not user_is_teacher(request.user):
            messages.error(request, "You do not have permission to access that page.")
            return redirect("dashboard_redirect")
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def student_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")

        if not user_is_student(request.user):
            messages.error(request, "You do not have permission to access that page.")
            return redirect("dashboard_redirect")
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def parent_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")

        if not user_is_parent(request.user):
            messages.error(request, "You do not have permission to access that page.")
            return redirect("dashboard_redirect")
        return view_func(request, *args, **kwargs)

    return _wrapped_view