# SmartConnect — College Management System

A full-stack web app for an engineering college covering **Attendance**,
**Performance Analysis (SGPA/CGPA)**, and a **Job Portal**, for three
roles: Admin, Teacher and Student.

Tech stack: **Python (Flask)** · **HTML/CSS/JS (Jinja templates)** ·
**SQLite** · **Matplotlib** (server-rendered charts) · **scikit-learn**
(AI placement-readiness score).

## 1. Setup

```bash
cd smartconnect
python3 -m venv venv          # optional but recommended
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
python seed.py                 # builds schema.sql + fills demo data
python app.py                  # runs on http://localhost:5000
```

## 2. Demo logins

| Role    | Username                        | Password    |
|---------|----------------------------------|-------------|
| Admin   | `admin`                          | `admin123`  |
| Teacher | `cse.t1` (also `ise.t1`, `ece.t1`, …) | `teach123`  |
| Student | any seeded USN, lowercase, e.g. `1sc21cse025` | `student123` |

Run `python seed.py` again any time to reset the database to a fresh
demo state (it wipes and rebuilds everything).

## 3. Project layout

```
smartconnect/
├── app.py                 # Flask entry point / blueprint registration
├── db.py                  # sqlite3 connection + query/execute helpers
├── schema.sql              # full database schema
├── seed.py                 # demo data generator
├── requirements.txt
├── routes/
│   ├── auth.py              # login / logout
│   ├── admin.py              # admin: students, teachers, subjects, jobs
│   ├── teacher.py             # teacher: attendance, marks, leave review
│   ├── student.py              # student: attendance, leave, performance, jobs
│   └── charts.py               # Matplotlib chart endpoints (PNG)
├── utils/
│   ├── calculations.py         # attendance %, grading, SGPA/CGPA
│   ├── ai_predictor.py          # placement-readiness ML model
│   └── auth_helpers.py           # session/login decorators
├── templates/               # Jinja2 HTML (base.html + per-role folders)
└── static/css/style.css      # design system (see full explanation)
```

See the chat response for the complete architectural write-up, the
attendance/SGPA/CGPA formulas, and how the AI model works.
