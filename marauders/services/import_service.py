# marauders/services/import_service.py

from __future__ import annotations
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional

from marauders.database import Database
from marauders.repositories.scores_repo import ScoreRepository


class ImportService:
    """
    Imports new scores from the MASTER_FILE Excel sheet.
    Replaces import_new_scores.py with clean, testable logic.
    """

    # Mapping from Excel → SQLite Scores table columns
    SCORES_RENAME_MAP = {
        "Game Date": "Game_Date",
        "Player Name": "Player_Name",
        "Front Nine": "Front_Nine",
        "Back Nine": "Back_Nine",
        "Overall": "Overall",
        "NTP Hole 3": "NTP_Hole3",
        "NTP Hole 6": "NTP_Hole6",
        "NTP in 2 Hole 7": "NTP_in2_Hole7",
        "NTP in 2 Hole 10": "NTP_in2_Hole10",
        "NTP Hole 11": "NTP_Hole11",
        "NTP Hole 15": "NTP_Hole15",
    }

    # Columns that exist in Excel but not in DB
    COLUMNS_TO_DROP = ["Handicap"]

    def __init__(self, db: Database, master_file: str):
        self.db = db
        self.master_file = Path(master_file)
        self.scores_repo = ScoreRepository(db)

    # ------------------------------------------------------------------
    # CORE IMPORT LOGIC
    # ------------------------------------------------------------------
    def import_new_scores(self) -> Dict[str, Any]:
        """
        Imports new rows from the Excel MASTER_FILE's "Scores" sheet.

        Returns a dict with:
            {
                "imported_count": int,
                "existing_count": int,
                "new_keys": list[(date, player)],
                "skipped_keys": list[(date, player)]
            }
        """

        # --------------------------------------------------------------
        # Step 1 — Validate file
        # --------------------------------------------------------------
        if not self.master_file.exists():
            raise FileNotFoundError(f"Master Excel file not found: {self.master_file}")

        # --------------------------------------------------------------
        # Step 2 — Load Excel
        # --------------------------------------------------------------
        df_new = pd.read_excel(self.master_file, sheet_name="Scores")

        # Drop columns not in DB
        for col in self.COLUMNS_TO_DROP:
            if col in df_new.columns:
                df_new.drop(columns=[col], inplace=True)

        # --------------------------------------------------------------
        # Step 3 — Normalise column names
        # --------------------------------------------------------------
        df_new.rename(columns=self.SCORES_RENAME_MAP, inplace=True, errors="ignore")

        # Ensure required fields are present
        required = ["Game_Date", "Player_Name"]
        for col in required:
            if col not in df_new.columns:
                raise ValueError(f"Missing required column '{col}' in Excel file.")

        # Clean values
        df_new["Game_Date"] = pd.to_datetime(df_new["Game_Date"], errors="coerce").dt.date
        df_new["Player_Name"] = df_new["Player_Name"].astype(str).str.strip()

        # --------------------------------------------------------------
        # Step 4 — Determine which rows already exist in SQLite
        # --------------------------------------------------------------
        existing_keys = self.scores_repo.get_existing_keys()
        new_keys = set(zip(df_new["Game_Date"], df_new["Player_Name"]))

        missing_keys = new_keys - existing_keys
        skipped_keys = new_keys.intersection(existing_keys)

        # Filter to the rows that should be imported
        mask = df_new.apply(
            lambda r: (r["Game_Date"], r["Player_Name"]) in missing_keys,
            axis=1,
        )
        df_to_import = df_new[mask].copy()

        # --------------------------------------------------------------
        # Step 5 — Append new rows into SQLite
        # --------------------------------------------------------------
        if not df_to_import.empty:
            # Convert Game_Date back to string for SQLite storage
            df_to_import["Game_Date"] = df_to_import["Game_Date"].astype(str)

            # Write new rows to DB
            self.scores_repo.add_scores(df_to_import)

        # --------------------------------------------------------------
        # Step 6 — Build return summary
        # --------------------------------------------------------------
        return {
            "imported_count": len(df_to_import),
            "existing_count": len(existing_keys),
            "new_keys": list(missing_keys),
            "skipped_keys": list(skipped_keys),
        }
