"""
seed.py
-------
Populates the database with a realistic engineering-college demo dataset:
branches, an 8-semester curriculum for 3 branches, an admin, a handful of
teachers + students, attendance history, internal/external marks and a
couple of job postings. Safe to re-run: it wipes and rebuilds the DB.

Run with:  python seed.py
"""
import random
from datetime import date, timedelta
from werkzeug.security import generate_password_hash

from db import init_db, execute, query, get_db

random.seed(42)

# ----------------------------------------------------------------------
# 1. Branches
# ----------------------------------------------------------------------
BRANCHES = [
    ("CSE", "Computer Science & Engineering"),
    ("ISE", "Information Science & Engineering"),
    ("ECE", "Electronics & Communication Engineering"),
    ("ADE", "Artificial Intelligence and Data Science"),
    ("CV", "Civil Engineering"),
    ("EEE", "Electrical and Electronics Engineering")
]

# ----------------------------------------------------------------------
# 2. Curriculum. Semesters 1-2 are common to every branch (first year).
#    Semesters 3-8 are branch specific. (credits, type)
# ----------------------------------------------------------------------
COMMON_YEAR1 = {
    1: [
        ("Engineering Mathematics I", 4, "Theory"),
        ("Engineering Physics", 4, "Theory and Lab"),
        ("Elective I", 3, "Theory"),
        ("Programming in C", 3, "Theory and Lab"),
        ("Elective II", 3, "Lab"),
        ("IDT", 1, "Lab"),
        ("English I",1,"Theory"),
        ("Kannada",1,"Theory")
    ],
    2: [
        ("Engineering Mathematics II", 4, "Theory"),
        ("Engineering Chemistry", 4, "Theory"),
        ("CAD", 3, "Lab"),
        ("Elective I", 3, "Theory"),
        ("Elective II", 3, "Lab"),
        ("Indian Constitution", 1, "Lab"),
        ("English II",1,"Theory"),
        ("SFH",1,"Theory")
    ],
}

