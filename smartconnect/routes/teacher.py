from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from db import query, execute
from utils.auth_helpers import role_required
from utils.calculations import attendance_percentage, attendance_alert_level

bp = Blueprint("teacher", __name__, url_prefix="/teacher")


def _get_teacher():
    return query("""SELECT t.*, b.code AS branch_code, b.name AS branch_name
                     FROM teachers t JOIN branches b ON b.id = t.branch_id
                     WHERE t.user_id=?""", (session["user_id"],), one=True)


def _my_assignments(teacher_id):
    """Distinct subject+section combos this teacher handles."""
    return query("""SELECT ts.id AS ts_id, ts.section, s.id AS subject_id, s.code, s.name,
                            s.semester, s.credits
                     FROM teacher_subjects ts JOIN subjects s ON s.id = ts.subject_id
                     WHERE ts.teacher_id=? ORDER BY s.semester, s.name, ts.section""",
                 (teacher_id,))


def _roster(subject_id, section, branch_id, semester):
    return query("""SELECT st.*, u.full_name FROM students st
                     JOIN users u ON u.id = st.user_id
                     WHERE st.branch_id=? AND st.semester=? AND st.section=?
                     ORDER BY st.usn""", (branch_id, semester, section))


@bp.route("/dashboard")
@role_required("teacher")
def dashboard():
    teacher = _get_teacher()
    assignments = _my_assignments(teacher["id"])

    pending_leaves = query("""SELECT COUNT(*) c FROM leave_applications la
                               JOIN subjects s ON s.id = la.subject_id
                               JOIN teacher_subjects ts ON ts.subject_id = s.id
                               WHERE ts.teacher_id=? AND la.status='Pending'""",
                           (teacher["id"],), one=True)["c"]

    subject_ids = {a["subject_id"] for a in assignments}
    total_students = query("""SELECT COUNT(DISTINCT st.id) c FROM students st
                               WHERE st.branch_id=?""", (teacher["branch_id"],), one=True)["c"]

    return render_template("teacher/dashboard.html", teacher=teacher, assignments=assignments,
                            pending_leaves=pending_leaves, total_students=total_students,
                            subject_count=len(subject_ids))


@bp.route("/attendance", methods=["GET"])
@role_required("teacher")
def attendance_select():
    teacher = _get_teacher()
    assignments = _my_assignments(teacher["id"])
    return render_template("teacher/attendance_select.html", teacher=teacher,
                            assignments=assignments, today=date.today().isoformat())


@bp.route("/attendance/mark", methods=["GET", "POST"])
@role_required("teacher")
def mark_attendance():
    teacher = _get_teacher()
    ts_id = request.args.get("ts_id", type=int) or request.form.get("ts_id", type=int)
    class_date = request.args.get("class_date") or request.form.get("class_date")

    assignment = query("""SELECT ts.*, s.name AS subject_name, s.code, s.semester
                           FROM teacher_subjects ts JOIN subjects s ON s.id = ts.subject_id
                           WHERE ts.id=? AND ts.teacher_id=?""", (ts_id, teacher["id"]), one=True)
    if not assignment:
        flash("Invalid class selection.", "error")
        return redirect(url_for("teacher.attendance_select"))

    roster = _roster(assignment["subject_id"], assignment["section"],
                      teacher["branch_id"], assignment["semester"])

    if request.method == "POST":
        for student in roster:
            status = request.form.get(f"status_{student['id']}", "Absent")
            execute("""INSERT INTO attendance (student_id, subject_id, class_date, status, marked_by)
                       VALUES (?,?,?,?,?)
                       ON CONFLICT(student_id, subject_id, class_date)
                       DO UPDATE SET status=excluded.status, marked_by=excluded.marked_by""",
                    (student["id"], assignment["subject_id"], class_date, status, teacher["id"]))
        flash(f"Attendance saved for {assignment['subject_name']} ({assignment['section']}) on {class_date}.",
              "success")
        return redirect(url_for("teacher.dashboard"))

    existing = {r["student_id"]: r["status"] for r in query(
        """SELECT student_id, status FROM attendance
           WHERE subject_id=? AND class_date=?""", (assignment["subject_id"], class_date))}

    return render_template("teacher/mark_attendance.html", teacher=teacher, assignment=assignment,
                            roster=roster, class_date=class_date, existing=existing)


