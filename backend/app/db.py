from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import psycopg

from .config import Settings


class Database:
    def __init__(self, settings: Settings) -> None:
        if not settings.database_url:
            raise ValueError("DATABASE_URL is required for the PostgreSQL backend")
        self.url = settings.database_url

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection]:
        with psycopg.connect(self.url) as connection:
            yield connection

    def migrate(self) -> None:
        sql = (Path(__file__).parents[1] / "migrations" / "001_init.sql").read_text()
        with self.connection() as connection:
            connection.execute(sql)

    def advisory_lock(self, connection: psycopg.Connection, key: int) -> bool:
        row = connection.execute("SELECT pg_try_advisory_lock(%s)", (key,)).fetchone()
        return bool(row and row[0])

