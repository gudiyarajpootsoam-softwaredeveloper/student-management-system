"""Tkinter GUI for the Student Management System.

Tabs: Students (CRUD + search) | Attendance | Results | Courses & Subjects
"""
from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk

from .db import DatabaseError
from .services import SMS
from .validators import ATTENDANCE_STATUSES, GENDERS, ValidationError

PAD = {"padx": 6, "pady": 4}


def safe(action):
    """Decorator: show validation/database errors in a dialog instead of crashing."""
    def wrapper(self, *args, **kwargs):
        try:
            return action(self, *args, **kwargs)
        except ValidationError as exc:
            messagebox.showwarning("Invalid input", str(exc), parent=self)
        except DatabaseError as exc:
            messagebox.showerror("Database error", str(exc), parent=self)
    return wrapper


def make_tree(parent, columns: dict[str, int], height: int = 12) -> ttk.Treeview:
    frame = ttk.Frame(parent)
    tree = ttk.Treeview(frame, columns=list(columns), show="headings", height=height,
                        selectmode="browse")
    for col, width in columns.items():
        tree.heading(col, text=col.replace("_", " ").title())
        tree.column(col, width=width, anchor="w")
    sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    tree.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")
    frame.pack(fill="both", expand=True, **PAD)
    return tree


def fill_tree(tree: ttk.Treeview, rows: list[dict], keys: list[str], iid_key: str | None = None):
    tree.delete(*tree.get_children())
    for r in rows:
        values = ["" if r.get(k) is None else r.get(k) for k in keys]
        tree.insert("", "end", iid=str(r[iid_key]) if iid_key else None, values=values)


# ============================================================== Students tab
class StudentsTab(ttk.Frame):
    COLS = {"roll_no": 110, "full_name": 170, "course_code": 70, "gender": 70,
            "dob": 95, "email": 200, "phone": 100, "admission_date": 110}

    def __init__(self, master, app: SMS, on_change):
        super().__init__(master)
        self.app, self.on_change = app, on_change
        self.selected_id: int | None = None
        self.vars = {k: tk.StringVar() for k in
                     ("roll_no", "full_name", "dob", "gender", "email", "phone",
                      "course", "admission_date")}
        self.search_var = tk.StringVar()
        self._build()
        self.refresh()

    def _build(self):
        form = ttk.LabelFrame(self, text="Student details")
        form.pack(fill="x", **PAD)
        fields = [("Roll No *", "roll_no"), ("Full Name *", "full_name"),
                  ("DOB (YYYY-MM-DD) *", "dob"), ("Gender *", "gender"),
                  ("Email", "email"), ("Phone", "phone"),
                  ("Course *", "course"), ("Admission Date *", "admission_date")]
        for i, (label, key) in enumerate(fields):
            r, c = divmod(i, 2)
            ttk.Label(form, text=label).grid(row=r, column=c * 2, sticky="e", **PAD)
            if key == "gender":
                w = ttk.Combobox(form, textvariable=self.vars[key], values=GENDERS,
                                 state="readonly", width=28)
            elif key == "course":
                w = self.course_box = ttk.Combobox(form, textvariable=self.vars[key],
                                                   state="readonly", width=28)
            else:
                w = ttk.Entry(form, textvariable=self.vars[key], width=31)
            w.grid(row=r, column=c * 2 + 1, sticky="w", **PAD)

        btns = ttk.Frame(self)
        btns.pack(fill="x", **PAD)
        ttk.Button(btns, text="Add", command=self.add).pack(side="left", padx=3)
        ttk.Button(btns, text="Update", command=self.update).pack(side="left", padx=3)
        ttk.Button(btns, text="Delete", command=self.delete).pack(side="left", padx=3)
        ttk.Button(btns, text="Clear", command=self.clear).pack(side="left", padx=3)
        ttk.Button(btns, text="Search", command=self.refresh).pack(side="right", padx=3)
        e = ttk.Entry(btns, textvariable=self.search_var, width=30)
        e.pack(side="right", padx=3)
        e.bind("<Return>", lambda _e: self.refresh())
        ttk.Label(btns, text="Roll / Name / Course:").pack(side="right")

        self.tree = make_tree(self, self.COLS)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

    def load_courses(self):
        self.courses = {f"{c['course_code']} - {c['course_name']}": c["course_id"]
                        for c in self.app.courses.list()}
        self.course_box["values"] = list(self.courses)

    def refresh(self):
        self.load_courses()
        rows = self.app.students.search(self.search_var.get())
        fill_tree(self.tree, rows, list(self.COLS), iid_key="student_id")

    def form_data(self) -> dict:
        d = {k: var.get() for k, var in self.vars.items()}
        d["course_id"] = self.courses.get(d.pop("course"))
        return d

    def on_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        self.selected_id = int(sel[0])
        s = self.app.students.get(self.selected_id)
        for k in ("roll_no", "full_name", "gender", "email", "phone"):
            self.vars[k].set(s.get(k) or "")
        self.vars["dob"].set(str(s["dob"]))
        self.vars["admission_date"].set(str(s["admission_date"]))
        label = next((k for k, v in self.courses.items() if v == s["course_id"]), "")
        self.vars["course"].set(label)

    def clear(self):
        for var in self.vars.values():
            var.set("")
        self.vars["admission_date"].set(date.today().isoformat())
        self.selected_id = None
        self.tree.selection_remove(self.tree.selection())

    @safe
    def add(self):
        self.app.students.create(self.form_data())
        messagebox.showinfo("Saved", "Student added successfully.", parent=self)
        self.clear(); self.refresh(); self.on_change()

    @safe
    def update(self):
        if self.selected_id is None:
            raise ValidationError("Select a student in the table first.")
        self.app.students.update(self.selected_id, self.form_data())
        messagebox.showinfo("Saved", "Student updated successfully.", parent=self)
        self.refresh(); self.on_change()

    @safe
    def delete(self):
        if self.selected_id is None:
            raise ValidationError("Select a student in the table first.")
        if messagebox.askyesno("Confirm delete",
                               "Delete this student along with attendance and results?",
                               parent=self):
            self.app.students.delete(self.selected_id)
            self.clear(); self.refresh(); self.on_change()


