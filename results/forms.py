from decimal import Decimal

from django import forms

from academics.models import AcademicSession, AcademicTerm, SchoolClass, Subject
from students.models import Student

from .models import (
    AssessmentComponent,
    AssessmentTemplate,
    BehaviorRating,
    GradeBoundary,
    GradingScheme,
    ResultSheet,
    SubjectResult,
)


class GradingSchemeForm(forms.ModelForm):
    class Meta:
        model = GradingScheme
        fields = ["name", "is_default"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
        }


class GradeBoundaryForm(forms.ModelForm):
    class Meta:
        model = GradeBoundary
        fields = ["grading_scheme", "grade", "min_score", "max_score", "remark", "color", "point"]
        widgets = {
            "grading_scheme": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "grade": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "min_score": forms.NumberInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "step": "0.01"}),
            "max_score": forms.NumberInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "step": "0.01"}),
            "remark": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "color": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "point": forms.NumberInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        school = kwargs.pop("school", None)
        super().__init__(*args, **kwargs)
        if school:
            self.fields["grading_scheme"].queryset = GradingScheme.objects.filter(
                school=school,
                is_active=True,
            ).order_by("name")


class AssessmentTemplateForm(forms.ModelForm):
    class Meta:
        model = AssessmentTemplate
        fields = ["name", "total_score", "is_default"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "total_score": forms.NumberInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "step": "0.01"}),
        }


class AssessmentComponentForm(forms.ModelForm):
    class Meta:
        model = AssessmentComponent
        fields = ["assessment_template", "name", "max_score", "order"]
        widgets = {
            "assessment_template": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "name": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "max_score": forms.NumberInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "step": "0.01"}),
            "order": forms.NumberInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
        }

    def __init__(self, *args, **kwargs):
        school = kwargs.pop("school", None)
        super().__init__(*args, **kwargs)
        if school:
            self.fields["assessment_template"].queryset = AssessmentTemplate.objects.filter(
                school=school,
                is_active=True,
            ).order_by("name")


class ResultSheetForm(forms.ModelForm):
    class Meta:
        model = ResultSheet
        fields = [
            "student",
            "school_class",
            "session",
            "term",
            "grading_scheme",
            "assessment_template",
            "attendance_present",
            "attendance_total",
            "next_resumption_date",
            "teacher_comment",
            "headteacher_comment",
        ]

        widgets = {
            "student": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "school_class": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "session": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "term": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "grading_scheme": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "assessment_template": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "attendance_present": forms.NumberInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "attendance_total": forms.NumberInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "teacher_comment": forms.Textarea(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "rows": 3}),
            "headteacher_comment": forms.Textarea(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "rows": 3}),
            "next_resumption_date": forms.DateInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        school = kwargs.pop("school", None)
        super().__init__(*args, **kwargs)
        if school:
            students_qs = Student.objects.filter(
                school=school,
                is_active=True
            ).order_by("surname", "first_name")

            class_id = self.data.get("school_class") or self.initial.get("school_class")
            session_id = self.data.get("session") or self.initial.get("session")
            term_id = self.data.get("term") or self.initial.get("term")
            selected_student_id = self.data.get("student")

            if class_id and session_id and term_id and not self.instance.pk:
                used_student_ids = ResultSheet.objects.filter(
                    school=school,
                    school_class_id=class_id,
                    session_id=session_id,
                    term_id=term_id,
                    is_active=True,
                ).values_list("student_id", flat=True)

                if selected_student_id:
                    used_student_ids = [sid for sid in used_student_ids if str(sid) != str(selected_student_id)]

                students_qs = students_qs.exclude(id__in=used_student_ids)

            self.fields["student"].queryset = students_qs
            self.fields["school_class"].queryset = SchoolClass.objects.filter(school=school, is_active=True).order_by("position_order", "name")
            self.fields["session"].queryset = AcademicSession.objects.filter(school=school, is_active=True).order_by("-name")
            self.fields["term"].queryset = AcademicTerm.objects.filter(school=school, is_active=True).order_by("session__name", "name")
            self.fields["grading_scheme"].queryset = GradingScheme.objects.filter(school=school, is_active=True).order_by("name")
            self.fields["assessment_template"].queryset = AssessmentTemplate.objects.filter(school=school, is_active=True).order_by("name")

