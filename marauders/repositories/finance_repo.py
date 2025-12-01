# marauders/repositories/finance_repo.py

import pandas as pd
from marauders.database import Database


class FinanceRepository:
    """
    Repository for finance-related DB tables:
      - PlayerTransactions
      - FinanceSettings (stores StartingKitty)
    """

    def __init__(self, db: Database):
        self.db = db
        self._ensure_tables()

    # ------------------------------------------------------------
    # Ensure Settings Table Exists
    # ------------------------------------------------------------
    def _ensure_tables(self):
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS FinanceSettings (
                Setting TEXT PRIMARY KEY,
                Value REAL
            )
            """
        )

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
        df = self.db.read_sql("""
            SELECT Value FROM FinanceSettings
            WHERE Setting='StartingKitty'
        """)
        if df.empty:
            return 0.0
        return float(df.iloc[0]["Value"])

    def set_starting_kitty(self, amount: float):
        self.db.execute(
            """
            INSERT INTO FinanceSettings (Setting, Value)
            VALUES ('StartingKitty', ?)
            ON CONFLICT(Setting)
            DO UPDATE SET Value = excluded.Value
            """,
            (amount,)
        )

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

