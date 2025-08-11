# src/prepare_data.py
from pathlib import Path
import re
import pandas as pd
from unidecode import unidecode

# ==============================================
# Objetivo
# - Ler o CSV bruto completo (todas as colunas)
# - Preservar TODAS as colunas originais no Parquet
# - Derivar/normalizar colunas para mapas e dimensões:
#     * estado (a partir de UF ou nome do estado, com unidecode)
#     * regiao_pais (a partir de UF/pais)
#     * garantir: centro_distribuicao, responsavelpedido, cod_pedido
# - Calcular quantidade e total quando ausentes
# - Salvar em chunks (part_XXX.parquet) e também um único arquivo combinado
# ==============================================

# --- Paths independentes do working dir ---
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
RAW = DATA_DIR / "raw" / "vendas.csv"  # ajuste se necessário
PROC = DATA_DIR / "processed"
SAMP = DATA_DIR / "sample"
PROC.mkdir(parents=True, exist_ok=True)
SAMP.mkdir(parents=True, exist_ok=True)

ENCODING = "latin1"    # ajuste se necessário
CHUNKSIZE = 500_000    # ajuste conforme memória disponível

# =====================
# Mapeamentos auxiliares
# =====================
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
    "brazil": "LATAM", "brasil": "LATAM",
    "argentina": "LATAM", "chile": "LATAM", "uruguay": "LATAM", "uruguai": "LATAM",
    "united states": "NA", "usa": "NA", "eua": "NA",
    "germany": "EMEA", "deutschland": "EMEA", "alemanha": "EMEA",
}

# =====================
# Funções utilitárias
# =====================

