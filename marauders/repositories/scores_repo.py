# marauders/repositories/scores_repo.py

import pandas as pd
from typing import List
from marauders.database import Database


class ScoreRepository:
    """Access to the Scores table."""

    def __init__(self, db: Database):
        self.db = db

    # ----------------------------------------------------------
    # READ
    # ----------------------------------------------------------
    def get_all(self) -> pd.DataFrame:
        df = self.db.get_table("Scores")
        df["Game_Date"] = pd.to_datetime(df["Game_Date"], errors="coerce")
        df["Player_Name"] = df["Player_Name"].astype(str).str.strip()
        return df.dropna(subset=["Game_Date", "Player_Name"])

    def get_game_dates(self) -> List[str]:
        df = self.db.read_sql("""
            SELECT DISTINCT Game_Date
            FROM Scores
            ORDER BY Game_Date
        """)
        return df["Game_Date"].tolist()

    def get_scores_for_date(self, date) -> pd.DataFrame:
        df = self.db.read_sql("""
            SELECT *
            FROM Scores
            WHERE DATE(Game_Date) = DATE(?)
        """, (str(date),))

        df["Game_Date"] = pd.to_datetime(df["Game_Date"], errors="coerce")
        df["Player_Name"] = df["Player_Name"].astype(str).str.strip()

        return df

    # ----------------------------------------------------------
    # EXISTING KEY CHECKER
    # ----------------------------------------------------------
    def get_existing_keys(self) -> set:
        df = self.db.read_sql("""
            SELECT Game_Date, Player_Name
            FROM Scores
        """)

        df["Game_Date"] = pd.to_datetime(df["Game_Date"]).dt.date
        df["Player_Name"] = df["Player_Name"].astype(str).str.strip()

        return set(zip(df["Game_Date"], df["Player_Name"]))

    # ----------------------------------------------------------
    # INSERT
    # ----------------------------------------------------------
    def add_scores(self, df_scores: pd.DataFrame) -> None:
        """Append new score rows to the Scores table."""
        self.db.write_table("Scores", df_scores, replace=False)
