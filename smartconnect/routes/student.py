from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from db import query, execute
from utils.auth_helpers import login_required, role_required
from utils.calculations import (attendance_percentage, attendance_alert_level,
                                 subject_result, calculate_sgpa, calculate_cgpa)
from utils.ai_predictor import predict_placement_readiness

bp = Blueprint("student", __name__, url_prefix="/student")


def _get_student():
    """Resolve the students row for the logged-in user."""
    return query("""SELECT s.*, b.code AS branch_code, b.name AS branch_name
                     FROM students s JOIN branches b ON b.id = s.branch_id
                     WHERE s.user_id=?""", (session["user_id"],), one=True)


def _subject_attendance(student_id, subject_id):
    row = query("""SELECT
                      SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) AS present,
                      COUNT(*) AS total
                    FROM attendance WHERE student_id=? AND subject_id=?""",
                (student_id, subject_id), one=True)
    present, total = row["present"] or 0, row["total"] or 0
    return present, total, attendance_percentage(present, total)


def _current_subjects(student):
    return query("""SELECT * FROM subjects WHERE branch_id=? AND semester=? ORDER BY name""",
                 (student["branch_id"], student["semester"]))


@bp.route("/dashboard")
@role_required("student")
def dashboard():
    student = _get_student()
    subjects = _current_subjects(student)

    total_present, total_classes = 0, 0
    subject_attendance = []
    for subj in subjects:
        present, total, pct = _subject_attendance(student["id"], subj["id"])
        total_present += present
        total_classes += total
        subject_attendance.append({"subject": subj, "present": present, "total": total,
                                    "pct": pct, "level": attendance_alert_level(pct)})

    overall_pct = attendance_percentage(total_present, total_classes)
    shortage_subjects = [s for s in subject_attendance if s["level"] == "danger"]

    pending_leaves = query("""SELECT COUNT(*) c FROM leave_applications
                               WHERE student_id=? AND status='Pending'""",
                           (student["id"],), one=True)["c"]

    my_apps = query("""SELECT COUNT(*) c FROM job_applications WHERE student_id=?""",
                    (student["id"],), one=True)["c"]

    backlog_count = query("""
        SELECT COUNT(*) c FROM subjects s
        WHERE s.branch_id=? AND s.semester < ?
        AND NOT EXISTS (
            SELECT 1 FROM external_marks em WHERE em.student_id=? AND em.subject_id=s.id
            AND em.marks_obtained >= em.max_marks * 0.4
        )""", (student["branch_id"], student["semester"], student["id"]), one=True)["c"]

    readiness = predict_placement_readiness(overall_pct, student["cgpa"] or 0, backlog_count)

    return render_template("student/dashboard.html", student=student,
                            overall_pct=overall_pct, subject_attendance=subject_attendance,
                            shortage_subjects=shortage_subjects, pending_leaves=pending_leaves,
                            my_apps=my_apps, readiness=readiness, backlog_count=backlog_count)


@bp.route("/attendance")
@role_required("student")
def attendance():
    student = _get_student()
    subjects = _current_subjects(student)
    subject_attendance = []
    for subj in subjects:
        present, total, pct = _subject_attendance(student["id"], subj["id"])
        recent = query("""SELECT class_date, status FROM attendance
                           WHERE student_id=? AND subject_id=?
                           ORDER BY class_date DESC LIMIT 10""", (student["id"], subj["id"]))
        subject_attendance.append({"subject": subj, "present": present, "total": total,
                                    "pct": pct, "level": attendance_alert_level(pct),
                                    "recent": recent})
    return render_template("student/attendance.html", student=student,
                            subject_attendance=subject_attendance)


@bp.route("/leave", methods=["GET", "POST"])
@role_required("student")
def leave():
    student = _get_student()
    subjects = _current_subjects(student)

    if request.method == "POST":
        subject_id = request.form.get("subject_id") or None
        from_date = request.form.get("from_date")
        to_date = request.form.get("to_date")
        reason = request.form.get("reason", "").strip()

        if not from_date or not to_date or not reason:
            flash("Please fill in all fields.", "error")
        elif from_date > to_date:
            flash("From date cannot be after to date.", "error")
        else:
            execute("""INSERT INTO leave_applications (student_id, subject_id, from_date, to_date, reason)
                       VALUES (?,?,?,?,?)""", (student["id"], subject_id, from_date, to_date, reason))
            flash("Leave application submitted for review.", "success")
            return redirect(url_for("student.leave"))

    history = query("""SELECT la.*, s.name AS subject_name FROM leave_applications la
                        LEFT JOIN subjects s ON s.id = la.subject_id
                        WHERE la.student_id=? ORDER BY la.applied_on DESC""", (student["id"],))
    return render_template("student/leave.html", student=student, subjects=subjects,
                            history=history, today=date.today().isoformat())


