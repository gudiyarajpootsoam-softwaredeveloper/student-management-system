"""Launch the Student Management System GUI.

    python main.py            # GUI
    python cli.py             # menu-driven console version
"""
import sys
from tkinter import messagebox

from sms import DatabaseError, open_app


def main() -> None:
    try:
        app = open_app()
    except DatabaseError as exc:
        messagebox.showerror("Database connection failed", str(exc))
        sys.exit(1)
    from sms.gui import MainWindow
    MainWindow(app).mainloop()


if __name__ == "__main__":
    main()