# ============================================================ Attendance tab
class AttendanceTab(ttk.Frame):
    COLS = {"roll_no": 130, "full_name": 220, "status": 120}

    def __init__(self, master, app: SMS):
        super().__init__(master)
        self.app = app
        self.date_var = tk.StringVar(value=date.today().isoformat())
        self.roll_var = tk.StringVar()
        self._build()
        self.refresh()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", **PAD)
        ttk.Label(top, text="Date (YYYY-MM-DD):").pack(side="left")
        ttk.Entry(top, textvariable=self.date_var, width=12).pack(side="left", padx=4)
        ttk.Button(top, text="Load", command=self.refresh).pack(side="left", padx=4)
        ttk.Label(top, text="   Mark selected as:").pack(side="left")
        for status in ATTENDANCE_STATUSES:
            ttk.Button(top, text=status,
                       command=lambda s=status: self.mark(s)).pack(side="left", padx=2)
        ttk.Button(top, text="Mark ALL Present",
                   command=self.mark_all_present).pack(side="left", padx=8)

        self.tree = make_tree(self, self.COLS, height=12)

        summary = ttk.LabelFrame(self, text="Student attendance summary")
        summary.pack(fill="x", **PAD)
        ttk.Label(summary, text="Roll No:").pack(side="left", **PAD)
        ttk.Entry(summary, textvariable=self.roll_var, width=16).pack(side="left")
        ttk.Button(summary, text="Show", command=self.show_summary).pack(side="left", padx=4)
        self.summary_lbl = ttk.Label(summary, text="")
        self.summary_lbl.pack(side="left", **PAD)

    @safe
    def refresh(self):
        rows = self.app.attendance.for_date(self.date_var.get())
        for r in rows:
            r["status"] = r["status"] or "— not marked —"
        fill_tree(self.tree, rows, list(self.COLS), iid_key="student_id")

    @safe
    def mark(self, status: str):
        sel = self.tree.selection()
        if not sel:
            raise ValidationError("Select a student first.")
        self.app.attendance.mark(int(sel[0]), self.date_var.get(), status)
        self.refresh()
        if self.tree.exists(sel[0]):
            self.tree.selection_set(sel[0])

    @safe
    def mark_all_present(self):
        for iid in self.tree.get_children():
            self.app.attendance.mark(int(iid), self.date_var.get(), "Present")
        self.refresh()

    @safe
    def show_summary(self):
        s = self.app.students.get_by_roll(self.roll_var.get())
        if not s:
            raise ValidationError("No student with that roll number.")
        a = self.app.attendance.summary(s["student_id"])
        self.summary_lbl.config(
            text=f"{s['full_name']}: {a['present']}/{a['total']} days present "
                 f"({a['percentage']}%) · Absent {a['absent']} · Leave {a['leave']}")


