from typing import Optional

from django.contrib.auth import get_user_model

User = get_user_model()


def user_is_super_admin(user) -> bool:
    return bool(
        user.is_authenticated
        and getattr(user, "role", None) == "SUPER_ADMIN"
    )


def user_is_school_admin(user) -> bool:
    return bool(
        user.is_authenticated
        and getattr(user, "role", None) == "SCHOOL_ADMIN"
    )


def user_is_teacher(user) -> bool:
    return bool(
        user.is_authenticated
        and getattr(user, "role", None) == "TEACHER"
    )


def user_is_student(user) -> bool:
    return bool(
        user.is_authenticated
        and getattr(user, "role", None) == "STUDENT"
    )


def user_is_parent(user) -> bool:
    return bool(
        user.is_authenticated
        and getattr(user, "role", None) == "PARENT"
    )


def user_belongs_to_school(user, school) -> bool:
    if not user.is_authenticated:
        return False

    if user_is_super_admin(user):
        return True

    return getattr(user, "school_id", None) == getattr(school, "id", None)


def get_user_dashboard_name(user) -> str:
    if not user.is_authenticated:
        return "Guest"

    role_map = {
        "SUPER_ADMIN": "Super Admin",
        "SCHOOL_ADMIN": "School Admin",
        "TEACHER": "Teacher",
        "STUDENT": "Student",
        "PARENT": "Parent",
        "ACCOUNTANT": "Accountant",
        "LIBRARIAN": "Librarian",
    }
    return role_map.get(getattr(user, "role", ""), "User")


def get_school_for_user(user) -> Optional[object]:
    if not user.is_authenticated:
        return None
    return getattr(user, "school", None)