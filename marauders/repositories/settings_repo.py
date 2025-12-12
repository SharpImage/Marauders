# marauders/repositories/settings_repo.py

from marauders.database import Database
from typing import Optional, Any


class SettingsRepository:
    """
    Unified repository for storing application settings.
    Replaces separate settings tables in Database, Manager, and FinanceRepo.

    Includes migration logic to preserve data from old 'AppSettings' and 'FinanceSettings' tables.
    """

    def __init__(self, db: Database):
        self.db = db
        self._ensure_table()
        self._migrate_old_settings()

    def _ensure_table(self):
        """Create GlobalSettings table if it does not exist."""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS GlobalSettings (
                Key TEXT PRIMARY KEY,
                Value TEXT
            )
        """)

    def _migrate_old_settings(self):
        """
        Migrate settings from legacy tables (AppSettings, FinanceSettings)
        if they exist and haven't been migrated yet.
        """
        # 1. Migrate MasterFile from AppSettings
        if self.db.table_exists("AppSettings"):
            try:
                # AppSettings schema: Setting, Value
                df = self.db.read_sql("SELECT Value FROM AppSettings WHERE Setting = 'MasterFile'")
                if not df.empty:
                    val = df.iloc[0]["Value"]
                    if val:
                        # Only overwrite if we don't already have a value (or force overwrite?)
                        # Let's overwrite safely (only if current is empty or default)
                        current = self.get_setting("MasterFile")
                        if not current:
                            self.set_setting("MasterFile", val)
                            print(f"DEBUG: Migrated MasterFile '{val}' from AppSettings.")
            except Exception as e:
                print(f"DEBUG: Failed to migrate AppSettings: {e}")

        # 2. Migrate StartingKitty from FinanceSettings
        if self.db.table_exists("FinanceSettings"):
            try:
                # FinanceSettings schema: Setting, Value
                df = self.db.read_sql("SELECT Value FROM FinanceSettings WHERE Setting = 'StartingKitty'")
                if not df.empty:
                    val = df.iloc[0]["Value"]
                    # Check current
                    current = self.get_setting("StartingKitty")
                    if not current or current == "0.0" or current == "0":
                         self.set_setting("StartingKitty", str(val))
                         print(f"DEBUG: Migrated StartingKitty '{val}' from FinanceSettings.")
            except Exception as e:
                print(f"DEBUG: Failed to migrate FinanceSettings: {e}")

        # Ensure default values exist if still missing
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
