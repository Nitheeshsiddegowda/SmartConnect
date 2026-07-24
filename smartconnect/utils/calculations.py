"""
utils/calculations.py
----------------------
All the "business rules" of SmartConnect live here so that routes stay
thin and the rules are unit-testable / reusable across templates & charts.
"""

ATTENDANCE_ELIGIBILITY_THRESHOLD = 75.0   # % below this -> shortage alert
ATTENDANCE_WARNING_THRESHOLD = 80.0       # % below this -> soft warning


def attendance_percentage(present, total):
    if total == 0:
        return 0.0
    return round((present / total) * 100, 2)


def attendance_alert_level(pct):
    """Returns 'danger' | 'warning' | 'ok' for UI badges."""
    if pct < ATTENDANCE_ELIGIBILITY_THRESHOLD:
        return "danger"
    if pct < ATTENDANCE_WARNING_THRESHOLD:
        return "warning"
    return "ok"


def grade_point(pct):
    """VTU-style 10 point grading scale from a percentage (0-100)."""
    if pct >= 90: return 10
    if pct >= 80: return 9
    if pct >= 70: return 8
    if pct >= 60: return 7
    if pct >= 55: return 6
    if pct >= 50: return 5
    if pct >= 40: return 4
    return 0


def grade_letter(pct):
    if pct >= 90: return "O"
    if pct >= 80: return "A+"
    if pct >= 70: return "A"
    if pct >= 60: return "B+"
    if pct >= 55: return "B"
    if pct >= 50: return "C"
    if pct >= 40: return "P"
    return "F"


def subject_result(internal_avg, internal_max, external_marks, external_max):
    """
    Combine CIE (internal) + SEE (external) into one subject result.
    Returns a dict with total, percentage, grade point, grade letter, pass/fail.
    """
    total_obtained = (internal_avg or 0) + (external_marks or 0)
    total_max = internal_max + external_max
    pct = round((total_obtained / total_max) * 100, 2) if total_max else 0
    passed = (external_marks or 0) >= (external_max * 0.4) and pct >= 40
    return {
        "total_obtained": round(total_obtained, 2),
        "total_max": total_max,
        "percentage": pct,
        "grade_point": grade_point(pct),
        "grade_letter": grade_letter(pct),
        "passed": passed,
    }


def calculate_sgpa(subject_results):
    """
    subject_results: list of dicts each with 'credits' and 'grade_point'
    Returns SGPA rounded to 2 decimals.
    """
    total_credits = sum(s["credits"] for s in subject_results)
    if total_credits == 0:
        return 0.0
    weighted = sum(s["credits"] * s["grade_point"] for s in subject_results)
    return round(weighted / total_credits, 2)


def calculate_cgpa(semester_results):
    """
    semester_results: list of dicts each with 'sgpa' and 'total_credits'
    Credit-weighted CGPA across all completed semesters.
    """
    total_credits = sum(s["total_credits"] for s in semester_results)
    if total_credits == 0:
        return 0.0
    weighted = sum(s["sgpa"] * s["total_credits"] for s in semester_results)
    return round(weighted / total_credits, 2)
