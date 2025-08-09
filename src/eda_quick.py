# src/eda_quick.py
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

# --- Paths independentes do working dir ---
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
PROC_DIR = DATA_DIR / "processed"
SAMP_DIR = DATA_DIR / "sample"

# --- Lê dados: prioriza processed/, senão usa sample/ ---
files = list(PROC_DIR.glob("*.parquet"))
if not files:
    print("[WARN] Nenhum dado em processed/, usando sample/")
    files = list(SAMP_DIR.glob("*.parquet"))
if not files:
    raise FileNotFoundError("Nenhum .parquet em processed/ ou sample/.")

print(f"[INFO] Lendo {len(files)} arquivo(s)...")
df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)

# Garante datetime
if "date" in df.columns and not pd.api.types.is_datetime64_any_dtype(df["date"]):
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

# --- KPIs mensais ---
df["yyyymm"] = df["date"].dt.to_period("M").astype(str)
kpi = df.groupby("yyyymm", as_index=False).agg(
    revenue=("revenue", "sum"),
    orders=("orders", "sum"),
)
kpi["ticket_medio"] = kpi["revenue"] / kpi["orders"].clip(lower=1)

print("\n[KPIs - últimos 6 meses]")
print(kpi.tail(6))

# --- Detecção de outliers (IQR) ---
q1 = kpi["revenue"].quantile(0.25)
q3 = kpi["revenue"].quantile(0.75)
iqr = q3 - q1
limite_sup = q3 + 1.5 * iqr

outliers = kpi[kpi["revenue"] > limite_sup].copy()
meses_zero = kpi[kpi["revenue"].fillna(0) == 0].copy()

print("\n[OUTLIERS] Meses com receita acima do padrão (IQR):")
print(outliers if not outliers.empty else "Nenhum.")

print("\n[ALERTA] Meses com receita zero:")
print(meses_zero if not meses_zero.empty else "Nenhum.")

# (Opcional) Salva resultado para auditoria rápida
OUT_DIR = BASE_DIR / "data" / "audit"
OUT_DIR.mkdir(parents=True, exist_ok=True)
kpi.to_csv(OUT_DIR / "kpi_mensal.csv", index=False)
outliers.to_csv(OUT_DIR / "kpi_outliers.csv", index=False)
meses_zero.to_csv(OUT_DIR / "kpi_receita_zero.csv", index=False)
print(f"\n[OK] Arquivos salvos em: {OUT_DIR}")

# --- Gráfico Receita x Pedidos ---
fig, ax1 = plt.subplots(figsize=(11, 5))
ax1.set_xlabel("Mês")
ax1.set_ylabel("Receita", color="tab:blue")
ax1.plot(kpi["yyyymm"], kpi["revenue"], marker="o", label="Receita", color="tab:blue")
ax1.tick_params(axis="y", labelcolor="tab:blue")
plt.xticks(rotation=45)

ax2 = ax1.twinx()
ax2.set_ylabel("Pedidos", color="tab:orange")
ax2.plot(kpi["yyyymm"], kpi["orders"], marker="x", label="Pedidos", color="tab:orange")
ax2.tick_params(axis="y", labelcolor="tab:orange")

plt.title("Receita e Pedidos por Mês")
plt.tight_layout()
plt.show()
