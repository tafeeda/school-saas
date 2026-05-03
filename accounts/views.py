from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from cbt.models import CBTAttempt
from django.shortcuts import redirect, render, get_object_or_404
from .audit import log_audit
from academics.models import SchoolClass
from core.utils import (
    user_is_parent,
    user_is_school_admin,
    user_is_student,
    user_is_super_admin,
    user_is_teacher,
)
from lessons.models import LessonNote
from results.models import ResultSheet
from schools.models import School
from staffs.models import StaffProfile
from students.models import Student
from .forms import LoginForm, UserProfileForm, SecurePasswordChangeForm, CreateSuperAdminForm
from django.utils import timezone
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import get_user_model
from .decorators import login_required_custom, super_admin_required
from .models import AuditLog
from schools.models import School
from django.db import models
from django.contrib.auth import logout
import json
import csv
from django.http import HttpResponse
from django.core.cache import cache
from results.models import SubjectResult
from staffs.models import TeacherSubjectAllocation



class CustomLoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_SECONDS = 300  # 5 minutes

    def get_rate_limit_key(self):
        username = self.request.POST.get("username", "").strip().lower()
        ip = self.request.META.get("REMOTE_ADDR", "")
        return f"login_attempts:{username}:{ip}"

    def dispatch(self, request, *args, **kwargs):
        if request.method == "POST":
            key = self.get_rate_limit_key()
            attempts = cache.get(key, 0)

            if attempts >= self.MAX_FAILED_ATTEMPTS:
                messages.error(
                    request,
                    "Too many failed login attempts. Please try again after 5 minutes."
                )
                return self.render_to_response(self.get_context_data(form=self.get_form()))

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.get_user()

        cache.delete(self.get_rate_limit_key())

        log_audit(
            self.request,
            "LOGIN",
            description=f"{user.username} logged in successfully.",
            affected_user=user
        )

        messages.success(self.request, "Login successful.")
        return super().form_valid(form)

    def form_invalid(self, form):
        username = self.request.POST.get("username", "").strip()
        key = self.get_rate_limit_key()

        attempts = cache.get(key, 0) + 1
        cache.set(key, attempts, self.LOCKOUT_SECONDS)

        log_audit(
            self.request,
            "FAILED_LOGIN",
            description=f"Failed login attempt for username: {username}. Attempt {attempts}/{self.MAX_FAILED_ATTEMPTS}",
            affected_user=None
        )

        remaining = self.MAX_FAILED_ATTEMPTS - attempts

        if remaining > 0:
            messages.error(
                self.request,
                f"Invalid login details. {remaining} attempt(s) remaining before temporary lock."
            )
        else:
            messages.error(
                self.request,
                "Too many failed login attempts. Please try again after 5 minutes."
            )

        return super().form_invalid(form)

@login_required
def custom_logout_view(request):
    log_audit(
        request,
        "LOGOUT",
        description=f"{request.user.username} logged out.",
        affected_user=request.user
    )

    logout(request)
    messages.success(request, "You have logged out successfully.")
    return redirect("login")


@login_required
def dashboard_redirect(request):
    user = request.user

    if user_is_super_admin(user):
        return redirect("super_admin_dashboard")

    if user_is_school_admin(user):
        return redirect("school_admin_dashboard")

    if user_is_teacher(user):
        return redirect("teacher_dashboard")

    if user_is_student(user):
        return redirect("students_student_dashboard")

    if user_is_parent(user):
        return redirect("parent_dashboard")

    messages.warning(request, "Your account role is not configured properly.")
    return redirect("login")



