import pandas as pd
from pathlib import Path

# caminho para o parquet combinado ou uma partição
PROC_DIR = Path("I:/Projetos_Python/Fiap_F5/Fiap_F5/data/processed")

# exemplo: ler uma partição específica
df_part = pd.read_parquet(PROC_DIR / "part_001.parquet")
print(df_part.head())

# ou ler todos os parquet e concatenar
files = list(PROC_DIR.glob("part_*.parquet"))
df_all = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
print(df_all.head())
print(df_all.info())

# se tiver um único arquivo 'vendas_completo.parquet'
# df_all = pd.read_parquet(PROC_DIR / "vendas_completo.parquet")
