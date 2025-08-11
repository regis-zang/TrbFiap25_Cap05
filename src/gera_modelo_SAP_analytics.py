from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
PROC_DIR = DATA_DIR / "processed"
EXPORT_DIR = DATA_DIR / "exports_sac"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# Lê todos os parquets processados
files = list(PROC_DIR.glob("*.parquet"))
if not files:
    raise FileNotFoundError("Nenhum parquet encontrado em data/processed/")

df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)

# Garante datetime
df["date"] = pd.to_datetime(df["date"], errors="coerce")

# DIM PRODUTO
dim_produto = df[["sku", "category"]].drop_duplicates().rename(columns={
    "sku": "ProdutoID",
    "category": "CategoriaID"
})
dim_produto.to_csv(EXPORT_DIR / "dim_produto.csv", index=False, encoding="utf-8-sig")

# DIM CATEGORIA
dim_categoria = df[["category"]].drop_duplicates().rename(columns={
    "category": "CategoriaID"
})
dim_categoria["CategoriaDescricao"] = dim_categoria["CategoriaID"]
dim_categoria.to_csv(EXPORT_DIR / "dim_categoria.csv", index=False, encoding="utf-8-sig")

# DIM CANAL
dim_canal = df[["channel"]].drop_duplicates().rename(columns={
    "channel": "CanalID"
})
dim_canal["CanalDescricao"] = dim_canal["CanalID"]
dim_canal.to_csv(EXPORT_DIR / "dim_canal.csv", index=False, encoding="utf-8-sig")

# DIM TEMPO
dim_tempo = df[["date"]].drop_duplicates().rename(columns={"date": "Data"})
dim_tempo["Ano"] = dim_tempo["Data"].dt.year
dim_tempo["Mes"] = dim_tempo["Data"].dt.month
dim_tempo["AnoMes"] = dim_tempo["Data"].dt.strftime("%Y-%m")
dim_tempo["MesNome"] = dim_tempo["Data"].dt.strftime("%B")
dim_tempo["Trimestre"] = dim_tempo["Data"].dt.quarter
dim_tempo.to_csv(EXPORT_DIR / "dim_tempo.csv", index=False, encoding="utf-8-sig")

# FATO VENDAS
fato_vendas = df[["date", "sku", "category", "channel", "orders", "revenue"]].rename(columns={
    "date": "Data",
    "sku": "ProdutoID",
    "category": "CategoriaID",
    "channel": "CanalID",
    "orders": "Pedidos",
    "revenue": "Receita"
})
fato_vendas.to_csv(EXPORT_DIR / "fato_vendas.csv", index=False, encoding="utf-8-sig")

print(f"[OK] Arquivos gerados em: {EXPORT_DIR}")
