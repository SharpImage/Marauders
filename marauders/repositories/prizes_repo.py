# marauders/repositories/prizes_repo.py

import pandas as pd
from typing import Optional, List
from marauders.database import Database


class PrizeRepository:
    """
    Handles the PrizeAllocation and PrizePayouts tables.
    PrizeAllocation  → prize rules based on number of players
    PrizePayouts     → results of prize calculations per game
    """

    def __init__(self, db: Database):
        self.db = db
        self._ensure_prizepayouts_table_exists()

    # ----------------------------------------------------------
    # INTERNAL: Ensure PrizePayouts table exists
    # ----------------------------------------------------------
    def _ensure_prizepayouts_table_exists(self):
        sql = """
            CREATE TABLE IF NOT EXISTS PrizePayouts (
                GameDate TEXT,
                Player TEXT,
                Category TEXT,
                Place TEXT,
                Amount REAL,
                Source TEXT DEFAULT 'PrizeEngine'
            );
        """
        self.db.execute(sql)

    # ----------------------------------------------------------
    # Prize Allocation Rules (per player count)
    # ----------------------------------------------------------
    def get_prize_allocation(self) -> pd.DataFrame:
        """
        Returns the full PrizeAllocation table.
        One row per number of players (Players column).
        """
        df = self.db.get_table("PrizeAllocation")
        if df.empty:
            return df

        df.columns = [c.strip() for c in df.columns]
        df["Players"] = pd.to_numeric(df["Players"], errors="coerce")

        # Ensure numeric prize columns
        for col in df.columns:
            if col.lower() != "players":
                df[col] = pd.to_numeric(df[col], errors="coerce")

        return df.sort_values("Players")

    def get_allocation_for_player_count(self, num_players: int) -> Optional[pd.Series]:
        """
        Returns the allocation row for the given number of players.
        If none exists, return None.
        """
        df = self.get_prize_allocation()
        if df.empty:
            return None

        match = df[df["Players"] == num_players]
        if match.empty:
            return None

        return match.iloc[0]

    # ----------------------------------------------------------
    # Prize Payouts (written by PrizeService)
    # ----------------------------------------------------------
    def clear_payouts(self):
        """Remove all rows (used before recomputing)."""
        self.db.execute("DELETE FROM PrizePayouts")

    def save_payouts(self, payouts_df: pd.DataFrame):
        """Append prize payout rows."""
        self.db.write_table("PrizePayouts", payouts_df, replace=False)

    def get_all_payouts(self) -> pd.DataFrame:
        """Returns PrizePayouts table with GameDate as raw string (not Timestamp)."""
        df = self.db.get_table("PrizePayouts")
        if df.empty:
            return df

        # Prevent Pandas auto-parsing by leaving GameDate as string
        df["GameDate"] = df["GameDate"].astype(str).str.strip()
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0.0)

        df["Player"] = df["Player"].astype(str).str.strip()
        df["Category"] = df["Category"].astype(str).str.strip()
        df["Place"] = df["Place"].astype(str).str.strip()

        return df.sort_values(["GameDate", "Category", "Player"])

    def get_payouts_for_game(self, game_date: str) -> pd.DataFrame:
        """Returns all prizes awarded for a single game."""
        df = self.db.read_sql("""
            SELECT *
            FROM PrizePayouts
            WHERE GameDate = ?
            ORDER BY Category, Player
        """, (game_date,))
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0.0)
        return df

    # ----------------------------------------------------------
    # Summary helpers
    # ----------------------------------------------------------
    def get_total_prizes(self) -> pd.DataFrame:
        """
        Returns total prize amount per player across all games.
        Excludes KITTY entries.
        """
        df = self.get_all_payouts()
        if df.empty:
            return pd.DataFrame(columns=["Player", "TotalPrize"])

        df_non_kitty = df[df["Player"] != "KITTY"]

        return (
            df_non_kitty.groupby("Player", as_index=False)["Amount"]
            .sum()
            .rename(columns={"Amount": "TotalPrize"})
            .sort_values("Player")
        )

    def get_total_prizes_for_game(self, game_date: str) -> pd.DataFrame:
        """
        Returns prize totals for one game (excluding KITTY).
        """
        df = self.get_payouts_for_game(game_date)
        df = df[df["Player"] != "KITTY"]

        if df.empty:
            return pd.DataFrame(columns=["Player", "TotalPrize"])

        return (
            df.groupby("Player", as_index=False)["Amount"]
            .sum()
            .rename(columns={"Amount": "TotalPrize"})
        )
