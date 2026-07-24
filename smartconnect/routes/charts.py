"""
routes/charts.py
-----------------
All visual analytics are rendered server-side with Matplotlib and streamed
back as PNG images (<img src="/charts/..."> from templates). Keeping chart
generation on the server (rather than a JS charting library) matches the
project's declared tech stack (HTML/CSS/JS + Python + Matplotlib).
"""
import io

import matplotlib
matplotlib.use("Agg")  # headless rendering, no display needed
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from flask import Blueprint, session, send_file, abort, request

from db import query
from utils.auth_helpers import login_required
from utils.calculations import attendance_percentage, subject_result, calculate_sgpa

bp = Blueprint("charts", __name__, url_prefix="/charts")

# ---- shared palette so every chart looks consistent with the site theme ----
NAVY = "#1B2A4A"
AMBER = "#E8A33D"
GREEN = "#2F9E68"
RED = "#D64545"
SLATE = "#5B6472"
GRID = "#E4E1D8"
PAPER = "#F7F5F0"


def _fig_response(fig, dpi=140):
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=dpi, facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


def _style_axes(ax):
    ax.set_facecolor(PAPER)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(GRID)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=SLATE, labelsize=9)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def _no_data_fig(msg="No data yet"):
    fig, ax = plt.subplots(figsize=(6, 3), facecolor=PAPER)
    ax.set_facecolor(PAPER)
    ax.text(0.5, 0.5, msg, ha="center", va="center", fontsize=12, color=SLATE)
    ax.axis("off")
    return fig


# ============================================================
# STUDENT CHARTS  (always scoped to the logged-in student)
# ============================================================
def _current_student():
    return query("""SELECT s.* FROM students s WHERE s.user_id=?""",
                 (session.get("user_id"),), one=True)


@bp.route("/student/attendance.png")
@login_required
def student_attendance_chart():
    if session.get("role") != "student":
        abort(403)
    student = _current_student()
    subjects = query("""SELECT * FROM subjects WHERE branch_id=? AND semester=? ORDER BY name""",
                     (student["branch_id"], student["semester"]))
    if not subjects:
        return _fig_response(_no_data_fig())

    names, pcts, colors = [], [], []
    for s in subjects:
        row = query("""SELECT SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) p, COUNT(*) t
                        FROM attendance WHERE student_id=? AND subject_id=?""",
                    (student["id"], s["id"]), one=True)
        pct = attendance_percentage(row["p"] or 0, row["t"] or 0)
        names.append(s["name"] if len(s["name"]) <= 18 else s["name"][:16] + "…")
        pcts.append(pct)
        colors.append(RED if pct < 75 else (AMBER if pct < 80 else GREEN))

    fig, ax = plt.subplots(figsize=(8.2, 4.2), facecolor=PAPER)
    _style_axes(ax)
    bars = ax.bar(names, pcts, color=colors, width=0.55, zorder=3)
    ax.axhline(75, color=RED, linestyle="--", linewidth=1, alpha=0.7)
    ax.text(len(names) - 0.5, 76, "75% eligibility line", color=RED, fontsize=8, ha="right")
    ax.set_ylim(0, 105)
    ax.set_ylabel("Attendance %")
    ax.set_title(f"Subject-wise Attendance — Semester {student['semester']}",
                 color=NAVY, fontsize=12, fontweight="bold", loc="left")
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    for b, p in zip(bars, pcts):
        ax.text(b.get_x() + b.get_width() / 2, p + 1.5, f"{p:.0f}%", ha="center",
                fontsize=8, color=NAVY)
    return _fig_response(fig)


