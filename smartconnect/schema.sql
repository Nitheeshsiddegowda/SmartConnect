-- SmartConnect database schema (SQLite dialect, portable to MySQL/PostgreSQL
-- with minor type changes: AUTOINCREMENT -> AUTO_INCREMENT / SERIAL).

PRAGMA foreign_keys = ON;

-- ===================== CORE / AUTH =====================
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('admin', 'teacher', 'student')),
    full_name     TEXT NOT NULL,
    email         TEXT,
    phone         TEXT,
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS branches (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    code  TEXT UNIQUE NOT NULL,       -- CSE, ISE, ECE, ME, CV, EEE
    name  TEXT NOT NULL
);

-- ===================== PEOPLE =====================
CREATE TABLE IF NOT EXISTS students (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    usn          TEXT UNIQUE NOT NULL,      -- University Seat Number
    branch_id    INTEGER NOT NULL REFERENCES branches(id),
    semester     INTEGER NOT NULL CHECK (semester BETWEEN 1 AND 8),
    section      TEXT NOT NULL DEFAULT 'A',
    batch_year   TEXT NOT NULL,              -- e.g. 2023-2027
    cgpa         REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS teachers (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    branch_id    INTEGER NOT NULL REFERENCES branches(id),   -- home department
    designation  TEXT NOT NULL DEFAULT 'Assistant Professor'
);

-- ===================== ACADEMIC STRUCTURE =====================
CREATE TABLE IF NOT EXISTS subjects (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    code         TEXT UNIQUE NOT NULL,
    name         TEXT NOT NULL,
    branch_id    INTEGER NOT NULL REFERENCES branches(id),
    semester     INTEGER NOT NULL CHECK (semester BETWEEN 1 AND 8),
    credits      INTEGER NOT NULL DEFAULT 4,
    subject_type TEXT NOT NULL DEFAULT 'Theory'   -- Theory / Lab
);

-- Which teacher teaches which subject, to which section
CREATE TABLE IF NOT EXISTS teacher_subjects (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id     INTEGER NOT NULL REFERENCES teachers(id) ON DELETE CASCADE,
    subject_id     INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    section        TEXT NOT NULL DEFAULT 'A',
    academic_year  TEXT NOT NULL DEFAULT '2025-2026',
    UNIQUE(teacher_id, subject_id, section, academic_year)
);

-- ===================== ATTENDANCE MODULE =====================
CREATE TABLE IF NOT EXISTS attendance (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id   INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    subject_id   INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    class_date   TEXT NOT NULL,          -- YYYY-MM-DD
    status       TEXT NOT NULL CHECK (status IN ('Present', 'Absent')),
    marked_by    INTEGER REFERENCES teachers(id),
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(student_id, subject_id, class_date)
);

CREATE TABLE IF NOT EXISTS leave_applications (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id    INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    subject_id    INTEGER REFERENCES subjects(id),   -- NULL = general leave
    from_date     TEXT NOT NULL,
    to_date       TEXT NOT NULL,
    reason        TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending','Approved','Rejected')),
    applied_on    TEXT NOT NULL DEFAULT (datetime('now')),
    reviewed_by   INTEGER REFERENCES teachers(id),
    reviewed_on   TEXT
);

-- ===================== PERFORMANCE MODULE =====================
-- Internal Assessments (CIE) - up to 3 tests per subject, each out of 50
CREATE TABLE IF NOT EXISTS internal_marks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id      INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    subject_id      INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    internal_no     INTEGER NOT NULL CHECK (internal_no IN (1,2,3)),
    marks_obtained  REAL NOT NULL,
    max_marks       REAL NOT NULL DEFAULT 50,
    entered_by      INTEGER REFERENCES teachers(id),
    entered_on      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(student_id, subject_id, internal_no)
);

-- External / Semester End Exam (SEE), out of 100
CREATE TABLE IF NOT EXISTS external_marks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id      INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    subject_id      INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    marks_obtained  REAL NOT NULL,
    max_marks       REAL NOT NULL DEFAULT 100,
    entered_by      INTEGER REFERENCES teachers(id),
    entered_on      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(student_id, subject_id)
);

-- ===================== JOB PORTAL MODULE =====================
CREATE TABLE IF NOT EXISTS jobs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    title            TEXT NOT NULL,
    company          TEXT NOT NULL,
    description      TEXT NOT NULL,
    location         TEXT NOT NULL DEFAULT 'Bengaluru',
    package_lpa      TEXT,
    min_cgpa         REAL NOT NULL DEFAULT 0,
    max_backlogs     INTEGER NOT NULL DEFAULT 0,
    allowed_branches TEXT NOT NULL DEFAULT 'ALL',   -- comma separated branch codes or ALL
    eligible_batch   TEXT,
    last_date        TEXT NOT NULL,
    posted_by        INTEGER REFERENCES users(id),
    posted_on        TEXT NOT NULL DEFAULT (datetime('now')),
    status           TEXT NOT NULL DEFAULT 'Open' CHECK (status IN ('Open','Closed'))
);

CREATE TABLE IF NOT EXISTS job_applications (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id          INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    student_id      INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    phone           TEXT NOT NULL,
    resume_link     TEXT NOT NULL,
    cover_note      TEXT,
    status          TEXT NOT NULL DEFAULT 'Applied' CHECK (status IN ('Applied','Shortlisted','Rejected','Selected')),
    applied_on      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_on      TEXT,
    UNIQUE(job_id, student_id)
);

-- ===================== INDEXES =====================
CREATE INDEX IF NOT EXISTS idx_attendance_student_subject ON attendance(student_id, subject_id);
CREATE INDEX IF NOT EXISTS idx_internal_student_subject ON internal_marks(student_id, subject_id);
CREATE INDEX IF NOT EXISTS idx_subjects_branch_sem ON subjects(branch_id, semester);
CREATE INDEX IF NOT EXISTS idx_jobapp_job ON job_applications(job_id);
