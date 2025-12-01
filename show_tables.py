from marauders.database import Database

db = Database("marauders.db")

df = db.read_sql("SELECT name FROM sqlite_master WHERE type='table'")
print("TABLES:\n", df)
