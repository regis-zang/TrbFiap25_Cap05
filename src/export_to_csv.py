from pathlib import Path
import pandas as pd

# Paths independentes do working dir
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
PROC_DIR = DATA_DIR / "processed"
OUT_DIR = DATA_DIR / "exports"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Lê todos os parquets processados
files = list(PROC_DIR.glob("*.parquet"))
if not files:
    raise FileNotFoundError("Nenhum parquet encontrado em data/processed/")

print(f"[INFO] Lendo {len(files)} arquivo(s) parquet…")
df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)

# Garante datetime e colunas esperadas
if "date" in df.columns and not pd.api.types.is_datetime64_any_dtype(df["date"]):
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
cols = [c for c in ["date","order_id","sku","category","channel","orders","revenue"] if c in df.columns]
df = df[cols].copy()

# Formata numéricos no padrão ponto decimal (Power BI/SAC entendem bem)
df["orders"] = pd.to_numeric(df["orders"], errors="coerce").fillna(0).astype("Int64")
df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce")

# ---------- Export 1: KPIs mensais ----------
df["yyyymm"] = df["date"].dt.to_period("M").astype(str)
kpi = (
    df.groupby("yyyymm", as_index=False)
      .agg(revenue=("revenue","sum"), orders=("orders","sum"))
)
kpi["ticket_medio"] = kpi["revenue"] / kpi["orders"].clip(lower=1)

kpi_path = OUT_DIR / "kpi_mensal.csv"
kpi.to_csv(kpi_path, index=False, encoding="utf-8-sig")
print(f"[OK] KPI mensal exportado: {kpi_path}")

# ---------- Export 2: Transações completas ----------
# Se ficar muito grande, exportar por ano
df["year"] = df["date"].dt.year

# Troque para False se quiser tudo num único arquivo
SPLIT_BY_YEAR = True

if SPLIT_BY_YEAR and "year" in df.columns:
    for y, part in df.groupby("year", dropna=True):
        out = OUT_DIR / f"vendas_{int(y)}.csv"
        (part.drop(columns=["year","yyyymm"], errors="ignore")
             .to_csv(out, index=False, encoding="utf-8-sig"))
        print(f"[OK] Exportado: {out} ({len(part)} linhas)")
else:
    full_path = OUT_DIR / "vendas_full.csv"
    df.drop(columns=["year","yyyymm"], errors="ignore").to_csv(full_path, index=False, encoding="utf-8-sig")
    print(f"[OK] Transações exportadas: {full_path} ({len(df)} linhas)")
