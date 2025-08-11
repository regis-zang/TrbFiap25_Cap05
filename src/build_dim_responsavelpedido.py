#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
build_dim_responsavelpedido.py

Gera a dimensão Responsável Pedido.
Cria responsavelpedido_id (sequencial VEND001, VEND002...).
Exporta dim_responsavelpedido.parquet e dim_responsavelpedido.csv.
"""

import pandas as pd
import os

# --- Configurações para rodar no Spyder ---
DEFAULT_RESPONSAVEIS = [
    "Adriana",
    "Andressa",
    "Antonio",
    "Beatriz",
    "Carlos",
    "Clarice",
    "Claudio",
    "Cristian",
    "Cristina",
    "Dolores",
    "Julia",
    "Ligia",
    "Lucia",
    "Maria Clara",
    "Maria Linda",
    "Marta",
    "Miriam",
    "Monique",
    "Neide",
    "Silvia",
    "Sonia",
    "Tereza",
    "Vitória",
    "Vivian",
    "Yuri"
]

DEFAULT_OUT_DIR = r"I:/Projetos_Python/Fiap_F5/Fiap_F5/data/dimensoes"

def gerar_dim_responsavelpedido(lista_resp):
    df = pd.DataFrame({"responsavel_pedido": lista_resp})
    df = df.dropna().drop_duplicates().reset_index(drop=True)
    df["responsavel_pedido_normalizado"] = df["responsavel_pedido"].str.strip()
    df["responsavelpedido_id"] = ["VEND" + f"{i+1:03d}" for i in range(len(df))]
    df["ativo"] = True
    return df[["responsavelpedido_id", "responsavel_pedido", "responsavel_pedido_normalizado", "ativo"]]

def main():
    os.makedirs(DEFAULT_OUT_DIR, exist_ok=True)
    dim_resp = gerar_dim_responsavelpedido(DEFAULT_RESPONSAVEIS)

    out_parquet = os.path.join(DEFAULT_OUT_DIR, "dim_responsavelpedido.parquet")
    out_csv = os.path.join(DEFAULT_OUT_DIR, "dim_responsavelpedido.csv")

    dim_resp.to_parquet(out_parquet, index=False)
    dim_resp.to_csv(out_csv, index=False, encoding="utf-8-sig")

    print(f"[OK] Dimensão Responsável Pedido salva:\n - {out_parquet}\n - {out_csv}")

if __name__ == "__main__":
    main()
