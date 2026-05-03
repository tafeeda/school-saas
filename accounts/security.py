def get_user_school(user):
    """
    Safely return the school attached to the logged-in user.
    Super Admin may return None because they are global.
    """

    if not user or not user.is_authenticated:
        return None

    if user.is_superuser:
        return None

    if hasattr(user, "school") and user.school:
        return user.school

    if hasattr(user, "schooladminprofile"):
        return user.schooladminprofile.school

    if hasattr(user, "teacherprofile"):
        return user.teacherprofile.school

    if hasattr(user, "student_profile"):
        return user.student_profile.school

    if hasattr(user, "studentprofile"):
        return user.studentprofile.school

    return None


def user_can_access_school(user, school):
    """
    Super Admin can access all schools.
    Other users can only access their own school.
    """

    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    user_school = get_user_school(user)

    return user_school == school