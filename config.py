"""Loads database settings from config.ini (falls back to sensible defaults)."""
from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT / "config.ini"


@dataclass
class DBConfig:
    backend: str = "mysql"          # "mysql" or "sqlite"
    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = ""
    database: str = "student_management"
    sqlite_path: str = str(ROOT / "student_management.db")


def load_config(path: Path | str = CONFIG_FILE) -> DBConfig:
    cfg = DBConfig()
    parser = configparser.ConfigParser()
    if parser.read(path):
        sec = parser["database"] if parser.has_section("database") else {}
        cfg.backend = sec.get("backend", cfg.backend).strip().lower()
        cfg.host = sec.get("host", cfg.host)
        cfg.port = int(sec.get("port", cfg.port))
        cfg.user = sec.get("user", cfg.user)
        cfg.password = sec.get("password", cfg.password)
        cfg.database = sec.get("database", cfg.database)
        sqlite_path = sec.get("sqlite_path")
        if sqlite_path:
            cfg.sqlite_path = str((ROOT / sqlite_path).resolve())
    if cfg.backend not in ("mysql", "sqlite"):
        raise ValueError("config.ini: backend must be 'mysql' or 'sqlite'")
    return cfg
