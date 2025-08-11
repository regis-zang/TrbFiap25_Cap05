#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import pandas as pd
from unidecode import unidecode

# --- paths (ajuste conforme sua árvore) ---
BASE_DIR  = r"I:/Projetos_Python/Fiap_F5/Fiap_F5"
FACT_PATH = os.path.join(BASE_DIR, "data/processed/vendas_completo.parquet")
DIM_DIR   = os.path.join(BASE_DIR, "data/dimensoes")
OUT_DIR   = os.path.join(BASE_DIR, "data/processed")

DIM_PROD_PATH = os.path.join(DIM_DIR, "dim_produto.csv")
DIM_CDS_PATH  = os.path.join(DIM_DIR, "dim_centro_distribuicao.csv")
DIM_FRM_PATH  = os.path.join(DIM_DIR, "dim_formapagto.csv")
DIM_VEND_PATH = os.path.join(DIM_DIR, "dim_responsavelpedido.csv")

# --- colunas na sua base ---
COL_PROD_FATO = "produto"
COL_CDS_FATO  = "centro_distribuicao"
COL_FRM_FATO  = "formapagto"
COL_VEND_FATO = "responsavelpedido"

def norm(s: str) -> str:
    s = unidecode(str(s or "")).lower().strip()
    return " ".join(s.split())

def load_parquet_or_csv(path):
    ext = os.path.splitext(path.lower())[1]
    if ext == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path, encoding="utf-8-sig")

