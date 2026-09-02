"""Dialect-portable column types.

Production runs on PostgreSQL. Local development and CI run on SQLite so the
full suite can execute without a database server. These variants keep one set
of models honest against both: Postgres gets JSONB/CITEXT/INET/UUID, SQLite
gets the closest faithful equivalent.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import CHAR, JSON, LargeBinary, String, TypeDecorator
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Dialect

# JSON payloads: JSONB on Postgres (indexable, binary), JSON on SQLite.
JSONB = JSON().with_variant(postgresql.JSONB(), "postgresql")

# Raw bytes: BYTEA on Postgres, BLOB on SQLite.
Bytes = LargeBinary().with_variant(postgresql.BYTEA(), "postgresql")

# IP addresses: INET on Postgres, TEXT on SQLite. Stored for abuse review only.
IPAddress = String(45).with_variant(postgresql.INET(), "postgresql")


class GUID(TypeDecorator[uuid.UUID]):
    """UUID that stores natively on Postgres and as a 32-char hex on SQLite."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(postgresql.UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value: Any, dialect: Dialect) -> Any:
        if value is None:
            return None
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(str(value))
        return value if dialect.name == "postgresql" else value.hex

    def process_result_value(self, value: Any, dialect: Dialect) -> uuid.UUID | None:
        if value is None:
            return None
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


class CaseInsensitiveEmail(TypeDecorator[str]):
    """CITEXT on Postgres; on SQLite, values are normalised to lowercase.

    Email addresses are stored lowercased in both cases, so uniqueness is
    genuinely case-insensitive on either backend rather than only appearing so.
    """

    impl = String
    cache_ok = True

    def __init__(self, length: int = 320) -> None:
        super().__init__(length=length)

    def load_dialect_impl(self, dialect: Dialect) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(postgresql.CITEXT())
        return dialect.type_descriptor(String(self.impl.length))

    def process_bind_param(self, value: Any, dialect: Dialect) -> Any:
        return value.strip().lower() if isinstance(value, str) else value