@login_required
def super_admin_dashboard(request):
    User = get_user_model()

    total_super_admins = User.objects.filter(
        role="SUPER_ADMIN",
        is_active=True,
    ).count()

    school_student_counts = (
        School.objects.filter(is_active=True)
        .annotate(student_count=Count("student_records"))
        .order_by("name")
    )

    school_labels = [item.name for item in school_student_counts]
    school_counts = [item.student_count for item in school_student_counts]

    last_login_log = AuditLog.objects.filter(
        actor=request.user,
        action="LOGIN"
    ).order_by("-created_at").first()

    top_schools = (
        School.objects.filter(is_active=True)
        .annotate(
            avg_score=models.Avg("resultsheet_records__average_score"),
            published_count=models.Count(
                "resultsheet_records",
                filter=models.Q(
                    resultsheet_records__is_published=True,
                    resultsheet_records__is_active=True,
                ),
            ),
        )
        .filter(published_count__gt=0)
        .order_by("-avg_score")[:5]
    )

    context = {
        "total_super_admins": total_super_admins,

        "total_schools": School.objects.count(),
        "active_schools": School.objects.filter(is_active=True).count(),
        "inactive_schools": School.objects.filter(is_active=False).count(),
        "trial_schools": School.objects.filter(is_on_trial=True).count(),
        "recent_schools": School.objects.order_by("-created_at")[:10],

        "total_students": Student.objects.filter(is_active=True).count(),
        "total_teachers": StaffProfile.objects.filter(is_active=True).count(),
        "total_classes": SchoolClass.objects.filter(is_active=True).count(),
        "total_lesson_notes": LessonNote.objects.filter(is_active=True).count(),
        "total_published_results": ResultSheet.objects.filter(
            is_active=True,
            is_published=True,
        ).count(),

        "school_labels": json.dumps(school_labels),
        "school_counts": json.dumps(school_counts),

        "last_login_log": last_login_log,
        "top_schools": top_schools,
    }

    return render(request, "accounts/super_admin_dashboard.html", context)



@login_required
def school_admin_dashboard(request):
    school = request.user.school

    if not school:
        messages.error(request, "Your account is not linked to any school. Please contact the Super Admin.")
        return redirect("dashboard_redirect")

    class_counts = (
        SchoolClass.objects.filter(school=school, is_active=True)
        .annotate(student_count=Count("students"))
        .order_by("position_order", "name")
    )

    class_labels = [item.name for item in class_counts]
    class_student_counts = [item.student_count for item in class_counts]

    published_results = ResultSheet.objects.filter(
        school=school,
        is_active=True,
        is_published=True,
    ).count()

    blocked_results = ResultSheet.objects.filter(
        school=school,
        is_active=True,
        is_result_blocked=True,
    ).count()

    unpublished_results = ResultSheet.objects.filter(
        school=school,
        is_active=True,
        is_published=False,
    ).count()

    today = timezone.now().date()

    expiry_date = school.subscription_end_date
    if not expiry_date and school.trial_end_date:
        expiry_date = school.trial_end_date.date()

    days_left = None
    subscription_state = "active"

    if expiry_date:
        days_left = (expiry_date - today).days

        if days_left < 0:
            subscription_state = "expired"
        elif days_left <= 7:
            subscription_state = "critical"
        elif days_left <= 14:
            subscription_state = "warning"

    last_login_log = AuditLog.objects.filter(
        actor=request.user,
        action="LOGIN"
    ).order_by("-created_at").first()

    context = {
        "school": school,
        "total_students": Student.objects.filter(school=school, is_active=True).count(),
        "total_teachers": StaffProfile.objects.filter(school=school, is_active=True).count(),
        "total_classes": SchoolClass.objects.filter(school=school, is_active=True).count(),
        "total_lesson_notes": LessonNote.objects.filter(school=school, is_active=True).count(),
        "total_published_results": published_results,

        "class_counts": class_counts,
        "class_labels": json.dumps(class_labels),
        "class_student_counts": json.dumps(class_student_counts),

        "published_results": published_results,
        "blocked_results": blocked_results,
        "unpublished_results": unpublished_results,

        "days_left": days_left,
        "subscription_state": subscription_state,
        "expiry_date": expiry_date,

        "last_login_log": last_login_log,
    }

    return render(request, "accounts/school_admin_dashboard.html", context)




