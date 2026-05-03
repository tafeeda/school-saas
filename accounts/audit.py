from .models import AuditLog


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")

    return ip


def get_user_school(user):
    if not user or not user.is_authenticated:
        return None

    if hasattr(user, "school") and user.school:
        return user.school

    if hasattr(user, "schooladminprofile"):
        return user.schooladminprofile.school

    if hasattr(user, "teacherprofile"):
        return user.teacherprofile.school

    if hasattr(user, "studentprofile"):
        return user.studentprofile.school

    return None


def log_audit(request, action, description="", affected_user=None):
    actor = request.user if request.user.is_authenticated else None

    AuditLog.objects.create(
        actor=actor,
        affected_user=affected_user,
        school=get_user_school(actor),
        action=action,
        description=description,
        ip_address=get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
    )