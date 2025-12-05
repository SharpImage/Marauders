# marauders/services/game_report_service.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

import pandas as pd

from marauders.database import Database
from marauders.repositories.scores_repo import ScoreRepository
from marauders.repositories.players_repo import PlayerRepository


@dataclass
class GameReportData:
    date: str
    ntp_table: pd.DataFrame
    podium_front9: pd.DataFrame
    podium_back9: pd.DataFrame
    podium_overall: pd.DataFrame
    full_scores: pd.DataFrame
    hcap_finance: pd.DataFrame


class GameReportService:
    """
    Generates HTML reports for a single game date, combining:
        - NTP results (from PrizePayouts)
        - Front 9 / Back 9 / Overall place tables (with 1st + 2nd rules)
        - Full score table with correct handicaps
        - Handicap/Finance summary
    """

    def __init__(self, db: Database):
        self.db = db
        self.scores_repo = ScoreRepository(db)
        self.players_repo = PlayerRepository(db)

    # ----------------------------------------------------------------------
    # PUBLIC API
    # ----------------------------------------------------------------------
    def build_game_report_html(self, game_date: date) -> str:
        data = self._collect_game_data(game_date)
        return self._render_html(data)

    # ----------------------------------------------------------------------
    # PODIUM (FRONT/BACK/OVERALL) FROM PrizePayouts
    # ----------------------------------------------------------------------
    def _build_podium_from_prizes(
        self, df_prizes: pd.DataFrame, category: str
    ) -> pd.DataFrame:
        """
        Apply the podium rule using the PrizePayouts table:

        - If multiple players are tied for 1st:
              -> show ONLY those tied for 1st (NO 2nd place shown)

        - If exactly one 1st-place player:
              -> show that 1st-place player
              -> AND all players whose Place starts with '2nd'
                (e.g. '2nd', '2nd (tie)', etc.)
        """
        if df_prizes.empty:
            return pd.DataFrame(columns=["Place", "Player", "Amount"])

        df_cat = df_prizes[df_prizes["Category"] == category].copy()
        if df_cat.empty:
            return pd.DataFrame(columns=["Place", "Player", "Amount"])

        df_cat["Place"] = df_cat["Place"].astype(str).str.strip()

        # Use startswith to handle '1st', '1st (tie)', etc.
        first_place = df_cat[df_cat["Place"].str.startswith("1st", na=False)].copy()

        if len(first_place) > 1:
            # Multiple 1st-place players → ONLY them
            return first_place[["Place", "Player", "Amount"]].reset_index(drop=True)

        if len(first_place) == 1:
            # Exactly one first place → first + all second places
            second_place = df_cat[df_cat["Place"].str.startswith("2nd", na=False)].copy()
            podium = pd.concat([first_place, second_place], ignore_index=True)
            return podium[["Place", "Player", "Amount"]].reset_index(drop=True)

        # No explicit '1st' -> fall back to whatever is there
        return df_cat[["Place", "Player", "Amount"]].reset_index(drop=True)

    # ----------------------------------------------------------------------
    # MAIN DATA COLLECTION
    # ----------------------------------------------------------------------
    def _collect_game_data(self, game_date: date) -> GameReportData:
        # ------------------------------------------------------------------
        # 1) Load scores for this game
        # ------------------------------------------------------------------
        df_scores = self.scores_repo.get_scores_for_date(game_date).copy()
        if df_scores.empty:
            raise ValueError(f"No scores found for {game_date}")

        df_scores["Player_Name"] = df_scores["Player_Name"].astype(str).str.strip()
        df_scores["Game_Date"] = pd.to_datetime(
            df_scores["Game_Date"], errors="coerce"
        ).dt.date

        # ------------------------------------------------------------------
        # 2) Handicap history for this game
        # ------------------------------------------------------------------
        df_hh = self.db.read_sql(
            """
            SELECT Player, GameDate, PreviousHandicap, NewHandicap
            FROM HandicapHistory
            WHERE GameDate = ?
            """,
            (str(game_date),),
        )

        if df_hh.empty:
            raise ValueError(
                f"HandicapHistory has no rows for {game_date}. "
                f"Have handicaps been rebuilt?"
            )

        df_hh["Player"] = df_hh["Player"].astype(str).str.strip()
        df_hh["GameDate"] = pd.to_datetime(
            df_hh["GameDate"], errors="coerce"
        ).dt.date

        # ------------------------------------------------------------------
        # 3) Prize payouts (NTP + place prizes) – NO Source column
        # ------------------------------------------------------------------
        df_prizes = self.db.read_sql(
            """
            SELECT GameDate, Player, Category, Place, Amount
            FROM PrizePayouts
            WHERE GameDate = ?
            """,
            (str(game_date),),
        )
        if not df_prizes.empty:
            df_prizes["GameDate"] = pd.to_datetime(
                df_prizes["GameDate"], errors="coerce"
            ).dt.date
            df_prizes["Player"] = df_prizes["Player"].astype(str).str.strip()

        # ------------------------------------------------------------------
        # 4) FULL SCORE TABLE (with proper handicaps)
        # ------------------------------------------------------------------
        full_scores = df_scores.copy()

        # Rename score columns nicely
        full_scores = full_scores.rename(
            columns={
                "Player_Name": "Player",
                "Front_Nine": "Front 9",
                "Back_Nine": "Back 9",
                "Overall": "Overall",
            }
        )

        # Merge in handicap history on (Player, Game_Date)
        full_scores = full_scores.merge(
            df_hh[["Player", "GameDate", "PreviousHandicap", "NewHandicap"]],
            how="left",
            left_on=["Player", "Game_Date"],
            right_on=["Player", "GameDate"],
        )

        # Drop merge helper column
        if "GameDate" in full_scores.columns:
            full_scores = full_scores.drop(columns=["GameDate"])

        # Rename handicap columns
        full_scores = full_scores.rename(
            columns={
                "PreviousHandicap": "Game Handicap",
                "NewHandicap": "New Handicap",
            }
        )

        # Drop any old raw Handicap column if present
        if "Handicap" in full_scores.columns:
            full_scores = full_scores.drop(columns=["Handicap"])

        # Order columns: Player / Front / Back / Overall / NTPs / Game/New Handicap
        ntp_cols = [c for c in full_scores.columns if "NTP" in c]
        ordered_cols = (
            [c for c in ["Player", "Front 9", "Back 9", "Overall"] if c in full_scores.columns]
            + ntp_cols
            + [c for c in ["Game Handicap", "New Handicap"] if c in full_scores.columns]
        )
        full_scores = full_scores[ordered_cols]

        # ---- Rounding fix: DO NOT round NTP columns ----
        # Only round score & handicap columns, leave NTP distances as-is
        score_cols = [c for c in ["Front 9", "Back 9", "Overall", "Game Handicap", "New Handicap"]
                      if c in full_scores.columns]
        for c in score_cols:
            full_scores[c] = pd.to_numeric(full_scores[c], errors="coerce").round(1)

        # Compress NTP columns that are entirely empty
        for col in list(ntp_cols):
            if col in full_scores.columns:
                if full_scores[col].isna().all() or (full_scores[col] == "").all():
                    full_scores = full_scores.drop(columns=[col])

        # Replace NaN/None with blanks for HTML
        full_scores = full_scores.replace(["nan", "None"], "").fillna("")

        # ------------------------------------------------------------------
        # 5) NTP table (from PrizePayouts) – no Source column
        # ------------------------------------------------------------------
        if df_prizes.empty:
            ntp = pd.DataFrame(columns=["Player", "Category", "Amount"])
        else:
            ntp = df_prizes[
                df_prizes["Category"].str.contains("NTP", na=False)
            ].copy()
            ntp = ntp[["Player", "Category", "Amount"]].sort_values(
                ["Category", "Player"]
            )

        # ------------------------------------------------------------------
        # 6) Front 9 / Back 9 / Overall place tables using tie rules
        # ------------------------------------------------------------------
        if df_prizes.empty:
            podium_front9 = pd.DataFrame(columns=["Place", "Player", "Amount"])
            podium_back9 = pd.DataFrame(columns=["Place", "Player", "Amount"])
            podium_overall = pd.DataFrame(columns=["Place", "Player", "Amount"])
        else:
            non_ntp = df_prizes[
                ~df_prizes["Category"].str.contains("NTP", na=False)
            ].copy()

            podium_front9 = self._build_podium_from_prizes(non_ntp, "Front9")
            podium_back9 = self._build_podium_from_prizes(non_ntp, "Back9")
            podium_overall = self._build_podium_from_prizes(non_ntp, "Overall")

        # ------------------------------------------------------------------
        # 7) HANDICAP + FINANCE SUMMARY
        # ------------------------------------------------------------------
        # Start from participants in this game
        hcap_fin = (
            full_scores.groupby("Player")
            .agg(
                {
                    "Game Handicap": "first",
                    "New Handicap": "first",
                }
            )
            .reset_index()
        )

        # Add prizes per player (total Amount)
        if df_prizes.empty:
            prize_totals = pd.DataFrame(columns=["Player", "Prizes"])
        else:
            prize_totals = (
                df_prizes.groupby("Player")["Amount"].sum().reset_index()
            )
            prize_totals = prize_totals.rename(columns={"Amount": "Prizes"})

        hcap_fin = hcap_fin.merge(prize_totals, on="Player", how="left")
        hcap_fin["Prizes"] = hcap_fin["Prizes"].fillna(0.0)

        # ---- NEW: Balance = CURRENT balance from FinanceLedger ----
        df_bal = self.db.get_table("FinanceLedger").copy()
        if (
            not df_bal.empty
            and "Player" in df_bal.columns
            and "Balance" in df_bal.columns
        ):
            # Normalise dates if present
            if "Date" in df_bal.columns:
                df_bal["Date"] = pd.to_datetime(
                    df_bal["Date"], errors="coerce"
                ).dt.date
                df_bal = df_bal.sort_values(["Player", "Date"])
            else:
                df_bal = df_bal.sort_values(["Player"])

            # Take the last row per player => current balance
            last_rows = df_bal.groupby("Player", as_index=False).tail(1)
            bal = last_rows[["Player", "Balance"]]
        else:
            bal = pd.DataFrame(columns=["Player", "Balance"])

        hcap_fin = hcap_fin.merge(bal, on="Player", how="left")
        hcap_fin["Balance"] = hcap_fin["Balance"].fillna(0.0)

        # Round handicaps to 1dp, money to 2dp
        if "Game Handicap" in hcap_fin.columns:
            hcap_fin["Game Handicap"] = pd.to_numeric(
                hcap_fin["Game Handicap"], errors="coerce"
            ).round(1)
        if "New Handicap" in hcap_fin.columns:
            hcap_fin["New Handicap"] = pd.to_numeric(
                hcap_fin["New Handicap"], errors="coerce"
            ).round(1)

        for col in ["Prizes", "Balance"]:
            if col in hcap_fin.columns:
                hcap_fin[col] = pd.to_numeric(
                    hcap_fin[col], errors="coerce"
                ).round(2)

        # Drop any duplicate players defensively
        hcap_fin = hcap_fin.drop_duplicates(subset=["Player"])

        # Clean NaN/None → blanks for HTML
        hcap_fin = hcap_fin.replace(["nan", "None"], "").fillna("")

        return GameReportData(
            date=str(game_date),
            ntp_table=ntp,
            podium_front9=podium_front9,
            podium_back9=podium_back9,
            podium_overall=podium_overall,
            full_scores=full_scores,
            hcap_finance=hcap_fin,
        )

    # ----------------------------------------------------------------------
    # HTML GENERATION
    # ----------------------------------------------------------------------
    def _render_html(self, data: GameReportData) -> str:
        """Renders a clean HTML file containing multiple tables, with £ symbols on money."""

        def format_money(df: pd.DataFrame) -> pd.DataFrame:
            """Return a copy of df with £ added to money columns."""
            df2 = df.copy()
            money_cols = ["Prizes", "Balance","Amount"]

            for col in money_cols:
                if col in df2.columns:
                    df2[col] = df2[col].apply(
                        lambda x: f"£{x:.2f}" if isinstance(x, (int, float)) else x
                    )

            return df2

        def table_html(df: pd.DataFrame, title: str) -> str:
            if df.empty:
                return f"<h3>{title}</h3><p>No data.</p>"

            df2 = format_money(df)
            df2 = df2.replace(["nan", "None"], "").fillna("")
            return f"<h3>{title}</h3>{df2.to_html(index=False)}"

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 20px; }}
                h2 {{ margin-top: 30px; }}
                table, th, td {{
                    border: 1px solid #444;
                    border-collapse: collapse;
                    padding: 4px;
                }}
                table {{
                    width: auto;
                    margin-bottom: 25px;
                }}
            </style>
        </head>
        <body>
            <h1>Marauders Game Report — {data.date}</h1>

            {table_html(data.ntp_table, "Nearest The Pin")}
            {table_html(data.podium_front9, "Front 9")}
            {table_html(data.podium_back9, "Back 9")}
            {table_html(data.podium_overall, "Overall")}
            {table_html(data.full_scores, "Full Scores")}
            {table_html(data.hcap_finance, "Handicap & Finance Summary")}

        </body>
        </html>
        """

        return html