@bp.route("/leaves", methods=["GET", "POST"])
@role_required("teacher")
def leaves():
    teacher = _get_teacher()

    if request.method == "POST":
        leave_id = request.form.get("leave_id", type=int)
        decision = request.form.get("decision")
        if decision in ("Approved", "Rejected"):
            execute("""UPDATE leave_applications
                       SET status=?, reviewed_by=?, reviewed_on=datetime('now')
                       WHERE id=?""", (decision, teacher["id"], leave_id))
            flash(f"Leave application {decision.lower()}.", "success")
        return redirect(url_for("teacher.leaves"))

    my_subject_ids = tuple(a["subject_id"] for a in _my_assignments(teacher["id"])) or (-1,)
    placeholders = ",".join("?" * len(my_subject_ids))
    pending = query(f"""SELECT la.*, u.full_name, st.usn, s.name AS subject_name
                        FROM leave_applications la
                        JOIN students st ON st.id = la.student_id
                        JOIN users u ON u.id = st.user_id
                        LEFT JOIN subjects s ON s.id = la.subject_id
                        WHERE la.status='Pending' AND (
                            la.subject_id IN ({placeholders})
                            OR (la.subject_id IS NULL AND st.branch_id=?)
                        )
                        ORDER BY la.applied_on""", (*my_subject_ids, teacher["branch_id"]))
    history = query("""SELECT la.*, u.full_name, st.usn, s.name AS subject_name
                        FROM leave_applications la
                        JOIN students st ON st.id = la.student_id
                        JOIN users u ON u.id = st.user_id
                        LEFT JOIN subjects s ON s.id = la.subject_id
                        WHERE la.status != 'Pending' AND la.reviewed_by=?
                        ORDER BY la.reviewed_on DESC LIMIT 30""", (teacher["id"],))
    return render_template("teacher/leaves.html", teacher=teacher, pending=pending, history=history)


@bp.route("/marks", methods=["GET"])
@role_required("teacher")
def marks_select():
    teacher = _get_teacher()
    assignments = _my_assignments(teacher["id"])
    return render_template("teacher/marks_select.html", teacher=teacher, assignments=assignments)


@bp.route("/marks/enter", methods=["GET", "POST"])
@role_required("teacher")
def enter_marks():
    teacher = _get_teacher()
    ts_id = request.args.get("ts_id", type=int) or request.form.get("ts_id", type=int)
    mtype = request.args.get("type") or request.form.get("type")   # 'internal1' / 'internal2' / 'internal3' / 'external'

    assignment = query("""SELECT ts.*, s.name AS subject_name, s.code, s.semester
                           FROM teacher_subjects ts JOIN subjects s ON s.id = ts.subject_id
                           WHERE ts.id=? AND ts.teacher_id=?""", (ts_id, teacher["id"]), one=True)
    if not assignment:
        flash("Invalid class selection.", "error")
        return redirect(url_for("teacher.marks_select"))

    roster = _roster(assignment["subject_id"], assignment["section"],
                      teacher["branch_id"], assignment["semester"])
    is_external = mtype == "external"
    internal_no = None if is_external else int(mtype[-1])
    max_marks = 100 if is_external else 50

    if request.method == "POST":
        for student in roster:
            raw = request.form.get(f"marks_{student['id']}", "").strip()
            if raw == "":
                continue
            try:
                marks = max(0, min(max_marks, float(raw)))
            except ValueError:
                continue
            if is_external:
                execute("""INSERT INTO external_marks (student_id, subject_id, marks_obtained, max_marks, entered_by)
                           VALUES (?,?,?,?,?)
                           ON CONFLICT(student_id, subject_id)
                           DO UPDATE SET marks_obtained=excluded.marks_obtained, entered_by=excluded.entered_by""",
                        (student["id"], assignment["subject_id"], marks, max_marks, teacher["id"]))
            else:
                execute("""INSERT INTO internal_marks
                           (student_id, subject_id, internal_no, marks_obtained, max_marks, entered_by)
                           VALUES (?,?,?,?,?,?)
                           ON CONFLICT(student_id, subject_id, internal_no)
                           DO UPDATE SET marks_obtained=excluded.marks_obtained, entered_by=excluded.entered_by""",
                        (student["id"], assignment["subject_id"], internal_no, marks, max_marks, teacher["id"]))
        flash(f"Marks saved for {assignment['subject_name']} ({assignment['section']}).", "success")
        return redirect(url_for("teacher.dashboard"))

    if is_external:
        existing = {r["student_id"]: r["marks_obtained"] for r in query(
            "SELECT student_id, marks_obtained FROM external_marks WHERE subject_id=?",
            (assignment["subject_id"],))}
    else:
        existing = {r["student_id"]: r["marks_obtained"] for r in query(
            "SELECT student_id, marks_obtained FROM internal_marks WHERE subject_id=? AND internal_no=?",
            (assignment["subject_id"], internal_no))}

    return render_template("teacher/enter_marks.html", teacher=teacher, assignment=assignment,
                            roster=roster, mtype=mtype, max_marks=max_marks, existing=existing,
                            label=("External / SEE" if is_external else f"Internal Test {internal_no}"))


@bp.route("/analytics")
@role_required("teacher")
def analytics():
    teacher = _get_teacher()
    assignments = _my_assignments(teacher["id"])
    ts_id = request.args.get("ts_id", type=int)
    selected = None
    if ts_id:
        selected = query("""SELECT ts.*, s.name AS subject_name, s.code, s.semester, s.credits
                             FROM teacher_subjects ts JOIN subjects s ON s.id = ts.subject_id
                             WHERE ts.id=? AND ts.teacher_id=?""", (ts_id, teacher["id"]), one=True)
    return render_template("teacher/analytics.html", teacher=teacher, assignments=assignments,
                            selected=selected)
