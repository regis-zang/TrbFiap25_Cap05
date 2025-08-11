# src/eda_quick.py
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from unidecode import unidecode

# ==================== MAPEAMENTOS ====================
REGIOES_BRASIL_POR_UF = {
    "AC":"Norte","AP":"Norte","AM":"Norte","PA":"Norte","RO":"Norte","RR":"Norte","TO":"Norte",
    "AL":"Nordeste","BA":"Nordeste","CE":"Nordeste","MA":"Nordeste","PB":"Nordeste","PE":"Nordeste",
    "PI":"Nordeste","RN":"Nordeste","SE":"Nordeste",
    "DF":"Centro-Oeste","GO":"Centro-Oeste","MT":"Centro-Oeste","MS":"Centro-Oeste",
    "ES":"Sudeste","MG":"Sudeste","RJ":"Sudeste","SP":"Sudeste",
    "PR":"Sul","RS":"Sul","SC":"Sul",
}

UF_POR_ESTADO = {
    "acre":"AC","amapa":"AP","amazonas":"AM","para":"PA","rondonia":"RO","roraima":"RR","tocantins":"TO",
    "alagoas":"AL","bahia":"BA","ceara":"CE","maranhao":"MA","paraiba":"PB","pernambuco":"PE",
    "piaui":"PI","rio grande do norte":"RN","sergipe":"SE",
    "distrito federal":"DF","goias":"GO","mato grosso":"MT","mato grosso do sul":"MS",
    "espirito santo":"ES","minas gerais":"MG","rio de janeiro":"RJ","sao paulo":"SP",
    "parana":"PR","rio grande do sul":"RS","santa catarina":"SC",
}

REGIOES_POR_PAIS = {
    "Brazil": "LATAM", "Brasil": "LATAM",
    "Argentina": "LATAM", "United States": "NA", "Germany": "EMEA"
}

# ==================== HELPERS ====================
def _nome_to_uf(nome):
    if pd.isna(nome): return pd.NA
    key = unidecode(str(nome)).strip().lower()
    return UF_POR_ESTADO.get(key, pd.NA)