@login_required
def teacher_dashboard(request):
    if not user_is_teacher(request.user):
        messages.error(request, "You are not allowed to access that dashboard.")
        return redirect("dashboard_redirect")

    allocation_count = request.user.teaching_allocations.filter(is_active=True).count()

    total_results = SubjectResult.objects.filter(
        teacher=request.user,
        is_active=True,
    ).count()

    total_assignments = TeacherSubjectAllocation.objects.filter(
        teacher=request.user,
        is_active=True,
    ).count()

    # Total result sheets handled by this teacher
    total_sheets = ResultSheet.objects.filter(
        school=request.user.school,
        is_active=True
    ).count()

    # Subjects per class (approx using allocations)
    subjects_per_class = TeacherSubjectAllocation.objects.filter(
        teacher=request.user,
        is_active=True
    ).values("subject").distinct().count()

    expected_total = total_sheets * subjects_per_class

    completion_rate = 0
    if expected_total > 0:
        completion_rate = round((total_results / expected_total) * 100, 2)

    subject_progress = (
        SubjectResult.objects.filter(
            teacher=request.user,
            is_active=True
        )
        .values("subject__name")
        .annotate(total=Count("id"))
        .order_by("subject__name")
    )

    subject_labels = [item["subject__name"] for item in subject_progress]
    subject_counts = [item["total"] for item in subject_progress]

    return render(
        request,
        "accounts/teacher_dashboard.html",
        {
            "page_title": "Teacher Dashboard",
            "allocation_count": allocation_count,
            "total_results": total_results,
            "total_assignments": total_assignments,
            "completion_rate": completion_rate,
            "subject_labels": json.dumps(subject_labels),
            "subject_counts": json.dumps(subject_counts),
        },
    )



@login_required
def student_dashboard(request):
    if not user_is_student(request.user):
        messages.error(request, "You are not allowed to access that dashboard.")
        return redirect("dashboard_redirect")

    return redirect("students_student_dashboard")

@login_required
def parent_dashboard(request):
    if not user_is_parent(request.user):
        messages.error(request, "You are not allowed to access that dashboard.")
        return redirect("dashboard_redirect")

    return render(
        request,
        "accounts/parent_dashboard.html",
        {
            "page_title": "Parent Dashboard",
        },
    )


def subscription_blocked(request):
    return render(request, "accounts/subscription_blocked.html")


@login_required_custom
def my_profile(request):
    form = UserProfileForm(instance=request.user)

    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=request.user)

        if form.is_valid():
            form.save()

            log_audit(
                request,
                "PROFILE_UPDATED",
                description=f"{request.user.username} updated their profile.",
                affected_user=request.user
            )
            messages.success(request, "Profile updated successfully.")
            return redirect("my_profile")

    return render(request, "accounts/my_profile.html", {
        "form": form
    })


@login_required_custom
def change_my_password(request):
    form = SecurePasswordChangeForm(request.user)

    if request.method == "POST":
        form = SecurePasswordChangeForm(request.user, request.POST)

        if form.is_valid():
            new_password = form.cleaned_data["new_password"]
            request.user.set_password(new_password)
            request.user.save()

            log_audit(
                request,
                "PASSWORD_CHANGED",
                description=f"{request.user.username} changed their password.",
                affected_user=request.user
            )

            update_session_auth_hash(request, request.user)

            messages.success(request, "Password changed successfully.")
            return redirect("my_profile")

    return render(request, "accounts/change_password.html", {
        "form": form
    })


@super_admin_required
def create_super_admin(request):
    form = CreateSuperAdminForm(request.user)

    if request.method == "POST":
        form = CreateSuperAdminForm(request.user, request.POST)

        if form.is_valid():
            User = get_user_model()

            user = User.objects.create_user(
                username=form.cleaned_data["username"],
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
            )

            user.is_staff = True
            user.is_superuser = True
            user.role = "SUPER_ADMIN"
            user.save()

            log_audit(
                request,
                "SUPER_ADMIN_CREATED",
                description=f"{request.user.username} created new super admin account: {user.username}",
                affected_user=user
            )

            messages.success(request, "New Super Admin created successfully.")
            return redirect("super_admin_dashboard")

    return render(request, "accounts/create_super_admin.html", {
        "form": form
    })



@super_admin_required
def super_admin_list(request):
    User = get_user_model()

    super_admins = User.objects.filter(
        role="SUPER_ADMIN"
    ).order_by("-is_active", "username")

    return render(request, "accounts/super_admin_list.html", {
        "page_title": "Super Admin Management",
        "super_admins": super_admins,
    })


