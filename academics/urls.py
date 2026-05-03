from django.urls import path
from .views import *

urlpatterns = [
    path("sessions/", session_list, name="session_list"),
    path("sessions/create/", session_create, name="session_create"),
    path("sessions/<int:pk>/edit/", session_update, name="session_update"),
    path("sessions/<int:pk>/delete/", session_delete, name="session_delete"),

    path("terms/", term_list, name="term_list"),
    path("terms/create/", term_create, name="term_create"),
    path("terms/<int:pk>/edit/", term_update, name="term_update"),
    path("terms/<int:pk>/delete/", term_delete, name="term_delete"),

    path("classes/", class_list, name="class_list"),
    path("classes/create/", class_create, name="class_create"),
    path("classes/<int:pk>/edit/", class_update, name="class_update"),
    path("classes/<int:pk>/delete/", class_delete, name="class_delete"),

    path("subjects/", subject_list, name="subject_list"),
    path("subjects/create/", subject_create, name="subject_create"),
    path("subjects/<int:pk>/edit/", subject_update, name="subject_update"),
    path("subjects/<int:pk>/delete/", subject_delete, name="subject_delete"),

    path("assign-subject/", assign_subject, name="assign_subject"),
    path("available-subjects/", available_subjects_for_class, name="available_subjects_for_class"),
]