BRANCH_CURRICULUM = {
    "CSE": {
        3: [("Data Structures", 4, "Theory"), ("Digital Design", 4, "Theory"),
            ("Discrete Mathematics", 4, "Theory"), ("OOP with Java", 4, "Theory"),
            ("Data Structures Lab", 1, "Lab")],
        4: [("Design & Analysis of Algorithms", 4, "Theory"), ("Operating Systems", 4, "Theory"),
            ("Microcontrollers", 4, "Theory"), ("Database Management Systems", 4, "Theory"),
            ("DBMS Lab", 1, "Lab")],
        5: [("Computer Networks", 4, "Theory"), ("Software Engineering", 4, "Theory"),
            ("Theory of Computation", 4, "Theory"), ("Web Technology", 3, "Theory"),
            ("Web Technology Lab", 1, "Lab")],
        6: [("Machine Learning", 4, "Theory"), ("Cloud Computing", 4, "Theory"),
            ("Compiler Design", 4, "Theory"), ("Cyber Security", 3, "Theory"),
            ("Machine Learning Lab", 1, "Lab")],
        7: [("Artificial Intelligence", 4, "Theory"), ("Big Data Analytics", 4, "Theory"),
            ("Distributed Systems", 3, "Theory"), ("Elective - Blockchain", 3, "Theory"),
            ("Major Project Phase I", 2, "Lab")],
        8: [("Mobile Application Development", 4, "Theory"), ("Elective - DevOps", 3, "Theory"),
            ("Internship", 3, "Lab"), ("Major Project Phase II", 6, "Lab")],
    },
    "ISE": {
        3: [("Data Structures", 4, "Theory"), ("Digital Design", 4, "Theory"),
            ("Discrete Mathematics", 4, "Theory"), ("Object Oriented Programming", 4, "Theory"),
            ("Data Structures Lab", 1, "Lab")],
        4: [("Design & Analysis of Algorithms", 4, "Theory"), ("Operating Systems", 4, "Theory"),
            ("Computer Organization", 4, "Theory"), ("Database Management Systems", 4, "Theory"),
            ("DBMS Lab", 1, "Lab")],
        5: [("Computer Networks", 4, "Theory"), ("Software Engineering", 4, "Theory"),
            ("Information Retrieval", 4, "Theory"), ("Web Technology", 3, "Theory"),
            ("Web Technology Lab", 1, "Lab")],
        6: [("Data Mining", 4, "Theory"), ("Cloud Computing", 4, "Theory"),
            ("System Software", 4, "Theory"), ("Cyber Security", 3, "Theory"),
            ("Data Mining Lab", 1, "Lab")],
        7: [("Artificial Intelligence", 4, "Theory"), ("Big Data Analytics", 4, "Theory"),
            ("Human Computer Interaction", 3, "Theory"), ("Elective - IoT", 3, "Theory"),
            ("Major Project Phase I", 2, "Lab")],
        8: [("Enterprise Resource Planning", 4, "Theory"), ("Elective - DevOps", 3, "Theory"),
            ("Internship", 3, "Lab"), ("Major Project Phase II", 6, "Lab")],
    },
    "ECE": {
        3: [("Network Analysis", 4, "Theory"), ("Electronic Devices & Circuits", 4, "Theory"),
            ("Digital System Design", 4, "Theory"), ("Signals & Systems", 4, "Theory"),
            ("Electronic Devices Lab", 1, "Lab")],
        4: [("Analog Electronics", 4, "Theory"), ("Control Systems", 4, "Theory"),
            ("Microcontrollers", 4, "Theory"), ("Electromagnetic Theory", 4, "Theory"),
            ("Analog Electronics Lab", 1, "Lab")],
        5: [("Digital Signal Processing", 4, "Theory"), ("Communication Systems", 4, "Theory"),
            ("VLSI Design", 4, "Theory"), ("Antennas & Wave Propagation", 3, "Theory"),
            ("DSP Lab", 1, "Lab")],
        6: [("Embedded Systems", 4, "Theory"), ("Wireless Communication", 4, "Theory"),
            ("Optical Fiber Communication", 4, "Theory"), ("Cyber Security", 3, "Theory"),
            ("Embedded Systems Lab", 1, "Lab")],
        7: [("Artificial Intelligence", 4, "Theory"), ("Satellite Communication", 4, "Theory"),
            ("Microwave Engineering", 3, "Theory"), ("Elective - IoT", 3, "Theory"),
            ("Major Project Phase I", 2, "Lab")],
        8: [("5G Technology", 4, "Theory"), ("Elective - Robotics", 3, "Theory"),
            ("Internship", 3, "Lab"), ("Major Project Phase II", 6, "Lab")],
    },
    "ADE": {
    3: [("Data Structures using Python", 4, "Theory"), ("Discrete Mathematics", 4, "Theory"),
        ("Digital Logic Design", 4, "Theory"), ("Object Oriented Programming with Java", 4, "Theory"),
        ("Data Structures Lab", 1, "Lab")],

    4: [("Design & Analysis of Algorithms", 4, "Theory"), ("Database Management Systems", 4, "Theory"),
        ("Probability & Statistics", 4, "Theory"), ("Operating Systems", 4, "Theory"),
        ("DBMS Lab", 1, "Lab")],

    5: [("Machine Learning", 4, "Theory"), ("Data Visualization", 4, "Theory"),
        ("Computer Networks", 4, "Theory"), ("Software Engineering", 3, "Theory"),
        ("Machine Learning Lab", 1, "Lab")],

    6: [("Deep Learning", 4, "Theory"), ("Big Data Analytics", 4, "Theory"),
        ("Artificial Intelligence", 4, "Theory"), ("Cloud Computing", 3, "Theory"),
        ("AI & Deep Learning Lab", 1, "Lab")],

    7: [("Natural Language Processing", 4, "Theory"), ("Data Mining & Warehousing", 4, "Theory"),
        ("Computer Vision", 3, "Theory"), ("Professional Elective", 3, "Theory"),
        ("Major Project Phase I", 2, "Lab")],

    8: [("Generative AI", 4, "Theory"), ("Open Elective", 3, "Theory"),
        ("Internship", 3, "Lab"), ("Major Project Phase II", 6, "Lab")],
},

"CV": {
    3: [("Strength of Materials", 4, "Theory"), ("Engineering Surveying", 4, "Theory"),
        ("Fluid Mechanics", 4, "Theory"), ("Building Materials", 4, "Theory"),
        ("Surveying Lab", 1, "Lab")],

    4: [("Structural Analysis", 4, "Theory"), ("Concrete Technology", 4, "Theory"),
        ("Geotechnical Engineering", 4, "Theory"), ("Hydraulics", 4, "Theory"),
        ("Concrete Lab", 1, "Lab")],

    5: [("Design of RCC Structures", 4, "Theory"), ("Transportation Engineering", 4, "Theory"),
        ("Environmental Engineering", 4, "Theory"), ("Water Resources Engineering", 3, "Theory"),
        ("Environmental Lab", 1, "Lab")],

    6: [("Steel Structures", 4, "Theory"), ("Construction Management", 4, "Theory"),
        ("Foundation Engineering", 4, "Theory"), ("Estimation & Costing", 3, "Theory"),
        ("CAD Lab", 1, "Lab")],

    7: [("Advanced Structural Engineering", 4, "Theory"), ("Pavement Engineering", 4, "Theory"),
        ("Professional Elective", 3, "Theory"), ("Open Elective", 3, "Theory"),
        ("Major Project Phase I", 2, "Lab")],

    8: [("Smart Cities & Sustainable Infrastructure", 4, "Theory"), ("Professional Elective", 3, "Theory"),
        ("Internship", 3, "Lab"), ("Major Project Phase II", 6, "Lab")],
},

"EEE": {
    3: [("Network Theory", 4, "Theory"), ("Analog Electronics", 4, "Theory"),
        ("Electrical Machines I", 4, "Theory"), ("Digital Electronics", 4, "Theory"),
        ("Electrical Machines Lab", 1, "Lab")],

    4: [("Electrical Machines II", 4, "Theory"), ("Power Electronics", 4, "Theory"),
        ("Control Systems", 4, "Theory"), ("Signals & Systems", 4, "Theory"),
        ("Power Electronics Lab", 1, "Lab")],

    5: [("Power Systems I", 4, "Theory"), ("Microcontrollers", 4, "Theory"),
        ("Electrical Measurements", 4, "Theory"), ("Renewable Energy Systems", 3, "Theory"),
        ("Microcontroller Lab", 1, "Lab")],

    6: [("Power Systems II", 4, "Theory"), ("Protection & Switchgear", 4, "Theory"),
        ("Electric Drives", 4, "Theory"), ("High Voltage Engineering", 3, "Theory"),
        ("Electric Drives Lab", 1, "Lab")],

    7: [("Smart Grid Technology", 4, "Theory"), ("Power System Operation & Control", 4, "Theory"),
        ("Professional Elective", 3, "Theory"), ("Open Elective", 3, "Theory"),
        ("Major Project Phase I", 2, "Lab")],

    8: [("Electric Vehicles", 4, "Theory"), ("Professional Elective", 3, "Theory"),
        ("Internship", 3, "Lab"), ("Major Project Phase II", 6, "Lab")],
},
}

