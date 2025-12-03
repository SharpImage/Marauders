"""
Completely corrected FINANCE SERVICE
------------------------------------

Fixes included:
- Correct use of PlayerTransactions instead of FinanceLedger
- Proper merging of game fees, prizes, and manual transactions
- Correct kitty computation
- Correct per-player balances
- No accidental filtering of manual transactions
- Full compatibility with excluded games
- Fully cleaned and simplified logic
"""

from __future__ import annotations
from dataclasses import dataclass
import pandas as pd

from marauders.database import Database
from marauders.repositories.finance_repo import FinanceRepository
from marauders.repositories.scores_repo import ScoreRepository
from marauders.repositories.prizes_repo import PrizeRepository
from marauders.repositories.players_repo import PlayerRepository


# ======================================================================
# RESULT STRUCTURE
# ======================================================================

@dataclass
class FinanceResult:
    ledger: pd.DataFrame
    balances: pd.DataFrame
    kitty_total: float
    game_summary: pd.DataFrame


# ======================================================================
# FINANCE SERVICE
# ======================================================================

class FinanceService:
    GAME_FEE = 2.0  # £2 per included game

    def __init__(self, db: Database):
        self.db = db
        self.finance_repo = FinanceRepository(db)
        self.scores_repo = ScoreRepository(db)
        self.prize_repo = PrizeRepository(db)
        self.players_repo = PlayerRepository(db)

    # ==================================================================
    # MAIN ENTRY POINT
    # ==================================================================
    def rebuild_finance(self) -> FinanceResult:

        # --------------------------------------------------------------
        # LOAD STARTING KITTY
        # --------------------------------------------------------------
        starting_kitty = self.finance_repo.get_starting_kitty()

        # --------------------------------------------------------------
        # EXCLUDED GAMES
        # --------------------------------------------------------------
        try:
            df_ex = self.db.read_sql("SELECT GameDate FROM ExcludedGames")
            df_ex["GameDate"] = pd.to_datetime(df_ex["GameDate"], errors="coerce").dt.date
            excluded_dates = set(df_ex["GameDate"].dropna().tolist())
        except Exception:
            excluded_dates = set()

        # --------------------------------------------------------------
        # SCORES
        # --------------------------------------------------------------
        scores_all = self.db.read_sql("""
            SELECT Game_Date, Player_Name
            FROM Scores
        """)
        scores_all["Game_Date"] = pd.to_datetime(scores_all["Game_Date"], errors="coerce").dt.date
        scores_all["Player_Name"] = scores_all["Player_Name"].astype(str).str.strip()
        scores_all = scores_all.dropna(subset=["Game_Date", "Player_Name"])

        # Only included games count toward game fees
        scores_all["Included"] = ~scores_all["Game_Date"].isin(excluded_dates)
        scores_inc = scores_all[scores_all["Included"]]

        # Count players per included game
        if not scores_inc.empty:
            per_game_players = (
                scores_inc.groupby("Game_Date")["Player_Name"]
                .count()
                .reset_index()
                .rename(columns={"Game_Date": "GameDate", "Player_Name": "Players"})
            )
        else:
            per_game_players = pd.DataFrame(columns=["GameDate", "Players"])

        per_game_players["GameFees"] = per_game_players["Players"] * self.GAME_FEE

        # --------------------------------------------------------------
        # PRIZES
        # --------------------------------------------------------------
        try:
            prizes_all = self.db.read_sql("""
                SELECT GameDate, Player, Amount, Category, Place
                FROM PrizePayouts
            """)
        except Exception:
            prizes_all = pd.DataFrame(columns=["GameDate", "Player", "Amount", "Category", "Place"])

        prizes_all["GameDate"] = pd.to_datetime(prizes_all["GameDate"], errors="coerce").dt.date
        prizes_all["Player"] = prizes_all["Player"].astype(str).str.strip()

        # Only included games
        prizes_included = prizes_all[~prizes_all["GameDate"].isin(excluded_dates)]

        prizes_players = prizes_included[prizes_included["Player"] != "KITTY"]

        # Sum prizes to players per game
        if not prizes_players.empty:
            per_game_prizes = (
                prizes_players.groupby("GameDate")["Amount"]
                .sum()
                .reset_index()
                .rename(columns={"Amount": "PrizeToPlayers"})
            )
        else:
            per_game_prizes = pd.DataFrame(columns=["GameDate", "PrizeToPlayers"])

        # --------------------------------------------------------------
        # MERGE GAME FEES + PRIZES
        # --------------------------------------------------------------
        game_summary = per_game_players.merge(per_game_prizes, on="GameDate", how="left")
        game_summary["PrizeToPlayers"] = game_summary["PrizeToPlayers"].fillna(0.0)
        game_summary["Surplus"] = game_summary["GameFees"] - game_summary["PrizeToPlayers"]

        total_surplus = game_summary["Surplus"].sum() if not game_summary.empty else 0.0
        kitty_total = starting_kitty + total_surplus

        # --------------------------------------------------------------
        # MANUAL PLAYER TRANSACTIONS  (the missing piece)
        # --------------------------------------------------------------
        manual = self.finance_repo.get_player_transactions().copy()

        if manual.empty:
            manual = pd.DataFrame(columns=["Date", "Player", "PaidIn", "PaidOut", "Description"])

        manual["Date"] = pd.to_datetime(manual["Date"], errors="coerce").dt.date
        manual["Player"] = manual["Player"].astype(str).str.strip()
        manual["PaidIn"] = pd.to_numeric(manual["PaidIn"], errors="coerce").fillna(0.0)
        manual["PaidOut"] = pd.to_numeric(manual["PaidOut"], errors="coerce").fillna(0.0)

        # --------------------------------------------------------------
        # BUILD LEDGER ROWS
        # --------------------------------------------------------------
        included_game_dates = set(game_summary["GameDate"].tolist())

        # Game fees per player (negative)
        game_rows = [
            {
                "Date": r["Game_Date"],
                "Player": r["Player_Name"],
                "Game Fee": -self.GAME_FEE,
                "Prizes": 0.0,
                "Other": 0.0,
                "Description": ""
            }
            for _, r in scores_all.iterrows()
            if r["Game_Date"] in included_game_dates
        ]

        # Prize payouts
        prize_rows = [
            {
                "Date": r["GameDate"],
                "Player": r["Player"],
                "Game Fee": 0.0,
                "Prizes": float(r["Amount"]),
                "Other": 0.0,
                "Description": f"{r['Category']} {r['Place']}".strip()
            }
            for _, r in prizes_players.iterrows()
            if r["GameDate"] in included_game_dates
        ]

        # Manual transactions (ALWAYS INCLUDED)
        manual_rows = [
            {
                "Date": r["Date"],
                "Player": r["Player"],
                "Game Fee": 0.0,
                "Prizes": 0.0,
                "Other": float(r["PaidIn"]) - float(r["PaidOut"]),
                "Description": r.get("Description", "")
            }
            for _, r in manual.iterrows()
        ]

        # --------------------------------------------------------------
        # COMBINE
        # --------------------------------------------------------------

        ledger = pd.DataFrame(
            game_rows + prize_rows + manual_rows,
            columns=["Date", "Player", "Game Fee", "Prizes", "Other", "Description"]
        )

        if ledger.empty:
            return FinanceResult(
                ledger=ledger,
                balances=pd.DataFrame(columns=["Player", "Balance"]),
                kitty_total=kitty_total,
                game_summary=game_summary,
            )

        # Clean types
        ledger["Date"] = pd.to_datetime(ledger["Date"], errors="coerce").dt.date
        ledger["Game Fee"] = pd.to_numeric(ledger["Game Fee"], errors="coerce").fillna(0.0)
        ledger["Prizes"] = pd.to_numeric(ledger["Prizes"], errors="coerce").fillna(0.0)
        ledger["Other"] = pd.to_numeric(ledger["Other"], errors="coerce").fillna(0.0)

        ledger = ledger.dropna(subset=["Player"]).copy()

        ledger["Net"] = ledger["Game Fee"] + ledger["Prizes"] + ledger["Other"]

        # --------------------------------------------------------------
        # PLAYER BALANCES
        # --------------------------------------------------------------
        players_df = self.players_repo.get_all()
        starting_balances = dict(zip(players_df["Player"], players_df["StartingBalance"]))

        ledger = ledger.sort_values(["Player", "Date"]).reset_index(drop=True)
        ledger["Balance"] = 0.0

        for player in ledger["Player"].unique():
            start = starting_balances.get(player, 0.0)
            mask = ledger["Player"] == player
            ledger.loc[mask, "Balance"] = start + ledger.loc[mask, "Net"].cumsum()

        # Sort for display
        ledger = ledger.sort_values(["Date", "Player"]).reset_index(drop=True)

        # Final balances per player
        balances = ledger.groupby("Player")["Balance"].last().reset_index()

        # ------------------------------------------------------------
        # WRITE LEDGER TO DATABASE
        # ------------------------------------------------------------
        try:
            # Overwrite table with new ledger
            self.db.write_table("FinanceLedger", ledger, replace=True)
        except Exception as e:
            print("ERROR WRITING FINANCELEDGER:", e)
            raise

        # Return standard result
        return FinanceResult(
            ledger=ledger,
            balances=balances,
            game_summary=game_summary,
            kitty_total=kitty_total,
        )

