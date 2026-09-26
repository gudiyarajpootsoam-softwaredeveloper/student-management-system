"""Student Management System package."""
from .config import load_config
from .db import Database, DatabaseError
from .services import SMS
from .validators import ValidationError

__version__ = "1.0.0"


def open_app(config=None) -> SMS:
    """Create the service facade using config.ini (or a supplied DBConfig)."""
    return SMS(Database(config or load_config()))


__all__ = ["open_app", "SMS", "Database", "DatabaseError", "ValidationError", "load_config"]
