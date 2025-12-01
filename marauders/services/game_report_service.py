# marauders/services/game_report_service.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import pandas as pd

from marauders.database import Database
from marauders.repositories.scores_repo import ScoreRepository
from marauders.repositories.players_repo import PlayerRepository
from marauders.services.finance_service import FinanceService


@dataclass
class GameReportData:
    game_date: date
    scores: pd.DataFrame
    ntp_table: pd.DataFrame
    podium_front: pd.DataFrame
    podium_back: pd.DataFrame
    podium_overall: pd.DataFrame
    full_scores: pd.DataFrame
    finance_table: pd.DataFrame


class GameReportService:
    """
    Generates an HTML email report for a specific game date.

    Sections:
      - NTP / In-2 results
      - Podium (Front 9 / Back 9 / Overall)
      - Full scores
      - Handicaps & Finance:
          Game Handicap (PreviousHandicap)
          New Handicap  (NewHandicap)
          Game Fee / Prizes / Other / Net / Balance After Game
    """

    NTP_COLUMNS = {
        "NTP_Hole3": "Nearest The Pin – Hole 3",
        "NTP_Hole6": "Nearest The Pin – Hole 6",
        "NTP_in2_Hole7": "Nearest The Pin in 2 – Hole 7",
        "NTP_in2_Hole10": "Nearest The Pin in 2 – Hole 10",
        "NTP_Hole11": "Nearest The Pin – Hole 11",
        "NTP_Hole15": "Nearest The Pin – Hole 15",
    }

    def __init__(self, db: Database):
        self.db = db
        self.scores_repo = ScoreRepository(db)
        self.players_repo = PlayerRepository(db)
        self.finance_service = FinanceService(db)

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------
    def build_game_report_html(self, game_date: date) -> str:
        data = self._collect_game_data(game_date)
        return self._render_html(data)

    # ---------------------------------------------------------
    # Collect all data needed for the report
    # ---------------------------------------------------------
    def _collect_game_data(self, game_date: date) -> GameReportData:
        scores = self.scores_repo.get_scores_for_date(game_date).copy()
        if scores.empty:
            raise ValueError(f"No scores found for game date {game_date}")

        scores["Player_Name"] = scores["Player_Name"].astype(str).str.strip()

        # 1) NTP / In-2 table
        ntp_rows = []
        for col, label in self.NTP_COLUMNS.items():
            if col not in scores.columns:
                continue
            non_null = scores.dropna(subset=[col])
            if non_null.empty:
                continue

            numeric = pd.to_numeric(non_null[col], errors="coerce")
            if numeric.notna().any():
                idx = numeric.idxmin()
            else:
                idx = non_null.index[0]

            row = non_null.loc[idx]
            ntp_rows.append(
                {
                    "Hole / Category": label,
                    "Player": row["Player_Name"],
                    "Value": row[col],
                }
            )

        ntp_table = pd.DataFrame(
            ntp_rows, columns=["Hole / Category", "Player", "Value"]
        )

        # 2) Podium tables
        podium_front = self._build_podium(scores, "Front_Nine")
        podium_back = self._build_podium(scores, "Back_Nine")
        podium_overall = self._build_podium(scores, "Overall")

        # 3) Full scores (sorted by Overall)
        full_scores = scores.copy()
        keep = [
            c
            for c in ["Player_Name", "Handicap", "Front_Nine", "Back_Nine", "Overall"]
            if c in full_scores.columns
        ]
        full_scores = full_scores[keep]
        full_scores = full_scores.rename(
            columns={
                "Player_Name": "Player",
                "Front_Nine": "Front 9",
                "Back_Nine": "Back 9",
            }
        )
        if "Overall" in full_scores.columns:
            full_scores = full_scores.sort_values("Overall", ascending=False)

        # 4) Finance & handicaps table (using HandicapHistory)
        finance_table = self._build_finance_table(game_date, scores)

        return GameReportData(
            game_date=game_date,
            scores=scores,
            ntp_table=ntp_table,
            podium_front=podium_front,
            podium_back=podium_back,
            podium_overall=podium_overall,
            full_scores=full_scores,
            finance_table=finance_table,
        )

    # ---------------------------------------------------------
    def _build_podium(self, scores: pd.DataFrame, col: str) -> pd.DataFrame:
        """
        Podium rule (per user requirement):

        - If multiple players are tied for 1st:
              -> show ONLY those tied for 1st (NO 2nd place shown)

        - If exactly one 1st-place player:
              -> show that 1st-place player
              -> AND all players tied for 2nd place
        """

        if col not in scores.columns:
            return pd.DataFrame(columns=["Place", "Player", col])

        df = scores[["Player_Name", col]].dropna().copy()
        if df.empty:
            return pd.DataFrame(columns=["Place", "Player", col])

        # Sort descending
        df = df.sort_values(col, ascending=False)

        # -------------------------------
        # Determine 1st-place group
        # -------------------------------
        first_score = df[col].iloc[0]
        first_place = df[df[col] == first_score].copy()
        first_place.insert(0, "Place", "1st")

        # If more than 1 player tied for 1st → STOP (NO 2nd place)
        if len(first_place) > 1:
            return first_place.rename(columns={"Player_Name": "Player"})

        # -------------------------------
        # Determine 2nd-place group (only if exactly 1 first-place)
        # -------------------------------
        df_remaining = df[df[col] < first_score]
        if df_remaining.empty:
            # No 2nd place at all
            return first_place.rename(columns={"Player_Name": "Player"})

        second_score = df_remaining[col].iloc[0]
        second_place = df_remaining[df_remaining[col] == second_score].copy()
        second_place.insert(0, "Place", "2nd")

        podium = pd.concat([first_place, second_place], ignore_index=True)
        podium = podium.rename(columns={"Player_Name": "Player"})

        return podium

    # ---------------------------------------------------------
    # Finance + Handicap before/after (from HandicapHistory)
    # ---------------------------------------------------------
    def _build_finance_table(self, game_date: date, scores: pd.DataFrame) -> pd.DataFrame:
        """
        Per-player snapshot for this game:
          - Player
          - Game Handicap (PreviousHandicap from HandicapHistory)
          - New Handicap  (NewHandicap   from HandicapHistory)
          - Game Fee, Prizes, Other, Net
          - Balance After Game
        """

        # Rebuild finance to get full ledger & kitty etc.
        fin = self.finance_service.rebuild_finance()
        ledger = fin.ledger.copy()

        # -------- Players who played this game --------
        players_today = (
            scores["Player_Name"].astype(str).str.strip().unique().tolist()
        )
        players_df = pd.DataFrame({"Player": players_today})

        # -------- Per-player finance for THIS game date --------
        df_game = ledger[ledger["Date"] == game_date].copy()
        if df_game.empty:
            per_player = pd.DataFrame(
                columns=["Player", "Game Fee", "Prizes", "Other", "Net"]
            )
        else:
            per_player = (
                df_game.groupby("Player")[["Game Fee", "Prizes", "Other", "Net"]]
                .sum()
                .reset_index()
            )

        # -------- Handicaps for this game from HandicapHistory --------
        # HandicapHistory is built by handicap_engine_sqlite.py and has:
        # Player, GameDate, PreviousHandicap, NewHandicap, ...
        try:
            df_h = self.db.read_sql(
                """
                SELECT Player, GameDate, PreviousHandicap, NewHandicap
                FROM HandicapHistory
                """
            )
            df_h["Player"] = df_h["Player"].astype(str).str.strip()
            df_h["GameDate"] = pd.to_datetime(
                df_h["GameDate"], errors="coerce"
            ).dt.date

            df_h_game = df_h[df_h["GameDate"] == game_date].copy()
        except Exception:
            df_h_game = pd.DataFrame(
                columns=["Player", "PreviousHandicap", "NewHandicap"]
            )

        if df_h_game.empty:
            # No handicap data for this game (should be rare) –
            # fall back to handicap stored in Scores if present.
            # This will populate Game Handicap, leave New Handicap blank.
            score_hcaps = (
                scores[["Player_Name", "Handicap"]]
                .drop_duplicates()
                .rename(
                    columns={
                        "Player_Name": "Player",
                        "Handicap": "Game Handicap",
                    }
                )
            )
            hcaps_for_game = score_hcaps
            hcaps_for_game["New Handicap"] = pd.NA
        else:
            hcaps_for_game = df_h_game.rename(
                columns={
                    "PreviousHandicap": "Game Handicap",
                    "NewHandicap": "New Handicap",
                }
            )[["Player", "Game Handicap", "New Handicap"]]

        # -------- Balance after game --------
        up_to = ledger[ledger["Date"] <= game_date].copy()
        if up_to.empty:
            balance_after = pd.Series(dtype=float)
        else:
            up_to = up_to.sort_values(["Player", "Date"])
            balance_after = up_to.groupby("Player")["Balance"].last()

        # -------- Merge everything together --------
        finance = players_df.merge(hcaps_for_game, on="Player", how="left")
        finance = finance.merge(per_player, on="Player", how="left")

        for col in ["Game Fee", "Prizes", "Other", "Net"]:
            if col in finance.columns:
                finance[col] = finance[col].fillna(0.0)
            else:
                finance[col] = 0.0

        finance["Balance After Game"] = (
            finance["Player"].map(balance_after).fillna(0.0)
        )

        # Order columns
        finance = finance[
            [
                "Player",
                "Game Handicap",
                "New Handicap",
                "Game Fee",
                "Prizes",
                "Other",
                "Net",
                "Balance After Game",
            ]
        ]

        return finance.sort_values("Player")

    # ---------------------------------------------------------
    # HTML Rendering
    # ---------------------------------------------------------
    def _render_html(self, data: GameReportData) -> str:
        game_date_str = data.game_date.strftime("%A %d %B %Y")
        num_players = data.scores["Player_Name"].nunique()

        css = """
        <style>
            body { font-family: Arial, sans-serif; font-size: 13px; color: #222; }
            h1 { font-size: 20px; margin: 6px 0; }
            h2 { font-size: 16px; margin: 4px 0; }
            h3 { font-size: 15px; margin: 6px 0 4px 0; }
            h4 { font-size: 14px; margin: 4px 0 4px 0; }
            .section { margin-bottom: 20px; }

            table.report-table {
                border-collapse: collapse;
                margin: 6px 0 12px 0;
                width: auto;
                max-width: 100%;
                border: 1px solid #bbb;
                font-size: 13px;
            }
            table.report-table th {
                background-color: #f3f3f3;
                border: 1px solid #bbb;
                padding: 4px 8px;
                white-space: nowrap;
            }
            table.report-table td {
                border: 1px solid #ccc;
                padding: 4px 8px;
                white-space: nowrap;
            }
        </style>
        """

        html = []
        html.append(f"<!DOCTYPE html><html><head>{css}</head><body>")

        # Header
        html.append("<div class='section'>")
        html.append("<h1>Marauders Golf – Game Report</h1>")
        html.append(f"<h2>{game_date_str}</h2>")
        html.append(f"<p><b>Players:</b> {num_players}</p>")
        html.append("</div>")

        # NTP / In-2
        if not data.ntp_table.empty:
            html.append("<div class='section'>")
            html.append("<h3>Nearest The Pin / In-2 Results</h3>")
            html.append(self._df_to_html_table(data.ntp_table))
            html.append("</div>")

        # Podium
        html.append("<div class='section'>")
        html.append("<h3>Podium Results</h3>")
        if not data.podium_front.empty:
            html.append("<h4>Front 9</h4>")
            html.append(self._df_to_html_table(data.podium_front))
        if not data.podium_back.empty:
            html.append("<h4>Back 9</h4>")
            html.append(self._df_to_html_table(data.podium_back))
        if not data.podium_overall.empty:
            html.append("<h4>Overall</h4>")
            html.append(self._df_to_html_table(data.podium_overall))
        html.append("</div>")

        # Full scores
        if not data.full_scores.empty:
            html.append("<div class='section'>")
            html.append("<h3>Full Scores</h3>")
            html.append(self._df_to_html_table(data.full_scores))
            html.append("</div>")

        # Handicaps / Finance
        if not data.finance_table.empty:
            html.append("<div class='section'>")
            html.append("<h3>Handicaps / Finance</h3>")

            finance_df = data.finance_table.copy()
            # Format currency columns
            for col in ["Game Fee", "Prizes", "Other", "Net", "Balance After Game"]:
                finance_df[col] = finance_df[col].map(lambda x: f"£{x:,.2f}")

            html.append(self._df_to_html_table(finance_df))
            html.append("</div>")

        html.append("</body></html>")
        return "".join(html)

    # ---------------------------------------------------------
    def _df_to_html_table(self, df: pd.DataFrame) -> str:
        return df.to_html(
            index=False,
            classes="report-table",
            border=0,
            escape=False,
        )
