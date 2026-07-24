from werkzeug.security import generate_password_hash

from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from db import query, execute
from utils.auth_helpers import role_required

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/dashboard")
@role_required("admin")
def dashboard():
    stats = {
        "students": query("SELECT COUNT(*) c FROM students", one=True)["c"],
        "teachers": query("SELECT COUNT(*) c FROM teachers", one=True)["c"],
        "subjects": query("SELECT COUNT(*) c FROM subjects", one=True)["c"],
        "open_jobs": query("SELECT COUNT(*) c FROM jobs WHERE status='Open'", one=True)["c"],
        "applications": query("SELECT COUNT(*) c FROM job_applications", one=True)["c"],
        "pending_leaves": query("SELECT COUNT(*) c FROM leave_applications WHERE status='Pending'",
                                one=True)["c"],
    }
    branch_breakdown = query("""SELECT b.name, b.code, COUNT(s.id) c FROM branches b
                                 LEFT JOIN students s ON s.branch_id = b.id
                                 GROUP BY b.id ORDER BY b.name""")
    low_attendance = query("""
        SELECT u.full_name, st.usn, b.code AS branch_code, st.semester,
               SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) present,
               COUNT(a.id) total
        FROM students st
        JOIN users u ON u.id = st.user_id
        JOIN branches b ON b.id = st.branch_id
        LEFT JOIN attendance a ON a.student_id = st.id
        GROUP BY st.id
        HAVING total > 0 AND (present * 100.0 / total) < 75
        ORDER BY (present * 1.0 / total) ASC LIMIT 10""")
    return render_template("admin/dashboard.html", stats=stats,
                            branch_breakdown=branch_breakdown, low_attendance=low_attendance)


@bp.route("/students")
@role_required("admin")
def students():
    branch = request.args.get("branch", "")
    semester = request.args.get("semester", "")
    sql = """SELECT st.*, u.full_name, u.email, u.is_active, b.code AS branch_code
              FROM students st JOIN users u ON u.id = st.user_id
              JOIN branches b ON b.id = st.branch_id WHERE 1=1"""
    params = []
    if branch:
        sql += " AND b.code=?"
        params.append(branch)
    if semester:
        sql += " AND st.semester=?"
        params.append(semester)
    sql += " ORDER BY b.code, st.semester, st.usn"
    rows = query(sql, params)
    branches = query("SELECT * FROM branches ORDER BY code")
    return render_template("admin/students.html", rows=rows, branches=branches,
                            branch=branch, semester=semester)


@bp.route("/students/add", methods=["GET", "POST"])
@role_required("admin")
def add_student():
    branches = query("SELECT * FROM branches ORDER BY code")
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        usn = request.form.get("usn", "").strip().upper()
        branch_id = request.form.get("branch_id", type=int)
        semester = request.form.get("semester", type=int)
        section = request.form.get("section", "A")
        batch_year = request.form.get("batch_year", "").strip()
        email = request.form.get("email", "").strip()

        if not all([full_name, usn, branch_id, semester, batch_year]):
            flash("Please fill in all required fields.", "error")
            return render_template("admin/add_student.html", branches=branches)

        existing = query("SELECT id FROM users WHERE username=?", (usn.lower(),), one=True)
        if existing:
            flash("A student with that USN already exists.", "error")
            return render_template("admin/add_student.html", branches=branches)

        uid = execute("""INSERT INTO users (username, password_hash, role, full_name, email)
                          VALUES (?,?,?,?,?)""",
                      (usn.lower(), generate_password_hash("student123"), "student",
                       full_name, email))
        execute("""INSERT INTO students (user_id, usn, branch_id, semester, section, batch_year)
                   VALUES (?,?,?,?,?,?)""", (uid, usn, branch_id, semester, section, batch_year))
        flash(f"Student {full_name} added. Default password: student123", "success")
        return redirect(url_for("admin.students"))

    return render_template("admin/add_student.html", branches=branches)


@bp.route("/teachers")
@role_required("admin")
def teachers():
    rows = query("""SELECT t.*, u.full_name, u.email, u.username, b.code AS branch_code
                     FROM teachers t JOIN users u ON u.id = t.user_id
                     JOIN branches b ON b.id = t.branch_id ORDER BY b.code, u.full_name""")
    return render_template("admin/teachers.html", rows=rows)


@bp.route("/teachers/add", methods=["GET", "POST"])
@role_required("admin")
def add_teacher():
    branches = query("SELECT * FROM branches ORDER BY code")
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip().lower()
        branch_id = request.form.get("branch_id", type=int)
        designation = request.form.get("designation", "Assistant Professor")
        email = request.form.get("email", "").strip()

        if not all([full_name, username, branch_id]):
            flash("Please fill in all required fields.", "error")
            return render_template("admin/add_teacher.html", branches=branches)

        existing = query("SELECT id FROM users WHERE username=?", (username,), one=True)
        if existing:
            flash("That username is already taken.", "error")
            return render_template("admin/add_teacher.html", branches=branches)

        uid = execute("""INSERT INTO users (username, password_hash, role, full_name, email)
                          VALUES (?,?,?,?,?)""",
                      (username, generate_password_hash("teach123"), "teacher", full_name, email))
        execute("""INSERT INTO teachers (user_id, branch_id, designation) VALUES (?,?,?)""",
                (uid, branch_id, designation))
        flash(f"Teacher {full_name} added. Default password: teach123", "success")
        return redirect(url_for("admin.teachers"))

    return render_template("admin/add_teacher.html", branches=branches)