@super_admin_required
def super_admin_edit(request, user_id):
    User = get_user_model()

    super_admin = get_object_or_404(
        User,
        id=user_id,
        role="SUPER_ADMIN"
    )

    if request.method == "POST":
        super_admin.username = request.POST.get("username", "").strip()
        super_admin.email = request.POST.get("email", "").strip()
        super_admin.first_name = request.POST.get("first_name", "").strip()
        super_admin.last_name = request.POST.get("last_name", "").strip()
        super_admin.save()

        log_audit(
            request,
            "SUPER_ADMIN_UPDATED",
            description=f"{request.user.username} updated super admin account: {super_admin.username}",
            affected_user=super_admin
        )

        messages.success(request, "Super Admin updated successfully.")
        return redirect("super_admin_list")

    return render(request, "accounts/super_admin_edit.html", {
        "page_title": "Edit Super Admin",
        "super_admin": super_admin,
    })


@super_admin_required
def super_admin_deactivate(request, user_id):
    User = get_user_model()

    super_admin = get_object_or_404(
        User,
        id=user_id,
        role="SUPER_ADMIN"
    )

    if super_admin == request.user:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect("super_admin_list")

    if request.method == "POST":
        super_admin.is_active = False
        super_admin.save()

        log_audit(
            request,
            "SUPER_ADMIN_DEACTIVATED",
            description=f"{request.user.username} deactivated super admin account: {super_admin.username}",
            affected_user=super_admin
        )

        messages.success(request, "Super Admin deactivated successfully.")

    return redirect("super_admin_list")


@super_admin_required
def super_admin_activate(request, user_id):
    User = get_user_model()

    super_admin = get_object_or_404(
        User,
        id=user_id,
        role="SUPER_ADMIN"
    )

    if request.method == "POST":
        super_admin.is_active = True
        super_admin.save()

        log_audit(
            request,
            "SUPER_ADMIN_REACTIVATED",
            description=f"{request.user.username} reactivated super admin account: {super_admin.username}",
            affected_user=super_admin
        )

        messages.success(request, "Super Admin reactivated successfully.")

    return redirect("super_admin_list")




@super_admin_required
def school_admin_list(request):
    User = get_user_model()

    school_admins = User.objects.filter(
        role="SCHOOL_ADMIN"
    ).select_related("school").order_by("school__name", "username")

    search = request.GET.get("search")

    if search:
        school_admins = school_admins.filter(
            models.Q(username__icontains=search) |
            models.Q(email__icontains=search) |
            models.Q(first_name__icontains=search) |
            models.Q(last_name__icontains=search) |
            models.Q(school__name__icontains=search)
        )

    return render(request, "accounts/school_admin_list.html", {
        "page_title": "School Admin Management",
        "school_admins": school_admins,
        "search": search,
    })


@super_admin_required
def school_admin_detail(request, user_id):
    User = get_user_model()

    school_admin = get_object_or_404(
        User.objects.select_related("school"),
        id=user_id,
        role="SCHOOL_ADMIN"
    )

    return render(request, "accounts/school_admin_detail.html", {
        "page_title": "School Admin Details",
        "school_admin": school_admin,
    })


@super_admin_required
def school_admin_edit(request, user_id):
    User = get_user_model()

    school_admin = get_object_or_404(
        User,
        id=user_id,
        role="SCHOOL_ADMIN"
    )

    schools = School.objects.filter(is_active=True).order_by("name")

    if request.method == "POST":
        school_admin.username = request.POST.get("username", "").strip()
        school_admin.email = request.POST.get("email", "").strip()
        school_admin.first_name = request.POST.get("first_name", "").strip()
        school_admin.last_name = request.POST.get("last_name", "").strip()

        school_id = request.POST.get("school")
        if school_id:
            school_admin.school = get_object_or_404(School, id=school_id)

        school_admin.save()

        log_audit(
            request,
            "SCHOOL_ADMIN_UPDATED",
            description=f"{request.user.username} updated school admin account: {school_admin.username}",
            affected_user=school_admin
        )

        messages.success(request, "School Admin updated successfully.")
        return redirect("school_admin_list")

    return render(request, "accounts/school_admin_edit.html", {
        "page_title": "Edit School Admin",
        "school_admin": school_admin,
        "schools": schools,
    })


@super_admin_required
def school_admin_deactivate(request, user_id):
    User = get_user_model()

    school_admin = get_object_or_404(
        User,
        id=user_id,
        role="SCHOOL_ADMIN"
    )

    if request.method == "POST":
        school_admin.is_active = False
        school_admin.save()

        log_audit(
            request,
            "SCHOOL_ADMIN_DEACTIVATED",
            description=f"{request.user.username} deactivated school admin account: {school_admin.username}",
            affected_user=school_admin
        )

        messages.success(request, "School Admin deactivated successfully.")

    return redirect("school_admin_list")


