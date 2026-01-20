from typing import Dict, Any, List
import pandas as pd
from marauders.database import Database


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

    # Players Rename Map
    PLAYERS_RENAME_MAP = {
        "Player": "Player",
        "First Name": "First_Name",
        "Last Name": "Last_Name",
        "Primary Email": "Primary_Email",
        "Starting Handicap": "StartingHandicap",
        "StartingHandicap": "StartingHandicap",
        "Active": "Active",
        "Starting Balance": "StartingBalance",
        "StartingBalance": "StartingBalance"
    }

    def __init__(self, db: Database, master_file: str):
        """Initialise the ImportService.

        Parameters:
            db           -- Database instance for repo construction
            master_file  -- Path to the Excel score sheet
        """
        self.db = db

        # Repositories
        from marauders.repositories.scores_repo import ScoreRepository
        from marauders.repositories.players_repo import PlayerRepository
        from marauders.repositories.finance_repo import FinanceRepository
        from marauders.repositories.settings_repo import SettingsRepository

        self.scores_repo = ScoreRepository(db)
        self.players_repo = PlayerRepository(db)
        self.finance_repo = FinanceRepository(db, SettingsRepository(db))

        # Store master file path
        self.master_file = master_file

    def _load_excel_sheet(self, sheet_names: List[str]) -> pd.DataFrame:
        """Try loading one of the possible sheet names."""
        for name in sheet_names:
            try:
                df = pd.read_excel(self.master_file, sheet_name=name)
                print(f"DEBUG: Loaded sheet '{name}'")
                return df
            except ValueError:
                continue
        return pd.DataFrame()

    def _load_excel_scores_sheet(self):
        try:
            # First try loading "Scores" sheet
            try:
                df = pd.read_excel(self.master_file, sheet_name="Scores")
            except ValueError:
                # Fallback to first sheet
                print("DEBUG: 'Scores' sheet not found, checking if first sheet looks like scores...")
                df = pd.read_excel(self.master_file)

                # Simple heuristic: check for typical columns
                cols = [str(c).lower() for c in df.columns]
                if not any("player" in c for c in cols) or not any("date" in c for c in cols):
                    print("DEBUG: First sheet does not look like Scores (missing 'Player'/'Date'). Skipping default fallback.")
                    return pd.DataFrame() # Return empty if it doesn't look like scores

            return df
        except Exception as e:
            raise RuntimeError(f"Failed to load Excel file '{self.master_file}': {e}")

    def import_all(self):
        """Run all imports."""
        results = {}
        results["scores"] = self.import_new_scores()
        results["players"] = self.import_players()
        results["finance"] = self.import_finance()
        results["config"] = self.import_config()
        return results

    def import_new_scores(self) -> Dict[str, Any]:
        """
        Import new scores from the master Excel file into the Scores table.
        Also AUTO-CREATES players found in scores if they don't exist.
        """
        df_new = self._load_excel_scores_sheet()

        if df_new.empty:
             print("DEBUG: No scores sheet found or sheet is empty.")
             return {"imported_count": 0, "status": "No data"}

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
                print(f"DEBUG: Missing required column '{col}' in Scores data.")
                return {"imported_count": 0, "status": f"Missing {col}"}

        # --------------------------------------------------------------
        # DATE PARSING
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
        df_new = df_new.dropna(subset=["Game_Date", "Player_Name"])

        # Normalise player names
        df_new["Player_Name"] = df_new["Player_Name"].astype(str).str.strip()

        # Deduplicate
        df_new = df_new.sort_values(["Game_Date", "Player_Name"])
        df_new = df_new.drop_duplicates(
            subset=["Game_Date", "Player_Name"],
            keep="last"
        )

        # --------------------------------------------------------------
        # AUTO-CREATE MISSING PLAYERS
        # --------------------------------------------------------------
        unique_players_in_scores = df_new["Player_Name"].unique()
        for player_name in unique_players_in_scores:
            if not self.players_repo.player_exists(player_name):
                print(f"DEBUG: Auto-creating missing player '{player_name}'")
                self.players_repo.add_player(
                    player=player_name,
                    starting_handicap=0.0, # Default
                    active="YES"
                )

        # --------------------------------------------------------------
        # Load existing keys & Import
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

    def import_players(self):
        """Import players from 'Players' sheet if it exists."""
        df = self._load_excel_sheet(["Players", "Player List"])
        if df.empty:
            return "No Players sheet found"

        # Rename columns
        df.rename(columns=self.PLAYERS_RENAME_MAP, inplace=True)

        if "Player" not in df.columns:
            return "Players sheet missing 'Player' column"

        count = 0
        for _, row in df.iterrows():
            player = str(row["Player"]).strip()
            if not player or str(player).lower() == 'nan':
                continue

            # Defaults
            fname = row.get("First_Name", "")
            lname = row.get("Last_Name", "")
            email = row.get("Primary_Email", "")
            try:
                hcap = float(row.get("StartingHandicap", 0.0))
            except:
                hcap = 0.0

            try:
                bal = float(row.get("StartingBalance", 0.0))
            except:
                bal = 0.0

            active = str(row.get("Active", "YES")).upper()

            # Upsert
            if self.players_repo.player_exists(player):
                self.players_repo.update_player(
                    player,
                    First_Name=fname,
                    Last_Name=lname,
                    Primary_Email=email,
                    StartingHandicap=hcap,
                    StartingBalance=bal,
                    Active=active
                )
            else:
                self.players_repo.add_player(
                    player=player,
                    first_name=fname,
                    last_name=lname,
                    email=email,
                    starting_handicap=hcap,
                    starting_balance=bal,
                    active=active
                )
            count += 1

        return f"Imported/Updated {count} players"

    def import_finance(self):
        """Import manual transactions from 'Transactions' or 'Finance' sheet."""
        df = self._load_excel_sheet(["Transactions", "Finance", "Ledger"])
        if df.empty:
            return "No Transactions sheet found"

        # Expected columns: Date, Player, PaidIn, PaidOut, Description
        count = 0
        existing_txs = self.finance_repo.get_ledger() # Just for info, we append all for now (could dupe)
        # To avoid dupes, we might need a better check, but for now let's just import valid rows

        required = ["Date", "Player", "PaidIn", "PaidOut", "Description"]
        if not all(col in df.columns for col in required):
            return f"Transactions sheet missing columns. Need: {required}"

        for _, row in df.iterrows():
            try:
                date_val = pd.to_datetime(row["Date"]).date()
                player = str(row["Player"]).strip()
                paid_in = float(row.get("PaidIn", 0.0))
                paid_out = float(row.get("PaidOut", 0.0))
                desc = str(row.get("Description", ""))

                # Check for exact duplicate in DB?
                # Doing a simple check here is expensive loop-by-loop.
                # We'll just append for now, user can delete.
                self.finance_repo.add_transaction(date_val, player, paid_in, paid_out, desc)
                count += 1
            except Exception:
                continue

        return f"Imported {count} transactions"

    def import_config(self):
        """Import PlaceCuts and PointsAdjustment."""
        res = []

        # PlaceCuts
        df_pc = self._load_excel_sheet(["PlaceCuts", "Place Cuts"])
        if not df_pc.empty:
            if all(c in df_pc.columns for c in ["noOfWinners", "Cut", "no2dPlaces", "Cut2"]):
                self.db.write_table("PlaceCuts", df_pc, replace=True)
                res.append("PlaceCuts updated")

        # PointsAdjustment
        df_pa = self._load_excel_sheet(["PointsAdjustment", "Points Adjustment"])
        if not df_pa.empty:
            if all(c in df_pa.columns for c in ["StbfPoints", "HndChange"]):
                self.db.write_table("PointsAdjustment", df_pa, replace=True)
                res.append("PointsAdjustment updated")

        return ", ".join(res) if res else "No config sheets found"
