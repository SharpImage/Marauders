# marauders/services/handicap_service.py

from __future__ import annotations

from typing import Dict, List, Tuple
import pandas as pd

from marauders.database import Database
from marauders.repositories.games_repo import GameRepository


class HandicapService:
    """
    Handicap engine ported from the original handicap_engine_sqlite.py,
    with one addition: games listed in ExcludedGames are ignored when
    computing handicap changes.
    """

    def __init__(self, db: Database):
        self.db = db
        self.game_repo = GameRepository(db)

    # ----------------------------------------------------------
    # PUBLIC ENTRY POINT
    # ----------------------------------------------------------
    def rebuild_handicaps(self) -> dict:
        """
        Rebuild HandicapHistory and CurrentHandicaps from scratch.

        Returns:
            {
              "history": DataFrame (HandicapHistory),
              "current": DataFrame (CurrentHandicaps)
            }
        """

        print("DEBUG: Handicap rebuild start")

        players = self._load_players()
        scores = self._load_scores()

        # ------------------------------------------------------
        # EXCLUDED GAMES
        # ------------------------------------------------------
        excluded_dates = set(self.game_repo.get_excluded_game_dates())
        print("DEBUG excluded dates:", excluded_dates)

        if excluded_dates:
            # scores["Game_Date"] is datetime64; convert to .dt.date for comparison
            before = len(scores)
            scores = scores[~scores["Game_Date"].dt.date.isin(excluded_dates)].copy()
            removed = before - len(scores)
            print(f"DEBUG: Removed {removed} excluded score rows.")
        else:
            print("DEBUG: No excluded games found.")

        placecuts = self._load_placecuts()
        points_adj = self._load_points_adjustment()

        print(f"Players: {len(players)}")
        print(f"Scores: {len(scores)} rows")
        print(f"PlaceCuts rows: {len(placecuts)}")
        print(f"PointsAdjustment rows: {len(points_adj)}")

        # ------------------------------------------------------
        # CORE COMPUTATION (same as original script)
        # ------------------------------------------------------
        print("\nComputing HandicapHistory...")
        history = self._compute_handicap_history(scores, players, placecuts, points_adj)

        print("Computing CurrentHandicaps...")
        current = self._compute_current_handicaps(history, players)

        # Save to SQLite using Database wrapper
        print("Saving HandicapHistory and CurrentHandicaps into SQLite...")
        self.db.write_table("HandicapHistory", history, replace=True)
        self.db.write_table("CurrentHandicaps", current, replace=True)

        print("DEBUG: Handicap rebuild complete")

        return {
            "history": history,
            "current": current,
        }

    # ----------------------------------------------------------
    # SIMPLE ACCESSORS FOR REPORTS / GUI
    # ----------------------------------------------------------
    def get_current_handicaps(self) -> pd.DataFrame:
        """
        Return CurrentHandicaps as a cleaned DataFrame.
        """
        df = self.db.get_table("CurrentHandicaps")
        if df.empty:
            return df

        df = df.copy()
        df["Player"] = df["Player"].astype(str).str.strip()
        df["CurrentHandicap"] = pd.to_numeric(df["CurrentHandicap"], errors="coerce")
        df["CurrentHandicap"] = df["CurrentHandicap"].fillna(0.0).round(1)
        return df.sort_values("Player").reset_index(drop=True)

    def get_handicap_history(self) -> pd.DataFrame:
        """
        Return HandicapHistory as a cleaned DataFrame.
        """
        df = self.db.get_table("HandicapHistory")
        if df.empty:
            return df

        df = df.copy()
        df["Player"] = df["Player"].astype(str).str.strip()
        df["GameDate"] = pd.to_datetime(df["GameDate"], errors="coerce").dt.date
        return df.sort_values(["GameDate", "Player"]).reset_index(drop=True)

    # ----------------------------------------------------------
    # BASIC LOADERS (ported from old script)
    # ----------------------------------------------------------
    def _load_table(self, table_name: str) -> pd.DataFrame:
        return self.db.get_table(table_name)

    def _load_players(self) -> pd.DataFrame:
        df = self._load_table("Players")
        df.columns = [c.strip() for c in df.columns]

        required = ["Player", "StartingHandicap", "Active"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Players table missing columns: {missing}")

        df["StartingHandicap"] = pd.to_numeric(df["StartingHandicap"], errors="coerce").fillna(0.0)
        df["Active"] = df["Active"].astype(str).str.upper().str.strip()
        df["Player"] = df["Player"].astype(str).str.strip()

        return df[required]

    def _load_scores(self) -> pd.DataFrame:
        df = self._load_table("Scores")
        df.columns = [c.strip() for c in df.columns]

        required = [
            "Game_Date",
            "Player_Name",
            "Front_Nine",
            "Back_Nine",
            "Overall",
        ]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Scores table missing columns: {missing}")

        df["Game_Date"] = pd.to_datetime(df["Game_Date"], errors="coerce")
        df["Player_Name"] = df["Player_Name"].astype(str).str.strip()
        df["Front_Nine"] = pd.to_numeric(df["Front_Nine"], errors="coerce")
        df["Back_Nine"] = pd.to_numeric(df["Back_Nine"], errors="coerce")
        df["Overall"] = pd.to_numeric(df["Overall"], errors="coerce")

        df = df.dropna(subset=["Game_Date", "Player_Name", "Overall"])
        return df

    def _load_placecuts(self) -> pd.DataFrame:
        df = self._load_table("PlaceCuts")
        df.columns = [c.strip() for c in df.columns]

        required = ["noOfWinners", "Cut", "no2dPlaces", "Cut2"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"PlaceCuts table missing columns: {missing}")

        df["noOfWinners"] = pd.to_numeric(df["noOfWinners"], errors="coerce")
        df["no2dPlaces"] = pd.to_numeric(df["no2dPlaces"], errors="coerce")
        df["Cut"] = pd.to_numeric(df["Cut"], errors="coerce").fillna(0.0)
        df["Cut2"] = pd.to_numeric(df["Cut2"], errors="coerce").fillna(0.0)

        return df[required]

    def _load_points_adjustment(self) -> pd.DataFrame:
        df = self._load_table("PointsAdjustment")
        df.columns = [c.strip() for c in df.columns]

        required = ["StbfPoints", "HndChange"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"PointsAdjustment table missing columns: {missing}")

        df["StbfPoints"] = pd.to_numeric(df["StbfPoints"], errors="coerce")
        df["HndChange"] = pd.to_numeric(df["HndChange"], errors="coerce").fillna(0.0)

        return df[required]

    # ----------------------------------------------------------
    # RULE LOOKUPS (ported from old script)
    # ----------------------------------------------------------
    def _get_rank_cuts(
        self,
        placecuts: pd.DataFrame,
        n_rank1: int,
        n_rank2: int,
    ) -> Tuple[float, float]:
        """
        Lookup rank-based cut values based on number of 1st and 2nd places.
        Tries, in order:
          1) exact match on both noOfWinners and no2dPlaces
          2) match on noOfWinners only
          3) fallback to the "standard" row (1 winner, 1 second place)
        Returns (cut_for_1st, cut_for_2nd).
        """
        df = placecuts.copy()

        df["noOfWinners"] = pd.to_numeric(df["noOfWinners"], errors="coerce")
        df["no2dPlaces"] = pd.to_numeric(df["no2dPlaces"], errors="coerce")

        # 1) Exact match
        exact = df[(df["noOfWinners"] == n_rank1) & (df["no2dPlaces"] == n_rank2)]
        if not exact.empty:
            row = exact.iloc[0]
            return float(row["Cut"]), float(row["Cut2"])

        # 2) Match on noOfWinners only
        winners_only = df[df["noOfWinners"] == n_rank1]
        if not winners_only.empty:
            row = winners_only.iloc[0]
            return float(row["Cut"]), float(row["Cut2"])

        # 3) Fallback to default row (1 winner, 1 second place) if it exists
        default = df[(df["noOfWinners"] == 1) & (df["no2dPlaces"] == 1)]
        if not default.empty:
            row = default.iloc[0]
            return float(row["Cut"]), float(row["Cut2"])

        # No rule found at all
        return 0.0, 0.0

    def _get_points_adjustment(self, points_df: pd.DataFrame, stableford: float) -> float:
        """
        Lookup points-based adjustment from PointsAdjustment table.
        Matching on StbfPoints == stableford (integer match).
        """
        df = points_df.copy()
        sf_int = int(round(stableford))
        match = df[df["StbfPoints"] == sf_int]

        if match.empty:
            return 0.0

        return float(match.iloc[0]["HndChange"])

    def _compute_segment_cut(
        self,
        rank: float,
        n_rank1: int,
        n_rank2: int,
        placecuts: pd.DataFrame,
    ) -> float:
        """
        Given the player's rank (1,2,...), and the number of tied 1st/2nd places in that segment,
        return the appropriate rank-based cut from PlaceCuts.
        """
        if pd.isna(rank):
            return 0.0

        cut1, cut2 = self._get_rank_cuts(placecuts, n_rank1, n_rank2)

        if int(rank) == 1:
            return cut1
        elif int(rank) == 2:
            return cut2
        else:
            return 0.0

    # ----------------------------------------------------------
    # CORE HANDICAP CALCULATION (ported exactly)
    # ----------------------------------------------------------
    def _compute_handicap_history(
        self,
        scores: pd.DataFrame,
        players: pd.DataFrame,
        placecuts: pd.DataFrame,
        points_adj: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Rebuild HandicapHistory from scratch using:
          - Scores (Front/Back/Overall)
          - starting handicaps from Players
          - rank-based cuts from PlaceCuts (for F9, B9, Overall)
          - points-based adjustments from PointsAdjustment
        """

        # Starting handicaps
        start_hcaps: Dict[str, float] = (
            players.set_index("Player")["StartingHandicap"].to_dict()
        )

        # Current handicaps
        current_hcap: Dict[str, float] = dict(start_hcaps)

        # Process games in date order
        scores = scores.sort_values(["Game_Date", "Player_Name"])

        history_rows: List[Dict] = []

        for game_date, group in scores.groupby("Game_Date", sort=True):
            df = group.copy()

            # Competition ranks (higher points better)
            df["F9Rank"] = df["Front_Nine"].rank(method="min", ascending=False)
            df["B9Rank"] = df["Back_Nine"].rank(method="min", ascending=False)
            df["OverallRank"] = df["Overall"].rank(method="min", ascending=False)

            # Tie counts per segment
            n_f9_1 = int((df["F9Rank"] == 1).sum())
            n_f9_2 = int((df["F9Rank"] == 2).sum())

            n_b9_1 = int((df["B9Rank"] == 1).sum())
            n_b9_2 = int((df["B9Rank"] == 2).sum())

            n_ov_1 = int((df["OverallRank"] == 1).sum())
            n_ov_2 = int((df["OverallRank"] == 2).sum())

            for _, row in df.iterrows():
                player = row["Player_Name"]
                stableford = float(row["Overall"])

                prev = float(current_hcap.get(player, start_hcaps.get(player, 0.0)))

                # Rank-based adjustments from all three segments
                f9_adj = self._compute_segment_cut(row["F9Rank"], n_f9_1, n_f9_2, placecuts)
                b9_adj = self._compute_segment_cut(row["B9Rank"], n_b9_1, n_b9_2, placecuts)
                ov_adj = self._compute_segment_cut(row["OverallRank"], n_ov_1, n_ov_2, placecuts)

                rank_adj = f9_adj + b9_adj + ov_adj

                # Points-based adjustment (Overall Stableford)
                pts_adj = self._get_points_adjustment(points_adj, stableford)

                total_adj = rank_adj + pts_adj

                # Final handicap: rounded to 1 decimal, not below 0.0
                new_val = prev + total_adj
                new_hcap = max(0.0, float(round(new_val + 1e-9, 1)))

                history_rows.append({
                    "Player": player,
                    "GameDate": game_date.date(),  # store as date only
                    "PreviousHandicap": prev,
                    "NewHandicap": new_hcap,
                    "TotalAdjustment": total_adj,
                    "RankBasedAdjustment": rank_adj,
                    "RankBasedAdjustment_F9": f9_adj,
                    "RankBasedAdjustment_B9": b9_adj,
                    "RankBasedAdjustment_Overall": ov_adj,
                    "PointsBasedAdjustment": pts_adj,
                    "F9Rank": int(row["F9Rank"]) if pd.notna(row["F9Rank"]) else None,
                    "B9Rank": int(row["B9Rank"]) if pd.notna(row["B9Rank"]) else None,
                    "OverallRank": int(row["OverallRank"]) if pd.notna(row["OverallRank"]) else None,
                    "StablefordPoints": stableford,
                })

                current_hcap[player] = new_hcap

        history = pd.DataFrame(history_rows)

        if history.empty:
            # Return empty structure with expected columns
            return pd.DataFrame(columns=[
                "Player", "GameDate", "PreviousHandicap", "NewHandicap",
                "TotalAdjustment", "RankBasedAdjustment",
                "RankBasedAdjustment_F9", "RankBasedAdjustment_B9",
                "RankBasedAdjustment_Overall", "PointsBasedAdjustment",
                "F9Rank", "B9Rank", "OverallRank", "StablefordPoints"
            ])

        history = history.sort_values(["GameDate", "Player", "OverallRank"]).reset_index(drop=True)

        return history

    def _compute_current_handicaps(
        self,
        history: pd.DataFrame,
        players: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Compute current handicap for each active player.
        If a player has never played, use StartingHandicap.
        """

        if not history.empty:
            latest = (
                history.sort_values("GameDate")
                .groupby("Player")
                .tail(1)[["Player", "NewHandicap"]]
                .rename(columns={"NewHandicap": "CurrentHandicap"})
            )
        else:
            latest = pd.DataFrame(columns=["Player", "CurrentHandicap"])

        players2 = players.copy()

        merged = players2.merge(latest, on="Player", how="left")

        missing = merged["CurrentHandicap"].isna()
        merged.loc[missing, "CurrentHandicap"] = merged.loc[missing, "StartingHandicap"]

        active = merged[merged["Active"] == "YES"].copy()

        return active[["Player", "CurrentHandicap"]].sort_values("Player")
