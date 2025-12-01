# marauders/services/handicap_service.py

from __future__ import annotations
import pandas as pd
from typing import Dict, List

from marauders.database import Database
from marauders.repositories.players_repo import PlayerRepository
from marauders.repositories.scores_repo import ScoreRepository
from marauders.repositories.handicaps_repo import HandicapRepository
from marauders.repositories.games_repo import GameRepository


class HandicapService:
    """
    Rebuilds:
      - HandicapHistory
      - CurrentHandicaps

    This version includes:
      - Safe handling for missing Overall values
      - Calculates Overall = Front + Back if missing and both present
      - Skips incomplete rounds (no handicap change)
    """

    FRONT9_COL = "Front_Nine"
    BACK9_COL = "Back_Nine"
    OVERALL_COL = "Overall"

    def __init__(self, db: Database):
        self.db = db
        self.players_repo = PlayerRepository(db)
        self.scores_repo = ScoreRepository(db)
        self.hcaps_repo = HandicapRepository(db)
        self.games_repo = GameRepository(db)

    # ----------------------------------------------------------------------
    # PUBLIC ENTRY POINT
    # ----------------------------------------------------------------------
    def rebuild_handicaps(self) -> Dict[str, pd.DataFrame]:
        """
        Recomputes the entire handicap system from scratch.

        Returns a dict:
            {
                "history": HandicapHistory DataFrame,
                "current": CurrentHandicaps DataFrame
            }
        """

        players = self.players_repo.get_all()
        scores = self._load_valid_scores()
        placecuts = self.hcaps_repo.get_place_cuts()
        points_adj = self.hcaps_repo.get_points_adjustment()

        history = self._compute_handicap_history(scores, players, placecuts, points_adj)
        current = self._compute_current_handicaps(history, players)

        # Save to DB
        self.hcaps_repo.save_history(history)
        self.hcaps_repo.save_current(current)

        return {"history": history, "current": current}

    # ----------------------------------------------------------------------
    # HELPERS
    # ----------------------------------------------------------------------
    def _load_valid_scores(self) -> pd.DataFrame:
        """Returns all scores EXCLUDING those from excluded games."""
        scores = self.scores_repo.get_all()
        excluded = self.games_repo.get_excluded_game_dates()

        if not excluded.empty:
            excluded_dates = set(excluded["GameDate"].tolist())
            scores = scores[~scores["Game_Date"].isin(excluded_dates)]

        return scores

    # ----------------------------------------------------------------------
    # CORE HANDICAP LOGIC
    # ----------------------------------------------------------------------
    def _compute_handicap_history(
        self,
        scores: pd.DataFrame,
        players: pd.DataFrame,
        placecuts: pd.DataFrame,
        points_adj: pd.DataFrame,
    ) -> pd.DataFrame:

        # Starting handicaps dictionary
        start_hcaps: Dict[str, float] = (
            players.set_index("Player")["StartingHandicap"].to_dict()
        )

        # Working handicaps
        current_hcap: Dict[str, float] = dict(start_hcaps)

        scores = scores.sort_values(["Game_Date", "Player_Name"])

        history_rows: List[Dict] = []

        for game_date, group in scores.groupby("Game_Date", sort=True):
            df = group.copy()

            # Rank for completed rows (blank ranks if missing values)
            df["F9Rank"] = df[self.FRONT9_COL].rank(method="min", ascending=False)
            df["B9Rank"] = df[self.BACK9_COL].rank(method="min", ascending=False)
            df["OverallRank"] = df[self.OVERALL_COL].rank(method="min", ascending=False)

            for _, row in df.iterrows():
                player = row["Player_Name"]

                prev_hcap = float(current_hcap.get(player, start_hcaps.get(player, 0.0)))

                # ------------------------------------------------------------
                # 1) FIX OVERALL IF MISSING
                # ------------------------------------------------------------
                f9 = row[self.FRONT9_COL]
                b9 = row[self.BACK9_COL]
                overall = row[self.OVERALL_COL]

                # If Overall missing but f9 + b9 available → calculate it
                if pd.isna(overall) and not pd.isna(f9) and not pd.isna(b9):
                    overall = f9 + b9

                # If still NaN → incomplete round → NO handicap change
                if pd.isna(overall):
                    history_rows.append({
                        "Player": player,
                        "GameDate": game_date.date(),
                        "PreviousHandicap": prev_hcap,
                        "NewHandicap": prev_hcap,
                        "TotalAdjustment": 0.0,
                        "RankBasedAdjustment": 0.0,
                        "RankBasedAdjustment_F9": 0.0,
                        "RankBasedAdjustment_B9": 0.0,
                        "RankBasedAdjustment_Overall": 0.0,
                        "PointsBasedAdjustment": 0.0,
                        "F9Rank": None,
                        "B9Rank": None,
                        "OverallRank": None,
                        "StablefordPoints": None,
                    })
                    continue  # skip to next row

                # Now safe to convert
                stableford = float(overall)

                # ------------------------------------------------------------
                # 2) RANK-BASED ADJUSTMENTS
                # ------------------------------------------------------------
                f9_adj = self._segment_cut(row["F9Rank"], placecuts)
                b9_adj = self._segment_cut(row["B9Rank"], placecuts)
                ov_adj = self._segment_cut(row["OverallRank"], placecuts)

                rank_adj = f9_adj + b9_adj + ov_adj

                # ------------------------------------------------------------
                # 3) POINTS-BASED ADJUSTMENT
                # ------------------------------------------------------------
                pts_adj = self._points_adjustment(points_adj, stableford)

                # Total
                total_adj = rank_adj + pts_adj
                new_hcap = max(0.0, float(round(prev_hcap + total_adj, 1)))

                # Record history row
                history_rows.append({
                    "Player": player,
                    "GameDate": game_date.date(),
                    "PreviousHandicap": prev_hcap,
                    "NewHandicap": new_hcap,
                    "TotalAdjustment": total_adj,
                    "RankBasedAdjustment": rank_adj,
                    "RankBasedAdjustment_F9": f9_adj,
                    "RankBasedAdjustment_B9": b9_adj,
                    "RankBasedAdjustment_Overall": ov_adj,
                    "PointsBasedAdjustment": pts_adj,
                    "F9Rank": None if pd.isna(row["F9Rank"]) else int(row["F9Rank"]),
                    "B9Rank": None if pd.isna(row["B9Rank"]) else int(row["B9Rank"]),
                    "OverallRank": None if pd.isna(row["OverallRank"]) else int(row["OverallRank"]),
                    "StablefordPoints": stableford,
                })

                current_hcap[player] = new_hcap

        history = pd.DataFrame(history_rows)
        return history.sort_values(["GameDate", "Player"]).reset_index(drop=True)

    # ----------------------------------------------------------------------
    # RANK-BASED ADJUSTMENT LOOKUP
    # ----------------------------------------------------------------------
    def _segment_cut(self, rank, placecuts: pd.DataFrame) -> float:
        if pd.isna(rank):
            return 0.0

        rank = int(rank)

        # Special-case: if multiple 1sts or 2nds, pick rules accordingly
        # You already have logic in original engine; simplifying here for now.
        if rank == 1:
            cut = placecuts[placecuts["noOfWinners"] == 1]
            if not cut.empty:
                return float(cut.iloc[0]["Cut"])
        if rank == 2:
            cut = placecuts[placecuts["no2dPlaces"] == 1]
            if not cut.empty:
                return float(cut.iloc[0]["Cut2"])
        return 0.0

    # ----------------------------------------------------------------------
    # POINTS-BASED ADJUSTMENT
    # ----------------------------------------------------------------------
    def _points_adjustment(self, points_df: pd.DataFrame, stableford: float) -> float:
        if points_df.empty:
            return 0.0

        sf_int = int(round(stableford))
        match = points_df[points_df["StbfPoints"] == sf_int]

        if match.empty:
            return 0.0

        return float(match.iloc[0]["HndChange"])

    # ----------------------------------------------------------------------
    # CURRENT HANDICAPS
    # ----------------------------------------------------------------------
    def _compute_current_handicaps(
        self,
        history: pd.DataFrame,
        players: pd.DataFrame,
    ) -> pd.DataFrame:

        if history.empty:
            # No rounds played → use starting handicaps
            df = players[["Player", "StartingHandicap"]].copy()
            df["CurrentHandicap"] = df["StartingHandicap"]
            return df[["Player", "CurrentHandicap"]]

        # Get latest handicap for each player
        latest = (
            history.sort_values(["GameDate"])
            .groupby("Player")
            .tail(1)[["Player", "NewHandicap"]]
            .rename(columns={"NewHandicap": "CurrentHandicap"})
        )

        players2 = players.copy()
        merged = players2.merge(latest, on="Player", how="left")

        # Fill missing with starting handicap
        missing = merged["CurrentHandicap"].isna()
        merged.loc[missing, "CurrentHandicap"] = merged.loc[missing, "StartingHandicap"]

        return merged[["Player", "CurrentHandicap"]].sort_values("Player")