@bp.route("/teachers/<int:teacher_id>/assign", methods=["GET", "POST"])
@role_required("admin")
def assign_subjects(teacher_id):
    teacher = query("""SELECT t.*, u.full_name, b.code AS branch_code FROM teachers t
                        JOIN users u ON u.id = t.user_id JOIN branches b ON b.id = t.branch_id
                        WHERE t.id=?""", (teacher_id,), one=True)
    if not teacher:
        flash("Teacher not found.", "error")
        return redirect(url_for("admin.teachers"))

    if request.method == "POST":
        subject_id = request.form.get("subject_id", type=int)
        section = request.form.get("section", "A")
        execute("""INSERT OR IGNORE INTO teacher_subjects (teacher_id, subject_id, section, academic_year)
                   VALUES (?,?,?,?)""", (teacher_id, subject_id, section, "2025-2026"))
        flash("Subject assigned.", "success")
        return redirect(url_for("admin.assign_subjects", teacher_id=teacher_id))

    subjects = query("SELECT * FROM subjects WHERE branch_id=? ORDER BY semester, name",
                     (teacher["branch_id"],))
    current = query("""SELECT ts.id, ts.section, s.name, s.code, s.semester FROM teacher_subjects ts
                        JOIN subjects s ON s.id = ts.subject_id WHERE ts.teacher_id=?
                        ORDER BY s.semester""", (teacher_id,))
    return render_template("admin/assign_subjects.html", teacher=teacher, subjects=subjects,
                            current=current)


@bp.route("/subjects")
@role_required("admin")
def subjects():
    branch = request.args.get("branch", "CSE")
    branches = query("SELECT * FROM branches ORDER BY code")
    rows = query("""SELECT s.* FROM subjects s JOIN branches b ON b.id = s.branch_id
                     WHERE b.code=? ORDER BY s.semester, s.name""", (branch,))
    return render_template("admin/subjects.html", rows=rows, branches=branches, branch=branch)


@bp.route("/jobs")
@role_required("admin")
def jobs():
    rows = query("""SELECT j.*, (SELECT COUNT(*) FROM job_applications ja WHERE ja.job_id=j.id) app_count
                     FROM jobs j ORDER BY j.posted_on DESC""")
    return render_template("admin/jobs.html", rows=rows)


@bp.route("/jobs/post", methods=["GET", "POST"])
@role_required("admin")
def post_job():
    branches = query("SELECT * FROM branches ORDER BY code")
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        company = request.form.get("company", "").strip()
        description = request.form.get("description", "").strip()
        location = request.form.get("location", "").strip() or "Bengaluru"
        package_lpa = request.form.get("package_lpa", "").strip()
        min_cgpa = request.form.get("min_cgpa", type=float) or 0
        max_backlogs = request.form.get("max_backlogs", type=int) or 0
        allowed_branches = ",".join(request.form.getlist("branches")) or "ALL"
        eligible_batch = request.form.get("eligible_batch", "").strip()
        last_date = request.form.get("last_date")

        if not all([title, company, description, last_date]):
            flash("Please fill in all required fields.", "error")
            return render_template("admin/post_job.html", branches=branches)

        execute("""INSERT INTO jobs (title, company, description, location, package_lpa,
                   min_cgpa, max_backlogs, allowed_branches, eligible_batch, last_date, posted_by)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (title, company, description, location, package_lpa, min_cgpa, max_backlogs,
                 allowed_branches, eligible_batch, last_date, session["user_id"]))
        flash(f"Job posting '{title}' published.", "success")
        return redirect(url_for("admin.jobs"))

    return render_template("admin/post_job.html", branches=branches)


@bp.route("/jobs/<int:job_id>/applications", methods=["GET", "POST"])
@role_required("admin")
def job_applications(job_id):
    job = query("SELECT * FROM jobs WHERE id=?", (job_id,), one=True)
    if not job:
        flash("Job not found.", "error")
        return redirect(url_for("admin.jobs"))

    if request.method == "POST":
        app_id = request.form.get("app_id", type=int)
        status = request.form.get("status")
        if status in ("Applied", "Shortlisted", "Rejected", "Selected"):
            execute("""UPDATE job_applications SET status=?, updated_on=datetime('now')
                       WHERE id=?""", (status, app_id))
            flash("Application status updated.", "success")
        return redirect(url_for("admin.job_applications", job_id=job_id))

    apps = query("""SELECT ja.*, u.full_name, st.usn, b.code AS branch_code, st.cgpa, st.semester
                     FROM job_applications ja JOIN students st ON st.id = ja.student_id
                     JOIN users u ON u.id = st.user_id JOIN branches b ON b.id = st.branch_id
                     WHERE ja.job_id=? ORDER BY ja.applied_on""", (job_id,))
    return render_template("admin/job_applications.html", job=job, apps=apps)


@bp.route("/jobs/<int:job_id>/close", methods=["POST"])
@role_required("admin")
def close_job(job_id):
    execute("UPDATE jobs SET status='Closed' WHERE id=?", (job_id,))
    flash("Job posting closed.", "success")
    return redirect(url_for("admin.jobs"))
