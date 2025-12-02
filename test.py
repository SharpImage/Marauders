from marauders.database import Database

db = Database("marauders.db")

df = db.read_sql("SELECT * FROM ExcludedGames")
print(df)
