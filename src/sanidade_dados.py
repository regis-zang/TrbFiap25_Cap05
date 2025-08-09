from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
df = pd.read_parquet(BASE_DIR/"data/processed/part_001.parquet")

print("Tipos:\n", df.dtypes)
print("\nNulos por coluna:\n", df.isna().sum())

# meses com receita = 0 ou NaN
df["yyyymm"] = df["date"].dt.to_period("M").astype(str)
k = df.groupby("yyyymm").agg(revenue=("revenue","sum"), orders=("orders","sum")).reset_index()
print("\nMeses com receita zerada:")
print(k[k["revenue"].fillna(0)==0])

# Amostra de linhas onde revenue está nulo/zero
bad = df[(df["revenue"].isna()) | (df["revenue"]==0)]
print("\nAmostra com revenue nulo/zero:")
print(bad.head(10))
