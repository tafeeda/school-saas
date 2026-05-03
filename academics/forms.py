from django import forms
from .models import AcademicSession, AcademicTerm, SchoolClass, Subject, ClassSubject


class SessionForm(forms.ModelForm):
    class Meta:
        model = AcademicSession
        fields = ["name", "start_date", "end_date", "is_current"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "start_date": forms.DateInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "type": "date"}),
            "end_date": forms.DateInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "type": "date"}),
        }


class TermForm(forms.ModelForm):
    class Meta:
        model = AcademicTerm
        fields = ["session", "name", "start_date", "end_date", "is_current"]
        widgets = {
            "session": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "name": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "start_date": forms.DateInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "type": "date"}),
            "end_date": forms.DateInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "type": "date"}),
        }


class ClassForm(forms.ModelForm):
    class Meta:
        model = SchoolClass
        fields = ["name", "category", "position_order"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "category": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "position_order": forms.NumberInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
        }


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ["name", "code", "short_name"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "code": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "short_name": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
        }


class ClassSubjectForm(forms.ModelForm):
    class Meta:
        model = ClassSubject
        fields = ["school_class", "subject"]
        widgets = {
            "school_class": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "subject": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
        }

    def __init__(self, *args, **kwargs):
        self.school = kwargs.pop("school", None)
        super().__init__(*args, **kwargs)

        if self.school:
            self.fields["school_class"].queryset = SchoolClass.objects.filter(
                school=self.school,
                is_active=True,
            ).order_by("position_order", "name")

            self.fields["subject"].queryset = Subject.objects.filter(
                school=self.school,
                is_active=True,
            ).order_by("name")

    def clean(self):
        cleaned_data = super().clean()
        school_class = cleaned_data.get("school_class")
        subject = cleaned_data.get("subject")

        if self.school and school_class and subject:
            exists = ClassSubject.objects.filter(
                school=self.school,
                school_class=school_class,
                subject=subject,
            ).exists()

            if exists:
                raise forms.ValidationError(
                    f"{subject.name} has already been assigned to {school_class.name}."
                )

        return cleaned_data