@super_admin_required
def school_admin_activate(request, user_id):
    User = get_user_model()

    school_admin = get_object_or_404(
        User,
        id=user_id,
        role="SCHOOL_ADMIN"
    )

    if request.method == "POST":
        school_admin.is_active = True
        school_admin.save()

        log_audit(
            request,
            "SCHOOL_ADMIN_REACTIVATED",
            description=f"{request.user.username} reactivated school admin account: {school_admin.username}",
            affected_user=school_admin
        )

        messages.success(request, "School Admin reactivated successfully.")

    return redirect("school_admin_list")


@super_admin_required
def school_admin_change_password(request, user_id):
    User = get_user_model()

    school_admin = get_object_or_404(
        User,
        id=user_id,
        role="SCHOOL_ADMIN"
    )

    if request.method == "POST":
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if not new_password or not confirm_password:
            messages.error(request, "Both password fields are required.")
            return redirect("school_admin_change_password", user_id=school_admin.id)

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("school_admin_change_password", user_id=school_admin.id)

        if len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters.")
            return redirect("school_admin_change_password", user_id=school_admin.id)

        school_admin.set_password(new_password)
        school_admin.save()

        log_audit(
            request,
            "SCHOOL_ADMIN_PASSWORD_CHANGED",
            description=f"{request.user.username} changed password for school admin: {school_admin.username}",
            affected_user=school_admin
        )

        messages.success(request, "School Admin password changed successfully.")
        return redirect("school_admin_detail", user_id=school_admin.id)

    return render(request, "accounts/school_admin_change_password.html", {
        "page_title": "Change School Admin Password",
        "school_admin": school_admin,
    })



@super_admin_required
def audit_log_list(request):
    logs = AuditLog.objects.select_related(
        "actor",
        "affected_user",
        "school",
    ).order_by("-created_at")

    action = request.GET.get("action")
    school_id = request.GET.get("school")
    search = request.GET.get("search")

    if action:
        logs = logs.filter(action=action)

    if school_id:
        logs = logs.filter(school_id=school_id)

    if search:
        logs = logs.filter(
            models.Q(actor__username__icontains=search) |
            models.Q(affected_user__username__icontains=search) |
            models.Q(description__icontains=search) |
            models.Q(ip_address__icontains=search)
        )

    logs = logs[:200]

    schools = School.objects.order_by("name")

    return render(request, "accounts/audit_log_list.html", {
        "page_title": "Audit Logs",
        "logs": logs,
        "schools": schools,
        "actions": AuditLog.ACTION_CHOICES,
        "selected_action": action,
        "selected_school": school_id,
        "search": search,
    })


@super_admin_required
def audit_log_export_csv(request):
    logs = AuditLog.objects.select_related(
        "actor",
        "affected_user",
        "school",
    ).order_by("-created_at")

    action = request.GET.get("action")
    school_id = request.GET.get("school")
    search = request.GET.get("search")

    if action:
        logs = logs.filter(action=action)

    if school_id:
        logs = logs.filter(school_id=school_id)

    if search:
        logs = logs.filter(
            models.Q(actor__username__icontains=search) |
            models.Q(affected_user__username__icontains=search) |
            models.Q(description__icontains=search) |
            models.Q(ip_address__icontains=search)
        )

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="audit_logs.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "Date",
        "Action",
        "Actor",
        "Affected User",
        "School",
        "IP Address",
        "Description",
        "User Agent",
    ])

    for log in logs:
        writer.writerow([
            log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            log.get_action_display(),
            log.actor.username if log.actor else "System",
            log.affected_user.username if log.affected_user else "",
            log.school.name if log.school else "Global",
            log.ip_address or "",
            log.description or "",
            log.user_agent or "",
        ])

    return response



