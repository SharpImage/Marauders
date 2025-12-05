# marauders/manager.py

import os
from datetime import date

from marauders.database import Database

# -------------------------------------------------------
# Repository Imports (Correct class names)
# -------------------------------------------------------
from marauders.repositories.players_repo import PlayerRepository
from marauders.repositories.scores_repo import ScoreRepository
from marauders.repositories.prizes_repo import PrizeRepository
from marauders.repositories.games_repo import GameRepository
from marauders.repositories.finance_repo import FinanceRepository

# -------------------------------------------------------
# Service Imports
# -------------------------------------------------------
from marauders.services.import_service import ImportService
from marauders.services.handicap_service import HandicapService
from marauders.services.prize_service import PrizeService
from marauders.services.finance_service import FinanceService
from marauders.services.player_service import PlayerService
from marauders.services.game_summary_service import GameSummaryService


class MaraudersManager:
    """
    Main application manager.
    All repositories and service layers are defined here and used by the GUI.
    """

    def __init__(self, db_path="marauders.db", master_file=None):
        # -------------------------------------------------------
        # Database connection
        # -------------------------------------------------------
        self.db = Database(db_path)

        # -------------------------------------------------------
        # Settings
        # -------------------------------------------------------
        self.master_file = master_file

        # -------------------------------------------------------
        # REPOSITORIES (must be created BEFORE services)
        # -------------------------------------------------------
        self.players_repo = PlayerRepository(self.db)
        self.scores_repo = ScoreRepository(self.db)
        self.prizes_repo = PrizeRepository(self.db)
        self.games_repo = GameRepository(self.db)
        self.finance_repo = FinanceRepository(self.db)

        # -------------------------------------------------------
        # IMPORT SERVICE (optional)
        # -------------------------------------------------------
        self.import_service = None
        if self.master_file:
            self.import_service = ImportService(self.db, str(self.master_file))

        # -------------------------------------------------------
        # SERVICES (depend on repositories)
        # -------------------------------------------------------
        self.handicap_service = HandicapService(self.db)
        self.prize_service = PrizeService(self.db)

        self.finance_service = FinanceService(
            self.db,
            self.players_repo,
            self.scores_repo,
            self.prizes_repo,
            self.games_repo,
            self.finance_repo
        )

        self.player_service = PlayerService(self.db)
        self.game_summary_service = GameSummaryService(self.db)

    # ===============================================================
    # PUBLIC METHODS EXPOSED TO GUI
    # ===============================================================

    def load_players(self):
        """Return all players from the repository."""
        return self.players_repo.get_all()

    def add_player(self, name, starting_handicap, active=True):
        return self.players_repo.add_player(name, starting_handicap, active)

    def update_player(self, player_id, name, starting_handicap, active):
        return self.players_repo.update_player(player_id, name, starting_handicap, active)

    def get_game_dates(self):
        return self.scores_repo.get_game_dates()

    # ---------------------------------------------------------------
    # IMPORT SCORES
    # ---------------------------------------------------------------
    def import_new_scores(self):
        if self.import_service is None:
            raise RuntimeError("No master score file set.")
        return self.import_service.import_new_scores()

    # ---------------------------------------------------------------
    # FINANCE WRAPPERS
    # ---------------------------------------------------------------
    def rebuild_finance(self):
        return self.finance_service.rebuild_finance()

    def get_balances(self):
        return self.rebuild_finance().balances

    def get_finance_ledger(self):
        return self.rebuild_finance().ledger

    def get_game_summary(self):
        return self.rebuild_finance().game_summary

    # ---------------------------------------------------------------
    # REPORT BUILDERS (HTML)
    # ---------------------------------------------------------------
    def build_game_report_html(self, game_date: date):
        return self.game_summary_service.build_game_report_html(game_date)

    def build_handicap_report_html(self):
        df = self.handicap_service.get_current_handicaps()
        html = df.to_html(index=False)
        return f"""
        <html>
            <head><title>Current Handicaps</title></head>
            <body>
                <h1>Current Handicaps</h1>
                {html}
            </body>
        </html>
        """

    def build_balances_report_html(self):
        finance = self.finance_service.rebuild_finance()
        balances = finance.balances.copy().sort_values("Player")
        html = balances.to_html(index=False)

        return f"""
        <html>
            <head><title>Player Balances</title></head>
            <body>
                <h1>Player Balances</h1>
                {html}
                <h3>Kitty: £{finance.kitty_total:.2f}</h3>
            </body>
        </html>
        """

    def build_game_surplus_report_html(self):
        finance = self.finance_service.rebuild_finance()
        game_summary = finance.game_summary.copy()

        if game_summary.empty:
            table_html = "<p>No game finance data available.</p>"
            total_surplus = 0.0
        else:
            game_summary = game_summary.sort_values("GameDate")

            df_display = game_summary.copy()
            df_display["GameDate"] = df_display["GameDate"].astype(str)
            df_display = df_display.rename(columns={
                "GameDate": "Game Date",
                "Players": "Players",
                "GameFees": "Game Fees (£2 pp)",
                "PrizeToPlayers": "Prizes Paid",
                "Surplus": "Surplus"
            })

            table_html = df_display.to_html(
                index=False,
                float_format=lambda x: f"{x:.2f}"
            )
            total_surplus = game_summary["Surplus"].sum()

        starting_kitty = self.finance_service.finance_repo.get_starting_kitty()
        expected_kitty = starting_kitty + total_surplus
        actual_kitty = finance.kitty_total

        return f"""
        <html>
            <head><title>Game Surplus Report</title></head>
            <body>
                <h1>Game Surplus Report</h1>
                {table_html}
                <h3>Total Surplus: £{total_surplus:.2f}</h3>
                <h3>Starting Kitty: £{starting_kitty:.2f}</h3>
                <h3>Expected Kitty: £{expected_kitty:.2f}</h3>
                <h3>Actual Kitty (FinanceLedger): £{actual_kitty:.2f}</h3>
            </body>
        </html>
        """

    def run_full_update(self):
        """
        Performs the system-wide update:
        - Import new scores (if master file is set)
        - Rebuild finance
        - Rebuild game summary
        - Recalculate handicaps (optional depending on your workflow)
        Returns a dictionary with useful summary info.
        """

        results = {}

        # 1. Import new scores (if importer set)
        if self.import_service:
            try:
                import_result = self.import_service.import_new_scores()
                results["import"] = import_result
            except Exception as e:
                results["import_error"] = str(e)
        else:
            results["import"] = "No import service configured."

        # 2. Rebuild finance
        try:
            finance_result = self.finance_service.rebuild_finance()
            results["finance"] = {
                "kitty": finance_result.kitty_total,
                "rows": len(finance_result.ledger)
            }
        except Exception as e:
            results["finance_error"] = str(e)

        # 3. Rebuild game summary
        try:
            summary = self.get_game_summary()
            results["summary"] = summary
        except Exception as e:
            results["summary_error"] = str(e)

        # 4. Recalculate handicaps (if needed)
        try:
            self.handicap_service.recalculate_all()
            results["handicaps"] = "Updated"
        except Exception:
            # If method doesn't exist or is optional, ignore gracefully
            pass

        return results


