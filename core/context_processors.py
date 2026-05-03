from .utils import get_school_for_user, user_is_school_admin, user_is_super_admin


def app_context(request):
    user = request.user
    return {
        "app_name": "EduPortal SaaS",
        "current_school": get_school_for_user(user) if user.is_authenticated else None,
        "is_super_admin_user": user_is_super_admin(user) if user.is_authenticated else False,
        "is_school_admin_user": user_is_school_admin(user) if user.is_authenticated else False,
    }