from pathlib import Path
import pandas as pd

# Sobe 1 nível a partir de src
BASE_DIR = Path(__file__).resolve().parents[1]

# Caminhos corretos
parquet_path = BASE_DIR / "data" / "processed_enriched" / "dataset_enriquecido.parquet"
csv_path = BASE_DIR / "data" / "processed_enriquecido" / "dataset_enriquecido_preview.csv"

# Leitura do parquet
df = pd.read_parquet(parquet_path)

# Exporta para CSV
df.to_csv(csv_path, index=False, encoding="utf-8-sig")

print(f"[OK] CSV gerado em: {csv_path}")
print("\nEstrutura da base:")
print(df.dtypes)
print("\nAmostra dos dados:")
print(df.head(10))
