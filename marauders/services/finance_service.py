from __future__ import annotations

from dataclasses import dataclass
import pandas as pd

from marauders.database import Database
from marauders.repositories.finance_repo import FinanceRepository
from marauders.repositories.scores_repo import ScoreRepository
from marauders.repositories.prizes_repo import PrizeRepository
from marauders.repositories.players_repo import PlayerRepository


@dataclass
class FinanceResult:
    ledger: pd.DataFrame
    balances: pd.DataFrame
    kitty_total: float
    game_summary: pd.DataFrame


class FinanceService:
    GAME_FEE = 2.0  # £2 per player per included game

    def __init__(self, db: Database):
        self.db = db
        self.finance_repo = FinanceRepository(db)
        self.scores_repo = ScoreRepository(db)
        self.prize_repo = PrizeRepository(db)
        self.players_repo = PlayerRepository(db)

    # ------------------------------------------------------------------
    def rebuild_finance(self) -> FinanceResult:
        """
        Finance rules:

        - INCLUDED games only:
            * Each player pays £2 Game Fee
            * Prizes are paid to players from that game's fees
            * Surplus per game = GameFees - PrizeToPlayers
        - EXCLUDED games (in ExcludedGames) are completely ignored.
        - PlayerTransactions affect player balances, NOT kitty.
        - Kitty = StartingKitty + sum(Surplus for all included games).
        """

        # ==============================================================
        # 1. Load core tables directly via SQL
        # ==============================================================

        # Starting kitty from whatever table/field you already use
        starting_kitty = self.finance_repo.get_starting_kitty()

        # Excluded games
        try:
            df_ex = self.db.read_sql("SELECT GameDate FROM ExcludedGames")
            df_ex["GameDate"] = pd.to_datetime(df_ex["GameDate"], errors="coerce").dt.date
            excluded_dates = set(df_ex["GameDate"].dropna().tolist())
        except Exception:
            excluded_dates = set()

        # Scores (for per-game players and ledger)
        scores_all = self.db.read_sql("SELECT Game_Date, Player_Name FROM Scores")
        scores_all["Game_Date"] = pd.to_datetime(scores_all["Game_Date"], errors="coerce").dt.date

        # Prize payouts (for per-game prizes and ledger)
        try:
            prizes_all = self.db.read_sql("""
                SELECT GameDate, Player, Amount, Category, Place
                FROM PrizePayouts
            """)
        except Exception:
            prizes_all = pd.DataFrame(columns=["GameDate", "Player", "Amount", "Category", "Place"])

        prizes_all["GameDate"] = pd.to_datetime(prizes_all["GameDate"], errors="coerce").dt.date

        # PlayerTransactions (for ledger "Other" column only)
        manual = self.finance_repo.get_ledger().copy()
        if manual.empty:
            manual = pd.DataFrame(columns=["Date", "Player", "PaidIn", "PaidOut", "Description"])
        manual["Date"] = pd.to_datetime(manual["Date"], errors="coerce").dt.date

        # Players (for starting balances)
        players_df = self.players_repo.get_all().copy()
        starting_balances = dict(zip(players_df["Player"], players_df["StartingBalance"]))

        # ==============================================================
        # 2. Compute INCLUDED games and per-game surplus (KITTY)
        # ==============================================================

        # Distinct game dates from scores
        scores_all = scores_all.dropna(subset=["Game_Date"])
        scores_all["Included"] = ~scores_all["Game_Date"].isin(excluded_dates)

        # Per-game player counts ONLY for included games
        scores_inc = scores_all[scores_all["Included"]].copy()
        if not scores_inc.empty:
            per_game_players = (
                scores_inc.groupby("Game_Date")["Player_Name"]
                .count()
                .reset_index()
                .rename(columns={"Player_Name": "Players"})
            )
        else:
            per_game_players = pd.DataFrame(columns=["Game_Date", "Players"])

        per_game_players["GameFees"] = per_game_players["Players"] * self.GAME_FEE
        per_game_players = per_game_players.rename(columns={"Game_Date": "GameDate"})

        # Per-game prizes for included games, ignoring Player='KITTY'
        prizes_all = prizes_all.dropna(subset=["GameDate"])
        prizes_all["Included"] = ~prizes_all["GameDate"].isin(excluded_dates)
        prizes_players = prizes_all[
            (prizes_all["Included"]) & (prizes_all["Player"] != "KITTY")
        ].copy()

        if not prizes_players.empty:
            per_game_prizes = (
                prizes_players.groupby("GameDate")["Amount"]
                .sum()
                .reset_index()
                .rename(columns={"Amount": "PrizeToPlayers"})
            )
        else:
            per_game_prizes = pd.DataFrame(columns=["GameDate", "PrizeToPlayers"])

        # Merge per-game summary
        game_summary = per_game_players.merge(
            per_game_prizes,
            on="GameDate",
            how="left"
        )
        game_summary["PrizeToPlayers"] = game_summary["PrizeToPlayers"].fillna(0.0)

        # Surplus per included game
        if not game_summary.empty:
            game_summary["Surplus"] = (
                game_summary["GameFees"] - game_summary["PrizeToPlayers"]
            )
            total_surplus = game_summary["Surplus"].sum()
        else:
            total_surplus = 0.0

        kitty_total = float(starting_kitty + total_surplus)

        # ==============================================================
        # 3. Build LEDGER for player balances
        # ==============================================================

        # ----- LEDGER: included game dates only -----
        included_game_dates = set(game_summary["GameDate"].tolist())

        # Game fees rows
        game_rows = []
        for _, r in scores_all.iterrows():
            if r["Game_Date"] not in included_game_dates:
                continue
            game_rows.append({
                "Date": r["Game_Date"],
                "Player": r["Player_Name"],
                "Game Fee": -self.GAME_FEE,
                "Prizes": 0.0,
                "Other": 0.0,
                "Description": ""
            })

        # Prize rows (players only, included games only)
        prize_rows = []
        for _, r in prizes_players.iterrows():
            if r["GameDate"] not in included_game_dates:
                continue
            prize_rows.append({
                "Date": r["GameDate"],
                "Player": r["Player"],
                "Game Fee": 0.0,
                "Prizes": float(r["Amount"]),
                "Other": 0.0,
                "Description": f"{r.get('Category', '')} {r.get('Place', '')}".strip()
            })

        # Manual rows: do NOT affect kitty, only player balances
        manual_rows = []
        for _, r in manual.iterrows():
            manual_rows.append({
                "Date": r["Date"],
                "Player": r["Player"],
                "Game Fee": 0.0,
                "Prizes": 0.0,
                "Other": float(r.get("PaidIn", 0) or 0) - float(r.get("PaidOut", 0) or 0),
                "Description": r.get("Description", "")
            })

        ledger = pd.DataFrame(
            game_rows + prize_rows + manual_rows,
            columns=["Date", "Player", "Game Fee", "Prizes", "Other", "Description"]
        )

        if ledger.empty:
            empty_ledger = pd.DataFrame(
                columns=["Date", "Player", "Game Fee", "Prizes", "Other", "Description", "Net", "Balance"]
            )
            empty_balances = pd.DataFrame(columns=["Player", "Balance"])
            return FinanceResult(
                ledger=empty_ledger,
                balances=empty_balances,
                kitty_total=kitty_total,
            )

        # Clean ledger types
        ledger["Date"] = pd.to_datetime(ledger["Date"], errors="coerce").dt.date
        ledger["Game Fee"] = pd.to_numeric(ledger["Game Fee"], errors="coerce").fillna(0.0)
        ledger["Prizes"] = pd.to_numeric(ledger["Prizes"], errors="coerce").fillna(0.0)
        ledger["Other"] = pd.to_numeric(ledger["Other"], errors="coerce").fillna(0.0)

        # Net impact to player
        ledger["Net"] = ledger["Game Fee"] + ledger["Prizes"] + ledger["Other"]

        # ==============================================================
        # 4. Running balances per player (including StartingBalance)
        # ==============================================================

        ledger = ledger.sort_values(["Player", "Date"]).reset_index(drop=True)
        ledger["Balance"] = 0.0

        for player in ledger["Player"].unique():
            start_bal = starting_balances.get(player, 0.0)
            mask = ledger["Player"] == player
            ledger.loc[mask, "Balance"] = start_bal + ledger.loc[mask, "Net"].cumsum()

        ledger = ledger.sort_values(["Date", "Player"]).reset_index(drop=True)

        balances = (
            ledger.groupby("Player")["Balance"]
            .last()
            .reset_index()
        )

        return FinanceResult(
            ledger=ledger,
            balances=balances,
            kitty_total=kitty_total,
            game_summary=game_summary,
        )
