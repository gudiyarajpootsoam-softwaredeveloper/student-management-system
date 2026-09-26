"""Unit tests — run with:  python -m unittest discover tests"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sms import ValidationError, open_app  # noqa: E402
from sms.config import DBConfig  # noqa: E402
from sms.services import grade_for  # noqa: E402


def student(**overrides):
    data = {"roll_no": "MCA2024001", "full_name": "aarav  sharma", "dob": "2001-04-12",
            "gender": "male", "email": "Aarav@Example.com", "phone": "+91 98765-43210",
            "course_id": 1, "admission_date": "2024-07-15"}
    data.update(overrides)
    return data


class SMSTestCase(unittest.TestCase):
    def setUp(self):
        self.app = open_app(DBConfig(backend="sqlite", sqlite_path=":memory:"))
        self.mca = self.app.courses.add("mca", "Master of Computer Applications", 2)
        self.bca = self.app.courses.add("BCA", "Bachelor of Computer Applications", 3)
        self.dsa = self.app.courses.add_subject(self.mca, "MCS-211", "Algorithms", 100)
        self.dm = self.app.courses.add_subject(self.mca, "MCS-212", "Discrete Maths", 100)
        self.bsub = self.app.courses.add_subject(self.bca, "BCS-011", "Computer Basics", 100)

    def tearDown(self):
        self.app.close()

    # ------------------------------------------------------------ students
    def test_create_normalises_fields(self):
        sid = self.app.students.create(student())
        s = self.app.students.get(sid)
        self.assertEqual(s["full_name"], "Aarav Sharma")
        self.assertEqual(s["email"], "aarav@example.com")
        self.assertEqual(s["phone"], "9876543210")
        self.assertEqual(s["gender"], "Male")
        self.assertEqual(s["course_code"], "MCA")

    def test_duplicate_roll_number_rejected(self):
        self.app.students.create(student())
        with self.assertRaisesRegex(ValidationError, "already assigned"):
            self.app.students.create(student(email="other@example.com"))

    def test_duplicate_email_rejected(self):
        self.app.students.create(student())
        with self.assertRaisesRegex(ValidationError, "already registered"):
            self.app.students.create(student(roll_no="MCA2024002"))

    def test_invalid_inputs_rejected(self):
        bad = [dict(roll_no="12"), dict(full_name="R2D2"), dict(dob="2001-13-01"),
               dict(dob="2020-01-01"), dict(gender="x"), dict(email="nope"),
               dict(phone="12345"), dict(course_id=99), dict(admission_date="2099-01-01")]
        for override in bad:
            with self.subTest(override=override), self.assertRaises(ValidationError):
                self.app.students.create(student(**override))
        self.assertEqual(self.app.students.count(), 0)

    def test_search_update_delete(self):
        sid = self.app.students.create(student())
        self.app.students.create(student(roll_no="BCA2024001", full_name="Rohan Gupta",
                                         email=None, course_id=self.bca))
        self.assertEqual(len(self.app.students.search("")), 2)
        self.assertEqual(len(self.app.students.search("rohan")), 1)
        self.assertEqual(len(self.app.students.search("MCA")), 1)

        self.app.students.update(sid, student(full_name="Aarav K Sharma"))
        self.assertEqual(self.app.students.get(sid)["full_name"], "Aarav K Sharma")

        self.app.students.delete(sid)
        self.assertIsNone(self.app.students.get(sid))
        with self.assertRaises(ValidationError):
            self.app.students.delete(sid)

    def test_update_to_existing_roll_rejected(self):
        self.app.students.create(student())
        other = self.app.students.create(student(roll_no="MCA2024002", email="b@example.com"))
        with self.assertRaises(ValidationError):
            self.app.students.update(other, student(email="b@example.com"))

    # ---------------------------------------------------------- attendance
    def test_attendance_mark_upsert_and_summary(self):
        sid = self.app.students.create(student())
        self.app.attendance.mark(sid, "2026-09-21", "present")
        self.app.attendance.mark(sid, "2026-09-22", "Absent")
        self.app.attendance.mark(sid, "2026-09-22", "Present")  # correction, not duplicate
        self.app.attendance.mark(sid, "2026-09-23", "Leave")
        s = self.app.attendance.summary(sid)
        self.assertEqual((s["total"], s["present"], s["leave"]), (3, 2, 1))
        self.assertEqual(s["percentage"], 66.67)
        with self.assertRaises(ValidationError):
            self.app.attendance.mark(sid, "2099-01-01", "Present")
        with self.assertRaises(ValidationError):
            self.app.attendance.mark(sid, "2026-09-24", "Late")

    def test_cascade_delete_removes_attendance_and_results(self):
        sid = self.app.students.create(student())
        self.app.attendance.mark(sid, "2026-09-21", "Present")
        self.app.results.record(sid, self.dsa, "T1", 80)
        self.app.students.delete(sid)
        n_att = self.app.db.fetch_one("SELECT COUNT(*) AS n FROM attendance")["n"]
        n_res = self.app.db.fetch_one("SELECT COUNT(*) AS n FROM results")["n"]
        self.assertEqual((n_att, n_res), (0, 0))

    # ------------------------------------------------------------- results
    def test_marksheet_totals_and_grades(self):
        sid = self.app.students.create(student())
        self.app.results.record(sid, self.dsa, "TEE-Jun-2025", 92)
        self.app.results.record(sid, self.dm, "TEE-Jun-2025", "71.5")
        self.app.results.record(sid, self.dm, "TEE-Jun-2025", 75)  # update
        m = self.app.results.marksheet(sid)
        self.assertEqual(len(m["rows"]), 2)
        self.assertEqual(m["total_obtained"], 167)
        self.assertEqual(m["percentage"], 83.5)
        self.assertEqual(m["grade"], "A+")
        self.assertEqual(m["status"], "PASS")

    def test_result_validation(self):
        sid = self.app.students.create(student())
        with self.assertRaises(ValidationError):
            self.app.results.record(sid, self.dsa, "T1", 101)
        with self.assertRaises(ValidationError):
            self.app.results.record(sid, self.dsa, "T1", "abc")
        with self.assertRaisesRegex(ValidationError, "does not belong"):
            self.app.results.record(sid, self.bsub, "T1", 50)

    def test_fail_status(self):
        sid = self.app.students.create(student())
        self.app.results.record(sid, self.dsa, "T1", 95)
        self.app.results.record(sid, self.dm, "T1", 30)
        self.assertEqual(self.app.results.marksheet(sid)["status"], "FAIL")

    def test_grade_boundaries(self):
        self.assertEqual([grade_for(p) for p in (95, 85, 75, 65, 55, 45, 20)],
                         ["O", "A+", "A", "B+", "B", "C", "F"])

    # ------------------------------------------------------------- courses
    def test_duplicate_course_rejected(self):
        with self.assertRaises(ValidationError):
            self.app.courses.add("MCA", "Duplicate", 2)


if __name__ == "__main__":
    unittest.main()
