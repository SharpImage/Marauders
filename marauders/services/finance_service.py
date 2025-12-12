import pandas as pd
import datetime
import re


class FinanceResult:
    def __init__(self, ledger, balances, kitty_total, game_summary):
        self.ledger = ledger
        self.balances = balances
        self.kitty_total = kitty_total
        self.game_summary = game_summary


class FinanceService:

    GAME_FEE = 2.0

    def __init__(self, db, players_repo, scores_repo, prizes_repo, games_repo, finance_repo):
        self.db = db
        self.players_repo = players_repo
        self.scores_repo = scores_repo
        self.prizes_repo = prizes_repo
        self.games_repo = games_repo
        self.finance_repo = finance_repo

    # =====================================================================
    # SAFE DATE PARSER
    # =====================================================================
    def _safe_date(self, val):
        """
        Convert any possible date representation into datetime.date or None.
        For non-ISO strings (e.g. '02/12/2025') we treat them as UK style
        day-first (2 December 2025), to avoid 02/12↔12/02 flips.
        """
        # Already a date
        if isinstance(val, datetime.date):
            return val

        # Pandas Timestamp -> datetime.date
        if isinstance(val, pd.Timestamp):
            return val.date()

        # String handling
        if isinstance(val, str):
            v = val.strip()
            if not v:
                return None

            # Fast path for ISO YYYY-MM-DD (unambiguous)
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
                try:
                    return datetime.date.fromisoformat(v)
                except Exception:
                    return None

            # Fallback parser for other string formats:
            # assume UK style (dayfirst=True) to match score/prize imports.
            parsed = pd.to_datetime(v, errors="coerce", dayfirst=True)
            return None if pd.isna(parsed) else parsed.date()

        # None / NaN
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return None

        # Anything else – let pandas try, still with dayfirst=True
        try:
            parsed = pd.to_datetime(val, errors="coerce", dayfirst=True)
            return None if pd.isna(parsed) else parsed.date()
        except Exception:
            return None

    # =====================================================================
    # NORMALISE DATE COLUMN AFTER CONCAT
    # =====================================================================
    def _normalise_final_dates(self, df):
        """
        Ensure the entire Date column is consistently datetime.date (not Timestamp),
        and allow None values. Required before sorting.
        """
        df["Date"] = df["Date"].apply(self._safe_date)

        # Convert all valid dates into pure datetime.date
        df["Date"] = df["Date"].apply(
            lambda d: None if d is None else datetime.date(d.year, d.month, d.day)
        )

        # Ensure dtype=object
        df["Date"] = df["Date"].astype(object)

        return df

    # =====================================================================
    # SAFE SORT USING python tuple key
    # =====================================================================
    def _sort_ledger(self, df):
        """
        Safe sorting that will not attempt direct comparison between None and date.
        """
        return df.sort_values(
            by="Date",
            key=lambda col: col.apply(lambda d: (d is None, d)),
            na_position="first"
        ).reset_index(drop=True)

    # =====================================================================
    # MAIN FINANCE REBUILD
    # =====================================================================
    def rebuild_finance(self) -> FinanceResult:

        # ---------------------------------------------------------------
        # LOAD SCORES
        # ---------------------------------------------------------------
        scores = self.scores_repo.get_all().copy()
        scores["Game_Date"] = scores["Game_Date"].apply(self._safe_date)

        # ---------------------------------------------------------------
        # EXCLUDED GAMES
        # ---------------------------------------------------------------
        excluded_raw = self.games_repo.get_excluded_game_dates()
        excluded_dates = [
            self._safe_date(x)
            for x in excluded_raw
            if isinstance(self._safe_date(x), datetime.date)
        ]

        if excluded_dates:
            scores["Game_Date"] = scores["Game_Date"].apply(self._safe_date)
            excluded_dates = [self._safe_date(x) for x in excluded_dates]

            scores["Included"] = ~scores["Game_Date"].apply(lambda d: d in excluded_dates)
        else:
            scores["Included"] = True

        scores_inc = scores[scores["Included"]]

        # players per game
        players_per_date = (
            scores_inc.groupby("Game_Date")["Player_Name"]
            .count()
            .to_dict()
        )

        # ---------------------------------------------------------------
        # GAME FEES
        # ---------------------------------------------------------------
        # Build per-player game-fee rows (no aggregated date rows)
        fee_rows = []

        # Work only with included scores
        scores_included_local = scores_inc.copy()

        # Ensure valid date format
        scores_included_local = scores_included_local[
            scores_included_local["Game_Date"].notna()
        ]

        # One fee row per (game_date, player)
        for _, row in (
                scores_included_local[["Game_Date", "Player_Name"]]
                        .drop_duplicates()
                        .iterrows()
        ):
            game_date = row["Game_Date"]
            player = row["Player_Name"]

            # Normalise Timestamp → date
            if hasattr(game_date, "date"):
                game_date = game_date.date()

            fee_rows.append({
                "Date": game_date,
                "Player": player,
                "PaidIn": self.GAME_FEE,  # £2 per player per game
                "PaidOut": 0.0,
                "Description": f"Game fee ({game_date})",
                "Category": "GAME_FEE",
            })

        df_fees = pd.DataFrame(fee_rows)
        if df_fees.empty:
             df_fees = pd.DataFrame(columns=["Date", "Player", "PaidIn", "PaidOut", "Description", "Category"])

        df_fees["Date"] = df_fees["Date"].apply(self._safe_date).astype(object)

        # ---------------------------------------------------------------
        # PRIZES
        # ---------------------------------------------------------------
        payouts = self.prizes_repo.get_all_payouts().copy()
        payouts["Date"] = payouts["GameDate"].apply(self._safe_date)

        df_prizes = pd.DataFrame({
            "Date": payouts["Date"],
            "Player": payouts["Player"],
            "PaidIn": 0.0,
            "PaidOut": payouts["Amount"],
            "Description": payouts["Category"] + " " + payouts["Place"],
            "Category": "PRIZE",
        })

        # ---------------------------------------------------------------
        # STARTING KITTY
        # ---------------------------------------------------------------
        starting_kitty = self.finance_repo.get_starting_kitty()
        df_start = pd.DataFrame([{
            "Date": None,
            "Player": "",
            "PaidIn": starting_kitty,
            "PaidOut": 0.0,
            "Description": "Starting Kitty",
            "Category": "STARTING_KITTY",
        }])

        # ---------------------------------------------------------------
        # MANUAL TRANSACTIONS (excluding prize duplicates)
        # ---------------------------------------------------------------
        df_manual = self.finance_repo.get_ledger().copy()
        df_manual["Date"] = df_manual["Date"].apply(self._safe_date)

        df_manual = df_manual[
            ~df_manual["Description"].str.contains("prize", case=False, na=False)
        ]

        # ---------------------------------------------------------------
        # CONCAT ALL PARTS
        # ---------------------------------------------------------------
        parts = [df_start, df_manual, df_fees, df_prizes]
        parts = [p for p in parts if not p.empty]

        df_all = pd.concat(parts, ignore_index=True)

        # ---------------------------------------------------------------
        # FINAL FIX — NORMALISE ALL DATES & SAFE SORT
        # ---------------------------------------------------------------
        df_all = self._normalise_final_dates(df_all)
        df_all = self._sort_ledger(df_all)

        # ---------------------------------------------------------------
        # BALANCES
        # ---------------------------------------------------------------
        balances = (
            df_all.groupby("Player")[["PaidIn", "PaidOut"]]
            .sum()
            .reset_index()
        )
        balances["Balance"] = balances["PaidIn"] - balances["PaidOut"]

        # ---------------------------------------------------------------
        # KITTY TOTAL
        # ---------------------------------------------------------------
        kitty_total = float(df_all["PaidIn"].sum() - df_all["PaidOut"].sum())

        # ---------------------------------------------------------------
        # GAME SUMMARY
        # ---------------------------------------------------------------
        prizes_by_date = df_prizes.groupby("Date")["PaidOut"].sum().to_dict()

        summary_rows = []
        for game_date, players in players_per_date.items():
            if isinstance(game_date, datetime.date):
                fees = players * self.GAME_FEE
                prize_spend = prizes_by_date.get(game_date, 0.0)
                surplus = fees - prize_spend

                summary_rows.append({
                    "GameDate": game_date,
                    "Players": players,
                    "GameFees": fees,
                    "PrizeToPlayers": prize_spend,
                    "Surplus": surplus,
                    "Category": "SURPLUS",
                })

        df_summary = pd.DataFrame(summary_rows)

        return FinanceResult(df_all, balances, kitty_total, df_summary)
