from django.urls import path

from .views import (
    lesson_note_create,
    lesson_note_detail,
    lesson_note_list,
    lesson_note_update,
    lesson_note_delete,
    lesson_note_toggle_status,
)

urlpatterns = [
    path("", lesson_note_list, name="lesson_note_list"),
    path("create/", lesson_note_create, name="lesson_note_create"),
    path("<int:pk>/", lesson_note_detail, name="lesson_note_detail"),
    path("<int:pk>/edit/", lesson_note_update, name="lesson_note_update"),
    path("<int:pk>/delete/", lesson_note_delete, name="lesson_note_delete"),
    path("<int:pk>/toggle-status/", lesson_note_toggle_status, name="lesson_note_toggle_status"),
]