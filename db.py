"""Database access layer.

Primary backend is MySQL (via mysql-connector-python). A SQLite backend with
the same schema is included so the app and its tests can run on a machine
without a MySQL server (set ``backend = sqlite`` in config.ini).
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Any, Iterable

from .config import DBConfig


class DatabaseError(Exception):
    """Raised for any database-level failure, with a user-friendly message."""


class IntegrityViolation(DatabaseError):
    """Raised when a UNIQUE / FOREIGN KEY constraint is violated."""


SQLITE_SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS courses (
    course_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    course_code    TEXT NOT NULL UNIQUE,
    course_name    TEXT NOT NULL,
    duration_years INTEGER NOT NULL DEFAULT 3 CHECK (duration_years BETWEEN 1 AND 6)
);
CREATE TABLE IF NOT EXISTS students (
    student_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    roll_no        TEXT NOT NULL UNIQUE,
    full_name      TEXT NOT NULL,
    dob            TEXT NOT NULL,
    gender         TEXT NOT NULL CHECK (gender IN ('Male','Female','Other')),
    email          TEXT UNIQUE,
    phone          TEXT,
    course_id      INTEGER NOT NULL REFERENCES courses(course_id)
                   ON UPDATE CASCADE ON DELETE RESTRICT,
    admission_date TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS subjects (
    subject_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id    INTEGER NOT NULL REFERENCES courses(course_id)
                 ON UPDATE CASCADE ON DELETE CASCADE,
    subject_code TEXT NOT NULL UNIQUE,
    subject_name TEXT NOT NULL,
    max_marks    INTEGER NOT NULL DEFAULT 100
);
CREATE TABLE IF NOT EXISTS attendance (
    attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id    INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    att_date      TEXT NOT NULL,
    status        TEXT NOT NULL CHECK (status IN ('Present','Absent','Leave')),
    UNIQUE (student_id, att_date)
);
CREATE TABLE IF NOT EXISTS results (
    result_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id     INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    subject_id     INTEGER NOT NULL REFERENCES subjects(subject_id) ON DELETE CASCADE,
    exam_term      TEXT NOT NULL,
    marks_obtained REAL NOT NULL,
    UNIQUE (student_id, subject_id, exam_term)
);
"""


class Database:
    """Thin wrapper that hides the differences between MySQL and SQLite."""

    def __init__(self, config: DBConfig):
        self.config = config
        self.backend = config.backend
        self._conn = self._connect()

    # ------------------------------------------------------------------ setup
    def _connect(self):
        if self.backend == "sqlite":
            conn = sqlite3.connect(self.config.sqlite_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.executescript(SQLITE_SCHEMA)
            return conn

        try:
            import mysql.connector  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise DatabaseError(
                "mysql-connector-python is not installed. "
                "Run: pip install -r requirements.txt"
            ) from exc
        try:
            return mysql.connector.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                autocommit=False,
            )
        except mysql.connector.Error as exc:  # pragma: no cover
            raise DatabaseError(
                f"Could not connect to MySQL at {self.config.host}:{self.config.port} "
                f"({exc.msg}). Check config.ini and that database/schema.sql was run."
            ) from exc

    # ---------------------------------------------------------------- helpers
    def _sql(self, query: str) -> str:
        # Queries are written with MySQL-style %s placeholders.
        return query.replace("%s", "?") if self.backend == "sqlite" else query

    def _is_integrity_error(self, exc: Exception) -> bool:
        if isinstance(exc, sqlite3.IntegrityError):
            return True
        try:
            import mysql.connector  # type: ignore
            return isinstance(exc, mysql.connector.IntegrityError)
        except ImportError:  # pragma: no cover
            return False

    @contextmanager
    def _cursor(self):
        if self.backend == "sqlite":
            cur = self._conn.cursor()
        else:
            cur = self._conn.cursor(dictionary=True)
        try:
            yield cur
        finally:
            cur.close()

    # -------------------------------------------------------------- public API
    def fetch_all(self, query: str, params: Iterable[Any] = ()) -> list[dict]:
        with self._cursor() as cur:
            cur.execute(self._sql(query), tuple(params))
            return [dict(r) for r in cur.fetchall()]

    def fetch_one(self, query: str, params: Iterable[Any] = ()) -> dict | None:
        rows = self.fetch_all(query, params)
        return rows[0] if rows else None

    def execute(self, query: str, params: Iterable[Any] = ()) -> int:
        """Run an INSERT/UPDATE/DELETE, commit, and return lastrowid/rowcount."""
        with self._cursor() as cur:
            try:
                cur.execute(self._sql(query), tuple(params))
                self._conn.commit()
            except Exception as exc:
                self._conn.rollback()
                if self._is_integrity_error(exc):
                    raise IntegrityViolation(str(exc)) from exc
                raise DatabaseError(str(exc)) from exc
            return cur.lastrowid if query.lstrip().upper().startswith("INSERT") else cur.rowcount

    def close(self) -> None:
        self._conn.close()
