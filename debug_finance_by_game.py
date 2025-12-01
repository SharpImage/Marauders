# debug_finance_by_game.py
#
# Shows clean per-game financial information:
#   - Whether the game is excluded
#   - Number of players
#   - Total game fees
#   - Total prizes to players
#   - Surplus
#
# This is the exact audit required to validate kitty behaviour.

from marauders.database import Database
import pandas as pd

DB_PATH = "marauders.db"
GAME_FEE = 2.0


def main():
    db = Database(DB_PATH)

    # -------------------------------------------------------
    # Load excluded games
    # -------------------------------------------------------
    try:
        excluded_df = db.read_sql("SELECT GameDate FROM ExcludedGames")
        excluded_df["GameDate"] = pd.to_datetime(excluded_df["GameDate"]).dt.date
        excluded = set(excluded_df["GameDate"].tolist())
    except:
        excluded = set()

    print("Excluded games:", excluded)

    # -------------------------------------------------------
    # Load scores (players per date)
    # -------------------------------------------------------
    df_scores = db.read_sql("""
        SELECT Game_Date, Player_Name
        FROM Scores
    """)

    df_scores["GameDate"] = pd.to_datetime(df_scores["Game_Date"]).dt.date

    players_per_game = (
        df_scores
        .groupby("GameDate")["Player_Name"]
        .count()
        .reset_index()
        .rename(columns={"Player_Name": "Players"})
    )

    # -------------------------------------------------------
    # Compute game fees per date
    # -------------------------------------------------------
    players_per_game["Included"] = ~players_per_game["GameDate"].isin(excluded)
    players_per_game["GameFees"] = players_per_game["Players"] * GAME_FEE
    players_per_game.loc[~players_per_game["Included"], "GameFees"] = 0.0

    # -------------------------------------------------------
    # Load prizes (per date)
    # -------------------------------------------------------
    try:
        df_prizes = db.read_sql("""
            SELECT GameDate, Player, Amount
            FROM PrizePayouts
            WHERE Player <> 'KITTY'
        """)
    except:
        df_prizes = pd.DataFrame(columns=["GameDate", "Player", "Amount"])

    if not df_prizes.empty:
        df_prizes["GameDate"] = pd.to_datetime(df_prizes["GameDate"]).dt.date
        prizes_per_game = (
            df_prizes.groupby("GameDate")["Amount"]
            .sum()
            .reset_index()
            .rename(columns={"Amount": "PrizeToPlayers"})
        )
    else:
        prizes_per_game = pd.DataFrame(columns=["GameDate", "PrizeToPlayers"])

    # Zero prizes for excluded games
    prizes_per_game["PrizeToPlayers"] = prizes_per_game["PrizeToPlayers"].astype(float)

    # -------------------------------------------------------
    # Merge
    # -------------------------------------------------------
    df = players_per_game.merge(prizes_per_game, on="GameDate", how="left")
    df["PrizeToPlayers"] = df["PrizeToPlayers"].fillna(0.0)

    # Zero prizes if game excluded
    df.loc[~df["Included"], "PrizeToPlayers"] = 0.0

    # -------------------------------------------------------
    # Surplus = GameFees – PrizeToPlayers
    # -------------------------------------------------------
    df["Surplus"] = df["GameFees"] - df["PrizeToPlayers"]

    # -------------------------------------------------------
    # Sort and display
    # -------------------------------------------------------
    df = df.sort_values("GameDate").reset_index(drop=True)

    pd.set_option("display.float_format", lambda x: f"{x:,.2f}")
    print("\nPER-GAME FINANCE AUDIT:\n")
    print(df.to_string(index=False))

    print("\nColumns:")
    print("  GameDate         = date of game")
    print("  Included         = False means excluded game (ignored)")
    print("  Players          = number of scores entered")
    print("  GameFees         = Players × £2 (zero if excluded)")
    print("  PrizeToPlayers   = sum of prize payouts")
    print("  Surplus          = GameFees − PrizeToPlayers\n")


if __name__ == "__main__":
    main()