def safe_merge_left(fato: pd.DataFrame,
                    dim: pd.DataFrame,
                    left_on: str,
                    right_on: str,
                    id_col: str,
                    keep_cols: list[str]):
    """
    Left join que evita colisões:
    - Seleciona somente right_on + keep_cols.
    - Renomeia em 'dim' qualquer coluna de keep_cols que já exista em fato: col -> col+'_dim'
    - Retorna (df_merged, df_nao_casados[left_on])
    """
    if right_on not in dim.columns:
        raise KeyError(f"Coluna de junção '{right_on}' não encontrada na dimensão.")

    # lista final a trazer (garante o id_col)
    cols = list(dict.fromkeys([id_col] + keep_cols))  # sem duplicatas e garantindo id_col primeiro
    cols = [c for c in cols if c in dim.columns]      # tolera CSVs mais enxutos

    # subset da dimensão
    dim_subset = dim[[right_on] + cols].copy()

    # renomeia conflitos (se alguma coluna de 'cols' já existir no fato)
    rename_map = {}
    for c in cols:
        if c in fato.columns and c != id_col:
            rename_map[c] = f"{c}_dim"
    if rename_map:
        dim_subset.rename(columns=rename_map, inplace=True)
        # atualiza nomes efetivos das colunas mantidas
        cols = [rename_map.get(c, c) for c in cols]

    before = len(fato)
    merged = fato.merge(dim_subset, left_on=left_on, right_on=right_on, how="left")
    assert len(merged) == before, "Join alterou o número de linhas — verifique chaves/chaves duplicadas."

    # não-casados (onde id_col ficou NaN)
    id_col_eff = rename_map.get(id_col, id_col)
    not_matched = merged[merged[id_col_eff].isna()][[left_on]].drop_duplicates()

    # remove a coluna de junção da dimensão
    merged.drop(columns=[right_on], inplace=True, errors="ignore")
    return merged, not_matched

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # 1) fato
    fato = load_parquet_or_csv(FACT_PATH)

    # 2) normalizações auxiliares para join por texto
    if COL_PROD_FATO in fato.columns:
        fato["__prod_norm"] = fato[COL_PROD_FATO].map(norm)
    if COL_CDS_FATO in fato.columns:
        fato["__cds_norm"]  = fato[COL_CDS_FATO].map(lambda x: str(x).strip())
    if COL_FRM_FATO in fato.columns:
        fato["__frm_norm"]  = fato[COL_FRM_FATO].map(lambda x: str(x).strip())
    if COL_VEND_FATO in fato.columns:
        fato["__vend_norm"] = fato[COL_VEND_FATO].map(lambda x: str(x).strip())

    reports = {}

    # 3) Produto
    if os.path.exists(DIM_PROD_PATH) and "__prod_norm" in fato.columns:
        dim_prod = pd.read_csv(DIM_PROD_PATH, encoding="utf-8-sig")
        if "produto_nome_normalizado" not in dim_prod.columns:
            dim_prod["produto_nome_normalizado"] = dim_prod["produto_nome"].map(norm)

        # Traga o essencial; evite 'ativo' para não colidir
        fato, not_matched = safe_merge_left(
            fato=fato,
            dim=dim_prod,
            left_on="__prod_norm",
            right_on="produto_nome_normalizado",
            id_col="produto_id",
            keep_cols=["produto_id", "produto_nome", "categoria"]  # será renomeado p/ *_dim se já existir
        )
        reports["nao_casados_produto.csv"] = not_matched

    # 4) Centro de distribuição
    if os.path.exists(DIM_CDS_PATH) and "__cds_norm" in fato.columns:
        dim_cds = pd.read_csv(DIM_CDS_PATH, encoding="utf-8-sig")
        if "centro_distribuicao_normalizado" not in dim_cds.columns:
            dim_cds["centro_distribuicao_normalizado"] = dim_cds["centro_distribuicao"].map(lambda x: str(x).strip())

        fato, not_matched = safe_merge_left(
            fato=fato,
            dim=dim_cds,
            left_on="__cds_norm",
            right_on="centro_distribuicao_normalizado",
            id_col="centro_id",
            keep_cols=["centro_id", "centro_distribuicao"]  # evita 'ativo'
        )
        reports["nao_casados_cds.csv"] = not_matched

    # 5) Forma de pagamento
    if os.path.exists(DIM_FRM_PATH) and "__frm_norm" in fato.columns:
        dim_frm = pd.read_csv(DIM_FRM_PATH, encoding="utf-8-sig")
        if "forma_pagamento_normalizado" not in dim_frm.columns:
            dim_frm["forma_pagamento_normalizado"] = dim_frm["forma_pagamento"].map(lambda x: str(x).strip())

        fato, not_matched = safe_merge_left(
            fato=fato,
            dim=dim_frm,
            left_on="__frm_norm",
            right_on="forma_pagamento_normalizado",
            id_col="formapagto_id",
            keep_cols=["formapagto_id", "forma_pagamento"]
        )
        reports["nao_casados_formapagto.csv"] = not_matched

    # 6) Responsável Pedido
    if os.path.exists(DIM_VEND_PATH) and "__vend_norm" in fato.columns:
        dim_vend = pd.read_csv(DIM_VEND_PATH, encoding="utf-8-sig")
        if "responsavel_pedido_normalizado" not in dim_vend.columns:
            dim_vend["responsavel_pedido_normalizado"] = dim_vend["responsavel_pedido"].map(lambda x: str(x).strip())

        fato, not_matched = safe_merge_left(
            fato=fato,
            dim=dim_vend,
            left_on="__vend_norm",
            right_on="responsavel_pedido_normalizado",
            id_col="responsavelpedido_id",
            keep_cols=["responsavelpedido_id", "responsavel_pedido"]
        )
        reports["nao_casados_responsavelpedido.csv"] = not_matched

    # 7) limpeza de colunas auxiliares
    fato.drop(columns=[c for c in ["__prod_norm","__cds_norm","__frm_norm","__vend_norm"] if c in fato.columns],
              inplace=True, errors="ignore")

    # 8) saída
    out_parquet = os.path.join(OUT_DIR, "vendas_completo_enriquecido.parquet")
    out_csv     = os.path.join(OUT_DIR, "vendas_completo_enriquecido.csv")
    fato.to_parquet(out_parquet, index=False)
    fato.to_csv(out_csv, index=False, encoding="utf-8-sig")

    # 9) relatórios de não-casados
    for fname, dfrep in reports.items():
        dfrep_path = os.path.join(OUT_DIR, fname)
        dfrep.to_csv(dfrep_path, index=False, encoding="utf-8-sig")

    print("[OK] Fato enriquecido salvo:")
    print(" -", out_parquet)
    print(" -", out_csv)
    if reports:
        print("[AVISO] Relatórios de não-casados gerados em:", OUT_DIR)
        for fn in reports:
            print("  *", fn)

if __name__ == "__main__":
    main()
