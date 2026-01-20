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
        """
        Ensure the Players table exists.

        NOTE: The original database used quoted column names with spaces
        (e.g., "First Name"). We define the schema to match that legacy format
        to ensure compatibility with existing databases.
        """
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS Players (
                Player TEXT PRIMARY KEY,
                "First Name" TEXT,
                "Last Name" TEXT,
                "Primary Email" TEXT,
                StartingHandicap REAL,
                Active TEXT,
                StartingBalance REAL
            )
        """)

    # ----------------------------------------------------------
    # READ
    # ----------------------------------------------------------
    def get_all(self) -> pd.DataFrame:

        has_hcaps = self.db.table_exists("CurrentHandicaps")

        # Use quoted identifiers for compatibility with legacy DBs
        if has_hcaps:
            sql = """
                  SELECT Players.Player, \
                         Players."First Name", \
                         Players."Last Name", \
                         Players."Primary Email", \
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
                         "First Name", \
                         "Last Name", \
                         "Primary Email", \
                         StartingHandicap, \
                         Active, \
                         StartingBalance, \
                         0.0 as CurrentHandicap
                  FROM Players
                  ORDER BY Player; \
                  """
        df = self.db.read_sql(sql)

        # Rename columns to standard underscored names for internal use
        df.rename(columns={
            "First Name": "First_Name",
            "Last Name": "Last_Name",
            "Primary Email": "Primary_Email"
        }, inplace=True)

        return df

    def get_active(self) -> pd.DataFrame:
        df = self.db.read_sql("""
            SELECT *
            FROM Players
            WHERE Active = 'YES'
            ORDER BY Player
        """)
        # Rename columns to standard underscored names
        df.rename(columns={
            "First Name": "First_Name",
            "Last Name": "Last_Name",
            "Primary Email": "Primary_Email"
        }, inplace=True)
        return df

    def get_by_name(self, name: str) -> Optional[pd.Series]:
        df = self.db.read_sql("""
            SELECT *
            FROM Players
            WHERE Player = ?
        """, (name,))

        if df.empty:
            return None

        df.rename(columns={
            "First Name": "First_Name",
            "Last Name": "Last_Name",
            "Primary Email": "Primary_Email"
        }, inplace=True)
        return df.iloc[0]

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

        if self.player_exists(player):
            raise ValueError(f"Player '{player}' already exists.")

        # Insert using quoted column names for legacy compatibility
        sql = """
            INSERT INTO Players
            (Player, "First Name", "Last Name", "Primary Email",
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

        # Map internal keys to legacy DB column names
        column_map = {
            "First Name": '"First Name"',
            "Last Name": '"Last Name"',
            "Primary Email": '"Primary Email"',
            "First_Name": '"First Name"',
            "Last_Name": '"Last Name"',
            "Primary_Email": '"Primary Email"',
            "StartingHandicap": "StartingHandicap",
            "StartingBalance": "StartingBalance",
            "Active": "Active",
        }

        set_clauses = []
        params = []

        for key, value in fields.items():
            db_col = column_map.get(key, key)
            set_clauses.append(f"{db_col} = ?")
            params.append(value)

        params.append(player)

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
        df = self.get_all().copy()
        if "Active" not in df.columns:
            return df

        df["Active"] = df["Active"].astype(str).str.strip().str.upper()
        return df[df["Active"] == "YES"].copy()

    def get_active_player_names(self) -> list:
        df_active = self.get_active_players()
        if "Player" not in df_active.columns:
            return []
        return df_active["Player"].tolist()