def clean(self):
        cleaned_data = super().clean()

        student = cleaned_data.get("student")
        school_class = cleaned_data.get("school_class")
        session = cleaned_data.get("session")
        term = cleaned_data.get("term")

        if student and school_class and session and term:
            exists = ResultSheet.objects.filter(
                school=student.school,
                student=student,
                school_class=school_class,
                session=session,
                term=term,
            )

            if self.instance.pk:
                exists = exists.exclude(pk=self.instance.pk)

            if exists.exists():
                raise forms.ValidationError(
                    "A result sheet already exists for this student, class, session, and term."
                )

        return cleaned_data
        

class SubjectResultForm(forms.ModelForm):
    class Meta:
        model = SubjectResult
        fields = ["subject", "ca_score", "exam_score"]
        widgets = {
            "subject": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "ca_score": forms.NumberInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "step": "0.01"}),
            "exam_score": forms.NumberInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3", "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        self.school = kwargs.pop("school", None)
        self.teacher = kwargs.pop("teacher", None)
        self.school_class = kwargs.pop("school_class", None)
        self.sheet = kwargs.pop("sheet", None)

        super().__init__(*args, **kwargs)

        if self.school:
            queryset = Subject.objects.filter(school=self.school, is_active=True)

            if self.teacher and self.school_class:
                from staffs.models import TeacherSubjectAllocation
                subject_ids = TeacherSubjectAllocation.objects.filter(
                    school=self.school,
                    teacher=self.teacher,
                    school_class=self.school_class,
                    is_active=True,
                ).values_list("subject_id", flat=True)
                queryset = queryset.filter(id__in=subject_ids)

            if self.sheet and not self.instance.pk:
                used_subject_ids = SubjectResult.objects.filter(
                    result_sheet=self.sheet
                ).values_list("subject_id", flat=True)

                queryset = queryset.exclude(id__in=used_subject_ids)

            self.fields["subject"].queryset = queryset.order_by("name")

    def clean(self):
        cleaned_data = super().clean()

        ca_score = cleaned_data.get("ca_score") or Decimal("0")
        exam_score = cleaned_data.get("exam_score") or Decimal("0")

        # ❌ Basic validation
        if ca_score < 0:
            self.add_error("ca_score", "CA score cannot be negative.")
        if exam_score < 0:
            self.add_error("exam_score", "Exam score cannot be negative.")

        # 🔥 NEW: Dynamic limits from Assessment Template
        max_ca = Decimal("30")
        max_exam = Decimal("70")

        if self.sheet and self.sheet.assessment_template:
            components = self.sheet.assessment_template.components.all()

            for comp in components:
                name = comp.name.lower()

                if name in ["ca", "continuous assessment"]:
                    max_ca = comp.max_score
                elif name in ["exam", "examination"]:
                    max_exam = comp.max_score

        # ❌ Apply dynamic limits
        if ca_score > max_ca:
            self.add_error("ca_score", f"CA score cannot be greater than {max_ca}.")

        if exam_score > max_exam:
            self.add_error("exam_score", f"Exam score cannot be greater than {max_exam}.")

        return cleaned_data



class BehaviorRatingForm(forms.ModelForm):
    class Meta:
        model = BehaviorRating
        fields = ["category", "trait_name", "score", "remark", "order"]
        widgets = {
            "category": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "trait_name": forms.Select(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "score": forms.NumberInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "remark": forms.TextInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
            "order": forms.NumberInput(attrs={"class": "w-full rounded-xl border border-slate-300 px-4 py-3"}),
        }

    def __init__(self, *args, **kwargs):
        sheet = kwargs.pop("sheet", None)
        super().__init__(*args, **kwargs)

        if sheet:
            # Get already used traits for this result sheet
            used_traits = BehaviorRating.objects.filter(
                result_sheet=sheet
            ).values_list("trait_name", flat=True)

            # Filter choices
            self.fields["trait_name"].choices = [
                choice for choice in self.fields["trait_name"].choices
                if choice[0] not in used_traits
            ]

            if not self.fields["trait_name"].choices:
                self.fields["trait_name"].choices = [("", "All traits already added")]
                self.fields["trait_name"].disabled = True