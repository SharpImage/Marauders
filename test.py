import pandas as pd

df = pd.read_excel("yourfile.xlsx", sheet_name="Scores")
print(df.columns.tolist())
