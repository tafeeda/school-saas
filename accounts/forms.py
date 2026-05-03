from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from schools.models import School

User = get_user_model()


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "w-full rounded-xl border border-slate-300 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500",
                "placeholder": "Enter username",
            }
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "w-full rounded-xl border border-slate-300 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500",
                "placeholder": "Enter password",
            }
        )
    )

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)

        if getattr(user, "role", None) == "SUPER_ADMIN":
            return

        school = getattr(user, "school", None)

        if not school:
            raise forms.ValidationError(
                "Your school account is no longer available on this system. Please contact EduPortal support.",
                code="school_missing",
            )

        if not school.is_active:
            raise forms.ValidationError(
                "Your school portal has been deactivated. Please contact your school management or EduPortal support.",
                code="school_inactive",
            )


class SchoolAdminCreationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"})
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"})
    )
    school = forms.ModelChoiceField(
        queryset=School.objects.all(),
        widget=forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"})
    )

    class Meta:
        model = User
        fields = [
            "school",
            "username",
            "first_name",
            "last_name",
            "email",
            "phone",
            "gender",
            "password",
            "confirm_password",
        ]
        widgets = {
            "username": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "first_name": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "last_name": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "email": forms.EmailInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "phone": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "gender": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = "SCHOOL_ADMIN"
        user.is_staff = True
        user.must_change_password = True
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

        widgets = {
            "first_name": forms.TextInput(attrs={
                "class": "w-full border border-slate-300 rounded-xl px-4 py-2 bg-slate-100 cursor-not-allowed",
                "readonly": "readonly"
            }),
            "last_name": forms.TextInput(attrs={
                "class": "w-full border border-slate-300 rounded-xl px-4 py-2 bg-slate-100 cursor-not-allowed",
                "readonly": "readonly"
            }),
            "email": forms.EmailInput(attrs={
                "class": "w-full border border-slate-300 rounded-xl px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            }),
        }


class SecurePasswordChangeForm(forms.Form):
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "w-full border border-slate-300 rounded-xl px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        }),
        label="Current Password"
    )

    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "w-full border border-slate-300 rounded-xl px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        }),
        label="New Password"
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "w-full border border-slate-300 rounded-xl px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        }),
        label="Confirm New Password"
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        current_password = self.cleaned_data.get("current_password")

        if not self.user.check_password(current_password):
            raise forms.ValidationError("Current password is incorrect.")

        return current_password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and confirm_password:
            if new_password != confirm_password:
                raise forms.ValidationError("New passwords do not match.")

            validate_password(new_password, self.user)

        return cleaned_data


class CreateSuperAdminForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            "class": "w-full border border-slate-300 rounded-xl px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        })
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class": "w-full border border-slate-300 rounded-xl px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "w-full border border-slate-300 rounded-xl px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        })
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "w-full border border-slate-300 rounded-xl px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        })
    )

    current_super_admin_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "w-full border border-slate-300 rounded-xl px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        }),
        label="Your Current Password"
    )

    def __init__(self, current_user, *args, **kwargs):
        self.current_user = current_user
        super().__init__(*args, **kwargs)

    def clean_username(self):
        username = self.cleaned_data.get("username")

        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already exists.")

        return username

    def clean_current_super_admin_password(self):
        password = self.cleaned_data.get("current_super_admin_password")

        if not self.current_user.check_password(password):
            raise forms.ValidationError("Your current password is incorrect.")

        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password:
            if password != confirm_password:
                raise forms.ValidationError("Passwords do not match.")

            validate_password(password)

        return cleaned_data