"""Menu-driven console interface for the Student Management System."""
from __future__ import annotations

import sys
from datetime import date

from sms import DatabaseError, ValidationError, open_app

MENU = """
================ STUDENT MANAGEMENT SYSTEM ================
 1. Add student                 6. Mark attendance
 2. View / search students      7. Attendance summary
 3. Update student              8. Enter marks
 4. Delete student              9. View marksheet
 5. List courses & subjects     0. Exit
===========================================================
"""


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default


def print_table(rows: list[dict], cols: list[str]) -> None:
    if not rows:
        print("  (no records)")
        return
    widths = {c: max(len(c), *(len(str(r.get(c) or "")) for r in rows)) for c in cols}
    print("  " + "  ".join(c.upper().ljust(widths[c]) for c in cols))
    print("  " + "  ".join("-" * widths[c] for c in cols))
    for r in rows:
        print("  " + "  ".join(str(r.get(c) or "").ljust(widths[c]) for c in cols))


def pick_course(app) -> int:
    courses = app.courses.list()
    print_table(courses, ["course_id", "course_code", "course_name"])
    return int(ask("Course ID"))


def student_form(app, current: dict | None = None) -> dict:
    c = current or {}
    return {
        "roll_no": ask("Roll number", c.get("roll_no", "")),
        "full_name": ask("Full name", c.get("full_name", "")),
        "dob": ask("Date of birth (YYYY-MM-DD)", str(c.get("dob", "") or "")),
        "gender": ask("Gender (Male/Female/Other)", c.get("gender", "")),
        "email": ask("Email (optional)", c.get("email") or ""),
        "phone": ask("Phone (optional)", c.get("phone") or ""),
        "course_id": pick_course(app) if not current or ask("Change course? (y/N)", "n").lower() == "y"
                     else c["course_id"],
        "admission_date": ask("Admission date", str(c.get("admission_date") or date.today())),
    }


def find_student(app) -> dict:
    s = app.students.get_by_roll(ask("Roll number"))
    if not s:
        raise ValidationError("No student with that roll number.")
    return s


def run(app) -> None:
    while True:
        print(MENU)
        choice = ask("Choose an option")
        try:
            if choice == "1":
                app.students.create(student_form(app))
                print("✔ Student added.")
            elif choice == "2":
                rows = app.students.search(ask("Search (roll/name/course, blank = all)"))
                print_table(rows, ["roll_no", "full_name", "course_code", "gender", "phone", "email"])
            elif choice == "3":
                s = find_student(app)
                app.students.update(s["student_id"], student_form(app, s))
                print("✔ Student updated.")
            elif choice == "4":
                s = find_student(app)
                if ask(f"Delete {s['full_name']}? (y/N)", "n").lower() == "y":
                    app.students.delete(s["student_id"])
                    print("✔ Student deleted.")
            elif choice == "5":
                for c in app.courses.list():
                    print(f"\n{c['course_code']} - {c['course_name']} ({c['duration_years']} yrs)")
                    print_table(app.courses.subjects(c["course_id"]),
                                ["subject_id", "subject_code", "subject_name", "max_marks"])
            elif choice == "6":
                d = ask("Date (YYYY-MM-DD)", date.today().isoformat())
                for r in app.attendance.for_date(d):
                    status = ask(f"  {r['roll_no']} {r['full_name']} (P/A/L)",
                                 (r["status"] or "Present")[0])
                    status = {"P": "Present", "A": "Absent", "L": "Leave"}.get(status.upper(), status)
                    app.attendance.mark(r["student_id"], d, status)
                print("✔ Attendance saved.")
            elif choice == "7":
                s = find_student(app)
                a = app.attendance.summary(s["student_id"])
                print(f"  {s['full_name']}: present {a['present']}/{a['total']} "
                      f"({a['percentage']}%), absent {a['absent']}, leave {a['leave']}")
            elif choice == "8":
                s = find_student(app)
                subs = app.courses.subjects(s["course_id"])
                print_table(subs, ["subject_id", "subject_code", "subject_name", "max_marks"])
                app.results.record(s["student_id"], int(ask("Subject ID")),
                                   ask("Exam term", "TEE-Dec-2025"), ask("Marks"))
                print("✔ Marks saved.")
            elif choice == "9":
                s = find_student(app)
                m = app.results.marksheet(s["student_id"])
                print(f"\n  MARKSHEET — {s['full_name']} ({s['roll_no']})")
                print_table(m["rows"], ["exam_term", "subject_code", "subject_name",
                                        "marks_obtained", "max_marks", "grade"])
                print(f"\n  Total {m['total_obtained']:g}/{m['total_max']} | "
                      f"{m['percentage']}% | Grade {m['grade']} | {m['status']}")
            elif choice == "0":
                print("Goodbye!")
                return
            else:
                print("Invalid option, try again.")
        except ValidationError as exc:
            print(f"✖ {exc}")
        except ValueError:
            print("✖ Please enter a valid number.")
        except DatabaseError as exc:
            print(f"✖ Database error: {exc}")


if __name__ == "__main__":
    try:
        application = open_app()
    except DatabaseError as exc:
        sys.exit(f"Database connection failed: {exc}")
    try:
        run(application)
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye!")
    finally:
        application.close()
