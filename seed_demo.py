"""Load demo courses, subjects, students, attendance and results into the
configured database (works for both MySQL and SQLite). Safe to re-run."""
from sms import ValidationError, open_app

COURSES = [("MCA", "Master of Computer Applications", 2),
           ("BCA", "Bachelor of Computer Applications", 3)]
SUBJECTS = {"MCA": [("MCS-211", "Design and Analysis of Algorithms"),
                    ("MCS-212", "Discrete Mathematics"),
                    ("MCS-213", "Software Engineering")],
            "BCA": [("BCS-011", "Computer Basics and PC Software"),
                    ("BCS-012", "Basic Mathematics")]}
STUDENTS = [
    ("MCA2024001", "Aarav Sharma", "2001-04-12", "Male", "aarav.sharma@example.com", "9876543210", "MCA"),
    ("MCA2024002", "Priya Verma", "2000-11-03", "Female", "priya.verma@example.com", "9123456780", "MCA"),
    ("BCA2024001", "Rohan Gupta", "2005-01-25", "Male", "rohan.gupta@example.com", "9988776655", "BCA"),
]


def seed(app) -> None:
    for code, name, yrs in COURSES:
        try:
            app.courses.add(code, name, yrs)
        except ValidationError:
            pass
    course_ids = {c["course_code"]: c["course_id"] for c in app.courses.list()}
    for course, subs in SUBJECTS.items():
        for code, name in subs:
            try:
                app.courses.add_subject(course_ids[course], code, name)
            except ValidationError:
                pass
    for roll, name, dob, gender, email, phone, course in STUDENTS:
        if app.students.get_by_roll(roll):
            continue
        sid = app.students.create({"roll_no": roll, "full_name": name, "dob": dob,
                                   "gender": gender, "email": email, "phone": phone,
                                   "course_id": course_ids[course],
                                   "admission_date": "2024-07-15"})
        for day, status in (("2026-09-21", "Present"), ("2026-09-22", "Present"),
                            ("2026-09-23", "Absent")):
            app.attendance.mark(sid, day, status)
        for i, sub in enumerate(app.courses.subjects(course_ids[course])):
            app.results.record(sid, sub["subject_id"], "TEE-Jun-2025", 60 + (i * 9 + sid * 5) % 35)


if __name__ == "__main__":
    application = open_app()
    seed(application)
    print(f"Demo data loaded. Students in database: {application.students.count()}")
    application.close()
