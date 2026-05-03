from django import forms

from academics.models import AcademicSession, AcademicTerm, SchoolClass, Subject
from .models import CBTExam, CBTQuestion, QuestionBank



class CBTExamForm(forms.ModelForm):
    class Meta:
        model = CBTExam
        fields = [
            "title",
            "instructions",
            "school_class",
            "subject",
            "session",
            "term",
            "duration_minutes",
            "is_active",
            "attempt_rule",
            "start_datetime",
            "end_datetime",
            "show_in_student_portal",
            "transfer_to_result",
            "result_score_max",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "school_class": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "subject": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "session": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "term": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "duration_minutes": forms.NumberInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "is_active": forms.CheckboxInput(attrs={"class": "h-5 w-5"}),
            "instructions": forms.Textarea(attrs={
                "class": "w-full rounded-xl border border-slate-300 px-4 py-3",
                "rows": 4
            }),
            "attempt_rule": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "start_datetime": forms.DateTimeInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "type": "datetime-local"}),
            "end_datetime": forms.DateTimeInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "type": "datetime-local"}),
            "show_in_student_portal": forms.CheckboxInput(attrs={"class": "h-5 w-5"}),
            "transfer_to_result": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "result_score_max": forms.NumberInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
        }

    def __init__(self, *args, **kwargs):
        school = kwargs.pop("school", None)
        super().__init__(*args, **kwargs)

        if school:
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
        else:
            self.fields["school_class"].queryset = SchoolClass.objects.none()
            self.fields["subject"].queryset = Subject.objects.none()
            self.fields["session"].queryset = AcademicSession.objects.none()
            self.fields["term"].queryset = AcademicTerm.objects.none()


class CBTQuestionForm(forms.ModelForm):
    class Meta:
        model = CBTQuestion
        fields = [
            "question_text",
            "question_image",
            "option_a",
            "option_b",
            "option_c",
            "option_d",
            "correct_option",
        ]
        widgets = {
            "question_text": forms.Textarea(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "rows": 4}),
            "option_a": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "option_b": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "option_c": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "option_d": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "correct_option": forms.Select(
                choices=[("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")],
                attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"},
            ),
            "question_image": forms.ClearableFileInput(attrs={
                "class": "w-full rounded-xl border border-slate-300 px-4 py-3",
            }),
        }


class CBTBulkUploadForm(forms.Form):
    file = forms.FileField(
        widget=forms.ClearableFileInput(attrs={
            "class": "w-full rounded-xl border border-slate-300 px-4 py-3"
        })
    )



class QuestionBankForm(forms.ModelForm):
    class Meta:
        model = QuestionBank
        fields = [
            "school_class",
            "subject",
            "question_text",
            "question_image",
            "option_a",
            "option_b",
            "option_c",
            "option_d",
            "correct_option",
            "difficulty",
            "is_active",
        ]

        widgets = {
            "school_class": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "subject": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "question_text": forms.Textarea(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "rows": 4}),
            "option_a": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "option_b": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "option_c": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "option_d": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "correct_option": forms.Select(
                choices=[("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")],
                attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"},
            ),
            "difficulty": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "is_active": forms.CheckboxInput(attrs={"class": "h-5 w-5"}),
            "question_image": forms.ClearableFileInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
        }

    def __init__(self, *args, **kwargs):
        school = kwargs.pop("school", None)
        super().__init__(*args, **kwargs)

        if school:
            from academics.models import SchoolClass, Subject

            self.fields["school_class"].queryset = SchoolClass.objects.filter(
                school=school,
                is_active=True,
            ).order_by("position_order", "name")

            self.fields["subject"].queryset = Subject.objects.filter(
                school=school,
                is_active=True,
            ).order_by("name")