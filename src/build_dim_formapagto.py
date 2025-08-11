#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
build_dim_formapagto.py

Gera a dimensão Forma de Pagamento.
Cria formapagto_id (sequencial FRM001, FRM002...).
Exporta dim_formapagto.parquet e dim_formapagto.csv.
"""

import pandas as pd
import os

# --- Configurações para rodar no Spyder ---
DEFAULT_FORMAPAGTO_LIST = [
    "Boleto Bancário",
    "Cartão Crédito",
    "Cartão Débito",
    "Dinheiro",
    "Pix"
]
DEFAULT_OUT_DIR = r"I:/Projetos_Python/Fiap_F5/Fiap_F5/data/dimensoes"

def gerar_dim_formapagto(lista_forma):
    df = pd.DataFrame({"forma_pagamento": lista_forma})
    df = df.dropna().drop_duplicates().reset_index(drop=True)
    df["forma_pagamento_normalizado"] = df["forma_pagamento"].str.strip()
    df["formapagto_id"] = ["FRM" + f"{i+1:03d}" for i in range(len(df))]
    df["ativo"] = True
    return df[["formapagto_id", "forma_pagamento", "forma_pagamento_normalizado", "ativo"]]

def main():
    os.makedirs(DEFAULT_OUT_DIR, exist_ok=True)
    dim_forma = gerar_dim_formapagto(DEFAULT_FORMAPAGTO_LIST)

    out_parquet = os.path.join(DEFAULT_OUT_DIR, "dim_formapagto.parquet")
    out_csv = os.path.join(DEFAULT_OUT_DIR, "dim_formapagto.csv")

    dim_forma.to_parquet(out_parquet, index=False)
    dim_forma.to_csv(out_csv, index=False, encoding="utf-8-sig")

    print(f"[OK] Dimensão Forma de Pagamento salva:\n - {out_parquet}\n - {out_csv}")

if __name__ == "__main__":
    main()
