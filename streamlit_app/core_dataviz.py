from io import BytesIO
import unicodedata, requests, pandas as pd, numpy as np

URL_PARQUET = "https://raw.githubusercontent.com/regis-zang/TrbFiap25_Cap05/main/sample/vendas_completo_enriquecido.parquet"

def _norm(txt: str | None) -> str | None:
    if txt is None: return None
    return unicodedata.normalize("NFKD", str(txt)).encode("ascii","ignore").decode("ascii").strip()

def to_number(s: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(s): return pd.to_numeric(s, errors="coerce")
    s = s.astype("string").str.replace("\u00A0"," ",regex=False).str.strip()
    s = s.str.replace(r"[^\d,.\-]", "", regex=True)
    both = s.str.contains(",", na=False) & s.str.contains(r"\.", na=False)
    s = s.mask(both, s[both].str.replace(".", "", regex=False).str.replace(",", ".", regex=False))
    only = s.str.contains(",", na=False) & ~s.str.contains(r"\.", na=False)
    s = s.mask(only, s[only].str.replace(",", ".", regex=False))
    return pd.to_numeric(s, errors="coerce")

def choose_col(df: pd.DataFrame, options: list[str]) -> str | None:
    return next((c for c in options if c in df.columns), None)

def load_df(url: str = URL_PARQUET) -> pd.DataFrame:
    r = requests.get(url, timeout=60); r.raise_for_status()
    df = pd.read_parquet(BytesIO(r.content), engine="pyarrow")

    data_col = choose_col(df, ["data_pedido","data","dt_pedido","pedido_data"])
    if not data_col: raise RuntimeError("coluna de data não encontrada (ex.: data_pedido).")
    df["_data_pedido"] = pd.to_datetime(df[data_col], errors="coerce", dayfirst=True)
    df["ano"] = df["_data_pedido"].dt.year
    df["mes"] = df["_data_pedido"].dt.to_period("M").astype(str)
    df["trimestre"] = df["_data_pedido"].dt.quarter

    total_col = choose_col(df, ["valor_total_bruto","valor_total","total_bruto","total"])
    if not total_col: raise RuntimeError("coluna de total não encontrada.")
    df["receita"] = to_number(df[total_col])

    qtd_col = choose_col(df, ["quantidade","qtd","qtde"])
    df["itens"] = to_number(df[qtd_col]) if qtd_col else np.nan

    pedido_col = choose_col(df, ["cod_pedido","pedido","id_pedido","num_pedido"])
    df["pedido_id"] = (df[pedido_col].astype("string") if pedido_col else df.index.astype(str))

    for c in ["estado","regiao_pais","categoria","subcategoria","produto","cliente",
              "canal","forma_pagamento","responsavelpedido"]:
        if c in df.columns: df[c] = df[c].astype("string").str.strip()
    return df

def filter_df(df: pd.DataFrame,
              anos=None, meses=None, categorias=None, canais=None, estados=None, responsaveis=None) -> pd.DataFrame:
    d = df.copy()
    if anos: d = d[d["ano"].isin(anos)]
    if meses: d = d[d["mes"].isin(meses)]
    if categorias and "categoria" in d.columns: d = d[d["categoria"].isin(categorias)]
    if canais and "canal" in d.columns: d = d[d["canal"].isin(canais)]
    if estados and "estado" in d.columns: d = d[d["estado"].isin(estados)]
    if responsaveis and "responsavelpedido" in d.columns: d = d[d["responsavelpedido"].isin(responsaveis)]
    return d

def kpis(df: pd.DataFrame, ref_mes: str | None = None) -> dict:
    receita = df["receita"].sum(min_count=1)
    pedidos = df["pedido_id"].nunique()
    itens   = df["itens"].sum(min_count=1)
    ticket  = receita / pedidos if pedidos and pd.notna(receita) else np.nan

    yoy = np.nan
    if ref_mes:
        try:
            y, m = ref_mes.split("-")
            prev = f"{int(y)-1:04d}-{m}"
            cur = df.loc[df["mes"]==ref_mes,"receita"].sum(min_count=1)
            prv = df.loc[df["mes"]==prev,"receita"].sum(min_count=1)
            if pd.notna(cur) and pd.notna(prv) and prv != 0: yoy = (cur-prv)/prv
        except Exception:
            pass

    return {"Receita":receita,"Pedidos":pedidos,"Itens":itens,"Ticket Médio":ticket,"YoY":yoy}

def choices(df: pd.DataFrame) -> dict:
    return {
        "anos": sorted([int(x) for x in df["ano"].dropna().unique()]),
        "meses": sorted(df["mes"].dropna().unique().tolist()),
        "categorias": sorted(df["categoria"].dropna().unique().tolist()) if "categoria" in df.columns else [],
        "canais": sorted(df["canal"].dropna().unique().tolist()) if "canal" in df.columns else [],
        "estados": sorted(df["estado"].dropna().unique().tolist()) if "estado" in df.columns else [],
        "responsaveis": sorted(df["responsavelpedido"].dropna().unique().tolist()) if "responsavelpedido" in df.columns else [],
    }
