# marauders/repositories/handicaps_repo.py

import pandas as pd
from typing import Optional
from marauders.database import Database


class HandicapRepository:
    """
    Provides access to handicap-related tables:
      - HandicapHistory
      - CurrentHandicaps
      - PointsAdjustment (Stableford → Handicap change)
      - PlaceCuts (Rank-based adjustments)
    """

    def __init__(self, db: Database):
        self.db = db

    # ----------------------------------------------------------
    # Handicap History
    # ----------------------------------------------------------
    def get_history(self) -> pd.DataFrame:
        """Return the entire HandicapHistory table."""
        df = self.db.get_table("HandicapHistory")
        if df.empty:
            return df

        df["GameDate"] = pd.to_datetime(df["GameDate"], errors="coerce")
        df = df.dropna(subset=["Player", "GameDate"])
        df["Player"] = df["Player"].astype(str).str.strip()
        return df.sort_values(["GameDate", "Player"]).reset_index(drop=True)

    def save_history(self, history_df: pd.DataFrame) -> None:
        """Replace the HandicapHistory table with new data."""
        self.db.write_table("HandicapHistory", history_df, replace=True)

    # ----------------------------------------------------------
    # Current Handicaps
    # ----------------------------------------------------------
    def get_current(self) -> pd.DataFrame:
        """
        Return CurrentHandicaps for ACTIVE players only.
        Performs safe numeric rounding and fallback for fresh DB.
        """
        try:
            df = self.db.read_sql("""
                                  SELECT ch.Player,
                                         ch.CurrentHandicap,
                                         p.Active
                                  FROM CurrentHandicaps ch
                                           LEFT JOIN Players p
                                                     ON ch.Player = p.Player
                                  """)
        except Exception:
            # Table not yet created
            return pd.DataFrame(columns=["Player", "CurrentHandicap"])

        if df.empty:
            return pd.DataFrame(columns=["Player", "CurrentHandicap"])

        # Only include Active players (default to YES if missing)
        df["Active"] = df["Active"].fillna("YES").astype(str).str.upper().str.strip()
        df = df[df["Active"] == "YES"]

        # Clean / round handicap values
        df["CurrentHandicap"] = (
            pd.to_numeric(df["CurrentHandicap"], errors="coerce")
            .fillna(0.0)
            .round(1)
        )

        df["Player"] = df["Player"].astype(str).str.strip()
        return df[["Player", "CurrentHandicap"]].sort_values("Player").reset_index(drop=True)

    def save_current(self, current_df: pd.DataFrame) -> None:
        """Replace the CurrentHandicaps table."""
        self.db.write_table("CurrentHandicaps", current_df, replace=True)

    # ----------------------------------------------------------
    # Adjustment Rules
    # ----------------------------------------------------------
    def get_place_cuts(self) -> pd.DataFrame:
        """
        Rank-based adjustments based on:
            - noOfWinners
            - no2dPlaces
            - Cut
            - Cut2
        """
        df = self.db.get_table("PlaceCuts")
        if df.empty:
            return df

        df["noOfWinners"] = pd.to_numeric(df["noOfWinners"], errors="coerce")
        df["no2dPlaces"] = pd.to_numeric(df["no2dPlaces"], errors="coerce")
        df["Cut"] = pd.to_numeric(df["Cut"], errors="coerce")
        df["Cut2"] = pd.to_numeric(df["Cut2"], errors="coerce")
        return df

    def get_points_adjustment(self) -> pd.DataFrame:
        """
        PointsAdjustment table maps Stableford points → Handicap adjustment.
        """
        df = self.db.get_table("PointsAdjustment")
        if df.empty:
            return df

        df["StbfPoints"] = pd.to_numeric(df["StbfPoints"], errors="coerce")
        df["HndChange"] = pd.to_numeric(df["HndChange"], errors="coerce")
        return df

    # ----------------------------------------------------------
    # Player-specific history helpers
    # ----------------------------------------------------------
    def get_latest_handicap_for_player(self, player: str) -> Optional[float]:
        """
        Returns the most recent handicap for a given player.
        If they have no history, return None.
        """
        df = self.db.read_sql("""
            SELECT Player, GameDate, NewHandicap
            FROM HandicapHistory
            WHERE Player = ?
            ORDER BY GameDate DESC
            LIMIT 1
        """, (player,))

        if df.empty:
            return None

        return float(df.iloc[0]["NewHandicap"])
