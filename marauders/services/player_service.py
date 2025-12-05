# marauders/services/player_service.py

from __future__ import annotations

from typing import Dict, Any, Optional
import pandas as pd

from marauders.database import Database
from marauders.repositories.players_repo import PlayerRepository
from marauders.repositories.handicaps_repo import HandicapRepository
from marauders.repositories.finance_repo import FinanceRepository


class PlayerService:
    """
    Combines player data, current handicaps, and balances into a single
    GUI-ready format.

    Also provides add/edit/deactivate operations via PlayerRepository.
    """

    def __init__(self, db: Database):
        self.db = db
        self.players_repo = PlayerRepository(db)
        self.hcaps_repo = HandicapRepository(db)
        self.finance_repo = FinanceRepository(db)

    # ----------------------------------------------------------------------
    # STATUS TABLE (Dashboard)
    # ----------------------------------------------------------------------
    def build_player_status_table(self, include_inactive: bool = False) -> pd.DataFrame:
        """
        Builds the player status table combining:
          - Player details
          - Current handicap (active only)
          - Current balance (all players, then merged)

        If include_inactive=True:
            All players appear (active + inactive)
        Otherwise:
            Only active players are included.
        """

        # 1. ACTIVE players only unless include_inactive flag is set
        if include_inactive:
            df_players = self.players_repo.get_all().copy()
        else:
            df_players = self.players_repo.get_active_players().copy()

        # 2. Current handicaps (already filtered to active players)
        df_hcaps = self.hcaps_repo.get_current().copy()
        if (
            df_hcaps is None
            or df_hcaps.empty
            or "Player" not in df_hcaps.columns
            or "CurrentHandicap" not in df_hcaps.columns
        ):
            df_hcaps = pd.DataFrame(columns=["Player", "CurrentHandicap"])
        else:
            df_hcaps["CurrentHandicap"] = pd.to_numeric(
                df_hcaps["CurrentHandicap"], errors="coerce"
            ).fillna(0.0)

        # 3. Balances – may include inactive players, that's fine
        balances = self.finance_repo.get_player_balances().copy()
        if "Balance" not in balances.columns:
            balances["Balance"] = 0.0

        balances["Balance"] = pd.to_numeric(
            balances["Balance"], errors="coerce"
        ).fillna(0.0)

        # 4. Merge players + handicaps
        df = df_players.merge(df_hcaps, on="Player", how="left")

        # 5. Merge balances
        df = df.merge(balances[["Player", "Balance"]], on="Player", how="left")

        # 6. Round numeric columns (safe)
        if "CurrentHandicap" in df.columns:
            df["CurrentHandicap"] = pd.to_numeric(
                df["CurrentHandicap"], errors="coerce"
            ).fillna(0.0)
            df["CurrentHandicap"] = df["CurrentHandicap"].round(1)

        df["Balance"] = pd.to_numeric(df["Balance"], errors="coerce").fillna(0.0)
        df["Balance"] = df["Balance"].round(2)

        # --- Fix floating-point precision on starting handicap ---
        for col in ["StartingHandicap", "Start_Handicap", "Starting_Handicap"]:
            if col in df.columns:
                df[col] = df[col].astype(float).round(1)

        # 7. Final ordering
        df = df.sort_values("Player").reset_index(drop=True)
        return df

    # ----------------------------------------------------------------------
    # PLAYER MANAGEMENT
    # ----------------------------------------------------------------------
    def add_player(
        self,
        player: str,
        first_name: str = "",
        last_name: str = "",
        email: str = "",
        starting_handicap: float = 0.0,
        starting_balance: float = 0.0,
    ) -> None:
        """
        Add a new player — validates uniqueness, normalises values.
        """
        player = player.strip()
        if not player:
            raise ValueError("Player name cannot be empty.")

        # Validate duplicate
        if self.players_repo.player_exists(player):
            raise ValueError(f"Player '{player}' already exists.")

        # Create record
        self.players_repo.add_player(
            player=player,
            first_name=first_name,
            last_name=last_name,
            email=email,
            starting_handicap=starting_handicap,
            starting_balance=starting_balance,
            active="YES",
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
        """
        Edit an existing player's details.
        Player name itself is read-only to preserve DB links.
        """
        if not self.players_repo.player_exists(player):
            raise ValueError(f"Player '{player}' does not exist.")

        fields: Dict[str, Any] = {}

        if first_name is not None:
            fields["First_Name"] = first_name
        if last_name is not None:
            fields["Last_Name"] = last_name
        if email is not None:
            fields["Primary_Email"] = email
        if starting_handicap is not None:
            fields["StartingHandicap"] = float(starting_handicap)
        if starting_balance is not None:
            fields["StartingBalance"] = float(starting_balance)
        if active is not None:
            fields["Active"] = active.strip().upper()

        if fields:
            self.players_repo.update_player(player, **fields)

    def deactivate_player(self, player: str):
        if not self.players_repo.player_exists(player):
            raise ValueError(f"Player '{player}' does not exist.")
        self.players_repo.deactivate_player(player)

    def activate_player(self, player: str):
        if not self.players_repo.player_exists(player):
            raise ValueError(f"Player '{player}' does not exist.")
        self.players_repo.activate_player(player)
