
from django.urls import path

from . import views

from .views import (
    CustomLoginView,
    dashboard_redirect,
    parent_dashboard,
    school_admin_dashboard,
    student_dashboard,
    super_admin_dashboard,
    teacher_dashboard,
    subscription_blocked,
)

urlpatterns = [
    path("login/", CustomLoginView.as_view(), name="login"),
    path("dashboard/redirect/", dashboard_redirect, name="dashboard_redirect"),
    path("dashboard/super-admin/", super_admin_dashboard, name="super_admin_dashboard"),
    path("dashboard/school-admin/", school_admin_dashboard, name="school_admin_dashboard"),
    path("dashboard/teacher/", teacher_dashboard, name="teacher_dashboard"),
    path("dashboard/student/", student_dashboard, name="student_dashboard"),
    path("dashboard/parent/", parent_dashboard, name="parent_dashboard"),
    path("subscription-blocked/", subscription_blocked, name="subscription_blocked"),
    path("my-profile/", views.my_profile, name="my_profile"),
    path("change-password/", views.change_my_password, name="change_my_password"),
    path("create-super-admin/", views.create_super_admin, name="create_super_admin"),
    path("audit-logs/", views.audit_log_list, name="audit_log_list"),
    path("audit-logs/export/", views.audit_log_export_csv, name="audit_log_export_csv"),
    path("about/", views.about_page, name="about_page"),
    path("mission-vision/", views.mission_vision_page, name="mission_vision_page"),
    path("contact/", views.contact_page, name="contact_page"),
    path("logout/", views.custom_logout_view, name="logout"),
    path("super-admins/", views.super_admin_list, name="super_admin_list"),
    path("super-admins/<int:user_id>/edit/", views.super_admin_edit, name="super_admin_edit"),
    path("super-admins/<int:user_id>/deactivate/", views.super_admin_deactivate, name="super_admin_deactivate"),
    path("super-admins/<int:user_id>/activate/", views.super_admin_activate, name="super_admin_activate"),

    path("school-admins/", views.school_admin_list, name="school_admin_list"),
    path("school-admins/<int:user_id>/", views.school_admin_detail, name="school_admin_detail"),
    path("school-admins/<int:user_id>/edit/", views.school_admin_edit, name="school_admin_edit"),
    path("school-admins/<int:user_id>/deactivate/", views.school_admin_deactivate, name="school_admin_deactivate"),
    path("school-admins/<int:user_id>/activate/", views.school_admin_activate, name="school_admin_activate"),
    path("school-admins/<int:user_id>/change-password/", views.school_admin_change_password, name="school_admin_change_password"),
    path("super-admin/schools-cbt/", views.super_admin_school_cbt_overview, name="super_admin_school_cbt_overview"),
    path("super-admin/schools-cbt/<int:school_id>/students/", views.super_admin_school_students_cbt, name="super_admin_school_students_cbt"),
    path("school-admin/classes/", views.school_admin_class_list, name="school_admin_class_list"),
    path("school-admin/classes/<int:class_id>/students/", views.school_admin_class_students, name="school_admin_class_students"),
    path("teacher/classes/", views.teacher_assigned_class_list, name="teacher_assigned_class_list"),
    path("teacher/classes/<int:class_id>/students/", views.teacher_assigned_class_students, name="teacher_assigned_class_students"),
]


