from django import forms

from academics.models import AcademicSession, AcademicTerm, SchoolClass, Subject
from schools.models import School

from .models import LessonNote


class LessonNoteForm(forms.ModelForm):
    class Meta:
        model = LessonNote
        fields = [
            "school",
            "school_class",
            "subject",
            "session",
            "term",
            "scope",
            "week",
            "title",
            "topic",
            "subtopic",
            "lesson_file",
            "description",
            "status",
        ]
        widgets = {
            "school": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "school_class": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "subject": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "session": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "term": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "week": forms.NumberInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "title": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "topic": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "subtopic": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "lesson_file": forms.ClearableFileInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "description": forms.Textarea(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "rows": 4}),
            "status": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "scope": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user and getattr(user, "role", None) == "SUPER_ADMIN":
            self.fields["school"].queryset = School.objects.filter(is_active=True).order_by("name")
        elif user and getattr(user, "role", None) == "SCHOOL_ADMIN":
            self.fields["school"].queryset = School.objects.filter(id=user.school_id)
            self.fields["school"].initial = user.school
        else:
            self.fields["school"].queryset = School.objects.none()

        school = None

        if self.is_bound:
            school_id = self.data.get("school")
            if school_id:
                school = School.objects.filter(id=school_id).first()
        elif self.instance and self.instance.pk:
            school = self.instance.school
        elif user and getattr(user, "role", None) == "SCHOOL_ADMIN":
            school = user.school
        elif user and getattr(user, "role", None) == "SUPER_ADMIN":
            first_school = self.fields["school"].queryset.first()
            if first_school:
                school = first_school
                self.fields["school"].initial = first_school

        if school:
            self.fields["school_class"].queryset = SchoolClass.objects.filter(
                school=school, is_active=True
            ).order_by("position_order", "name")
            self.fields["subject"].queryset = Subject.objects.filter(
                school=school, is_active=True
            ).order_by("name")
            self.fields["session"].queryset = AcademicSession.objects.filter(
                school=school, is_active=True
            ).order_by("-name")
            self.fields["term"].queryset = AcademicTerm.objects.filter(
                school=school, is_active=True
            ).order_by("session__name", "name")
        else:
            self.fields["school_class"].queryset = SchoolClass.objects.none()
            self.fields["subject"].queryset = Subject.objects.none()
            self.fields["session"].queryset = AcademicSession.objects.none()
            self.fields["term"].queryset = AcademicTerm.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        scope = cleaned_data.get("scope")
        week = cleaned_data.get("week")

        if scope == "WEEKLY" and not week:
            self.add_error("week", "Week is required for weekly lesson notes.")

        if scope in ["TERMLY", "SESSION"] and week:
            self.add_error("week", "Week should be empty for term-wide or session-wide lesson notes.")

        return cleaned_data