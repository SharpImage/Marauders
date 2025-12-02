# marauders/database.py

import sqlite3
import pandas as pd
from pathlib import Path
from typing import Any, Iterable, Optional


class DatabaseNotFoundError(Exception):
    """Raised when the Marauders database is missing."""


class Database:
    """
    Central SQLite access point for the Marauders system.
    All modules should use this instead of sqlite3.connect().
    """

    def __init__(self, db_path: str = "marauders.db"):
        self.db_path = Path(db_path)
        self._init_settings_table()

        if not self.db_path.exists():
            raise DatabaseNotFoundError(
                f"Database file not found: {self.db_path}\n"
                f"Run excel_to_sqlite.py once before using the system."
            )

    # ----------------------------------------------------------
    # Basic connection helper
    # ----------------------------------------------------------
    def connect(self) -> sqlite3.Connection:
        """Open a new SQLite connection."""
        return sqlite3.connect(self.db_path)

    # ----------------------------------------------------------
    # Query helpers (read operations)
    # ----------------------------------------------------------
    def read_sql(self, sql: str, params: Iterable[Any] = ()) -> pd.DataFrame:
        """Execute a SELECT statement and return a Pandas DataFrame."""
        with self.connect() as conn:
            df = pd.read_sql_query(sql, conn, params=params)
        df.columns = [c.strip() for c in df.columns]
        return df

    def table_exists(self, table_name: str) -> bool:
        """Check if a table is present in the SQLite database."""
        sql = """
            SELECT name
            FROM sqlite_master
            WHERE type='table' AND name=?;
        """
        df = self.read_sql(sql, (table_name,))
        return not df.empty

    def get_table(self, table_name: str) -> pd.DataFrame:
        """Return a whole table as a DataFrame."""
        if not self.table_exists(table_name):
            return pd.DataFrame()
        return self.read_sql(f"SELECT * FROM {table_name}")

    # ----------------------------------------------------------
    # Write helpers (INSERT/UPDATE/DELETE and full writes)
    # ----------------------------------------------------------
    def execute(self, sql: str, params: Iterable[Any] = ()) -> None:
        """Execute INSERT, UPDATE, DELETE or DDL (no return)."""
        with self.connect() as conn:
            conn.execute(sql, params)
            conn.commit()

    def executemany(self, sql: str, param_list: Iterable[Iterable[Any]]) -> None:
        """Execute bulk operations."""
        with self.connect() as conn:
            conn.executemany(sql, param_list)
            conn.commit()

    def write_table(
        self,
        table_name: str,
        df: pd.DataFrame,
        replace: bool = True,
        index: bool = False,
    ) -> None:
        """
        Write a Pandas DataFrame into a SQLite table.
        If replace=True, REPLACE existing table.
        """
        if df is None or df.empty:
            return

        with self.connect() as conn:
            if_exists = "replace" if replace else "append"
            df.to_sql(table_name, conn, if_exists=if_exists, index=index)

    def _init_settings_table(self):
        """Ensure the Settings table exists."""
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                         CREATE TABLE IF NOT EXISTS Settings
                         (
                             Key
                             TEXT
                             PRIMARY
                             KEY,
                             Value
                             TEXT
                         )
                         """)
            conn.commit()

    def get_setting(self, key: str):
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT Value FROM Settings WHERE Key = ?", (key,))
            row = cur.fetchone()
            return None if row is None else row[0]

    def set_setting(self, key: str, value: str):
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                         INSERT INTO Settings (Key, Value)
                         VALUES (?, ?) ON CONFLICT(Key) DO
                         UPDATE SET Value = excluded.Value
                         """, (key, value))
            conn.commit()

    # ----------------------------------------------------------
    # Utility helpers
    # ----------------------------------------------------------
    def list_tables(self) -> list[str]:
        """Return a list of table names in the database."""
        df = self.read_sql("SELECT name FROM sqlite_master WHERE type='table'")
        return sorted(df["name"].tolist())

    def vacuum(self):
        """Clean + compact SQLite database."""
        with self.connect() as conn:
            conn.execute("VACUUM")
            conn.commit()
