from typing import Dict, Any
import pandas as pd


class ImportService:
    COLUMNS_TO_DROP = [
        "Handicaps"
    ]
    SCORES_RENAME_MAP = {
        "Game Date": "Game_Date",
        "Player Name": "Player_Name",
        "Front Nine": "Front_Nine",
        "Back Nine": "Back_Nine",
        "Overall": "Overall",
        # NTP columns – Excel headers → DB column names
        "NTP Hole 3": "NTP_Hole3",
        "NTP Hole 6": "NTP_Hole6",
        "NTP in 2 Hole 7": "NTP_in2_Hole7",
        "NTP in 2 Hole 10": "NTP_in2_Hole10",
        "NTP Hole 11": "NTP_Hole11",
        "NTP Hole 15": "NTP_Hole15",
    }

    def __init__(self, db, master_file: str):
        """Initialise the ImportService.

        Parameters:
            db           -- Database instance for repo construction
            master_file  -- Path to the Excel score sheet
        """

        # The scores repo is constructed using the database
        from marauders.repositories.scores_repo import ScoreRepository
        self.scores_repo = ScoreRepository(db)

        # Store master file path
        self.master_file = master_file

    def _load_excel_scores_sheet(self):
        import pandas as pd

        try:
            df = pd.read_excel(self.master_file)
            return df
        except Exception as e:
            raise RuntimeError(f"Failed to load Excel file '{self.master_file}': {e}")

    def import_new_scores(self) -> Dict[str, Any]:
        """
        Import new scores from the master Excel file into the Scores table.

        Returns a dict summarising what happened:
            {
                "imported_count": int,
                "existing_count": int,
                "new_keys":      List[(Game_Date, Player_Name)],
                "skipped_keys":  List[(Game_Date, Player_Name)],
            }
        """

        df_new = self._load_excel_scores_sheet()

        # Drop unnecessary Excel columns
        for col in self.COLUMNS_TO_DROP:
            if col in df_new.columns:
                df_new.drop(columns=[col], inplace=True)

        # Normalise columns
        df_new.rename(
            columns=self.SCORES_RENAME_MAP,
            inplace=True,
            errors="ignore"
        )

        # Validate required columns
        required = ["Game_Date", "Player_Name"]
        for col in required:
            if col not in df_new.columns:
                raise ValueError(
                    f"Missing required column '{col}' in Excel file."
                )

        # --------------------------------------------------------------
        # ✔ FIXED DATE PARSING
        # --------------------------------------------------------------
        raw_dates = df_new["Game_Date"].astype(str).copy()

        df_new["Game_Date"] = pd.to_datetime(
            raw_dates,
            format="%Y-%m-%d",
            errors="coerce"
        )

        mask_bad = df_new["Game_Date"].isna()
        if mask_bad.any():
            fallback = pd.to_datetime(
                raw_dates[mask_bad],
                errors="coerce"
            )
            df_new.loc[mask_bad, "Game_Date"] = fallback

        df_new["Game_Date"] = df_new["Game_Date"].dt.date

        invalid_rows = df_new[df_new["Game_Date"].isna()]
        if not invalid_rows.empty:
            print("\n⚠️ WARNING: Skipping rows with invalid dates:")
            print(invalid_rows[["Game_Date", "Player_Name"]])

        df_new = df_new.dropna(subset=["Game_Date", "Player_Name"])

        # Normalise player names (bugfix: use .str.strip())
        df_new["Player_Name"] = df_new["Player_Name"].astype(str).str.strip()

        # --------------------------------------------------------------
        # Ensure at most one row per (Game_Date, Player_Name) in this import
        # (prevents duplicate rows like we saw for 2025-12-02).
        # If the Excel has duplicates for the same player on the same date,
        # keep the last occurrence.
        # --------------------------------------------------------------
        df_new = df_new.sort_values(["Game_Date", "Player_Name"])
        df_new = df_new.drop_duplicates(
            subset=["Game_Date", "Player_Name"],
            keep="last"
        )

        # --------------------------------------------------------------
        # Load existing keys
        # --------------------------------------------------------------
        existing_keys = self.scores_repo.get_existing_keys()
        new_keys = set(zip(df_new["Game_Date"], df_new["Player_Name"]))

        missing_keys = new_keys - existing_keys
        skipped_keys = new_keys.intersection(existing_keys)

        df_to_import = df_new[
            df_new.apply(
                lambda r: (r["Game_Date"], r["Player_Name"]) in missing_keys,
                axis=1,
            )
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
