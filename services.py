"""Business logic: CRUD for students/courses/subjects, attendance and results.

The GUI and the CLI both talk only to this module, never to SQL directly.
"""
from __future__ import annotations

from . import validators as v
from .db import Database, IntegrityViolation
from .validators import ValidationError


def grade_for(percentage: float) -> str:
    if percentage >= 90: return "O"
    if percentage >= 80: return "A+"
    if percentage >= 70: return "A"
    if percentage >= 60: return "B+"
    if percentage >= 50: return "B"
    if percentage >= 40: return "C"
    return "F"


class CourseService:
    def __init__(self, db: Database):
        self.db = db

    def add(self, code: str, name: str, duration_years: int = 3) -> int:
        code = v.require(code, "Course code").upper()
        name = v.require(name, "Course name")
        try:
            duration_years = int(duration_years)
        except (TypeError, ValueError):
            raise ValidationError("Duration must be a whole number of years.") from None
        if not 1 <= duration_years <= 6:
            raise ValidationError("Duration must be between 1 and 6 years.")
        try:
            return self.db.execute(
                "INSERT INTO courses (course_code, course_name, duration_years) VALUES (%s, %s, %s)",
                (code, name, duration_years),
            )
        except IntegrityViolation:
            raise ValidationError(f"Course code '{code}' already exists.") from None

    def list(self) -> list[dict]:
        return self.db.fetch_all("SELECT * FROM courses ORDER BY course_code")

    def add_subject(self, course_id: int, code: str, name: str, max_marks: int = 100) -> int:
        code = v.require(code, "Subject code").upper()
        name = v.require(name, "Subject name")
        if not self.db.fetch_one("SELECT 1 AS ok FROM courses WHERE course_id = %s", (course_id,)):
            raise ValidationError("Selected course does not exist.")
        try:
            return self.db.execute(
                "INSERT INTO subjects (course_id, subject_code, subject_name, max_marks) "
                "VALUES (%s, %s, %s, %s)",
                (course_id, code, name, int(max_marks)),
            )
        except IntegrityViolation:
            raise ValidationError(f"Subject code '{code}' already exists.") from None

    def subjects(self, course_id: int) -> list[dict]:
        return self.db.fetch_all(
            "SELECT * FROM subjects WHERE course_id = %s ORDER BY subject_code", (course_id,)
        )


class StudentService:
    FIELDS = ("roll_no", "full_name", "dob", "gender", "email", "phone",
              "course_id", "admission_date")

    def __init__(self, db: Database):
        self.db = db

    def _clean(self, data: dict) -> dict:
        clean = {
            "roll_no": v.roll_no(data.get("roll_no")),
            "full_name": v.full_name(data.get("full_name")),
            "dob": v.dob(data.get("dob")),
            "gender": v.gender(data.get("gender")),
            "email": v.email(data.get("email")),
            "phone": v.phone(data.get("phone")),
            "admission_date": v.admission_date(data.get("admission_date")),
        }
        try:
            clean["course_id"] = int(data.get("course_id"))
        except (TypeError, ValueError):
            raise ValidationError("Please select a course.") from None
        if not self.db.fetch_one("SELECT 1 AS ok FROM courses WHERE course_id = %s",
                                 (clean["course_id"],)):
            raise ValidationError("Selected course does not exist.")
        return clean

    def _check_duplicates(self, clean: dict, exclude_id: int | None = None) -> None:
        q = "SELECT student_id FROM students WHERE roll_no = %s"
        row = self.db.fetch_one(q, (clean["roll_no"],))
        if row and row["student_id"] != exclude_id:
            raise ValidationError(f"Roll number {clean['roll_no']} is already assigned.")
        if clean["email"]:
            row = self.db.fetch_one("SELECT student_id FROM students WHERE email = %s",
                                    (clean["email"],))
            if row and row["student_id"] != exclude_id:
                raise ValidationError(f"Email {clean['email']} is already registered.")

    # ---------------------------------------------------------------- CRUD
    def create(self, data: dict) -> int:
        clean = self._clean(data)
        self._check_duplicates(clean)
        cols = ", ".join(self.FIELDS)
        marks = ", ".join(["%s"] * len(self.FIELDS))
        try:
            return self.db.execute(f"INSERT INTO students ({cols}) VALUES ({marks})",
                                   [clean[f] for f in self.FIELDS])
        except IntegrityViolation:
            raise ValidationError("Duplicate roll number or email.") from None

    def get(self, student_id: int) -> dict | None:
        return self.db.fetch_one(
            "SELECT s.*, c.course_code, c.course_name FROM students s "
            "JOIN courses c ON c.course_id = s.course_id WHERE s.student_id = %s",
            (student_id,),
        )

    def get_by_roll(self, roll_no: str) -> dict | None:
        return self.db.fetch_one(
            "SELECT s.*, c.course_code FROM students s "
            "JOIN courses c ON c.course_id = s.course_id WHERE s.roll_no = %s",
            ((roll_no or "").strip().upper(),),
        )

    def search(self, term: str = "") -> list[dict]:
        like = f"%{(term or '').strip()}%"
        return self.db.fetch_all(
            "SELECT s.student_id, s.roll_no, s.full_name, s.gender, s.email, s.phone, "
            "s.dob, s.admission_date, s.course_id, c.course_code "
            "FROM students s JOIN courses c ON c.course_id = s.course_id "
            "WHERE s.roll_no LIKE %s OR s.full_name LIKE %s OR c.course_code LIKE %s "
            "ORDER BY s.roll_no",
            (like, like, like),
        )

    def update(self, student_id: int, data: dict) -> None:
        if not self.get(student_id):
            raise ValidationError("Student not found.")
        clean = self._clean(data)
        self._check_duplicates(clean, exclude_id=student_id)
        sets = ", ".join(f"{f} = %s" for f in self.FIELDS)
        try:
            self.db.execute(f"UPDATE students SET {sets} WHERE student_id = %s",
                            [clean[f] for f in self.FIELDS] + [student_id])
        except IntegrityViolation:
            raise ValidationError("Duplicate roll number or email.") from None

    def delete(self, student_id: int) -> None:
        if self.db.execute("DELETE FROM students WHERE student_id = %s", (student_id,)) == 0:
            raise ValidationError("Student not found.")

    def count(self) -> int:
        return self.db.fetch_one("SELECT COUNT(*) AS n FROM students")["n"]


