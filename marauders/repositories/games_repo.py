# marauders/repositories/games_repo.py

import pandas as pd
from datetime import date
from marauders.database import Database


class GameRepository:
    """
    Handles access to game-related tables including ExcludedGames.
    """

    def __init__(self, db: Database):
        self.db = db

    # --------------------------------------------------------------
    # GAME DATE LIST FROM SCORES
    # --------------------------------------------------------------
    def get_all_game_dates(self):
        df = self.db.read_sql("""
            SELECT DISTINCT Game_Date
            FROM Scores
            ORDER BY Game_Date
        """)
        if df.empty:
            return []
        df["Game_Date"] = pd.to_datetime(df["Game_Date"], errors="coerce").dt.date
        return df["Game_Date"].tolist()

    # --------------------------------------------------------------
    # FULL TABLE FOR GUI — RETURNS DataFrame
    # --------------------------------------------------------------
    def get_excluded_games_table(self) -> pd.DataFrame:
        """
        Returns the FULL ExcludedGames table for GUI display.
        """
        df = self.db.get_table("ExcludedGames").copy()

        if df.empty:
            return pd.DataFrame(columns=["GameDate", "Reason"])

        df["GameDate"] = pd.to_datetime(df["GameDate"], errors="coerce").dt.date
        df["Reason"] = df["Reason"].astype(str)

        return df

    # --------------------------------------------------------------
    # FOR HANDICAP ENGINE — RETURNS LIST OF DATES
    # --------------------------------------------------------------
    def get_excluded_game_dates(self) -> list[date]:
        """
        Returns only the list of excluded game dates as Python date objects.
        """
        df = self.db.get_table("ExcludedGames").copy()

        if df.empty or "GameDate" not in df.columns:
            return []

        df["GameDate"] = pd.to_datetime(df["GameDate"], errors="coerce").dt.date
        return df["GameDate"].dropna().tolist()

    # --------------------------------------------------------------
    # ADD EXCLUDED GAME
    # --------------------------------------------------------------
    def add_excluded_game(self, game_date: date, reason: str):
        df = pd.DataFrame([{
            "GameDate": pd.to_datetime(game_date),
            "Reason": reason
        }])
        self.db.write_table("ExcludedGames", df, replace=False)

    # --------------------------------------------------------------
    # REMOVE EXCLUDED GAME
    # --------------------------------------------------------------
    def remove_excluded_game(self, game_date):
        date_str = str(game_date)
        self.db.execute(
            "DELETE FROM ExcludedGames WHERE GameDate = ?",
            (date_str,),
        )