FIRST_NAMES = ["Aarav", "Vihaan", "Aditya", "Ishaan", "Kabir", "Ananya", "Diya", "Ishita",
               "Kavya", "Meera", "Rohan", "Sahil", "Tanvi", "Neha", "Priya", "Arjun",
               "Karthik", "Sneha", "Pooja", "Varun", "Nikhil", "Ritika", "Sanjay", "Divya"]
LAST_NAMES = ["Sharma", "Gowda", "Reddy", "Iyer", "Nair", "Rao", "Kumar", "Patel",
              "Singh", "Gupta", "Shetty", "Bhat", "Kulkarni", "Desai", "Menon"]


def rand_name(used):
    while True:
        n = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        if n not in used:
            used.add(n)
            return n


def grade_point(pct):
    if pct >= 90: return 10
    if pct >= 80: return 9
    if pct >= 70: return 8
    if pct >= 60: return 7
    if pct >= 55: return 6
    if pct >= 50: return 5
    if pct >= 40: return 4
    return 0


def build():
    print("Initializing schema...")
    init_db()

    conn = get_db()
    conn.executescript("""
        DELETE FROM job_applications; DELETE FROM jobs;
        DELETE FROM external_marks; DELETE FROM internal_marks;
        DELETE FROM leave_applications; DELETE FROM attendance;
        DELETE FROM teacher_subjects; DELETE FROM subjects;
        DELETE FROM teachers; DELETE FROM students;
        DELETE FROM users; DELETE FROM branches;
    """)
    conn.commit()
    conn.close()

    used_names = set()

    # ---------------- Branches ----------------
    branch_ids = {}
    for code, name in BRANCHES:
        bid = execute("INSERT INTO branches (code, name) VALUES (?,?)", (code, name))
        branch_ids[code] = bid
    print("Branches created.")

    # ---------------- Admin ----------------
    execute("""INSERT INTO users (username, password_hash, role, full_name, email)
               VALUES (?,?,?,?,?)""",
            ("admin", generate_password_hash("admin123"), "admin",
             "Dr. Ramesh Iyengar (Principal)", "admin@smartconnect.edu"))
    print("Admin created -> username: admin / password: admin123")

    # ---------------- Subjects ----------------
    subject_ids = {}  # (branch_code, semester) -> [subject_id,...]
    for code in branch_ids:
        for sem in range(1, 9):
            subjects = COMMON_YEAR1[sem] if sem in (1, 2) else BRANCH_CURRICULUM[code][sem]
            subject_ids[(code, sem)] = []
            for name, credits, stype in subjects:
                subj_code = f"{code}{sem}{abs(hash(name)) % 900 + 100}"
                sid = execute("""INSERT OR IGNORE INTO subjects
                                  (code, name, branch_id, semester, credits, subject_type)
                                  VALUES (?,?,?,?,?,?)""",
                              (subj_code, name, branch_ids[code], sem, credits, stype))
                if not sid:
                    row = query("SELECT id FROM subjects WHERE code=?", (subj_code,), one=True)
                    sid = row["id"]
                subject_ids[(code, sem)].append(sid)
    print("Curriculum (subjects) created for all branches/semesters.")

    # ---------------- Teachers ----------------
    # a few teachers per branch, covering multiple semesters
    teacher_ids = {code: [] for code in branch_ids}
    designations = ["Assistant Professor", "Associate Professor", "Professor"]
    for code in branch_ids:
        for i in range(4):
            uname = f"{code.lower()}.t{i+1}"
            full_name = "Prof. " + rand_name(used_names)
            uid = execute("""INSERT INTO users (username, password_hash, role, full_name, email)
                              VALUES (?,?,?,?,?)""",
                          (uname, generate_password_hash("teach123"), "teacher",
                           full_name, f"{uname}@smartconnect.edu"))
            tid = execute("""INSERT INTO teachers (user_id, branch_id, designation)
                              VALUES (?,?,?)""",
                          (uid, branch_ids[code], random.choice(designations)))
            teacher_ids[code].append(tid)
    print("Teachers created (username pattern e.g. cse.t1 / password: teach123)")

    # Assign teachers to subjects (round robin) for section A and B
    for code in branch_ids:
        t_list = teacher_ids[code]
        idx = 0
        for sem in range(1, 9):
            for sid in subject_ids[(code, sem)]:
                for section in ("A", "B"):
                    execute("""INSERT INTO teacher_subjects (teacher_id, subject_id, section, academic_year)
                               VALUES (?,?,?,?)""",
                            (t_list[idx % len(t_list)], sid, section, "2025-2026"))
                    idx += 1
    print("Teacher-subject assignments created.")

    # ---------------- Students ----------------
    # 6 students per branch per semester (demo scale), split sections A/B
    student_records = []  # (student_id, branch_code, semester)
    for code in branch_ids:
        usn_counter = 1
        for sem in range(1, 9):
            for i in range(6):
                full_name = rand_name(used_names)
                usn = f"1SC{21 + ((8 - sem) // 4)}{code}{usn_counter:03d}"
                usn_counter += 1
                uname = usn.lower()
                uid = execute("""INSERT INTO users (username, password_hash, role, full_name, email)
                                  VALUES (?,?,?,?,?)""",
                              (uname, generate_password_hash("student123"), "student",
                               full_name, f"{uname}@smartconnect.edu"))
                section = "A" if i % 2 == 0 else "B"
                batch_year = f"{2026 - sem // 2}-{2030 - sem // 2}"
                stid = execute("""INSERT INTO students (user_id, usn, branch_id, semester, section, batch_year)
                                   VALUES (?,?,?,?,?,?)""",
                               (uid, usn, branch_ids[code], sem, section, batch_year))
                student_records.append((stid, code, sem, section))
    print(f"{len(student_records)} students created (username = USN, password: student123)")

    # ---------------- Attendance (last 40 working days) ----------------
    today = date.today()
    class_dates = []
    d = today
    while len(class_dates) < 40:
        if d.weekday() < 6:  # skip Sunday
            class_dates.append(d.isoformat())
        d -= timedelta(days=1)
    class_dates.reverse()

    teacher_lookup = {}  # (subject_id, section) -> teacher_id
    for row in query("SELECT teacher_id, subject_id, section FROM teacher_subjects"):
        teacher_lookup[(row["subject_id"], row["section"])] = row["teacher_id"]

    conn = get_db()
    att_rows = []
    for stid, code, sem, section in student_records:
        # each student has their own baseline attendance rate (some low, most healthy)
        base_rate = random.choice([0.95, 0.9, 0.85, 0.8, 0.7, 0.6, 0.55])
        for sid in subject_ids[(code, sem)]:
            for cdate in class_dates:
                status = "Present" if random.random() < base_rate else "Absent"
                teacher_id = teacher_lookup.get((sid, section))
                att_rows.append((stid, sid, cdate, status, teacher_id))
    conn.executemany("""INSERT OR IGNORE INTO attendance
                         (student_id, subject_id, class_date, status, marked_by)
                         VALUES (?,?,?,?,?)""", att_rows)
    conn.commit()
    conn.close()
    print(f"Attendance seeded ({len(att_rows)} records across {len(class_dates)} class days).")

    # ---------------- Internal + External marks ----------------
    conn = get_db()
    im_rows, em_rows = [], []
    for stid, code, sem, section in student_records:
        # skill level per student drives marks + is correlated with attendance a little
        skill = random.uniform(0.35, 0.97)
        # Marks must exist for every COMPLETED semester (1..sem-1) so SGPA/CGPA
        # rollups have data, plus the CURRENT semester's internals-in-progress.
        for hist_sem in range(1, sem + 1):
            for sid in subject_ids[(code, hist_sem)]:
                teacher_id = teacher_lookup.get((sid, section))
                for internal_no in (1, 2, 3):
                    noise = random.uniform(-8, 8)
                    marks = max(0, min(50, round(50 * skill + noise, 1)))
                    im_rows.append((stid, sid, internal_no, marks, 50, teacher_id))
                if hist_sem < sem:
                    # completed semester -> also has an external/SEE result
                    ext_noise = random.uniform(-12, 12)
                    ext_marks = max(0, min(100, round(100 * skill + ext_noise, 1)))
                    em_rows.append((stid, sid, ext_marks, 100, teacher_id))
    conn.executemany("""INSERT OR IGNORE INTO internal_marks
                         (student_id, subject_id, internal_no, marks_obtained, max_marks, entered_by)
                         VALUES (?,?,?,?,?,?)""", im_rows)
    conn.executemany("""INSERT OR IGNORE INTO external_marks
                         (student_id, subject_id, marks_obtained, max_marks, entered_by)
                         VALUES (?,?,?,?,?)""", em_rows)
    conn.commit()
    conn.close()
    print(f"Marks seeded: {len(im_rows)} internal rows, {len(em_rows)} external rows.")

    # ---------------- CGPA rollup (semesters strictly before current sem) ----------------
    for stid, code, sem, section in student_records:
        completed_sems = range(1, sem)  # only fully completed semesters count
        total_credit_points, total_credits = 0, 0
        for csem in completed_sems:
            subs = query("SELECT id, credits FROM subjects WHERE branch_id=? AND semester=?",
                         (branch_ids[code], csem))
            for s in subs:
                im = query("""SELECT AVG(marks_obtained) a FROM internal_marks
                               WHERE student_id=? AND subject_id=?""", (stid, s["id"]), one=True)
                em = query("""SELECT marks_obtained FROM external_marks
                               WHERE student_id=? AND subject_id=?""", (stid, s["id"]), one=True)
                if im and im["a"] is not None and em:
                    total = im["a"] + em["marks_obtained"]  # out of 150
                    pct = total / 150 * 100
                    gp = grade_point(pct)
                    total_credit_points += gp * s["credits"]
                    total_credits += s["credits"]
        cgpa = round(total_credit_points / total_credits, 2) if total_credits else 0
        execute("UPDATE students SET cgpa=? WHERE id=?", (cgpa, stid))
    print("CGPA rollup complete.")

    # ---------------- Jobs ----------------
    admin_user = query("SELECT id FROM users WHERE username='admin'", one=True)
    jobs = [
        ("Software Development Engineer", "Zynovia Tech", "Building scalable backend "
         "services in Python/Java, working closely with product teams on cloud-native "
         "systems.", "Bengaluru", "8-14 LPA", 7.0, 1, "CSE,ISE", "2026", 45),
        ("Embedded Systems Engineer", "OrbitWave Semiconductors", "Firmware development "
         "for IoT and communication devices, working with microcontrollers and RTOS.",
         "Hyderabad", "6-10 LPA", 6.5, 2, "ECE", "2026", 30),
        ("Data Analyst Intern", "Quanta Insights", "6-month internship analyzing product "
         "data, building dashboards, and supporting the analytics team.", "Remote",
         "25,000/month", 6.0, 2, "ALL", "2027", 20),
        ("Associate Cloud Engineer", "Nimbus Cloud Labs", "Deploying and maintaining "
         "cloud infrastructure on AWS/Azure, CI/CD pipeline management.", "Pune",
         "7-11 LPA", 6.8, 1, "CSE,ISE,ECE", "2026", 60),
        ("VLSI Design Engineer", "SiliconPeak Systems", "RTL design and verification "
         "for next generation chips.", "Bengaluru", "9-15 LPA", 7.5, 0, "ECE", "2026", 40),
    ]
    for title, company, desc, loc, pkg, min_cgpa, max_bl, branches_allowed, batch, days in jobs:
        last_date = (today + timedelta(days=days)).isoformat()
        execute("""INSERT INTO jobs (title, company, description, location, package_lpa,
                   min_cgpa, max_backlogs, allowed_branches, eligible_batch, last_date, posted_by)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (title, company, desc, loc, pkg, min_cgpa, max_bl, branches_allowed,
                 batch, last_date, admin_user["id"]))
    print(f"{len(jobs)} job postings created.")

    print("\nSeed complete.")
    print("=" * 60)
    print("LOGIN CREDENTIALS")
    print("  Admin    : admin / admin123")
    print("  Teacher  : cse.t1 / teach123   (also ise.t1, ece.t1, ...)")
    print("  Student  : use any generated USN (lowercase) / student123")
    row = query("SELECT usn FROM students LIMIT 1", one=True)
    if row:
        print(f"             example -> {row['usn'].lower()} / student123")
    print("=" * 60)


if __name__ == "__main__":
    build()
