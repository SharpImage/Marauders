# marauders/services/game_summary_service.py

from __future__ import annotations

import pandas as pd
from typing import Dict, Any

from marauders.database import Database
from marauders.repositories.scores_repo import ScoreRepository
from marauders.repositories.handicaps_repo import HandicapRepository
from marauders.repositories.prizes_repo import PrizeRepository
from marauders.repositories.games_repo import GameRepository


class GameSummaryService:
    """
    Builds the full summary for a single game.

    Returns three DataFrames:
      - scores:     Raw scores + ranks
      - handicaps:  Handicap changes on that game date
      - prizes:     Prize payouts for that game

    GUI is responsible for formatting, previewing, exporting.
    """

    def __init__(self, db: Database):
        self.db = db
        self.scores_repo = ScoreRepository(db)
        self.hcaps_repo = HandicapRepository(db)
        self.prizes_repo = PrizeRepository(db)
        self.games_repo = GameRepository(db)

    # ----------------------------------------------------------------------
    # PUBLIC API
    # ----------------------------------------------------------------------
    def build_game_summary(self, game_date: str) -> Dict[str, pd.DataFrame]:
        """
        Build summary for a single game_date (YYYY-MM-DD).

        Returns:
            {
                "scores": df_scores,
                "handicaps": df_handicaps,
                "prizes": df_prizes
            }
        """

        # ----------------------------------------------------------
        # Scores (with ranks)
        # ----------------------------------------------------------
        scores = self._build_scores_section(game_date)

        # ----------------------------------------------------------
        # Handicap changes for this date
        # ----------------------------------------------------------
        hcaps = self._build_handicaps_section(game_date)

        # ----------------------------------------------------------
        # Prize payouts for this date
        # ----------------------------------------------------------
        prizes = self.prizes_repo.get_payouts_for_game(game_date)

        return {
            "scores": scores,
            "handicaps": hcaps,
            "prizes": prizes,
        }

    # ----------------------------------------------------------------------
    # SCORES SECTION
    # ----------------------------------------------------------------------
    def _build_scores_section(self, game_date: str) -> pd.DataFrame:
        df = self.scores_repo.get_scores_for_date(game_date)

        if df.empty:
            return pd.DataFrame()

        df = df.copy()

        # Rank each section (higher score = better)
        # Use nullable Int64 so NaN ranks don't crash
        df["F9Rank"] = (
            df["Front_Nine"]
            .rank(method="min", ascending=False)
            .astype("Int64")
        )

        df["B9Rank"] = (
            df["Back_Nine"]
            .rank(method="min", ascending=False)
            .astype("Int64")
        )

        df["OverallRank"] = (
            df["Overall"]
            .rank(method="min", ascending=False)
            .astype("Int64")
        )

        return df[
            [
                "Player_Name",
                "Front_Nine",
                "Back_Nine",
                "Overall",
                "F9Rank",
                "B9Rank",
                "OverallRank",
            ]
        ].sort_values("OverallRank")

    # ----------------------------------------------------------------------
    # HANDICAP SECTION
    # ----------------------------------------------------------------------
    def _build_handicaps_section(self, game_date: str) -> pd.DataFrame:
        """
        Returns handicap changes for the given game date:
        Player | PreviousHandicap | NewHandicap | TotalAdjustment | Breakdown
        """
        history = self.hcaps_repo.get_history()
        if history.empty:
            return pd.DataFrame()

        df = history[history["GameDate"] == pd.to_datetime(game_date).date()]
        if df.empty:
            return pd.DataFrame()

        df = df.copy()

        # -----------------------------------------------------------
        # Fix missing Overall values by recomputing Front + Back
        # -----------------------------------------------------------
        df["Overall"] = df.apply(
            lambda r: (
                r["Front_Nine"] + r["Back_Nine"]
                if pd.isna(r["Overall"])
                   and not pd.isna(r["Front_Nine"])
                   and not pd.isna(r["Back_Nine"])
                else r["Overall"]
            ),
            axis=1
        )

        return df[
            [
                "Player",
                "PreviousHandicap",
                "NewHandicap",
                "TotalAdjustment",
                "RankBasedAdjustment",
                "PointsBasedAdjustment",
            ]
        ].sort_values("Player")

