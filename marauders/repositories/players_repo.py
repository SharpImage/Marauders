# marauders/repositories/players_repo.py

from typing import Optional, Dict, Any, List
import pandas as pd
from marauders.database import Database


class PlayerRepository:
    """CRUD operations for the Players table."""

    def __init__(self, db: Database):
        self.db = db
        self._ensure_table()

    def _ensure_table(self):
        """Ensure the Players table exists."""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS Players (
                Player TEXT PRIMARY KEY,
                First_Name TEXT,
                Last_Name TEXT,
                Primary_Email TEXT,
                StartingHandicap REAL,
                Active TEXT,
                StartingBalance REAL
            )
        """)

    # ----------------------------------------------------------
    # READ
    # ----------------------------------------------------------
    def get_all(self) -> pd.DataFrame:
        # Check if table has CurrentHandicaps.CurrentHandicap joined
        # But wait, CurrentHandicaps table might not exist yet?
        # Safe to left join if table exists, but if not?
        # We can just return columns from Players table first.
        # But the original code joined with CurrentHandicaps.
        # We need to make sure CurrentHandicaps exists or handle it.
        # However, this repo is PlayersRepo. It shouldn't depend on CurrentHandicaps table existence ideally,
        # but the query does.
        # Let's check if CurrentHandicaps table exists.

        has_hcaps = self.db.table_exists("CurrentHandicaps")

        if has_hcaps:
            sql = """
                  SELECT Players.Player, \
                         Players.First_Name, \
                         Players.Last_Name, \
                         Players.Primary_Email, \
                         Players.StartingHandicap, \
                         Players.Active, \
                         Players.StartingBalance, \
                         CurrentHandicaps.CurrentHandicap
                  FROM Players
                           LEFT JOIN CurrentHandicaps
                                     ON CurrentHandicaps.Player = Players.Player
                  ORDER BY Players.Player; \
                  """
        else:
             sql = """
                  SELECT Player, \
                         First_Name, \
                         Last_Name, \
                         Primary_Email, \
                         StartingHandicap, \
                         Active, \
                         StartingBalance, \
                         0.0 as CurrentHandicap
                  FROM Players
                  ORDER BY Player; \
                  """
        return self.db.read_sql(sql)

    def get_active(self) -> pd.DataFrame:
        return self.db.read_sql("""
            SELECT *
            FROM Players
            WHERE Active = 'YES'
            ORDER BY Player
        """)

    def get_by_name(self, name: str) -> Optional[pd.Series]:
        df = self.db.read_sql("""
            SELECT *
            FROM Players
            WHERE Player = ?
        """, (name,))
        return df.iloc[0] if not df.empty else None

    def player_exists(self, name: str) -> bool:
        df = self.db.read_sql("""
            SELECT Player
            FROM Players
            WHERE Player = ?
        """, (name,))
        return not df.empty

    # ----------------------------------------------------------
    # CREATE
    # ----------------------------------------------------------
    def add_player(
        self,
        player: str,
        first_name: str = "",
        last_name: str = "",
        email: str = "",
        starting_handicap: float = 0.0,
        starting_balance: float = 0.0,
        active: str = "YES",
    ) -> None:

        # Prevent duplicates
        if self.player_exists(player):
            raise ValueError(f"Player '{player}' already exists.")

        sql = """
            INSERT INTO Players
            (Player, First_Name, Last_Name, Primary_Email,
             StartingHandicap, Active, StartingBalance)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """

        self.db.execute(sql, (
            player.strip(),
            first_name.strip(),
            last_name.strip(),
            email.strip(),
            float(starting_handicap),
            active.strip().upper(),
            float(starting_balance),
        ))

    # ----------------------------------------------------------
    # UPDATE
    # ----------------------------------------------------------
    def update_player(self, player: str, **fields):
        """
        Update any fields for a player.
        """

        # Mapping from service field names → actual DB column names
        # Standardized to underscores
        column_map = {
            "First Name": "First_Name",
            "Last Name": "Last_Name",
            "Primary Email": "Primary_Email",
            "First_Name": "First_Name",
            "Last_Name": "Last_Name",
            "Primary_Email": "Primary_Email",
            "StartingHandicap": "StartingHandicap",
            "StartingBalance": "StartingBalance",
            "Active": "Active",
        }

        # Build SET clause
        set_clauses = []
        params = []

        for key, value in fields.items():
            db_col = column_map.get(key, key)
            set_clauses.append(f"`{db_col}` = ?")
            params.append(value)

        params.append(player)  # For WHERE clause

        sql = f"""
            UPDATE Players
            SET {', '.join(set_clauses)}
            WHERE Player = ?
        """

        self.db.execute(sql, params)

    # ----------------------------------------------------------
    # SPECIAL OPERATIONS
    # ----------------------------------------------------------
    def activate_player(self, player: str) -> None:
        self.update_player(player, Active="YES")

    def deactivate_player(self, player: str) -> None:
        self.update_player(player, Active="NO")

    def get_active_players(self) -> pd.DataFrame:
        """
        Return only players marked as Active = 'YES'.
        """
        df = self.get_all().copy()
        if "Active" not in df.columns:
            return df  # fallback: no active flag, return all

        df["Active"] = df["Active"].astype(str).str.strip().str.upper()
        return df[df["Active"] == "YES"].copy()

    def get_active_player_names(self) -> list:
        """
        Convenience helper: returns list of active player names.
        """
        df_active = self.get_active_players()
        if "Player" not in df_active.columns:
            return []
        return df_active["Player"].tolist()
