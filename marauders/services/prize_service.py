# marauders/services/prize_service.py

from __future__ import annotations

import math
from typing import Dict, List

import pandas as pd

from marauders.database import Database
from marauders.repositories.scores_repo import ScoreRepository
from marauders.repositories.prizes_repo import PrizeRepository
from marauders.repositories.games_repo import GameRepository


class PrizeService:
    """
    Computes prize payouts for all games and saves them into PrizePayouts.

    Replaces the original prize_engine_sqlite.py, but:
      - Uses repositories instead of raw SQL
      - Respects excluded games via GameRepository
      - Returns DataFrames instead of writing CSV/printing
    """

    # Scores table column names
    SCORES_DATE_COL = "Game_Date"
    SCORES_PLAYER_COL = "Player_Name"

    FRONT9_COL = "Front_Nine"
    BACK9_COL = "Back_Nine"
    OVERALL_COL = "Overall"

    # NTP result columns in Scores table
    NTP_COLS = {
        3: "NTP_Hole3",
        6: "NTP_Hole6",
        7: "NTP_in2_Hole7",
        10: "NTP_in2_Hole10",
        11: "NTP_Hole11",
        15: "NTP_Hole15",
    }

    # Map hole → which PrizeAllocation column to use
    # These keys refer to columns in PrizeAllocation
    NTP_PRIZE_COLUMN_FOR_HOLE = {
        3: "ntp3",
        6: "ntp3",
        11: "ntp3",
        15: "ntp3",
        7: "ntp7",
        10: "ntp10",
    }

    # Column names for place prizes
    FIRST_PLACE_COL = "1stPlace"
    SECOND_PLACE_COL = "2ndPlace"

    def __init__(self, db: Database):
        self.db = db
        self.scores_repo = ScoreRepository(db)
        self.prizes_repo = PrizeRepository(db)
        self.games_repo = GameRepository(db)

    # ------------------------------------------------------------------
    # PUBLIC ENTRY POINT
    # ------------------------------------------------------------------
    def compute_all_prizes(self) -> Dict[str, pd.DataFrame]:
        """
        Computes prize payouts for all games (excluding excluded games),
        writes them to PrizePayouts, and returns:

            {
                "payouts": prize_df,
                "totals_per_player": totals_df
            }
        """
        # Load all scores, exclude games marked in ExcludedGames
        scores = self._load_valid_scores()

        # Load PrizeAllocation rules
        pa_df = self.prizes_repo.get_prize_allocation()
        if pa_df.empty:
            # No rules defined → nothing to compute
            empty = pd.DataFrame(
                columns=["GameDate", "Player", "Category", "Place", "Amount", "Source"]
            )
            return {"payouts": empty, "totals_per_player": empty}

        # We will build prize records in memory, then save via PrizeRepository
        prize_records: List[Dict] = []

        for game_date, df_game in scores.groupby(self.SCORES_DATE_COL, sort=True):
            df_game = df_game.copy()
            n_players = len(df_game)

            alloc_row = self._get_alloc_row(pa_df, n_players)
            if alloc_row is None:
                # No allocation row for this player count, skip quietly
                continue

            # 1st/2nd place prizes for Front9, Back9, Overall
            for points_col, label in [
                (self.FRONT9_COL, "Front9"),
                (self.BACK9_COL, "Back9"),
                (self.OVERALL_COL, "Overall"),
            ]:
                if points_col not in df_game.columns:
                    continue
                prize_records.extend(
                    self._allocate_place_prizes_for_comp(
                        game_date, df_game, points_col, label, alloc_row
                    )
                )

            # NTP prizes
            prize_records.extend(
                self._allocate_ntp_prizes_for_game(game_date, df_game, alloc_row)
            )

        if not prize_records:
            empty = pd.DataFrame(
                columns=["GameDate", "Player", "Category", "Place", "Amount", "Source"]
            )
            return {"payouts": empty, "totals_per_player": empty}

        prize_df = pd.DataFrame(prize_records)
        prize_df = prize_df.sort_values(
            ["GameDate", "Category", "Place", "Player"]
        ).reset_index(drop=True)

        # Save into PrizePayouts (wipe old then append)
        self.prizes_repo.clear_payouts()
        self.prizes_repo.save_payouts(prize_df)

        # Build totals per game & player (excluding KITTY)
        totals = (
            prize_df[prize_df["Player"] != "KITTY"]
            .groupby(["GameDate", "Player"], as_index=False)["Amount"]
            .sum()
            .rename(columns={"Amount": "TotalPrize"})
            .sort_values(["GameDate", "Player"])
        )

        return {"payouts": prize_df, "totals_per_player": totals}

    # ------------------------------------------------------------------
    # INTERNAL HELPERS
    # ------------------------------------------------------------------
    def _load_valid_scores(self) -> pd.DataFrame:
        """
        Returns all Scores rows excluding dates in ExcludedGames.
        """
        scores = self.scores_repo.get_all()
        excluded = self.games_repo.get_excluded_game_dates()
        if not excluded.empty:
            excluded_dates = set(excluded["GameDate"].tolist())
            scores = scores[~scores[self.SCORES_DATE_COL].isin(excluded_dates)]
        return scores

    def _get_alloc_row(self, pa_df: pd.DataFrame, n_players: int) -> pd.Series | None:
        """
        Find the PrizeAllocation row for the given number of players.
        """
        match = pa_df[pa_df["Players"] == n_players]
        if match.empty:
            return None
        return match.iloc[0]

    # ------------------------------------------------------------------
    # ROUND DOWN TO NEAREST 0.50
    # ------------------------------------------------------------------
    @staticmethod
    def _round_down_50(amount: float) -> float:
        """
        Round down to nearest 0.50 (e.g., 3.74 → 3.5, 3.99 → 3.5).
        """
        return math.floor(amount * 2) / 2.0

    # ------------------------------------------------------------------
    # 1st / 2nd PLACE PRIZE ALLOCATION
    # ------------------------------------------------------------------
    def _allocate_place_prizes_for_comp(
        self,
        game_date,
        df_game: pd.DataFrame,
        points_col: str,
        comp_label: str,
        alloc_row: pd.Series,
    ) -> List[Dict]:
        """
        Allocate 1st / 2nd prizes for a given competition (Front9 / Back9 / Overall)
        within a single game.
        """

        df = df_game.copy()
        if points_col not in df.columns:
            return []

        df[points_col] = pd.to_numeric(df[points_col], errors="coerce")
        df_valid = df.dropna(subset=[points_col]).copy()
        if df_valid.empty:
            return []

        # Higher points = better
        df_valid["Rank"] = df_valid[points_col].rank(method="min", ascending=False).astype("Int64")

        # Prize pool amounts from PrizeAllocation
        first_prize = float(alloc_row.get(self.FIRST_PLACE_COL, 0.0) or 0.0)
        second_prize = float(alloc_row.get(self.SECOND_PLACE_COL, 0.0) or 0.0)

        records: List[Dict] = []

        winners_1 = df_valid[df_valid["Rank"] == 1]
        winners_2 = df_valid[df_valid["Rank"] == 2]

        n1 = len(winners_1)
        n2 = len(winners_2)

        if n1 == 0:
            return records

        if n1 > 1:
            # Tie for 1st: combine 1st + 2nd prize, split evenly, no separate 2nd prize
            total_pot = first_prize + second_prize
            if total_pot <= 0:
                return records
            share = self._round_down_50(total_pot / n1)
            for _, row in winners_1.iterrows():
                records.append(
                    {
                        "GameDate": game_date.date(),
                        "Category": comp_label,
                        "Place": "1st (tie)",
                        "Player": row[self.SCORES_PLAYER_COL],
                        "Amount": share,
                        "Source": "PrizeEngine",
                    }
                )
            return records

        # Single 1st place winner
        winner_1 = winners_1.iloc[0]
        if first_prize > 0:
            records.append(
                {
                    "GameDate": game_date.date(),
                    "Category": comp_label,
                    "Place": "1st",
                    "Player": winner_1[self.SCORES_PLAYER_COL],
                    "Amount": self._round_down_50(first_prize),
                    "Source": "PrizeEngine",
                }
            )

        # 2nd place handling
        if n2 == 0 or second_prize <= 0:
            return records

        share_2 = self._round_down_50(second_prize / n2)
        for _, row in winners_2.iterrows():
            records.append(
                {
                    "GameDate": game_date.date(),
                    "Category": comp_label,
                    "Place": "2nd" if n2 == 1 else "2nd (tie)",
                    "Player": row[self.SCORES_PLAYER_COL],
                    "Amount": share_2,
                    "Source": "PrizeEngine",
                }
            )

        return records

    # ------------------------------------------------------------------
    # NTP PRIZE ALLOCATION
    # ------------------------------------------------------------------
    def _allocate_ntp_prizes_for_game(
        self,
        game_date,
        df_game: pd.DataFrame,
        alloc_row: pd.Series,
    ) -> List[Dict]:
        """
        Allocate NTP prizes for configured holes for a single game.
        If no valid entry on a hole, prize goes to KITTY.
        """

        records: List[Dict] = []

        for hole, ntp_col in self.NTP_COLS.items():
            if ntp_col not in df_game.columns:
                continue

            # Which PrizeAllocation column to use for this hole
            pa_col_name = self.NTP_PRIZE_COLUMN_FOR_HOLE.get(hole)
            if pa_col_name is None:
                continue

            ntp_prize_total = float(alloc_row.get(pa_col_name, 0.0) or 0.0)
            if ntp_prize_total <= 0:
                continue

            df = df_game.copy()
            df[ntp_col] = pd.to_numeric(df[ntp_col], errors="coerce")

            # Only values > 0 count as a valid NTP
            df_valid = df[(df[ntp_col].notna()) & (df[ntp_col] > 0)]
            if df_valid.empty:
                # No winner – prize goes to KITTY
                records.append(
                    {
                        "GameDate": game_date.date(),
                        "Category": f"NTP Hole {hole}",
                        "Place": "",
                        "Player": "KITTY",
                        "Amount": self._round_down_50(ntp_prize_total),
                        "Source": "PrizeEngine",
                    }
                )
                continue

            best_val = df_valid[ntp_col].min()
            winners = df_valid[df_valid[ntp_col] == best_val]
            n_winners = len(winners)

            share = self._round_down_50(ntp_prize_total / n_winners)
            for _, row in winners.iterrows():
                records.append(
                    {
                        "GameDate": game_date.date(),
                        "Category": f"NTP Hole {hole}",
                        "Place": "NTP",
                        "Player": row[self.SCORES_PLAYER_COL],
                        "Amount": share,
                        "Source": "PrizeEngine",
                    }
                )

        return records
