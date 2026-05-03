def generate_teacher_comment(sheet):
    avg = float(sheet.average_score or 0)

    if avg >= 80:
        return "Excellent performance. Keep up the outstanding work."
    elif avg >= 70:
        return "Very good performance. Maintain the effort and aim even higher."
    elif avg >= 60:
        return "Good performance. More consistency will lead to better results."
    elif avg >= 50:
        return "Fair performance. There is room for improvement with more dedication."
    else:
        return "Performance needs improvement. More hard work and focus are required."


def generate_headteacher_comment(sheet):
    avg = float(sheet.average_score or 0)

    if avg >= 80:
        return "An excellent result. The student has shown strong academic promise."
    elif avg >= 70:
        return "A very commendable performance. The student is progressing well."
    elif avg >= 60:
        return "A good result. Continued effort will produce stronger achievement."
    elif avg >= 50:
        return "An average performance. The student should work harder for improvement."
    else:
        return "The student needs serious academic improvement and closer attention."


def generate_performance_summary(sheet):
    avg = float(sheet.average_score or 0)
    total = float(sheet.total_obtained or 0)
    percentage = float(sheet.percentage or 0)

    return (
        f"Student obtained {total:.2f} total marks "
        f"with an average score of {avg:.2f} "
        f"and percentage of {percentage:.2f}%."
    )