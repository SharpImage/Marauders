# marauders/services/import_service.py

from __future__ import annotations

import pandas as pd
import requests
from io import BytesIO
from pathlib import Path
from typing import Dict, Any

from marauders.database import Database
from marauders.repositories.scores_repo import ScoreRepository


class ImportService:
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

    COLUMNS_TO_DROP = ["Handicap"]

    def __init__(self, db: Database, master_file: str):
        self.db = db
        self.master_file = master_file
        self.scores_repo = ScoreRepository(db)

    # ------------------------------------------------------------------
    # INTERNAL: LOAD EXCEL (LOCAL OR URL)
    # ------------------------------------------------------------------
    def _load_excel_scores_sheet(self) -> pd.DataFrame:
        if not self.master_file:
            raise ValueError("Master Excel file path/URL is not set.")

        path = str(self.master_file).strip()

        # URL
        if path.startswith("http://") or path.startswith("https://"):
            print("DEBUG: ImportService loading Excel from URL:", path)
            try:
                resp = requests.get(path, timeout=15)
                resp.raise_for_status()
                stream = BytesIO(resp.content)
                df = pd.read_excel(stream, sheet_name="Scores")
            except Exception as e:
                raise RuntimeError(
                    f"Failed to read Excel from URL:\n{path}\nError: {e}"
                )
            return df

        # LOCAL
        excel_path = Path(path)
        if not excel_path.exists():
            raise FileNotFoundError(f"Master Excel file not found: {excel_path}")

        print("DEBUG: ImportService loading Excel from LOCAL file:", excel_path)
        return pd.read_excel(excel_path, sheet_name="Scores")

    # ------------------------------------------------------------------
    # CORE IMPORT LOGIC
    # ------------------------------------------------------------------
    def import_new_scores(self) -> Dict[str, Any]:

        df_new = self._load_excel_scores_sheet()

        # Drop unnecessary Excel columns
        for col in self.COLUMNS_TO_DROP:
            if col in df_new.columns:
                df_new.drop(columns=[col], inplace=True)

        # Normalise columns
        df_new.rename(columns=self.SCORES_RENAME_MAP, inplace=True, errors="ignore")

        # Validate required columns
        required = ["Game_Date", "Player_Name"]
        for col in required:
            if col not in df_new.columns:
                raise ValueError(f"Missing required column '{col}' in Excel file.")

        # ------------------------------------------------------------------
        # ⭐ FIXED: Interpret dates as UK/EU day-first format
        # ------------------------------------------------------------------
        df_new["Game_Date"] = pd.to_datetime(
            df_new["Game_Date"],
            dayfirst=True,        # ⭐ <<<<<<<< FIX HERE
            errors="coerce"
        ).dt.date

        df_new["Player_Name"] = df_new["Player_Name"].astype(str).str.strip()

        df_new = df_new.dropna(subset=["Game_Date", "Player_Name"])

        # ------------------------------------------------------------------
        # Load existing DB keys — must also use dayfirst=True!
        # ------------------------------------------------------------------
        existing_keys = self.scores_repo.get_existing_keys()

        new_keys = set(zip(df_new["Game_Date"], df_new["Player_Name"]))

        missing_keys = new_keys - existing_keys
        skipped_keys = new_keys.intersection(existing_keys)

        df_to_import = df_new[
            df_new.apply(lambda r: (r["Game_Date"], r["Player_Name"]) in missing_keys, axis=1)
        ].copy()

        if not df_to_import.empty:

            df_to_import["Game_Date"] = df_to_import["Game_Date"].astype(str)

            print(f"DEBUG: Importing {len(df_to_import)} NEW score rows...")
            self.scores_repo.add_scores(df_to_import)
        else:
            print("DEBUG: No new score rows to import.")

        return {
            "imported_count": len(df_to_import),
            "existing_count": len(existing_keys),
            "new_keys": list(missing_keys),
            "skipped_keys": list(skipped_keys),
        }
