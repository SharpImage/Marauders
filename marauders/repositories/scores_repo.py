# marauders/repositories/scores_repo.py

import pandas as pd
import datetime
from marauders.database import Database


class ScoreRepository:
    """Repository for accessing the Scores table safely."""

    def __init__(self, db: Database):
        self.db = db
        self._ensure_table()

    def _ensure_table(self):
        """Ensure the Scores table exists."""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS Scores (
                Game_Date TEXT,
                Player_Name TEXT,
                Front_Nine INTEGER,
                Back_Nine INTEGER,
                Overall INTEGER,
                NTP_Hole3 REAL,
                NTP_Hole6 REAL,
                NTP_in2_Hole7 REAL,
                NTP_in2_Hole10 REAL,
                NTP_Hole11 REAL,
                NTP_Hole15 REAL
            )
        """)
        self.db.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_scores_unique
            ON Scores (Game_Date, Player_Name);
        """)

    # ----------------------------------------------------------
    # Internal date parser to guarantee Python datetime.date
    # ----------------------------------------------------------
    def _safe_to_date(self, val):
        """Convert a value into Python datetime.date or None."""
        if isinstance(val, datetime.date):
            return val

        if isinstance(val, pd.Timestamp):
            # Convert Timestamp → Python date
            return val.date()

        if isinstance(val, str):
            v = val.strip()
            parsed = pd.to_datetime(v, errors="coerce")
            if pd.isna(parsed):
                return None
            return parsed.date()

        # Anything else → try Pandas, fallback to None
        try:
            parsed = pd.to_datetime(val, errors="coerce")
            if pd.isna(parsed):
                return None
            return parsed.date()
        except:
            return None

    # ----------------------------------------------------------
    # MAIN GETTER — FIXED
    # ----------------------------------------------------------
    def get_all(self) -> pd.DataFrame:
        """
        Load scores and force Game_Date to Python datetime.date
        so Pandas cannot convert them back into Timestamps
        during concatenation in FinanceService.
        """
        df = self.db.get_table("Scores").copy()

        if df.empty:
            return df

        # Ensure raw string first
        df["Game_Date"] = df["Game_Date"].astype(str).str.strip()
        df["Player_Name"] = df["Player_Name"].astype(str).str.strip()

        # Convert to safe Python date
        df["Game_Date"] = df["Game_Date"].apply(self._safe_to_date)

        # CRITICAL: Prevent Pandas from upcasting to Timestamp later
        df["Game_Date"] = df["Game_Date"].astype(object)

        return df

    # ----------------------------------------------------------
    def get_existing_keys(self) -> set:
        """
        Return set of (Game_Date_string, Player_Name).
        FinanceService will convert date strings later.
        """
        df = self.db.read_sql("""
            SELECT Game_Date, Player_Name
            FROM Scores
        """)

        if df.empty:
            return set()

        # Leave strings – FinanceService parses safely
        df["Game_Date"] = df["Game_Date"].astype(str).str.strip()
        df["Player_Name"] = df["Player_Name"].astype(str).str.strip()

        return set(zip(df["Game_Date"], df["Player_Name"]))

    # ----------------------------------------------------------
    def add_scores(self, df_scores: pd.DataFrame) -> None:
        """Append new score rows to the Scores table."""
        self.db.write_table("Scores", df_scores, replace=False)

    def get_game_dates(self):
        """
        Return distinct game dates as raw strings.
        Always leave them as strings; FinanceService will convert.
        """
        df = self.db.read_sql("""
            SELECT DISTINCT Game_Date
            FROM Scores
            ORDER BY Game_Date
        """)

        if df.empty:
            return []

        # Make sure SQL values are treated as strings
        df["Game_Date"] = df["Game_Date"].astype(str).str.strip()

        return df["Game_Date"].tolist()