@login_required
def super_admin_school_cbt_overview(request):
    if not user_is_super_admin(request.user):
        messages.error(request, "You are not allowed to access this page.")
        return redirect("dashboard_redirect")

    schools = (
        School.objects.all()
        .annotate(
            total_students_count=Count("student_records", distinct=True),
            total_cbt_attempts=Count("cbtexam__cbtattempt", distinct=True),
        )
        .order_by("name")
    )

    return render(request, "accounts/super_admin_school_cbt_overview.html", {
        "page_title": "Schools & CBT Records",
        "schools": schools,
    })


@login_required
def super_admin_school_students_cbt(request, school_id):
    if not user_is_super_admin(request.user):
        messages.error(request, "You are not allowed to access this page.")
        return redirect("dashboard_redirect")

    school = get_object_or_404(School, id=school_id)

    students = (
        Student.objects.filter(school=school, is_active=True)
        .select_related("current_class", "user")
        .annotate(
            cbt_attempt_count=Count("cbtattempt", distinct=True),
        )
        .order_by("current_class__position_order", "surname", "first_name")
    )

    return render(request, "accounts/super_admin_school_students_cbt.html", {
        "page_title": f"{school.name} Students CBT Records",
        "school": school,
        "students": students,
    })



def about_page(request):
    return render(request, "accounts/public/about.html")


def mission_vision_page(request):
    return render(request, "accounts/public/mission_vision.html")


def contact_page(request):
    return render(request, "accounts/public/contact.html")



@login_required
def school_admin_class_list(request):
    if not user_is_school_admin(request.user):
        messages.error(request, "You are not allowed to access this page.")
        return redirect("dashboard_redirect")

    school = request.user.school

    classes = (
        SchoolClass.objects.filter(school=school, is_active=True)
        .annotate(student_count=Count("students"))
        .order_by("position_order", "name")
    )

    return render(request, "accounts/school_admin_class_list.html", {
        "page_title": "My School Classes",
        "school": school,
        "classes": classes,
    })


@login_required
def school_admin_class_students(request, class_id):
    if not user_is_school_admin(request.user):
        messages.error(request, "You are not allowed to access this page.")
        return redirect("dashboard_redirect")

    school = request.user.school

    school_class = get_object_or_404(
        SchoolClass,
        id=class_id,
        school=school,
        is_active=True,
    )

    students = (
        Student.objects.filter(
            school=school,
            current_class=school_class,
            is_active=True,
        )
        .select_related("user", "current_session")
        .order_by("surname", "first_name", "admission_number")
    )

    return render(request, "accounts/school_admin_class_students.html", {
        "page_title": f"{school_class.name} Students",
        "school": school,
        "school_class": school_class,
        "students": students,
    })


@login_required
def teacher_assigned_class_list(request):
    if not user_is_teacher(request.user):
        messages.error(request, "You are not allowed to access this page.")
        return redirect("dashboard_redirect")

    assigned_classes = (
        TeacherSubjectAllocation.objects.filter(
            teacher=request.user,
            school=request.user.school,
            is_active=True,
        )
        .values(
            "school_class__id",
            "school_class__name",
            "school_class__position_order",
        )
        .annotate(
            subject_count=Count("subject", distinct=True),
            student_count=Count("school_class__students", distinct=True),
        )
        .order_by("school_class__position_order", "school_class__name")
    )

    return render(request, "accounts/teacher_assigned_class_list.html", {
        "page_title": "My Assigned Classes",
        "assigned_classes": assigned_classes,
    })


@login_required
def teacher_assigned_class_students(request, class_id):
    if not user_is_teacher(request.user):
        messages.error(request, "You are not allowed to access this page.")
        return redirect("dashboard_redirect")

    allocation_exists = TeacherSubjectAllocation.objects.filter(
        teacher=request.user,
        school=request.user.school,
        school_class_id=class_id,
        is_active=True,
    ).exists()

    if not allocation_exists:
        messages.error(request, "This class is not assigned to you.")
        return redirect("teacher_assigned_class_list")

    school_class = get_object_or_404(
        SchoolClass,
        id=class_id,
        school=request.user.school,
        is_active=True,
    )

    students = (
        Student.objects.filter(
            school=request.user.school,
            current_class=school_class,
            is_active=True,
        )
        .select_related("user", "current_session")
        .order_by("surname", "first_name", "admission_number")
    )

    return render(request, "accounts/teacher_assigned_class_students.html", {
        "page_title": f"{school_class.name} Students",
        "school_class": school_class,
        "students": students,
    })