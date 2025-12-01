# marauders/repositories/games_repo.py

from typing import List, Optional
import pandas as pd
from marauders.database import Database


class GameRepository:
    """
    Handles access to:
      - Distinct game dates from Scores table
      - ExcludedGames table for ignoring specific rounds
      - Helper methods for retrieving filtered game lists
    """

    def __init__(self, db: Database):
        self.db = db
        self._ensure_excluded_table_exists()

    # ----------------------------------------------------------
    # INTERNAL: Ensure table exists
    # ----------------------------------------------------------
    def _ensure_excluded_table_exists(self) -> None:
        """
        Makes sure the ExcludedGames table exists.
        This supports your 'exclude game dates from analysis' feature.
        """
        sql = """
            CREATE TABLE IF NOT EXISTS ExcludedGames (
                GameDate TEXT PRIMARY KEY,
                Reason TEXT
            );
        """
        self.db.execute(sql)

    # ----------------------------------------------------------
    # GAME DATE QUERIES
    # ----------------------------------------------------------
    def get_all_game_dates(self) -> List[str]:
        """
        Returns *all* unique game dates from the Scores table.
        """
        df = self.db.read_sql("""
            SELECT DISTINCT Game_Date
            FROM Scores
            ORDER BY Game_Date;
        """)
        return df["Game_Date"].tolist()

    def get_valid_game_dates(self) -> List[str]:
        """
        Returns game dates EXCLUDING those in the ExcludedGames table.
        """
        df = self.db.read_sql("""
            SELECT DISTINCT s.Game_Date
            FROM Scores s
            LEFT JOIN ExcludedGames e
              ON s.Game_Date = e.GameDate
            WHERE e.GameDate IS NULL
            ORDER BY s.Game_Date;
        """)
        return df["Game_Date"].tolist()

    def get_excluded_game_dates(self) -> pd.DataFrame:
        """
        Returns a DataFrame of excluded game dates and reasons.
        """
        return self.db.read_sql("""
            SELECT *
            FROM ExcludedGames
            ORDER BY GameDate;
        """)

    # ----------------------------------------------------------
    # EXCLUSION OPERATIONS
    # ----------------------------------------------------------
    def exclude_game(self, game_date: str, reason: str = "") -> None:
        """
        Mark a game date as excluded from analysis.
        """
        sql = """
            INSERT OR REPLACE INTO ExcludedGames (GameDate, Reason)
            VALUES (?, ?)
        """
        self.db.execute(sql, (game_date, reason))

    def include_game(self, game_date: str) -> None:
        """
        Remove a game from the exclusion list.
        """
        self.db.execute("DELETE FROM ExcludedGames WHERE GameDate=?", (game_date,))

    def is_excluded(self, game_date: str) -> bool:
        df = self.db.read_sql("""
            SELECT GameDate
            FROM ExcludedGames
            WHERE GameDate = ?
        """, (game_date,))
        return not df.empty

    # ----------------------------------------------------------
    # SCORE ACCESS FOR A SPECIFIC GAME
    # ----------------------------------------------------------
    def get_scores_for_game(self, game_date: str) -> pd.DataFrame:
        """
        Retrieves all score rows for a given game date.
        Useful for summary, prizes, and handicap engines.
        """
        df = self.db.read_sql("""
            SELECT *
            FROM Scores
            WHERE Game_Date = ?
            ORDER BY Player_Name;
        """, (game_date,))

        df["Game_Date"] = pd.to_datetime(df["Game_Date"], errors="coerce")
        df["Player_Name"] = df["Player_Name"].astype(str).strip()

        return df