def rename_truncated_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza colunas comuns com nomes truncados/variações."""
    ren = {}
    cols = {c.lower(): c for c in df.columns}

    def has_prefix(prefixes):
        for p in prefixes:
            for low, orig in cols.items():
                if low.startswith(p):  # prefix match
                    return orig
        return None

    mapping = {
        "Cod_pedido": has_prefix(["cod_pedid", "cod_pedido", "pedido", "order_id"]),
        "regiao_pais": has_prefix(["regiao_pai", "regiao_pais"]),
        "centro_distribuicao": has_prefix(["centro_dis", "centro_distribuicao"]),
        "responsavelpedido": has_prefix(["responsavi", "responsavel", "responsavelpedido"]),
        "valor_comissao": has_prefix(["valor_comi", "valor_comissao"]),
        "lucro_liquido": has_prefix(["lucro_liqui", "lucro_liquido"]),
        "valor_total": has_prefix(["valor_total", "total_venda", "valorvenda"]),
        "data": has_prefix(["data", "data_pedido", "date"]),
        "uf": has_prefix(["uf"]),
        "estado_nome": has_prefix(["estado_nome", "estadoextenso", "estado_por_extenso"]),
        "pais": has_prefix(["pais", "country"])
    }
    for std, found in mapping.items():
        if found and found != std:
            ren[found] = std
    if ren:
        df = df.rename(columns=ren)
    return df

def enriquecer_para_mapas_e_dimensoes(
    df: pd.DataFrame,
    *,
    col_pais="pais",
    col_uf="uf",                 # se NÃO tiver UF, passe None e use col_estado_nome
    col_estado_nome=None,        # nome por extenso (ex.: "São Paulo")
    col_resp="responsavelpedido",
    col_cd="centro_distribuicao",
    col_cod_pedido="cod_pedido",
    col_valor_comissao="valor_comissao",
    col_lucro_liquido="lucro_liquido",
) -> pd.DataFrame:
    df = df.copy()

    # Garante dimensões mínimas
    for c in [col_resp, col_cd, col_cod_pedido]:
        if c and c not in df.columns:
            df[c] = pd.NA

    # Detecta UF a partir do nome do estado, se necessário
    uf_col = None
    if col_uf and col_uf in df.columns:
        uf_col = col_uf
    elif col_estado_nome and col_estado_nome in df.columns:
        df["_uf_tmp_"] = df[col_estado_nome].apply(_nome_to_uf)
        uf_col = "_uf_tmp_"

    # === regiao_pais ===
    def _derive_regiao(row):
        pais = row.get(col_pais)
        uf   = row.get(uf_col) if uf_col else None
        if pais and str(pais).strip().lower() in ["brazil","brasil"]:
            if pd.notna(uf):
                return REGIOES_BRASIL_POR_UF.get(str(uf).upper(), "Brasil - Desconhecida")
            return "Brasil - N/A"
        if pais and pd.notna(pais):
            return REGIOES_POR_PAIS.get(str(pais), "Outras Regiões")
        # Se país não vier mas tivermos UF, assumir Brasil
        if uf and pd.notna(uf):
            return REGIOES_BRASIL_POR_UF.get(str(uf).upper(), "Brasil - Desconhecida")
        return "N/A"

    if (col_pais in df.columns) or uf_col:
        df["regiao_pais"] = df.apply(_derive_regiao, axis=1)
    else:
        df["regiao_pais"] = "N/A"

    # === estado (preserva se já existir algo) ===
    if "estado" in df.columns and df["estado"].notna().any():
        pass  # mantém
    elif uf_col:
        df["estado"] = df[uf_col].astype("string").str.upper()
    elif col_estado_nome and col_estado_nome in df.columns:
        df["estado"] = df[col_estado_nome].astype("string")
    else:
        # não criar/limpar se já existe mas vazio; cria se não existe
        if "estado" not in df.columns:
            df["estado"] = pd.NA

    # Renomeia padrões finais
    rename_final = {}
    if col_resp in df.columns:            rename_final[col_resp] = "responsavelpedido"
    if col_cd in df.columns:              rename_final[col_cd] = "centro_distribuicao"
    if col_cod_pedido in df.columns:      rename_final[col_cod_pedido] = "Cod_pedido"
    if col_valor_comissao in df.columns:  rename_final[col_valor_comissao] = "valor_comissao"
    if col_lucro_liquido in df.columns:   rename_final[col_lucro_liquido] = "lucro_liquido"
    df = df.rename(columns=rename_final)

    # Tipagens
    for c in ["regiao_pais","estado","responsavelpedido","centro_distribuicao","Cod_pedido"]:
        if c in df.columns:
            try: df[c] = df[c].astype("string[pyarrow]")
            except: pass
    for c in ["valor_comissao","lucro_liquido","valor_total"]:
        if c in df.columns:
            try: df[c] = pd.to_numeric(df[c], errors="coerce")
            except: pass

    if "_uf_tmp_" in df.columns:
        df = df.drop(columns="_uf_tmp_")

    return df

# ==================== PATHS ====================
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
PROC_DIR = DATA_DIR / "processed"
SAMP_DIR = DATA_DIR / "sample"

# ==================== LOAD ====================
files = list(PROC_DIR.glob("*.parquet"))
if not files:
    print("[WARN] Nenhum dado em processed/, usando sample/")
    files = list(SAMP_DIR.glob("*.parquet"))
if not files:
    raise FileNotFoundError("Nenhum .parquet em processed/ ou sample/.")

print(f"[INFO] Lendo {len(files)} arquivo(s)...")
df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)

# Normaliza cabeçalhos “truncados”
df = rename_truncated_columns(df)

# ==================== ENRIQUECIMENTO ====================
df = enriquecer_para_mapas_e_dimensoes(
    df,
    col_pais="pais",
    col_uf="uf",                     # se não houver, ele tenta col_estado_nome
    col_estado_nome="estado_nome",   # será ignorado se não existir
    col_resp="responsavelpedido",
    col_cd="centro_distribuicao",
    col_cod_pedido="cod_pedido",
    col_valor_comissao="valor_comissao",
    col_lucro_liquido="lucro_liquido",
)

# Salva parquet enriquecido
ENR_DIR = DATA_DIR / "processed_enriched"
ENR_DIR.mkdir(parents=True, exist_ok=True)
out_parquet = ENR_DIR / "dataset_enriquecido.parquet"
df.to_parquet(out_parquet, engine="pyarrow", index=False, compression="snappy")
print(f"[OK] Parquet enriquecido salvo em: {out_parquet}")

# ==================== APRESENTAÇÃO ====================
CAMPOS_CHAVE = [
    "regiao_pais","estado","responsavelpedido","centro_distribuicao",
    "Cod_pedido","valor_comissao","lucro_liquido",
]
presentes = [c for c in CAMPOS_CHAVE if c in df.columns]
faltando   = [c for c in CAMPOS_CHAVE if c not in df.columns]

print("\n[APRESENTAÇÃO] Campos-chave esperados:")
print(" - Encontrados :", presentes)
print(" - Faltando    :", faltando if faltando else "Nenhum")

if presentes:
    print("\n[PREVIEW] Top 10 linhas dos campos-chave:")
    print(df[presentes].head(10).to_string(index=False))

out_campos_csv = ENR_DIR / "dataset_campos_chave.csv"
if presentes:
    df[presentes].to_csv(out_campos_csv, index=False, encoding="utf-8-sig")
    print(f"[OK] CSV de campos-chave salvo em: {out_campos_csv}")

def _print_contagem(col):
    if col in df.columns:
        nun = df[col].nunique(dropna=True)
        top = df[col].value_counts(dropna=True).head(5).to_string()
        print(f"\n[DIM] {col} — distintos: {nun}\nTOP 5:\n{top}")

for dim in ["regiao_pais","estado","responsavelpedido","centro_distribuicao"]:
    _print_contagem(dim)

somas = {}
for m in ["valor_comissao","lucro_liquido"]:
    if m in df.columns:
        somas[m] = float(pd.to_numeric(df[m], errors="coerce").sum())
if somas:
    print("\n[MÉTRICAS] Somatórios numéricos dos campos-chave:")
    for k, v in somas.items():
        print(f" - {k}: {v:,.2f}")

# ==================== KPIs MENSAIS (ROBUSTO) ====================
# Detecta coluna de data
date_candidates = [c for c in ["date","data","data_pedido"] if c in df.columns]
if date_candidates:
    date_col = date_candidates[0]
    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)
    df["yyyymm"] = df[date_col].dt.to_period("M").astype(str)
else:
    df["yyyymm"] = "N/A"

# revenue
if "revenue" not in df.columns:
    if "valor_total" in df.columns:
        df["revenue"] = pd.to_numeric(df["valor_total"], errors="coerce")
    elif all(c in df.columns for c in ["preco_unitario","quantidade"]):
        df["revenue"] = (
            pd.to_numeric(df["preco_unitario"], errors="coerce") *
            pd.to_numeric(df["quantidade"], errors="coerce")
        )
    elif "lucro_liquido" in df.columns:
        df["revenue"] = pd.to_numeric(df["lucro_liquido"], errors="coerce")
    else:
        df["revenue"] = pd.NA

# agg
agg_dict = {"revenue": ("revenue","sum")}
if "Cod_pedido" in df.columns:
    agg_dict["orders"] = ("Cod_pedido","nunique")
else:
    df["_ones_"] = 1
    agg_dict["orders"] = ("_ones_","sum")

if "valor_comissao" in df.columns:
    agg_dict["valor_comissao"] = ("valor_comissao","sum")
if "lucro_liquido" in df.columns:
    agg_dict["lucro_liquido"] = ("lucro_liquido","sum")

kpi = df.groupby("yyyymm", as_index=False).agg(**agg_dict)
kpi["ticket_medio"] = kpi["revenue"] / kpi["orders"].clip(lower=1)

print("\n[KPIs - últimos 6 meses]")
print(kpi.tail(6))

# Outliers
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

OUT_DIR = DATA_DIR / "audit"
OUT_DIR.mkdir(parents=True, exist_ok=True)
kpi.to_csv(OUT_DIR / "kpi_mensal.csv", index=False)
outliers.to_csv(OUT_DIR / "kpi_outliers.csv", index=False)
meses_zero.to_csv(OUT_DIR / "kpi_receita_zero.csv", index=False)
print(f"\n[OK] Arquivos salvos em: {OUT_DIR}")

# ==================== EXPORTS ====================
preview_csv = ENR_DIR / "dataset_enriquecido_preview.csv"
schema_csv  = ENR_DIR / "dataset_enriquecido_schema.csv"
sample_csv  = ENR_DIR / "dataset_enriquecido_sample_500.csv"

print(f"[INFO] Exportando CSVs de análise em: {ENR_DIR}")
df.to_csv(preview_csv, index=False, encoding="utf-8-sig")
df.head(500).to_csv(sample_csv, index=False, encoding="utf-8-sig")

schema = (
    pd.DataFrame({
        "coluna": df.columns,
        "dtype": [str(df[c].dtype) for c in df.columns],
        "n_nulos": [int(df[c].isna().sum()) for c in df.columns],
        "n_distintos": [int(df[c].nunique(dropna=True)) for c in df.columns],
        "exemplo": [df[c].dropna().iloc[0] if df[c].notna().any() else "" for c in df.columns],
    })
    .sort_values("coluna")
)
schema.to_csv(schema_csv, index=False, encoding="utf-8-sig")
print(f"[OK] CSV completo: {preview_csv}")
print(f"[OK] Amostra 500:  {sample_csv}")
print(f"[OK] Estrutura:    {schema_csv}")
