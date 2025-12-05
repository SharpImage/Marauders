from typing import Dict, Any
import pandas as pd


class ImportService:

    # Columns that exist in Excel but we do not need
    COLUMNS_TO_DROP = [
        "Email", "Phone", "Handicap Index", "Updated"
    ]

    # FIXED – RENAME MAP RESTORED
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

        from marauders.repositories.scores_repo import ScoreRepository
        self.scores_repo = ScoreRepository(db)

        self.master_file = master_file

    # ----------------------------------------------------------
    # LOAD EXCEL
    # ----------------------------------------------------------
    def _load_excel_scores_sheet(self):
        try:
            # Some files have multiple sheets; Scores is the canonical one
            df = pd.read_excel(self.master_file, sheet_name="Scores")
            return df
        except Exception:
            # fallback if Scores sheet is missing
            try:
                return pd.read_excel(self.master_file)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to load Excel file '{self.master_file}': {e}"
                )

    # ----------------------------------------------------------
    # IMPORT NEW SCORES
    # ----------------------------------------------------------
    def import_new_scores(self) -> Dict[str, Any]:

        df_new = self._load_excel_scores_sheet()

        # -----------------------------------------------
        # NORMALISE HEADERS (critical fix)
        # -----------------------------------------------
        # Simple normalisation: just trim whitespace
        df_new.columns = df_new.columns.str.strip()

        # Rename Excel headers → internal names that match the DB schema
        df_new.rename(columns=self.SCORES_RENAME_MAP, inplace=True, errors="ignore")

        # At this point “Game Date” becomes “Game_Date”
        # and rename will correctly detect it.

        # -----------------------------------------------
        # APPLY RENAME MAP
        # -----------------------------------------------
        df_new.rename(columns=self.SCORES_RENAME_MAP, inplace=True, errors="ignore")

        # -----------------------------------------------
        # DROP UNUSED COLUMNS
        # -----------------------------------------------
        for col in self.COLUMNS_TO_DROP:
            if col in df_new.columns:
                df_new.drop(columns=[col], inplace=True)

        # -----------------------------------------------
        # VALIDATE REQUIRED COLUMNS
        # -----------------------------------------------
        required = ["Game_Date", "Player_Name"]
        missing = [col for col in required if col not in df_new.columns]

        if missing:
            raise ValueError(
                "Missing required columns in Excel file:\n" +
                "\n".join(f" - {m}" for m in missing)
            )

        # -----------------------------------------------
        # DATE PARSING – robust
        # -----------------------------------------------
        df_new["Game_Date"] = pd.to_datetime(
            df_new["Game_Date"], errors="coerce", dayfirst=False
        ).dt.date

        df_new = df_new.dropna(subset=["Game_Date", "Player_Name"])
        df_new["Player_Name"] = df_new["Player_Name"].astype(str).str.strip()

        # -----------------------------------------------
        # FIND NEW ROWS ONLY
        # -----------------------------------------------
        existing_keys = self.scores_repo.get_existing_keys()

        new_keys = set(zip(df_new["Game_Date"], df_new["Player_Name"]))

        missing_keys = new_keys - existing_keys
        skipped_keys = new_keys.intersection(existing_keys)

        df_to_import = df_new[
            df_new.apply(lambda r: (r["Game_Date"], r["Player_Name"]) in missing_keys, axis=1)
        ].copy()

        # -----------------------------------------------
        # INSERT NEW SCORES
        # -----------------------------------------------
        if not df_to_import.empty:
            df_to_import["Game_Date"] = df_to_import["Game_Date"].astype(str)
            self.scores_repo.add_scores(df_to_import)
        else:
            print("DEBUG: No new score rows to import.")

        return {
            "imported_count": len(df_to_import),
            "existing_count": len(existing_keys),
            "new_keys": list(missing_keys),
            "skipped_keys": list(skipped_keys),
        }
