#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
build_dim_centro_distribuicao.py

Gera a dimensão Centro de Distribuição a partir de uma lista/base.
Cria centro_id (sequencial CDS001, CDS002...).
Exporta dim_centro_distribuicao.parquet e dim_centro_distribuicao.csv.
"""

import pandas as pd
import os

# --- Configurações para rodar no Spyder ---
DEFAULT_CDS_LIST = [
    "Gold Beach",
    "Grãos Blue",
    "Papa Léguas",
    "Rapid Pink",
    "Tree True"
]
DEFAULT_OUT_DIR = r"I:/Projetos_Python/Fiap_F5/Fiap_F5/data/dimensoes"

def gerar_dim_cds(lista_cds):
    df = pd.DataFrame({"centro_distribuicao": lista_cds})
    df = df.dropna().drop_duplicates().reset_index(drop=True)
    df["centro_distribuicao_normalizado"] = df["centro_distribuicao"].str.strip()
    df["centro_id"] = ["CDS" + f"{i+1:03d}" for i in range(len(df))]
    df["ativo"] = True
    return df[["centro_id", "centro_distribuicao", "centro_distribuicao_normalizado", "ativo"]]

def main():
    os.makedirs(DEFAULT_OUT_DIR, exist_ok=True)
    dim_cds = gerar_dim_cds(DEFAULT_CDS_LIST)

    out_parquet = os.path.join(DEFAULT_OUT_DIR, "dim_centro_distribuicao.parquet")
    out_csv = os.path.join(DEFAULT_OUT_DIR, "dim_centro_distribuicao.csv")

    dim_cds.to_parquet(out_parquet, index=False)
    dim_cds.to_csv(out_csv, index=False, encoding="utf-8-sig")

    print(f"[OK] Dimensão Centro de Distribuição salva:\n - {out_parquet}\n - {out_csv}")

if __name__ == "__main__":
    main()
