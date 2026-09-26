"""Input validation. Every function raises ValidationError with a clear message."""
from __future__ import annotations

import re
from datetime import date, datetime


class ValidationError(ValueError):
    pass


ROLL_RE = re.compile(r"^[A-Z]{2,5}\d{4,8}$")
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z .'-]{1,99}$")
EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")
PHONE_RE = re.compile(r"^[6-9]\d{9}$")  # 10-digit Indian mobile number

GENDERS = ("Male", "Female", "Other")
ATTENDANCE_STATUSES = ("Present", "Absent", "Leave")


def require(value: str | None, field: str) -> str:
    value = (value or "").strip()
    if not value:
        raise ValidationError(f"{field} is required.")
    return value


def roll_no(value: str) -> str:
    value = require(value, "Roll number").upper()
    if not ROLL_RE.match(value):
        raise ValidationError(
            "Roll number must be 2-5 letters followed by 4-8 digits (e.g. MCA2024001)."
        )
    return value


def full_name(value: str) -> str:
    value = " ".join(require(value, "Name").split())
    if not NAME_RE.match(value):
        raise ValidationError("Name may contain only letters, spaces, '.', ''' and '-'.")
    return value.title()


def parse_date(value: str, field: str) -> date:
    value = require(value, field)
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError(f"{field} must be a valid date in YYYY-MM-DD format.") from None


def dob(value: str) -> str:
    d = parse_date(value, "Date of birth")
    today = date.today()
    age = today.year - d.year - ((today.month, today.day) < (d.month, d.day))
    if not 15 <= age <= 80:
        raise ValidationError("Student age must be between 15 and 80 years.")
    return d.isoformat()


def admission_date(value: str) -> str:
    d = parse_date(value, "Admission date")
    if d > date.today():
        raise ValidationError("Admission date cannot be in the future.")
    return d.isoformat()


def attendance_date(value: str) -> str:
    d = parse_date(value, "Attendance date")
    if d > date.today():
        raise ValidationError("Cannot mark attendance for a future date.")
    return d.isoformat()


def gender(value: str) -> str:
    value = require(value, "Gender").capitalize()
    if value not in GENDERS:
        raise ValidationError(f"Gender must be one of: {', '.join(GENDERS)}.")
    return value


def email(value: str | None) -> str | None:
    value = (value or "").strip().lower()
    if not value:
        return None
    if not EMAIL_RE.match(value):
        raise ValidationError("Please enter a valid email address.")
    return value


def phone(value: str | None) -> str | None:
    value = re.sub(r"[\s-]", "", value or "")
    if value.startswith("+91"):
        value = value[3:]
    if not value:
        return None
    if not PHONE_RE.match(value):
        raise ValidationError("Phone must be a 10-digit mobile number starting with 6-9.")
    return value


def attendance_status(value: str) -> str:
    value = require(value, "Status").capitalize()
    if value not in ATTENDANCE_STATUSES:
        raise ValidationError(f"Status must be one of: {', '.join(ATTENDANCE_STATUSES)}.")
    return value


def marks(value, max_marks: int) -> float:
    try:
        m = float(value)
    except (TypeError, ValueError):
        raise ValidationError("Marks must be a number.") from None
    if not 0 <= m <= max_marks:
        raise ValidationError(f"Marks must be between 0 and {max_marks}.")
    return round(m, 2)
