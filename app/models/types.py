from sqlalchemy import JSON, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.types import TypeDecorator


class StringArray(TypeDecorator):
    """
    Cross-dialect array-of-strings column.

    Renders as native PostgreSQL ARRAY(Text) in production.
    Falls back to JSON (a plain list) on dialects that don't support
    ARRAY natively — namely SQLite, which is used for fast in-memory
    functional tests (see tests/conftest.py). This keeps the test suite
    free of any external database dependency while preserving the same
    Python-level interface (a list[str]) in both environments.
    """

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(Text))
        return dialect.type_descriptor(JSON())