from django import forms
from django.contrib.auth import get_user_model

from academics.models import AcademicSession, AcademicTerm, SchoolClass, Subject
from .models import StaffProfile, TeacherSubjectAllocation

User = get_user_model()


class TeacherCreationForm(forms.ModelForm):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"})
    )
    confirm_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"})
    )
    staff_id = forms.CharField(
        widget=forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"})
    )
    designation = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"})
    )
    qualification = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"})
    )
    date_joined = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "type": "date"})
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "phone",
            "gender",
            "passport",
        ]
        widgets = {
            "username": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "first_name": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "last_name": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "email": forms.EmailInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "phone": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "gender": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "passport": forms.ClearableFileInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if self.instance and self.instance.pk:
            if password or confirm_password:
                if password != confirm_password:
                    raise forms.ValidationError("Passwords do not match.")
        else:
            if not password or not confirm_password:
                raise forms.ValidationError("Password and confirm password are required.")
            if password != confirm_password:
                raise forms.ValidationError("Passwords do not match.")

        return cleaned_data


class TeacherAllocationForm(forms.ModelForm):
    class Meta:
        model = TeacherSubjectAllocation
        fields = ["teacher", "school_class", "subject", "session", "term"]
        widgets = {
            "teacher": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "school_class": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "subject": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "session": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "term": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
        }

    def __init__(self, *args, **kwargs):
        school = kwargs.pop("school", None)
        super().__init__(*args, **kwargs)

        if school:
            self.fields["teacher"].queryset = User.objects.filter(
                school=school,
                role="TEACHER",
                is_active=True,
            ).order_by("first_name", "last_name")
            self.fields["school_class"].queryset = SchoolClass.objects.filter(
                school=school,
                is_active=True,
            ).order_by("position_order", "name")
            self.fields["subject"].queryset = Subject.objects.filter(
                school=school,
                is_active=True,
            ).order_by("name")
            self.fields["session"].queryset = AcademicSession.objects.filter(
                school=school,
                is_active=True,
            ).order_by("-name")
            self.fields["term"].queryset = AcademicTerm.objects.filter(
                school=school,
                is_active=True,
            ).order_by("session__name", "name")

    def clean(self):
        cleaned_data = super().clean()

        teacher = cleaned_data.get("teacher")
        school_class = cleaned_data.get("school_class")
        subject = cleaned_data.get("subject")
        session = cleaned_data.get("session")
        term = cleaned_data.get("term")

        if all([teacher, school_class, subject, session, term]):
            exists = TeacherSubjectAllocation.objects.filter(
                school=teacher.school,
                teacher=teacher,
                school_class=school_class,
                subject=subject,
                session=session,
                term=term,
            ).exists()

            if exists:
                raise forms.ValidationError(
                    f"{teacher.get_full_name()} is already assigned to {subject.name} in {school_class.name} for this session/term."
                )

        return cleaned_data