@bp.route("/student/performance.png")
@login_required
def student_performance_chart():
    if session.get("role") != "student":
        abort(403)
    student = _current_student()
    subjects = query("""SELECT * FROM subjects WHERE branch_id=? AND semester=? ORDER BY name""",
                     (student["branch_id"], student["semester"]))
    if not subjects:
        return _fig_response(_no_data_fig())

    names, internal_pcts, external_pcts = [], [], []
    for s in subjects:
        internals = query("""SELECT marks_obtained, max_marks FROM internal_marks
                              WHERE student_id=? AND subject_id=?""", (student["id"], s["id"]))
        iavg = (sum(i["marks_obtained"] for i in internals) / len(internals)) if internals else 0
        imax = internals[0]["max_marks"] if internals else 50
        ext = query("""SELECT marks_obtained, max_marks FROM external_marks
                        WHERE student_id=? AND subject_id=?""", (student["id"], s["id"]), one=True)
        names.append(s["name"] if len(s["name"]) <= 16 else s["name"][:14] + "…")
        internal_pcts.append(round(iavg / imax * 100, 1) if imax else 0)
        external_pcts.append(round(ext["marks_obtained"] / ext["max_marks"] * 100, 1) if ext else 0)

    x = range(len(names))
    width = 0.36
    fig, ax = plt.subplots(figsize=(8.4, 4.2), facecolor=PAPER)
    _style_axes(ax)
    ax.bar([i - width / 2 for i in x], internal_pcts, width, label="Internal (CIE)", color=NAVY, zorder=3)
    ax.bar([i + width / 2 for i in x], external_pcts, width, label="External (SEE)", color=AMBER, zorder=3)
    ax.set_xticks(list(x))
    ax.set_xticklabels(names, rotation=30, ha="right")
    ax.set_ylabel("Score %")
    ax.set_ylim(0, 110)
    ax.set_title(f"Internal vs External Performance — Semester {student['semester']}",
                 color=NAVY, fontsize=12, fontweight="bold", loc="left")
    ax.legend(frameon=False, loc="upper right", fontsize=9)
    return _fig_response(fig)


@bp.route("/student/sgpa-trend.png")
@login_required
def student_sgpa_trend_chart():
    if session.get("role") != "student":
        abort(403)
    student = _current_student()

    sems, sgpas = [], []
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
            sems.append(f"Sem {sem}")
            sgpas.append(calculate_sgpa(results))

    if not sgpas:
        return _fig_response(_no_data_fig("SGPA history will appear after semester 1 completes"))

    fig, ax = plt.subplots(figsize=(7.5, 3.8), facecolor=PAPER)
    _style_axes(ax)
    ax.plot(sems, sgpas, color=NAVY, marker="o", linewidth=2.2, markersize=6,
            markerfacecolor=AMBER, markeredgecolor=NAVY, zorder=3)
    for i, v in enumerate(sgpas):
        ax.text(i, v + 0.15, f"{v:.2f}", ha="center", fontsize=8, color=NAVY)
    ax.set_ylim(0, 10.5)
    ax.set_ylabel("SGPA")
    ax.set_title("SGPA Trend", color=NAVY, fontsize=12, fontweight="bold", loc="left")
    return _fig_response(fig)


# ============================================================
# TEACHER CHARTS (scoped to a teacher_subjects assignment they own)
# ============================================================
def _current_teacher():
    return query("SELECT * FROM teachers WHERE user_id=?", (session.get("user_id"),), one=True)


def _owned_assignment(ts_id):
    teacher = _current_teacher()
    return teacher, query("""SELECT ts.*, s.name, s.semester, s.credits FROM teacher_subjects ts
                              JOIN subjects s ON s.id = ts.subject_id
                              WHERE ts.id=? AND ts.teacher_id=?""",
                          (ts_id, teacher["id"] if teacher else -1), one=True)


@bp.route("/teacher/class-attendance.png")
@login_required
def teacher_class_attendance_chart():
    if session.get("role") != "teacher":
        abort(403)
    ts_id = request.args.get("ts_id", type=int)
    teacher, assignment = _owned_assignment(ts_id)
    if not assignment:
        return _fig_response(_no_data_fig("Select a class to view its chart"))

    roster = query("""SELECT st.id, u.full_name FROM students st JOIN users u ON u.id=st.user_id
                       WHERE st.branch_id=? AND st.semester=? AND st.section=?""",
                   (teacher["branch_id"], assignment["semester"], assignment["section"]))
    if not roster:
        return _fig_response(_no_data_fig())

    buckets = {"< 75% (Shortage)": 0, "75-85%": 0, "85%+": 0}
    for st in roster:
        row = query("""SELECT SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) p, COUNT(*) t
                        FROM attendance WHERE student_id=? AND subject_id=?""",
                    (st["id"], assignment["subject_id"]), one=True)
        pct = attendance_percentage(row["p"] or 0, row["t"] or 0)
        if pct < 75:
            buckets["< 75% (Shortage)"] += 1
        elif pct < 85:
            buckets["75-85%"] += 1
        else:
            buckets["85%+"] += 1

    fig, ax = plt.subplots(figsize=(6.2, 4), facecolor=PAPER)
    _style_axes(ax)
    colors = [RED, AMBER, GREEN]
    bars = ax.bar(buckets.keys(), buckets.values(), color=colors, width=0.5, zorder=3)
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax.set_ylabel("Number of students")
    ax.set_title(f"Attendance Distribution — {assignment['name']} ({assignment['section']})",
                 color=NAVY, fontsize=11, fontweight="bold", loc="left")
    for b, v in zip(bars, buckets.values()):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.1, str(v), ha="center", fontsize=9, color=NAVY)
    return _fig_response(fig)


