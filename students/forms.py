from django import forms
from django.contrib.auth import get_user_model
from academics.models import AcademicSession, SchoolClass
from .models import Student, StudentClassHistory



User = get_user_model()


class StudentForm(forms.ModelForm):
    username = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"})
    )

    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"})
    )

    confirm_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"})
    )

    class Meta:
        model = Student
        fields = [
            "admission_number",
            "surname",
            "first_name",
            "other_name",
            "gender",
            "date_of_birth",
            "passport",
            "current_class",
            "current_session",
            "date_admitted",
            "address",
            "guardian_name",
            "guardian_phone",
            "guardian_email",
            "guardian_address",
            "guardian_relationship",
        ]
        widgets = {
            "admission_number": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "surname": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "first_name": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "other_name": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "gender": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "date_of_birth": forms.DateInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "type": "date"}),
            "passport": forms.ClearableFileInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "current_class": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "current_session": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "date_admitted": forms.DateInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "type": "date"}),
            "address": forms.Textarea(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "rows": 3}),
            "guardian_name": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "guardian_phone": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "guardian_email": forms.EmailInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "guardian_address": forms.Textarea(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "rows": 3}),
            "guardian_relationship": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
        }

    def __init__(self, *args, **kwargs):
        self.school = kwargs.pop("school", None)
        school = self.school
        super().__init__(*args, **kwargs)

        # Hide login fields when editing an existing student.
        # Login should be created only during student creation.
        if self.instance and self.instance.pk:
            self.fields.pop("username", None)
            self.fields.pop("password", None)
            self.fields.pop("confirm_password", None)

        if school:
            self.fields["current_class"].queryset = SchoolClass.objects.filter(
                school=school,
                is_active=True,
            ).order_by("position_order", "name")

            self.fields["current_session"].queryset = AcademicSession.objects.filter(
                school=school,
                is_active=True,
            ).order_by("-name")

    def clean_admission_number(self):
        admission_number = self.cleaned_data.get("admission_number")

        if admission_number and self.school:
            qs = Student.objects.filter(
                school=self.school,
                admission_number__iexact=admission_number,
            )

            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise forms.ValidationError(
                    "This admission number already belongs to another student in this school."
                )

        return admission_number

    def clean(self):
        cleaned_data = super().clean()

        # Do not validate login fields while editing existing student.
        if self.instance and self.instance.pk:
            return cleaned_data

        username = cleaned_data.get("username")
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if username or password or confirm_password:
            if not username:
                self.add_error("username", "Username is required.")
            if not password:
                self.add_error("password", "Password is required.")
            if password != confirm_password:
                self.add_error("confirm_password", "Passwords do not match.")

            if username and User.objects.filter(username=username).exists():
                self.add_error("username", "This username already exists.")

        return cleaned_data

    def save(self, commit=True):
        student = super().save(commit=False)

        if self.school:
            student.school = self.school

        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if username and password and not student.user:
            user = User.objects.create_user(
                username=username,
                password=password,
            )

            # ✅ ALWAYS SET THESE FIELDS PROPERLY
            user.role = "STUDENT"
            user.school = self.school
            user.is_active = True
            user.must_change_password = True

            user.save(update_fields=["role", "school", "is_active", "must_change_password"])

            student.user = user
            student.portal_initial_password = password

        if commit:
            student.save()

        return student


class StudentMovementForm(forms.Form):
    new_class = forms.ModelChoiceField(
        queryset=SchoolClass.objects.none(),
        widget=forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
    )
    movement_type = forms.ChoiceField(
        choices=StudentClassHistory.MOVEMENT_TYPE_CHOICES,
        widget=forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
    )
    movement_date = forms.DateField(
        widget=forms.DateInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "type": "date"}),
    )
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "rows": 4}),
    )

    def __init__(self, *args, **kwargs):
        school = kwargs.pop("school", None)
        super().__init__(*args, **kwargs)

        if school:
            self.fields["new_class"].queryset = SchoolClass.objects.filter(
                school=school,
                is_active=True,
            ).order_by("position_order", "name")