@bp.route("/performance")
@role_required("student")
def performance():
    student = _get_student()
    subjects = _current_subjects(student)

    subject_rows = []
    for subj in subjects:
        internals = query("""SELECT internal_no, marks_obtained, max_marks FROM internal_marks
                              WHERE student_id=? AND subject_id=? ORDER BY internal_no""",
                          (student["id"], subj["id"]))
        internal_avg = (sum(i["marks_obtained"] for i in internals) / len(internals)
                         if internals else 0)
        internal_max = internals[0]["max_marks"] if internals else 50
        ext = query("""SELECT marks_obtained, max_marks FROM external_marks
                        WHERE student_id=? AND subject_id=?""",
                    (student["id"], subj["id"]), one=True)
        ext_marks = ext["marks_obtained"] if ext else None
        ext_max = ext["max_marks"] if ext else 100

        result = subject_result(internal_avg, internal_max, ext_marks, ext_max)
        subject_rows.append({"subject": subj, "internals": internals,
                              "internal_avg": round(internal_avg, 1), "internal_max": internal_max,
                              "ext_marks": ext_marks, "ext_max": ext_max, **result})

    sgpa_ready = [s for s in subject_rows if s["ext_marks"] is not None]
    current_sgpa = calculate_sgpa([{"credits": s["subject"]["credits"],
                                     "grade_point": s["grade_point"]} for s in sgpa_ready]) \
        if sgpa_ready else None

    # semester-wise history for SGPA trend / CGPA
    sem_history = []
    for sem in range(1, student["semester"]):
        subs = query("SELECT * FROM subjects WHERE branch_id=? AND semester=?",
                     (student["branch_id"], sem))
        results = []
        for s in subs:
            internals = query("""SELECT marks_obtained FROM internal_marks
                                  WHERE student_id=? AND subject_id=?""", (student["id"], s["id"]))
            iavg = sum(i["marks_obtained"] for i in internals) / len(internals) if internals else 0
            ext = query("""SELECT marks_obtained, max_marks FROM external_marks
                            WHERE student_id=? AND subject_id=?""",
                        (student["id"], s["id"]), one=True)
            if ext:
                r = subject_result(iavg, 50, ext["marks_obtained"], ext["max_marks"])
                results.append({"credits": s["credits"], "grade_point": r["grade_point"]})
        if results:
            sgpa = calculate_sgpa(results)
            sem_history.append({"semester": sem, "sgpa": sgpa,
                                 "total_credits": sum(r["credits"] for r in results)})

    cgpa = calculate_cgpa(sem_history) if sem_history else 0

    return render_template("student/performance.html", student=student,
                            subject_rows=subject_rows, current_sgpa=current_sgpa,
                            sem_history=sem_history, cgpa=cgpa)


@bp.route("/jobs")
@role_required("student")
def jobs():
    student = _get_student()
    all_jobs = query("SELECT * FROM jobs WHERE status='Open' ORDER BY last_date")
    applied_ids = {r["job_id"] for r in query(
        "SELECT job_id FROM job_applications WHERE student_id=?", (student["id"],))}

    job_list = []
    for j in all_jobs:
        allowed = j["allowed_branches"].split(",")
        eligible_branch = "ALL" in allowed or student["branch_code"] in allowed
        eligible_cgpa = (student["cgpa"] or 0) >= j["min_cgpa"]
        job_list.append({"job": j, "eligible": eligible_branch and eligible_cgpa,
                          "eligible_branch": eligible_branch, "eligible_cgpa": eligible_cgpa,
                          "applied": j["id"] in applied_ids})
    return render_template("student/jobs.html", student=student, job_list=job_list)


@bp.route("/jobs/<int:job_id>/apply", methods=["GET", "POST"])
@role_required("student")
def apply_job(job_id):
    student = _get_student()
    job = query("SELECT * FROM jobs WHERE id=?", (job_id,), one=True)
    if not job:
        flash("Job not found.", "error")
        return redirect(url_for("student.jobs"))

    already = query("SELECT id FROM job_applications WHERE job_id=? AND student_id=?",
                    (job_id, student["id"]), one=True)

    if request.method == "POST":
        if already:
            flash("You have already applied to this job.", "error")
            return redirect(url_for("student.jobs"))
        phone = request.form.get("phone", "").strip()
        resume_link = request.form.get("resume_link", "").strip()
        cover_note = request.form.get("cover_note", "").strip()
        if not phone or not resume_link:
            flash("Phone and resume link are required.", "error")
        else:
            execute("""INSERT INTO job_applications (job_id, student_id, phone, resume_link, cover_note)
                       VALUES (?,?,?,?,?)""", (job_id, student["id"], phone, resume_link, cover_note))
            flash("Application submitted successfully!", "success")
            return redirect(url_for("student.my_applications"))

    return render_template("student/apply_job.html", student=student, job=job, already=already)


@bp.route("/applications")
@role_required("student")
def my_applications():
    student = _get_student()
    apps = query("""SELECT ja.*, j.title, j.company, j.package_lpa FROM job_applications ja
                     JOIN jobs j ON j.id = ja.job_id
                     WHERE ja.student_id=? ORDER BY ja.applied_on DESC""", (student["id"],))
    return render_template("student/my_applications.html", student=student, apps=apps)
