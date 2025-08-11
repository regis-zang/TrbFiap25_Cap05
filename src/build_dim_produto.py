#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
build_dim_produto.py

Gera a dimensão Produto a partir de uma base tratada.
- Cria produto_id (sequencial OU hash).
- Classifica categoria por regras quando a coluna não existir.
- Preserva IDs de dimensão anterior (se informada).
- Exporta dim_produto.parquet e dim_produto.csv.
- Exporta relatório dim_produto_sem_categoria.csv para revisão.

MODO 1 — Terminal (recomendado):
  python build_dim_produto.py ^
    --input I:/Projetos_Python/Fiap_F5/Fiap_F5/data/processed/vendas_completo.parquet ^
    --col-nome produto ^
    --col-categoria categoriaprod ^
    --out-dir I:/Projetos_Python/Fiap_F5/Fiap_F5/data/dimensoes ^
    --method sequencial

MODO 2 — Spyder/IPython (sem argumentos):
  - Ajuste DEFAULT_INPUT / DEFAULT_OUT_DIR abaixo
  - Execute o arquivo (Run File)
"""

import argparse
import os
import sys
from hashlib import md5
import pandas as pd

# -----------------------
# Defaults para rodar no Spyder (sem argumentos)
# -----------------------
DEFAULT_INPUT = r"I:/Projetos_Python/Fiap_F5/Fiap_F5/data/processed/vendas_completo.parquet"
DEFAULT_OUT_DIR = r"I:/Projetos_Python/Fiap_F5/Fiap_F5/data/dimensoes"
DEFAULT_COL_NOME = "produto"            # sua coluna no parquet
DEFAULT_COL_CATEGORIA = "categoriaprod" # sua coluna no parquet (ou None se não existir)
DEFAULT_EXISTING_DIM = None             # ex.: r"I:/.../dim_produto.parquet"
DEFAULT_METHOD = "sequencial"           # ou "hash"

try:
    from unidecode import unidecode
except Exception:
    print("[ERRO] Biblioteca 'Unidecode' não encontrada. Instale com: pip install Unidecode", file=sys.stderr)
    raise

# -----------------------
# Configuração de regras (para quando não houver coluna de categoria)
# -----------------------
CATEGORIAS_VALIDAS = {
    "acessorio": "Acessório",
    "alimentacao": "Alimentação",
    "bebedouros_comedouros": "Bebedouros e Comedouros",
    "brinquedo": "Brinquedo",
    "higiene": "Higiene e Limpeza",
    "medicamento": "Medicamento",
    "petisco": "Petisco",
}

REGRAS = {
    "medicamento": [
        "bravecto", "antipulga", "vermif", "vitamina", "suplemento", "condroitina", "omega", "ômega"
    ],
    "acessorio": [
        "bandana", "cama ", "almofada", "roupa ", "meia", "pote ", "coleira", "peitoral", "ninho", "arranhador"
    ],
    "bebedouros_comedouros": [
        "bebedouro", "comedouro", "alimentador", "automatico", "automático"
    ],
    "petisco": [
        "biscoito", "petisco", "snack", "sache", "sachê", "sticks", "bifinho", "cookie"
    ],
    "brinquedo": [
        "bola", "mordedor", "brinquedo", "penas"
    ],
    "higiene": [
        "shampoo", "banho", "tosa", "rasqueadeira", "higiene", "limpeza", "tapete higienico", "tapete higiênico"
    ],
    "alimentacao": [
        "racao", "ração", "lata", "pate", "patê", "granulado alimentar"
    ],
}

# -----------------------
# Funções utilitárias
# -----------------------
def norm(s: str) -> str:
    s = unidecode(str(s or "")).lower().strip()
    return " ".join(s.split())

def classificar_categoria(nome_produto: str) -> str:
    n = norm(nome_produto)
    for cat_key, palavras in REGRAS.items():
        for p in palavras:
            if p in n:
                return CATEGORIAS_VALIDAS[cat_key]
    return "#"  # pendente de revisão

def carregar_df_caminho(path: str, usecols=None) -> pd.DataFrame:
    ext = os.path.splitext(path.lower())[1]
    if ext == ".parquet":
        return pd.read_parquet(path, columns=usecols)
    if ext == ".csv":
        return pd.read_csv(path, usecols=usecols, encoding="utf-8-sig")
    raise ValueError(f"Formato não suportado: {path}")

def gerar_ids_hash(nomes_norm: pd.Series) -> pd.Series:
    return nomes_norm.map(lambda s: "PROD" + md5(s.encode()).hexdigest()[:8].upper())

def gerar_ids_sequenciais(qtd: int, start_from: int = 1) -> list:
    return ["PROD" + f"{i:03d}" for i in range(start_from, start_from + qtd)]

def construir_dim(
    df_base: pd.DataFrame,
    col_nome: str,
    col_categoria: str | None,
    metodo: str,
    df_dim_existente: pd.DataFrame | None = None,
) -> pd.DataFrame:
    # Base única e normalizada
    cols = [col_nome]
    if col_categoria and col_categoria in df_base.columns:
        cols.append(col_categoria)

    base = (
        df_base[cols]
        .dropna(subset=[col_nome])
        .drop_duplicates(subset=[col_nome])
        .rename(columns={col_nome: "produto_nome"})
        .copy()
    )
    base["produto_nome_normalizado"] = base["produto_nome"].map(norm)

    # Categoria: usa a coluna original se existir, senão aplica regras
    if col_categoria and col_categoria in df_base.columns:
        cat = (
            df_base[[col_nome, col_categoria]]
            .dropna(subset=[col_nome])
            .drop_duplicates(subset=[col_nome], keep="last")
            .rename(columns={col_nome: "produto_nome", col_categoria: "categoria"})
        )
        base = base.merge(cat, on="produto_nome", how="left")
    else:
        base["categoria"] = base["produto_nome"].map(classificar_categoria)

    # Preservar IDs já existentes, se fornecidos
    if df_dim_existente is not None and "produto_id" in df_dim_existente.columns:
        dim_old = df_dim_existente[["produto_id", "produto_nome", "produto_nome_normalizado"]].copy()
        base = base.merge(dim_old, on=["produto_nome", "produto_nome_normalizado"], how="left")

    # Garante que a coluna produto_id exista
    if "produto_id" not in base.columns:
        base["produto_id"] = pd.NA

    # Atribuir IDs faltantes
    faltantes = base["produto_id"].isna()
    if metodo == "hash":
        base.loc[faltantes, "produto_id"] = gerar_ids_hash(base.loc[faltantes, "produto_nome_normalizado"])
    elif metodo == "sequencial":
        start = 1
        if df_dim_existente is not None and "produto_id" in df_dim_existente.columns:
            prev = df_dim_existente["produto_id"].dropna().astype(str)
            prev_num = prev.str.extract(r"PROD(\d+)", expand=False).dropna().astype(int)
            if len(prev_num) > 0:
                start = int(prev_num.max()) + 1
        novos_qtd = int(faltantes.sum())
        base.loc[faltantes, "produto_id"] = gerar_ids_sequenciais(novos_qtd, start_from=start)
    else:
        raise ValueError("method deve ser 'sequencial' ou 'hash'.")

    base["ativo"] = True

    # Ordenação final previsível
    dim = base.sort_values(["produto_nome_normalizado", "produto_id"]).reset_index(drop=True)
    return dim[["produto_id", "produto_nome", "produto_nome_normalizado", "categoria", "ativo"]]

def executar(input_path, out_dir, col_nome, col_categoria, existing_dim_path, method):
    os.makedirs(out_dir, exist_ok=True)

    usecols = [col_nome] + ([col_categoria] if col_categoria else [])
    df_base = carregar_df_caminho(input_path, usecols=usecols)

    df_dim_exist = None
    if existing_dim_path:
        df_dim_exist = carregar_df_caminho(existing_dim_path)

    dim = construir_dim(
        df_base=df_base,
        col_nome=col_nome,
        col_categoria=col_categoria,
        metodo=method,
        df_dim_existente=df_dim_exist,
    )

    out_parquet = os.path.join(out_dir, "dim_produto.parquet")
    out_csv = os.path.join(out_dir, "dim_produto.csv")
    dim.to_parquet(out_parquet, index=False)
    dim.to_csv(out_csv, index=False, encoding="utf-8-sig")

    pend = dim[dim["categoria"].fillna("#") == "#"].copy()
    pend_path = os.path.join(out_dir, "dim_produto_sem_categoria.csv")
    pend.to_csv(pend_path, index=False, encoding="utf-8-sig")

    print(f"[OK] Dimensão salva:\n - {out_parquet}\n - {out_csv}")
    if len(pend) > 0:
        print(f"[ATENÇÃO] {len(pend)} item(ns) sem categoria. Revise {pend_path}")
    else:
        print("[OK] Todos os itens possuem categoria.")

def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="Gera dimensão Produto a partir de uma base tratada.")
    ap.add_argument("--input", required=True, help="Arquivo de entrada (parquet ou csv) com os produtos.")
    ap.add_argument("--col-nome", default="produto_nome", help="Nome da coluna com o nome/descrição do produto.")
    ap.add_argument("--col-categoria", default=None, help="Nome da coluna de categoria (opcional).")
    ap.add_argument("--existing-dim", default=None, help="Dimensão existente para preservar IDs (parquet/csv).")
    ap.add_argument("--out-dir", required=True, help="Diretório de saída.")
    ap.add_argument("--method", choices=["sequencial", "hash"], default="sequencial",
                    help="Método de geração do ID.")
    return ap.parse_args(argv)

def running_in_ipython():
    try:
        get_ipython  # Spyder/Jupyter
        return True
    except Exception:
        return False

def main():
    # Caso sem argumentos (Spyder/Runfile) OU rodando em IPython, usa defaults
    if len(sys.argv) == 1 or running_in_ipython():
        print("[INFO] Execução sem argumentos detectada. Usando DEFAULTS no topo do arquivo.")
        executar(
            input_path=DEFAULT_INPUT,
            out_dir=DEFAULT_OUT_DIR,
            col_nome=DEFAULT_COL_NOME,
            col_categoria=DEFAULT_COL_CATEGORIA,
            existing_dim_path=DEFAULT_EXISTING_DIM,
            method=DEFAULT_METHOD,
        )
        return

    # Caso contrário, parse normal de argumentos CLI
    args = parse_args()
    executar(
        input_path=args.input,
        out_dir=args.out_dir,
        col_nome=args.col_nome,
        col_categoria=args.col_categoria,
        existing_dim_path=args.existing_dim,
        method=args.method,
    )

if __name__ == "__main__":
    main()
