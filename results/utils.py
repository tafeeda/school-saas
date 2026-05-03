from decimal import Decimal

from django.db.models import Avg, Max, Min

from .models import ResultSheet, SubjectResult


def recalculate_subject_statistics_for_sheet(result_sheet):
    """
    For each subject result in a student's sheet, calculate:
    - class highest
    - class average
    - class lowest
    across all students in the same class/session/term for that subject.
    """
    subject_results = result_sheet.subject_results.select_related("subject").all()

    for item in subject_results:
        queryset = SubjectResult.objects.filter(
            result_sheet__school=result_sheet.school,
            result_sheet__school_class=result_sheet.school_class,
            result_sheet__session=result_sheet.session,
            result_sheet__term=result_sheet.term,
            subject=item.subject,
            is_active=True,
        )

        stats = queryset.aggregate(
            highest=Max("total_score"),
            average=Avg("total_score"),
            lowest=Min("total_score"),
        )

        item.class_highest = stats["highest"] or Decimal("0")
        item.class_average = stats["average"] or Decimal("0")
        item.class_lowest = stats["lowest"] or Decimal("0")
        item.save(update_fields=["class_highest", "class_average", "class_lowest", "updated_at"])


def recalculate_positions_for_class(school, school_class, session, term):
    """
    Rank all result sheets in a class by total_obtained descending.
    Handles ties by assigning the same position to equal totals.
    """
    sheets = list(
        ResultSheet.objects.filter(
            school=school,
            school_class=school_class,
            session=session,
            term=term,
            is_active=True,
        ).order_by("-total_obtained", "student__surname", "student__first_name")
    )

    last_score = None
    last_position = 0

    for index, sheet in enumerate(sheets, start=1):
        if last_score is None or sheet.total_obtained != last_score:
            position = index
            last_position = position
            last_score = sheet.total_obtained
        else:
            position = last_position

        if hasattr(sheet, "class_position"):
            sheet.class_position = position
            sheet.class_size = len(sheets)
            sheet.save(update_fields=["class_position", "class_size", "updated_at"])


def fully_recalculate_result_sheet(result_sheet):
    """
    Recalculate:
    - subject totals/grades
    - overall sheet totals/average/percentage
    - subject statistics
    - class positions
    """
    for subject_result in result_sheet.subject_results.all():
        subject_result.recalculate()

    result_sheet.recalculate()
    recalculate_subject_statistics_for_sheet(result_sheet)
    recalculate_positions_for_class(
        school=result_sheet.school,
        school_class=result_sheet.school_class,
        session=result_sheet.session,
        term=result_sheet.term,
    )