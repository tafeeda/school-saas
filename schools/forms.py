from django import forms

from .models import School, SchoolSetting, SchoolSubscriptionRecord




class SchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = [
            "name",
            "code",
            "email",
            "phone",
            "address",
            "logo",
            "portal_subpath",
            "allow_result_checking",
            "is_active",
            "is_on_trial",
            "trial_end_date",
            "enable_cbt",
            "shuffle_cbt_questions",
            "shuffle_cbt_options",
            "show_cbt_score_immediately",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "code": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "email": forms.EmailInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "phone": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "address": forms.Textarea(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "rows": 4}),
            "logo": forms.ClearableFileInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "portal_subpath": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "trial_end_date": forms.DateInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "type": "date"}),
            "enable_cbt": forms.CheckboxInput(attrs={"class": "h-5 w-5"}),
            "shuffle_cbt_questions": forms.CheckboxInput(attrs={"class": "h-5 w-5"}),
            "shuffle_cbt_options": forms.CheckboxInput(attrs={"class": "h-5 w-5"}),
            "show_cbt_score_immediately": forms.CheckboxInput(attrs={"class": "h-5 w-5"}),
        }


class SchoolSettingForm(forms.ModelForm):
    class Meta:
        model = SchoolSetting
        fields = [
            "result_header_text",
            "grading_mode",
            "passkey_length",
            "enable_parent_portal",
            "enable_cbt",
            "enable_sms",
            "enable_email",
            "theme_mode",
            "primary_color",
            "secondary_color",
        ]
        widgets = {
            "result_header_text": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "grading_mode": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "passkey_length": forms.NumberInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "theme_mode": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "primary_color": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "secondary_color": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
        }


class SchoolSubscriptionControlForm(forms.ModelForm):
    class Meta:
        model = School
        fields = [
            "payment_method",
            "online_payment_enabled",
            "subscription_amount",
            "subscription_start_date",
            "subscription_end_date",
            "is_subscription_active",
            "is_suspended",
        ]
        widgets = {
            "payment_method": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "online_payment_enabled": forms.CheckboxInput(attrs={"class": "h-5 w-5"}),
            "subscription_amount": forms.NumberInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "subscription_start_date": forms.DateInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "type": "date"}),
            "subscription_end_date": forms.DateInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "type": "date"}),
            "is_subscription_active": forms.CheckboxInput(attrs={"class": "h-5 w-5"}),
            "is_suspended": forms.CheckboxInput(attrs={"class": "h-5 w-5"}),
        }


class ManualSubscriptionPaymentForm(forms.ModelForm):
    class Meta:
        model = SchoolSubscriptionRecord
        fields = [
            "amount",
            "payment_method",
            "payment_status",
            "reference",
            "paid_at",
            "subscription_start_date",
            "subscription_end_date",
            "note",
        ]
        widgets = {
            "amount": forms.NumberInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "payment_method": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "payment_status": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "reference": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "paid_at": forms.DateTimeInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "type": "datetime-local"}),
            "subscription_start_date": forms.DateInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "type": "date"}),
            "subscription_end_date": forms.DateInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "type": "date"}),
            "note": forms.Textarea(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "rows": 4}),
        }


class SchoolSubscriptionControlForm(forms.ModelForm):
    class Meta:
        model = School
        fields = [
            "payment_method",
            "online_payment_enabled",
            "subscription_amount",
            "subscription_start_date",
            "subscription_end_date",
            "is_subscription_active",
            "is_suspended",
        ]
        widgets = {
            "payment_method": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "online_payment_enabled": forms.CheckboxInput(attrs={"class": "h-5 w-5"}),
            "subscription_amount": forms.NumberInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "subscription_start_date": forms.DateInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "type": "date"}),
            "subscription_end_date": forms.DateInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "type": "date"}),
            "is_subscription_active": forms.CheckboxInput(attrs={"class": "h-5 w-5"}),
            "is_suspended": forms.CheckboxInput(attrs={"class": "h-5 w-5"}),
        }


class ManualSubscriptionPaymentForm(forms.ModelForm):
    class Meta:
        model = SchoolSubscriptionRecord
        fields = [
            "amount",
            "payment_method",
            "payment_status",
            "reference",
            "paid_at",
            "subscription_start_date",
            "subscription_end_date",
            "note",
        ]
        widgets = {
            "amount": forms.NumberInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "payment_method": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "payment_status": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "reference": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "paid_at": forms.DateTimeInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "type": "datetime-local"}),
            "subscription_start_date": forms.DateInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "type": "date"}),
            "subscription_end_date": forms.DateInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "type": "date"}),
            "note": forms.Textarea(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "rows": 4}),
        }