# =============================================================== Results tab
class ResultsTab(ttk.Frame):
    COLS = {"exam_term": 120, "subject_code": 100, "subject_name": 260,
            "marks_obtained": 110, "max_marks": 90, "grade": 70}

    def __init__(self, master, app: SMS):
        super().__init__(master)
        self.app = app
        self.student = None
        self.roll_var, self.term_var = tk.StringVar(), tk.StringVar(value="TEE-Dec-2025")
        self.subject_var, self.marks_var = tk.StringVar(), tk.StringVar()
        self._build()

    def _build(self):
        top = ttk.LabelFrame(self, text="Enter marks")
        top.pack(fill="x", **PAD)
        ttk.Label(top, text="Roll No:").grid(row=0, column=0, sticky="e", **PAD)
        ttk.Entry(top, textvariable=self.roll_var, width=16).grid(row=0, column=1, **PAD)
        ttk.Button(top, text="Load student", command=self.load_student).grid(row=0, column=2, **PAD)
        self.student_lbl = ttk.Label(top, text="")
        self.student_lbl.grid(row=0, column=3, columnspan=3, sticky="w", **PAD)

        ttk.Label(top, text="Exam term:").grid(row=1, column=0, sticky="e", **PAD)
        ttk.Entry(top, textvariable=self.term_var, width=16).grid(row=1, column=1, **PAD)
        ttk.Label(top, text="Subject:").grid(row=1, column=2, sticky="e", **PAD)
        self.subject_box = ttk.Combobox(top, textvariable=self.subject_var,
                                        state="readonly", width=36)
        self.subject_box.grid(row=1, column=3, **PAD)
        ttk.Label(top, text="Marks:").grid(row=1, column=4, sticky="e", **PAD)
        ttk.Entry(top, textvariable=self.marks_var, width=8).grid(row=1, column=5, **PAD)
        ttk.Button(top, text="Save marks", command=self.save).grid(row=1, column=6, **PAD)
        ttk.Button(top, text="Delete selected", command=self.delete).grid(row=1, column=7, **PAD)

        self.tree = make_tree(self, self.COLS, height=10)
        self.total_lbl = ttk.Label(self, text="", font=("Segoe UI", 10, "bold"))
        self.total_lbl.pack(anchor="w", **PAD)

    @safe
    def load_student(self):
        s = self.app.students.get_by_roll(self.roll_var.get())
        if not s:
            raise ValidationError("No student with that roll number.")
        self.student = s
        self.student_lbl.config(text=f"{s['full_name']}  ({s['course_code']})")
        self.subjects = {f"{x['subject_code']} - {x['subject_name']} (/{x['max_marks']})":
                         x["subject_id"] for x in self.app.courses.subjects(s["course_id"])}
        self.subject_box["values"] = list(self.subjects)
        self.refresh()

    def refresh(self):
        if not self.student:
            return
        sheet = self.app.results.marksheet(self.student["student_id"])
        fill_tree(self.tree, sheet["rows"], list(self.COLS), iid_key="result_id")
        self.total_lbl.config(
            text=f"Total: {sheet['total_obtained']:g} / {sheet['total_max']}   "
                 f"Percentage: {sheet['percentage']}%   Grade: {sheet['grade']}   "
                 f"Result: {sheet['status']}")

    @safe
    def save(self):
        if not self.student:
            raise ValidationError("Load a student first.")
        subject_id = self.subjects.get(self.subject_var.get())
        if not subject_id:
            raise ValidationError("Select a subject.")
        self.app.results.record(self.student["student_id"], subject_id,
                                self.term_var.get(), self.marks_var.get())
        self.marks_var.set("")
        self.refresh()

    @safe
    def delete(self):
        sel = self.tree.selection()
        if not sel:
            raise ValidationError("Select a result row first.")
        if messagebox.askyesno("Confirm", "Delete the selected result?", parent=self):
            self.app.results.delete(int(sel[0]))
            self.refresh()


