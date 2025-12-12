# marauders/repositories/settings_repo.py

from marauders.database import Database
from typing import Optional, Any


class SettingsRepository:
    """
    Unified repository for storing application settings.
    Replaces separate settings tables in Database, Manager, and FinanceRepo.
    """

    def __init__(self, db: Database):
        self.db = db
        self._ensure_table()

    def _ensure_table(self):
        """Create GlobalSettings table if it does not exist."""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS GlobalSettings (
                Key TEXT PRIMARY KEY,
                Value TEXT
            )
        """)

        # Ensure default values exist
        defaults = {
            "MasterFile": "",
            "StartingKitty": "0.0"
        }
        for key, value in defaults.items():
            self.set_setting(key, value, default=True)

    def get_setting(self, key: str, default: Optional[Any] = None) -> Any:
        """Get a setting value by key."""
        df = self.db.read_sql(
            "SELECT Value FROM GlobalSettings WHERE Key = ?", (key,)
        )
        if df.empty:
            return default
        return df.iloc[0]["Value"]

    def set_setting(self, key: str, value: Any, default: bool = False):
        """
        Set a setting value.
        If default=True, only set if key does not exist (INSERT OR IGNORE).
        Otherwise, UPSERT (INSERT OR REPLACE).
        """
        val_str = str(value)
        if default:
             self.db.execute(
                "INSERT OR IGNORE INTO GlobalSettings (Key, Value) VALUES (?, ?)",
                (key, val_str)
            )
        else:
            self.db.execute(
                """
                INSERT INTO GlobalSettings (Key, Value)
                VALUES (?, ?)
                ON CONFLICT(Key) DO UPDATE SET Value = excluded.Value
                """,
                (key, val_str)
            )

    def get_starting_kitty(self) -> float:
        val = self.get_setting("StartingKitty", "0")
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    def set_starting_kitty(self, amount: float):
        self.set_setting("StartingKitty", amount)

    def get_master_file(self) -> str:
        return self.get_setting("MasterFile", "")

    def set_master_file(self, path: str):
        self.set_setting("MasterFile", path)
