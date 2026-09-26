# Student Management System

A desktop application for managing **student records, attendance and exam results**. It replaces manual, register-based tracking.
It is built with **Python (Tkinter)** and a **normalized MySQL database**. It also has a menu-driven console version.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue) ![MySQL](https://img.shields.io/badge/MySQL-8.0-orange) ![Tests](https://img.shields.io/badge/tests-13%20passing-brightgreen)

## Features

| Module | What it does |
|---|---|
| **Students** | Full CRUD: add, search (by roll no / name / course), update and delete student records |
| **Attendance** | Mark Present / Absent / Leave per date, "mark all present", and a per-student attendance % summary |
| **Results** | Enter marks per subject and exam term. The marksheet shows the total, percentage, grade (O / A+ / A / B+ / B / C / F) and PASS/FAIL |
| **Courses & Subjects** | Maintain courses (MCA, BCA, …) and the subjects under each |
| **Validation** | Blocks duplicate roll numbers and emails, and checks name, date, age (15–80), phone (10-digit Indian mobile), email format and marks range. Attendance can't be marked for future dates, and marks can only be entered for subjects in the student's own course |
| **Error handling** | All errors show as friendly dialogs and never crash the app. DB writes are wrapped in transactions with rollback |

## Database design (3NF)

```
courses (course_id PK, course_code UQ, course_name, duration_years)
   │1
   ├──< students (student_id PK, roll_no UQ, full_name, dob, gender, email UQ, phone, course_id FK, admission_date)
   │        │1
   │        ├──< attendance (attendance_id PK, student_id FK, att_date, status)   UNIQUE(student_id, att_date)
   │        └──< results    (result_id PK, student_id FK, subject_id FK, exam_term, marks_obtained)
   │                                                     UNIQUE(student_id, subject_id, exam_term)
   └──< subjects (subject_id PK, course_id FK, subject_code UQ, subject_name, max_marks)
```

* Course details live in one place (`courses`), and students and subjects only reference them, so nothing is repeated.
* `ON DELETE CASCADE` removes a student's attendance and results when the student is deleted. `ON DELETE RESTRICT` prevents deleting a course that still has students.
* UNIQUE constraints stop duplicate attendance entries for the same day and duplicate marks for the same subject and term.

## Project structure

```
student-management-system/
├── main.py               # Launches the Tkinter GUI
├── cli.py                # Menu-driven console version
├── seed_demo.py          # Loads demo data
├── config.example.ini    # DB settings template -> copy to config.ini
├── database/
│   ├── schema.sql        # MySQL schema (tables, keys, constraints)
│   └── sample_data.sql   # Sample records
├── sms/
│   ├── config.py         # Reads config.ini
│   ├── db.py             # DB layer (MySQL; SQLite fallback for demo/tests)
│   ├── validators.py     # Input validation rules
│   ├── services.py       # Business logic: CRUD, attendance, results, grading
│   └── gui.py            # Tkinter screens
└── tests/
    └── test_services.py  # 13 unit tests
```

The layers are kept separate: **GUI/CLI → services → db**. The UI never writes SQL itself.

## Getting started

**1. Prerequisites:** Python 3.9+ (with Tkinter, which comes with the Windows/macOS installers) and MySQL Server 8.

**2. Clone and install:**
```bash
git clone https://github.com/<your-username>/student-management-system.git
cd student-management-system
pip install -r requirements.txt
```

**3. Create the database** (in MySQL Workbench or the terminal):
```bash
mysql -u root -p < database/schema.sql
mysql -u root -p < database/sample_data.sql   # optional sample records
```

**4. Configure:** copy `config.example.ini` to `config.ini` and set your MySQL password.

**5. Run:**
```bash
python main.py      # GUI
python cli.py       # console menu
```

> **No MySQL installed?** Set `backend = sqlite` in `config.ini`, then run `python seed_demo.py` followed by `python main.py`. The same app runs on a local SQLite file.

## Running tests
```bash
python -m unittest discover tests -v
```

## Tech stack
Python 3 · Tkinter / ttk · MySQL 8 (mysql-connector-python) · SQLite (fallback) · unittest · Git
