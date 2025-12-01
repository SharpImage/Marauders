# marauders/manager.py

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import date
import pandas as pd

from marauders.database import Database
from marauders.repositories.games_repo import GameRepository
from marauders.repositories.scores_repo import ScoreRepository

from marauders.services.import_service import ImportService
from marauders.services.handicap_service import HandicapService
from marauders.services.prize_service import PrizeService
from marauders.services.finance_service import FinanceService, FinanceResult
from marauders.services.player_service import PlayerService
from marauders.services.game_summary_service import GameSummaryService
from marauders.services.game_report_service import GameReportService


class MaraudersManager:
    """
    High-level façade for the Marauders backend.

    This is what the future GUI should talk to.

    Responsibilities:
      - Coordinate services (import, handicaps, prizes, finance, players, summaries)
      - Provide simple methods with sensible defaults
      - Hide low-level repositories from the GUI
    """

    def __init__(
        self,
        db_path: str = "marauders.db",
        master_file: Optional[str] = None,
    ):
        """
        db_path:     path to marauders.db (must already exist)
        master_file: path to the Excel master file used for importing scores
        """
        self.db_path = db_path
        self.db = Database(db_path)
        self.game_report_service = GameReportService(self.db)

        self.master_file = Path(master_file) if master_file is not None else None

        # Core repositories/services
        self.game_repo = GameRepository(self.db)

        self.import_service = None
        if self.master_file is not None:
            self.import_service = ImportService(self.db, str(self.master_file))

        self.handicap_service = HandicapService(self.db)
        self.prize_service = PrizeService(self.db)
        self.finance_service = FinanceService(self.db)
        self.player_service = PlayerService(self.db)
        self.game_summary_service = GameSummaryService(self.db)
        self.scores_repo = ScoreRepository(self.db)
    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------
    def set_master_file(self, master_file: str):
        """Update the MASTER_FILE path used for importing scores."""
        self.master_file = Path(master_file)
        self.import_service = ImportService(self.db, str(self.master_file))

    # ------------------------------------------------------------------
    # 1) Import new scores
    # ------------------------------------------------------------------
    def import_new_scores(self) -> Dict[str, Any]:
        """
        Import new scores from MASTER_FILE (Excel) into SQLite.

        Returns:
            {
                "imported_count": int,
                "existing_count": int,
                "new_keys": list[(date, player)],
                "skipped_keys": list[(date, player)]
            }
        """
        if self.import_service is None:
            raise RuntimeError("MASTER_FILE is not configured. Call set_master_file() first.")

        return self.import_service.import_new_scores()

    # ------------------------------------------------------------------
    # 2) Rebuild handicaps
    # ------------------------------------------------------------------
    def rebuild_handicaps(self) -> Dict[str, pd.DataFrame]:
        """
        Recompute:
          - HandicapHistory
          - CurrentHandicaps

        Returns:
            {
                "history": DataFrame,
                "current": DataFrame
            }
        """
        return self.handicap_service.rebuild_handicaps()

    # ------------------------------------------------------------------
    # 3) Compute prizes
    # ------------------------------------------------------------------
    def compute_prizes(self) -> Dict[str, pd.DataFrame]:
        """
        Compute prize payouts for all games.

        Returns:
            {
                "payouts": DataFrame (PrizePayouts-style),
                "totals_per_player": DataFrame
            }
        """
        return self.prize_service.compute_all_prizes()

    # ------------------------------------------------------------------
    # 4) Rebuild finance ledger
    # ------------------------------------------------------------------
    def rebuild_finance(self) -> FinanceResult:
        """
        Rebuild the finance ledger and summary data.

        Returns a FinanceResult dataclass:
            ledger: DataFrame
            balances: DataFrame
            game_profit_loss: DataFrame
            kitty_total: float
            pot_total: float
        """
        return self.finance_service.rebuild_finance()

    # ------------------------------------------------------------------
    # 5) Player status + management
    # ------------------------------------------------------------------
    def get_player_status(self, include_inactive: bool = False):
        return self.player_service.build_player_status_table(include_inactive=include_inactive)

    def add_player(
        self,
        player: str,
        first_name: str = "",
        last_name: str = "",
        email: str = "",
        starting_handicap: float = 0.0,
        starting_balance: float = 0.0,
    ) -> None:
        """Add a new player."""
        self.player_service.add_player(
            player=player,
            first_name=first_name,
            last_name=last_name,
            email=email,
            starting_handicap=starting_handicap,
            starting_balance=starting_balance,
        )

    def edit_player(
        self,
        player: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        email: Optional[str] = None,
        starting_handicap: Optional[float] = None,
        starting_balance: Optional[float] = None,
        active: Optional[str] = None,
    ) -> None:
        """Edit an existing player's details."""
        self.player_service.edit_player(
            player=player,
            first_name=first_name,
            last_name=last_name,
            email=email,
            starting_handicap=starting_handicap,
            starting_balance=starting_balance,
            active=active,
        )

    def deactivate_player(self, player: str) -> None:
        self.player_service.deactivate_player(player)

    def activate_player(self, player: str) -> None:
        self.player_service.activate_player(player)

    def get_player_record(self, player: str) -> dict:
        """Return a full player record as a dict."""
        df = self.player_service.players_repo.get_all()   # using player_service
        row = df[df["Player"] == player]

        if row.empty:
            raise ValueError(f"Player '{player}' not found.")

        return row.iloc[0].to_dict()

    # ------------------------------------------------------------------
    # 6) Game dates & exclusions
    # ------------------------------------------------------------------
    def get_all_game_dates(self) -> List[str]:
        """All game dates (including excluded ones)."""
        return self.game_repo.get_all_game_dates()

    def get_valid_game_dates(self) -> List[str]:
        """Game dates excluding those in ExcludedGames."""
        return self.game_repo.get_valid_game_dates()

    def get_excluded_games(self) -> pd.DataFrame:
        """DataFrame of excluded games (GameDate | Reason)."""
        return self.game_repo.get_excluded_game_dates()

    def exclude_game(self, game_date: str, reason: str = "") -> None:
        """Mark a game date as excluded from analysis."""
        self.game_repo.exclude_game(game_date, reason)

    def include_game(self, game_date: str) -> None:
        """Remove a game from the exclusion list."""
        self.game_repo.include_game(game_date)

    # ------------------------------------------------------------------
    # 7) Game summaries
    # ------------------------------------------------------------------
    def build_game_summary(self, game_date: str) -> Dict[str, pd.DataFrame]:
        """
        Returns per-game summary:
            {
                "scores": DataFrame,
                "handicaps": DataFrame,
                "prizes": DataFrame
            }
        """
        return self.game_summary_service.build_game_summary(game_date)

    # ------------------------------------------------------------------
    # 8) Full pipeline helper (import → handicaps → prizes → finance)
    # ------------------------------------------------------------------
    def run_full_update(self) -> Dict[str, Any]:
        """
        Convenience method to run the full pipeline in logical order:

          1. Import new scores from Excel (if MASTER_FILE configured)
          2. Rebuild handicaps
          3. Compute prizes
          4. Rebuild finance

        Returns a summary dict with the key results of each stage.
        """

        results: Dict[str, Any] = {}

        if self.import_service is not None:
            results["import"] = self.import_new_scores()

        results["handicaps"] = self.rebuild_handicaps()
        results["prizes"] = self.compute_prizes()
        results["finance"] = self.rebuild_finance()

        return results

    # ------------------------------------------------------------------
    # 9) Reports
    # ------------------------------------------------------------------
    def build_game_report_html(self, game_date: date) -> str:
        return self.game_report_service.build_game_report_html(game_date)

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
        balances = finance.balances.copy()
        balances = balances.sort_values("Player")

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


