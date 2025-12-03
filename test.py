from marauders.database import Database
import pandas as pd

db = Database("marauders.db")
conn = db.connect()

game = "2025-12-02"

print("\n--- Scores ---")
print(pd.read_sql("SELECT Player_Name FROM Scores WHERE Game_Date = ?", conn, params=[game]))

print("\n--- HandicapHistory ---")
print(pd.read_sql("SELECT Player, PreviousHandicap, NewHandicap FROM HandicapHistory WHERE GameDate = ?", conn, params=[game]))

print("\n--- PrizePayouts ---")
print(pd.read_sql("SELECT * FROM PrizePayouts WHERE GameDate = ?", conn, params=[game]))
