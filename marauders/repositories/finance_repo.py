# marauders/repositories/finance_repo.py

import pandas as pd
from marauders.database import Database
from marauders.repositories.settings_repo import SettingsRepository


class FinanceRepository:
    """
    Repository for finance-related DB tables:
      - PlayerTransactions
    """

    def __init__(self, db: Database, settings_repo: SettingsRepository):
        self.db = db
        self.settings_repo = settings_repo
        self._ensure_table()

    def _ensure_table(self):
        """Ensure the PlayerTransactions table exists."""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS PlayerTransactions (
                Date TEXT,
                Player TEXT,
                PaidIn REAL,
                PaidOut REAL,
                Description TEXT
            )
        """)

    # ------------------------------------------------------------
    # Player Transactions
    # ------------------------------------------------------------
    def get_ledger(self) -> pd.DataFrame:
        df = self.db.read_sql("""
            SELECT *
            FROM PlayerTransactions
            ORDER BY Date
        """)
        if not df.empty:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        return df

    def add_transaction(self, date, player, paid_in, paid_out, description):
        self.db.execute(
            """
            INSERT INTO PlayerTransactions (Date, Player, PaidIn, PaidOut, Description)
            VALUES (?, ?, ?, ?, ?)
            """,
            (date, player, paid_in, paid_out, description)
        )

    # ------------------------------------------------------------
    # Starting Kitty
    # ------------------------------------------------------------
    def get_starting_kitty(self) -> float:
        return self.settings_repo.get_starting_kitty()

    def set_starting_kitty(self, amount: float):
        self.settings_repo.set_starting_kitty(amount)

    # ------------------------------------------------------------
    # Account Balances
    # ------------------------------------------------------------
    def get_account_balance(self, account: str) -> float:
        """Returns the sum of PaidIn - PaidOut filtered by Description containing the account name."""
        df = self.get_ledger()
        if df.empty:
            return 0.0

        mask = df["Description"].str.contains(account, case=False, na=False)
        if not mask.any():
            return 0.0

        subset = df[mask]
        return float(subset["PaidIn"].sum() - subset["PaidOut"].sum())

    def get_player_balances(self) -> pd.DataFrame:
        """
        Safe version:
        Returns empty dataframe if FinanceLedger does not yet exist.
        Prevents Dashboard from crashing on first run.
        """
        try:
            df = self.db.read_sql("""
                                  SELECT Player, Date, Balance
                                  FROM FinanceLedger
                                  ORDER BY Player, Date
                                  """)
        except Exception:
            # Table does not exist yet → return empty structure
            return pd.DataFrame(columns=["Player", "Balance"])

        if df.empty:
            return pd.DataFrame(columns=["Player", "Balance"])

        df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date

        latest = (
            df.sort_values(["Player", "Date"])
            .groupby("Player")
            .tail(1)[["Player", "Balance"]]
            .reset_index(drop=True)
        )

        return latest

    def get_player_transactions(self) -> pd.DataFrame:
        """
        Return the PlayerTransactions table as a DataFrame.

        Includes a synthetic TransactionID column (SQLite rowid)
        for editing purposes.

        Columns:
            TransactionID, Date, Player, PaidIn, PaidOut, Description
        """
        try:
            df = self.db.read_sql(
                """
                SELECT rowid AS TransactionID, Date, Player, PaidIn, PaidOut, Description
                FROM PlayerTransactions
                ORDER BY Date
                """
            )
            return df
        except Exception:
            return pd.DataFrame(
                columns=["TransactionID", "Date", "Player", "PaidIn", "PaidOut", "Description"]
            )

    def update_transaction(
            self,
            transaction_id: int,
            date: str,
            player: str,
            paid_in: float,
            paid_out: float,
            description: str,
    ) -> None:
        """
        Update an existing transaction identified by TransactionID (rowid).
        """
        self.db.execute(
            """
            UPDATE PlayerTransactions
            SET Date        = ?,
                Player      = ?,
                PaidIn      = ?,
                PaidOut     = ?,
                Description = ?
            WHERE rowid = ?
            """,
            (date, player, paid_in, paid_out, description, transaction_id),
        )
