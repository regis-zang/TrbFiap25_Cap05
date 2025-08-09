# src/prepare_data.py
from pathlib import Path
import pandas as pd

# --- Paths independentes do working dir ---
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
RAW = Path("I:/Projetos_Python/Fiap_F5/Fiap_F5/data/raw/vendas.csv")
PROC = DATA_DIR / "processed"
SAMP = DATA_DIR / "sample"
PROC.mkdir(parents=True, exist_ok=True)
SAMP.mkdir(parents=True, exist_ok=True)

ENCODING = "latin1"  # detectado
CHUNKSIZE = 500_000  # ajuste se precisar

# mapeamento real do seu CSV -> nomes padrão do projeto
COL_MAP = {
    "cod_pedido": "order_id",
    "data": "date",
    "produto": "sku",
    "categoriaprod": "category",
    "formapagto": "channel",
    # receita vamos calcular mais abaixo (valor_total_bruto ou valor*quantidade)
    # orders será 1 por linha
}

# colunas que precisamos ler do arquivo
USECOLS = [
    "cod_pedido", "data", "produto", "categoriaprod", "formapagto",
    "valor_total_bruto", "valor", "quantidade"
]

def process_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    # renomear principais
    chunk = chunk.rename(columns=COL_MAP)

    # datas
    chunk["date"] = pd.to_datetime(chunk["date"], dayfirst=True, errors="coerce")

    # Normaliza valores numéricos (remove milhar, troca vírgula por ponto)
    def fix_number(col):
        if col in chunk.columns:
            chunk[col] = (
                chunk[col].astype(str)
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
            )
            chunk[col] = pd.to_numeric(chunk[col], errors="coerce")

    fix_number("valor_total_bruto")
    fix_number("valor")
    fix_number("quantidade")

    # calcula receita usando valor_total_bruto ou fallback valor*quantidade
    chunk["revenue"] = chunk["valor_total_bruto"]
    fallback = chunk["valor"] * chunk["quantidade"]
    chunk["revenue"] = chunk["revenue"].fillna(fallback)
    chunk.loc[chunk["revenue"] == 0, "revenue"] = fallback

    # orders = 1 por linha
    chunk["orders"] = 1

    # tipagem leve
    if "category" in chunk.columns:
        chunk["category"] = chunk["category"].astype("category")
    if "channel" in chunk.columns:
        chunk["channel"] = chunk["channel"].astype("category")

    # colunas finais
    final_cols = ["date", "order_id", "sku", "category", "channel", "orders", "revenue"]
    final_cols = [c for c in final_cols if c in chunk.columns]
    chunk = chunk[final_cols]

    # features de ano/mês
    if "date" in chunk.columns:
        chunk["year"] = chunk["date"].dt.year.astype("Int16")
        chunk["month"] = chunk["date"].dt.month.astype("Int8")

    return chunk
def main():
    # leitura em chunks com auto-separador
    chunks = pd.read_csv(
        RAW,
        encoding=ENCODING,
        sep=None,
        engine="python",
        usecols=[c for c in USECOLS if c],  # garante apenas os existentes
        chunksize=CHUNKSIZE,
        on_bad_lines="skip",
    )

    sample_parts = []
    for i, chunk in enumerate(chunks, 1):
        chunk = process_chunk(chunk)

        out_path = PROC / f"part_{i:03d}.parquet"
        chunk.to_parquet(out_path, index=False)

        # amostra (até 10k linhas por chunk)
        if len(chunk) > 0:
            sample_parts.append(chunk.sample(min(10_000, len(chunk)), random_state=42))

    if sample_parts:
        sample_df = pd.concat(sample_parts, ignore_index=True)
        sample_df.to_csv(SAMP / "vendas_sample.csv", index=False)
        sample_df.to_parquet(SAMP / "vendas_sample.parquet", index=False)

    print("[OK] Processamento concluído.")
    print(f" - Parquets: {PROC}")
    print(f" - Amostras: {SAMP}")

if __name__ == "__main__":
    main()