# =============================================================== Courses tab
class CoursesTab(ttk.Frame):
    def __init__(self, master, app: SMS, on_change):
        super().__init__(master)
        self.app, self.on_change = app, on_change
        self.c_code, self.c_name, self.c_dur = tk.StringVar(), tk.StringVar(), tk.StringVar(value="3")
        self.s_code, self.s_name, self.s_max = tk.StringVar(), tk.StringVar(), tk.StringVar(value="100")
        self._build()
        self.refresh()

    def _build(self):
        cf = ttk.LabelFrame(self, text="Add course")
        cf.pack(fill="x", **PAD)
        for i, (lbl, var, w) in enumerate([("Code", self.c_code, 10), ("Name", self.c_name, 36),
                                           ("Years", self.c_dur, 5)]):
            ttk.Label(cf, text=lbl).grid(row=0, column=i * 2, **PAD)
            ttk.Entry(cf, textvariable=var, width=w).grid(row=0, column=i * 2 + 1, **PAD)
        ttk.Button(cf, text="Add course", command=self.add_course).grid(row=0, column=6, **PAD)

        self.course_tree = make_tree(self, {"course_code": 100, "course_name": 320,
                                            "duration_years": 110}, height=5)
        self.course_tree.bind("<<TreeviewSelect>>", lambda _e: self.refresh_subjects())

        sf = ttk.LabelFrame(self, text="Add subject to selected course")
        sf.pack(fill="x", **PAD)
        for i, (lbl, var, w) in enumerate([("Code", self.s_code, 10), ("Name", self.s_name, 36),
                                           ("Max marks", self.s_max, 6)]):
            ttk.Label(sf, text=lbl).grid(row=0, column=i * 2, **PAD)
            ttk.Entry(sf, textvariable=var, width=w).grid(row=0, column=i * 2 + 1, **PAD)
        ttk.Button(sf, text="Add subject", command=self.add_subject).grid(row=0, column=6, **PAD)

        self.subject_tree = make_tree(self, {"subject_code": 100, "subject_name": 320,
                                             "max_marks": 110}, height=6)

    def refresh(self):
        fill_tree(self.course_tree, self.app.courses.list(),
                  ["course_code", "course_name", "duration_years"], iid_key="course_id")
        self.refresh_subjects()

    def refresh_subjects(self):
        sel = self.course_tree.selection()
        rows = self.app.courses.subjects(int(sel[0])) if sel else []
        fill_tree(self.subject_tree, rows, ["subject_code", "subject_name", "max_marks"])

    @safe
    def add_course(self):
        self.app.courses.add(self.c_code.get(), self.c_name.get(), self.c_dur.get())
        self.c_code.set(""); self.c_name.set("")
        self.refresh(); self.on_change()

    @safe
    def add_subject(self):
        sel = self.course_tree.selection()
        if not sel:
            raise ValidationError("Select a course in the table first.")
        try:
            max_marks = int(self.s_max.get())
        except ValueError:
            raise ValidationError("Max marks must be a whole number.") from None
        self.app.courses.add_subject(int(sel[0]), self.s_code.get(), self.s_name.get(), max_marks)
        self.s_code.set(""); self.s_name.set("")
        self.refresh_subjects()


# ============================================================== Main window
class MainWindow(tk.Tk):
    def __init__(self, app: SMS):
        super().__init__()
        self.app = app
        self.title("Student Management System")
        self.geometry("1000x640")
        self.minsize(900, 560)
        ttk.Style(self).theme_use("clam")

        header = ttk.Frame(self)
        header.pack(fill="x", padx=10, pady=(10, 0))
        ttk.Label(header, text="Student Management System",
                  font=("Segoe UI", 16, "bold")).pack(side="left")
        self.count_lbl = ttk.Label(header, text="")
        self.count_lbl.pack(side="right")

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=10)
        self.attendance_tab = AttendanceTab(nb, app)
        self.students_tab = StudentsTab(nb, app, self.on_data_change)
        self.results_tab = ResultsTab(nb, app)
        self.courses_tab = CoursesTab(nb, app, self.on_data_change)
        nb.add(self.students_tab, text="  Students  ")
        nb.add(self.attendance_tab, text="  Attendance  ")
        nb.add(self.results_tab, text="  Results  ")
        nb.add(self.courses_tab, text="  Courses & Subjects  ")
        self.students_tab.clear()
        self.update_count()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_data_change(self):
        self.students_tab.refresh()
        self.attendance_tab.refresh()
        self.update_count()

    def update_count(self):
        self.count_lbl.config(text=f"Total students: {self.app.students.count()}")

    def on_close(self):
        self.app.close()
        self.destroy()