class AttendanceService:
    def __init__(self, db: Database):
        self.db = db

    def mark(self, student_id: int, att_date: str, status: str) -> None:
        """Insert or update the attendance entry for a student on a date."""
        att_date = v.attendance_date(att_date)
        status = v.attendance_status(status)
        existing = self.db.fetch_one(
            "SELECT attendance_id FROM attendance WHERE student_id = %s AND att_date = %s",
            (student_id, att_date),
        )
        if existing:
            self.db.execute("UPDATE attendance SET status = %s WHERE attendance_id = %s",
                            (status, existing["attendance_id"]))
        else:
            try:
                self.db.execute(
                    "INSERT INTO attendance (student_id, att_date, status) VALUES (%s, %s, %s)",
                    (student_id, att_date, status),
                )
            except IntegrityViolation:
                raise ValidationError("Student not found.") from None

    def for_date(self, att_date: str) -> list[dict]:
        att_date = v.attendance_date(att_date)
        return self.db.fetch_all(
            "SELECT s.student_id, s.roll_no, s.full_name, a.status FROM students s "
            "LEFT JOIN attendance a ON a.student_id = s.student_id AND a.att_date = %s "
            "ORDER BY s.roll_no",
            (att_date,),
        )

    def history(self, student_id: int) -> list[dict]:
        return self.db.fetch_all(
            "SELECT att_date, status FROM attendance WHERE student_id = %s ORDER BY att_date DESC",
            (student_id,),
        )

    def summary(self, student_id: int) -> dict:
        rows = self.history(student_id)
        total = len(rows)
        present = sum(1 for r in rows if r["status"] == "Present")
        return {
            "total": total,
            "present": present,
            "absent": sum(1 for r in rows if r["status"] == "Absent"),
            "leave": sum(1 for r in rows if r["status"] == "Leave"),
            "percentage": round(present * 100 / total, 2) if total else 0.0,
        }


class ResultService:
    def __init__(self, db: Database):
        self.db = db

    def record(self, student_id: int, subject_id: int, exam_term: str, marks) -> None:
        exam_term = v.require(exam_term, "Exam term")
        subject = self.db.fetch_one(
            "SELECT sub.max_marks, sub.course_id FROM subjects sub WHERE sub.subject_id = %s",
            (subject_id,),
        )
        if not subject:
            raise ValidationError("Subject not found.")
        student = self.db.fetch_one("SELECT course_id FROM students WHERE student_id = %s",
                                    (student_id,))
        if not student:
            raise ValidationError("Student not found.")
        if student["course_id"] != subject["course_id"]:
            raise ValidationError("This subject does not belong to the student's course.")
        m = v.marks(marks, subject["max_marks"])
        existing = self.db.fetch_one(
            "SELECT result_id FROM results WHERE student_id = %s AND subject_id = %s "
            "AND exam_term = %s", (student_id, subject_id, exam_term),
        )
        if existing:
            self.db.execute("UPDATE results SET marks_obtained = %s WHERE result_id = %s",
                            (m, existing["result_id"]))
        else:
            self.db.execute(
                "INSERT INTO results (student_id, subject_id, exam_term, marks_obtained) "
                "VALUES (%s, %s, %s, %s)", (student_id, subject_id, exam_term, m),
            )

    def delete(self, result_id: int) -> None:
        self.db.execute("DELETE FROM results WHERE result_id = %s", (result_id,))

    def marksheet(self, student_id: int, exam_term: str | None = None) -> dict:
        q = ("SELECT r.result_id, r.exam_term, sub.subject_code, sub.subject_name, "
             "r.marks_obtained, sub.max_marks FROM results r "
             "JOIN subjects sub ON sub.subject_id = r.subject_id WHERE r.student_id = %s")
        params: list = [student_id]
        if exam_term:
            q += " AND r.exam_term = %s"
            params.append(exam_term)
        rows = self.db.fetch_all(q + " ORDER BY r.exam_term, sub.subject_code", params)
        for r in rows:
            r["marks_obtained"] = float(r["marks_obtained"])
            r["grade"] = grade_for(r["marks_obtained"] * 100 / r["max_marks"])
        obtained = sum(r["marks_obtained"] for r in rows)
        maximum = sum(r["max_marks"] for r in rows)
        pct = round(obtained * 100 / maximum, 2) if maximum else 0.0
        return {
            "rows": rows,
            "total_obtained": obtained,
            "total_max": maximum,
            "percentage": pct,
            "grade": grade_for(pct) if rows else "-",
            "status": ("PASS" if rows and all(r["grade"] != "F" for r in rows)
                       else ("FAIL" if rows else "-")),
        }


class SMS:
    """Facade bundling all services around one database connection."""

    def __init__(self, db: Database):
        self.db = db
        self.courses = CourseService(db)
        self.students = StudentService(db)
        self.attendance = AttendanceService(db)
        self.results = ResultService(db)

    def close(self) -> None:
        self.db.close()
