from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic.base import ContextMixin

from .utils import user_is_school_admin, user_is_super_admin


class SuperAdminRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")

        if getattr(request.user, "role", None) != "SUPER_ADMIN":
            messages.error(request, "You are not allowed to access that page.")
            return redirect("dashboard_redirect")
        return super().dispatch(request, *args, **kwargs)


class SchoolAdminRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")

        if not (
            user_is_school_admin(request.user)
            or user_is_super_admin(request.user)
        ):
            messages.error(request, "You are not allowed to access that page.")
            return redirect("dashboard_redirect")
        return super().dispatch(request, *args, **kwargs)


class DashboardContextMixin(ContextMixin):
    page_title = None

    def get_page_title(self):
        return self.page_title or "Dashboard"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = self.get_page_title()
        context["current_user_role"] = getattr(self.request.user, "role", "")
        context["current_school"] = getattr(self.request.user, "school", None)
        return context
        