def _normalize_spaces_text(text: str) -> str:
    """Troca NBSP por espaço, colapsa múltiplos espaços e aplica strip."""
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return text
    s = str(text).replace("\u00A0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _normalize_series(s: pd.Series) -> pd.Series:
    s = s.astype("string")
    s = s.str.replace("\u00A0", " ", regex=False)
    s = s.str.replace(r"\s+", " ", regex=True).str.strip()
    return s

def _clean_all_text_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza **todas** as colunas de texto do chunk (NBSP, espaços duplicados, trim)."""
    for c in df.columns:
        if pd.api.types.is_string_dtype(df[c]) or df[c].dtype == "object":
            df[c] = _normalize_series(df[c])
    return df

def _to_number(s: pd.Series) -> pd.Series:
    """Converte strings monetárias/numéricas para float.
    - remove símbolos (R$, $), espaços e NBSP
    - trata milhar (.) e vírgula decimal (,)
    """
    s = s.astype("string").str.replace("\u00A0", " ", regex=False).str.strip()
    # remove tudo que não é dígito, ponto, vírgula ou sinal
    s = s.str.replace(r"[^\d,.\-]", "", regex=True)

    # casos com ponto e vírgula: assume ponto=milhar, vírgula=decimal
    both = s.str.contains(",", na=False) & s.str.contains(r"\.", na=False)
    s = s.mask(both, s[both].str.replace(".", "", regex=False).str.replace(",", ".", regex=False))

    # casos só com vírgula: trata como decimal
    only_comma = s.str.contains(",", na=False) & ~s.str.contains(r"\.", na=False)
    s = s.mask(only_comma, s[only_comma].str.replace(",", ".", regex=False))

    return pd.to_numeric(s, errors="coerce")

def _nome_to_uf(nome: str):
    """Mapeia nome do estado -> UF, com unidecode e colapso de espaços."""
    if pd.isna(nome):
        return pd.NA
    key = unidecode(str(nome))
    key = re.sub(r"\s+", " ", key).strip().lower()
    return UF_POR_ESTADO.get(key, pd.NA)

def _derive_estado(df: pd.DataFrame) -> pd.Series:
    """Produz coluna 'estado' usando prioridade: UF -> nome do estado."""
    uf_col = None
    for c in ["uf", "UF", "estado_uf", "sigla_uf"]:
        if c in df.columns:
            uf_col = c
            break

    if uf_col is not None:
        est = df[uf_col].astype("string").str.upper()
    else:
        # tenta por nome do estado
        nome_col = None
        for c in ["estado", "Estado", "estado_nome", "nome_estado"]:
            if c in df.columns:
                nome_col = c
                break
        if nome_col is not None:
            nomes_norm = df[nome_col].map(_normalize_spaces_text)
            est = nomes_norm.map(_nome_to_uf).astype("string")
        else:
            est = pd.Series(pd.NA, index=df.index, dtype="string")
    # higieniza (mesmo sendo UF)
    est = _normalize_series(est)
    return est

def _derive_regiao_pais(df: pd.DataFrame, estado_series: pd.Series) -> pd.Series:
    # Detecta coluna de país
    pais_col = None
    for c in ["pais", "Pais", "country", "Country"]:
        if c in df.columns:
            pais_col = c
            break

    if pais_col is None and estado_series.isna().all():
        return pd.Series("N/A", index=df.index, dtype="string")

    # normaliza texto do país para evitar ruído de espaço
    pais_vals = df[pais_col].map(_normalize_spaces_text) if pais_col else None

    def _calc(i):
        uf = estado_series.iat[i]
        pais_val = pais_vals.iat[i] if pais_col else None
        pais_key = unidecode(str(pais_val)).strip().lower() if pd.notna(pais_val) else None

        if pais_key in ("brazil", "brasil"):
            if pd.notna(uf):
                return REGIOES_BRASIL_POR_UF.get(str(uf), "Brasil - Desconhecida")
            return "Brasil - N/A"
        if pais_key:
            return REGIOES_POR_PAIS.get(pais_key, "Outras Regiões")
        return "N/A"

    reg = pd.Series([_calc(i) for i in range(len(df))], index=df.index, dtype="string")
    reg = _normalize_series(reg)
    return reg

def _choose_col(df: pd.DataFrame, options: list[str]) -> str | None:
    """Retorna o primeiro nome de coluna existente na ordem dada."""
    return next((c for c in options if c in df.columns), None)

# =====================
# Processamento por chunk
# =====================

def process_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    # 0) Higieniza todas as colunas de texto (remove NBSP, espaços duplicados, trim)
    chunk = _clean_all_text_cols(chunk)

    # 1) GARANTIR que as colunas mínimas existam
    for c in ["centro_distribuicao", "responsavelpedido", "cod_pedido"]:
        if c not in chunk.columns:
            chunk[c] = pd.NA

    # 2) estado (UF) com unidecode e colapso de espaços nos nomes
    estado = _derive_estado(chunk)
    chunk["estado"] = estado

    # 3) regiao_pais derivada de UF/pais com unidecode
    chunk["regiao_pais"] = _derive_regiao_pais(chunk, estado)

    # 4) Tipos amigáveis em texto + higienização final
    for c in ["estado", "regiao_pais", "centro_distribuicao", "responsavelpedido", "cod_pedido"]:
        if c in chunk.columns:
            try:
                chunk[c] = chunk[c].astype("string[pyarrow]")
            except Exception:
                chunk[c] = chunk[c].astype("string")
            chunk[c] = _normalize_series(chunk[c])

    # ====== Quantidade faltante = valor_total_bruto / valor ======
    col_total = _choose_col(chunk, ["valor_total_bruto", "valor_total", "total_bruto", "total"])
    col_valor = _choose_col(chunk, ["valor", "preco_unitario", "valor_unitario", "preco"])
    col_qtd   = _choose_col(chunk, ["quantidade", "qtd", "qtde"])
    if col_qtd is None:
        col_qtd = "quantidade"
        chunk[col_qtd] = pd.NA

    if col_total and col_valor:
        v_total = _to_number(chunk[col_total])
        v_unit  = _to_number(chunk[col_valor])

        qtd_atual = pd.to_numeric(chunk[col_qtd], errors="coerce")

        # Condição: quantidade vazia/zero e termos válidos (v_unit != 0)
        cond_qtd = (qtd_atual.isna() | (qtd_atual == 0)) & v_total.notna() & v_unit.notna() & (v_unit != 0)
        qtd_calc = v_total / v_unit

        # Snap para inteiro quando muito próximo (tolerância 0,01)
        def _snap_close(x):
            if pd.isna(x):
                return x
            r = round(float(x))
            return r if abs(float(x) - r) <= 0.01 else x

        qtd_new = qtd_atual.copy()
        qtd_new[cond_qtd] = qtd_calc[cond_qtd].map(_snap_close)
        chunk[col_qtd] = qtd_new

        # ====== Backfill do total quando ele estiver ausente/zero ======
        v_total_num = v_total
        qtd_num = pd.to_numeric(chunk[col_qtd], errors="coerce")
        cond_total = (v_total_num.isna() | (v_total_num == 0)) & v_unit.notna() & (v_unit != 0) & qtd_num.notna()

        total_calc = qtd_num * v_unit

        # Escreve apenas onde a condição é verdadeira (mantém valores originais nos demais casos)
        total_new = v_total_num.copy()
        total_new[cond_total] = total_calc[cond_total]
        # coloca de volta no dataframe (preserva nome original da coluna de total)
        chunk[col_total] = total_new

    # NÃO remover nenhuma coluna original! Somente acrescentamos/ajustamos as derivadas
    return chunk

# =====================
# Main
# =====================

def main():
    if not RAW.exists():
        raise FileNotFoundError(f"Arquivo CSV não encontrado: {RAW}")

    # Lê TODAS as colunas (sep=None tenta detectar ; ou ,)
    reader = pd.read_csv(
        RAW,
        encoding=ENCODING,
        sep=None,
        engine="python",
        chunksize=CHUNKSIZE,
        on_bad_lines="skip",
        dtype=str,   # preserva valores como string; conversões ficam para etapas posteriores
    )

    parts = []
    for i, chunk in enumerate(reader, 1):
        chunk = process_chunk(chunk)

        # salva partições
        out_part = PROC / f"part_{i:03d}.parquet"
        chunk.to_parquet(out_part, index=False, engine="pyarrow")
        parts.append(out_part)

        # salva também uma amostra
        if len(chunk) > 0:
            amostra = chunk.sample(min(10_000, len(chunk)), random_state=42)
            amostra.to_parquet(SAMP / f"vendas_sample_{i:03d}.parquet", index=False)

    # Gera um único parquet combinado
    if parts:
        dfs = [pd.read_parquet(p) for p in parts]
        combinado = pd.concat(dfs, ignore_index=True)
        combinado_path = PROC / "vendas_completo.parquet"
        combinado.to_parquet(combinado_path, index=False, engine="pyarrow")
        # salva também como CSV completo
        csv_path = PROC / "vendas_completo.csv"
        combinado.to_csv(csv_path, index=False, encoding="utf-8-sig")
        # amostra geral
        combinado.head(50_000).to_parquet(SAMP / "vendas_sample.parquet", index=False)
        combinado.head(50_000).to_csv(SAMP / "vendas_sample.csv", index=False, encoding="utf-8-sig")
        print("[OK] Processamento concluído.")
        print(f" - Partições: {PROC}")
        print(f" - Parquet combinado: {combinado_path}")
        print(f" - CSV combinado: {csv_path}")
        print(f" - Amostras: {SAMP}")
    else:
        print("[WARN] Nenhum chunk processado.")

if __name__ == "__main__":
    main()