@bp.route("/teacher/class-marks.png")
@login_required
def teacher_class_marks_chart():
    if session.get("role") != "teacher":
        abort(403)
    ts_id = request.args.get("ts_id", type=int)
    teacher, assignment = _owned_assignment(ts_id)
    if not assignment:
        return _fig_response(_no_data_fig("Select a class to view its chart"))

    ext_rows = query("""SELECT marks_obtained FROM external_marks WHERE subject_id=?""",
                     (assignment["subject_id"],))
    if not ext_rows:
        return _fig_response(_no_data_fig("No external marks entered yet"))

    marks = [r["marks_obtained"] for r in ext_rows]
    fig, ax = plt.subplots(figsize=(6.6, 4), facecolor=PAPER)
    _style_axes(ax)
    ax.hist(marks, bins=[0, 40, 50, 60, 70, 80, 90, 100], color=NAVY,
            edgecolor=PAPER, zorder=3, rwidth=0.9)
    ax.axvline(40, color=RED, linestyle="--", linewidth=1)
    ax.set_xlabel("External (SEE) marks out of 100")
    ax.set_ylabel("Number of students")
    ax.set_title(f"Marks Distribution — {assignment['name']} ({assignment['section']})",
                 color=NAVY, fontsize=11, fontweight="bold", loc="left")
    return _fig_response(fig)


# ============================================================
# ADMIN CHARTS (college-wide)
# ============================================================
@bp.route("/admin/branch-distribution.png")
@login_required
def admin_branch_distribution_chart():
    if session.get("role") != "admin":
        abort(403)
    rows = query("""SELECT b.code, COUNT(s.id) c FROM branches b
                     LEFT JOIN students s ON s.branch_id=b.id GROUP BY b.id ORDER BY b.code""")
    labels = [r["code"] for r in rows]
    values = [r["c"] for r in rows]
    if not any(values):
        return _fig_response(_no_data_fig())

    colors = [NAVY, AMBER, GREEN, SLATE, RED, "#7C8CD8"]
    fig, ax = plt.subplots(figsize=(5.6, 4.4), facecolor=PAPER)
    wedges, texts, autotexts = ax.pie(values, labels=labels, autopct="%1.0f%%",
                                       colors=colors[:len(labels)], startangle=90,
                                       textprops={"color": NAVY, "fontsize": 10},
                                       wedgeprops={"edgecolor": PAPER, "linewidth": 2})
    ax.set_title("Student Distribution by Branch", color=NAVY, fontsize=12,
                 fontweight="bold", loc="left")
    return _fig_response(fig)


@bp.route("/admin/attendance-overview.png")
@login_required
def admin_attendance_overview_chart():
    if session.get("role") != "admin":
        abort(403)
    rows = query("""
        SELECT b.code, st.id sid,
               SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) p, COUNT(a.id) t
        FROM students st JOIN branches b ON b.id = st.branch_id
        LEFT JOIN attendance a ON a.student_id = st.id
        GROUP BY st.id""")
    from collections import defaultdict
    branch_pcts = defaultdict(list)
    for r in rows:
        if r["t"]:
            branch_pcts[r["code"]].append(attendance_percentage(r["p"], r["t"]))

    if not branch_pcts:
        return _fig_response(_no_data_fig())

    labels = sorted(branch_pcts.keys())
    avgs = [sum(branch_pcts[b]) / len(branch_pcts[b]) for b in labels]

    fig, ax = plt.subplots(figsize=(6, 4), facecolor=PAPER)
    _style_axes(ax)
    colors = [RED if a < 75 else (AMBER if a < 85 else GREEN) for a in avgs]
    bars = ax.bar(labels, avgs, color=colors, width=0.5, zorder=3)
    ax.axhline(75, color=RED, linestyle="--", linewidth=1)
    ax.set_ylim(0, 100)
    ax.set_ylabel("Average attendance %")
    ax.set_title("College-wide Attendance by Branch", color=NAVY, fontsize=12,
                 fontweight="bold", loc="left")
    for b, v in zip(bars, avgs):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v:.0f}%", ha="center",
                fontsize=9, color=NAVY)
    return _fig_response(fig)
