from django.urls import path

from .views import (
    allocation_create,
    allocation_delete,
    allocation_list,
    allocation_update,
    teacher_create,
    teacher_delete,
    teacher_list,
    teacher_update,
    allocation_matrix,
    teacher_reset_password,
    available_subjects_for_teacher,
)

urlpatterns = [
    path("teachers/", teacher_list, name="teacher_list"),
    path("teachers/create/", teacher_create, name="teacher_create"),
    path("teachers/<int:pk>/edit/", teacher_update, name="teacher_update"),
    path("teachers/<int:pk>/delete/", teacher_delete, name="teacher_delete"),

    path("allocations/", allocation_list, name="allocation_list"),
    path("allocations/create/", allocation_create, name="allocation_create"),
    path("allocations/<int:pk>/edit/", allocation_update, name="allocation_update"),
    path("allocations/<int:pk>/delete/", allocation_delete, name="allocation_delete"),
    path("allocation-matrix/", allocation_matrix, name="allocation_matrix"),
    path("teachers/<int:pk>/reset-password/", teacher_reset_password, name="teacher_reset_password"),
    path("available-subjects/", available_subjects_for_teacher, name="available_subjects_for_teacher"),
]