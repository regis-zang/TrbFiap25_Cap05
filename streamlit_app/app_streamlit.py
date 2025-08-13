# app_streamlit.py
import streamlit as st, plotly.express as px, pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from core_dataviz import load_df, filter_df, kpis, choices
from maps_plotly import choropleth_receita_por_uf, bubblemap_receita_por_uf

# --- Paths para assets ---
BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "DashImg"
LOGO_PATH = ASSETS_DIR / "LogoMelhoresComprasPET_NEW.png"  # ajuste se o nome for outro

# --- Config da página ---
st.set_page_config(page_title="Mapa de Oportunidades (Pet)", page_icon="📊", layout="wide")

# --- Header ---
col_logo, col_title = st.columns([1, 6])
with col_logo:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), use_container_width=True)
with col_title:
    st.markdown("# 📊 Mapa de Oportunidades (Pet)")
    st.caption("Preview em Streamlit — filtros no painel lateral, gráficos interativos e mapas")

@st.cache_data(show_spinner=False)
def _load():
    df = load_df()
    return df, choices(df)

df, opts = _load()

# ---------- Fallback: Canal = Forma de Pagamento ----------
CANAL_FALLBACK_ACTIVE = False
if "canal" not in df.columns and "forma_pagamento" in df.columns:
    df = df.copy()
    df["canal"] = df["forma_pagamento"]
    CANAL_FALLBACK_ACTIVE = True

def _unique_sorted(series: pd.Series):
    return sorted(series.dropna().astype(str).str.strip().unique().tolist())

canal_opts = _unique_sorted(df["canal"]) if "canal" in df.columns else []

# ---------- Centro de Distribuição ----------
CENTRO_COL = next((c for c in ["centro_distribuicao_normalizado", "centro_distribuicao", "centro_id", "centro"] if c in df.columns), None)
centro_opts = _unique_sorted(df[CENTRO_COL]) if CENTRO_COL else []

# ---------- Donut robusto (matplotlib) ----------
def donut_canal_streamlit(df: pd.DataFrame):
    cand_cols = ["canal", "canal_venda", "canal_vendas", "forma_pagamento"]
    col = next((c for c in cand_cols if c in df.columns), None)
    if not col or "receita" not in df.columns:
        st.info("Colunas necessárias para o donut não encontradas.")
        return
    tmp = df[[col, "receita"]].copy()
    tmp[col] = tmp[col].astype(str).str.strip()
    tmp["receita"] = pd.to_numeric(tmp["receita"], errors="coerce")
    g = (tmp.dropna().groupby(col, dropna=False)["receita"].sum().sort_values(ascending=False))
    g = g[g > 0]
    if g.empty:
        st.warning("Sem valores positivos para plotar no donut.")
        return
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(g.values, labels=g.index.astype(str), autopct="%1.1f%%", startangle=90)
    centre_circle = plt.Circle((0, 0), 0.65, fc="white")
    ax.add_artist(centre_circle)
    ax.set_title(f"Receita por {col}")
    ax.axis("equal")
    fig.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

# ---------- Hover do choropleth em R$ MM (apenas receita) ----------
def format_choropleth_hover_mm(fig):
    for tr in fig.data:
        if hasattr(tr, "z") and tr.z is not None:
            vals = np.array(tr.z, dtype=float) / 1e6
            tr.customdata = vals
            label_expr = "%{hovertext}" if getattr(tr, "hovertext", None) is not None else "%{location}"
            tr.hovertemplate = f"{label_expr}<br>Receita=R$ " + "%{customdata:.1f} MM<extra></extra>"
    # acrescenta sufixo ao título
    if getattr(fig.layout, "title", None) and getattr(fig.layout.title, "text", None):
        if "– R$ MM" not in fig.layout.title.text:
            fig.update_layout(title=str(fig.layout.title.text) + " – R$ MM")
    return fig

# ---------- Métrica p/ mapa de bolhas ----------
def compute_metric_by_uf(df: pd.DataFrame, metric: str) -> pd.Series:
    """Retorna série indexada por UF com a métrica escolhida (sempre float >= 0)."""
    uf_col = "estado" if "estado" in df.columns else ("uf" if "uf" in df.columns else None)
    if uf_col is None:
        return pd.Series(dtype=float)

    to_num = lambda s: pd.to_numeric(s, errors="coerce")

    if metric == "Ticket Médio":
        tmp = df[[uf_col, "receita", "pedido_id"]].copy()
        tmp["receita"] = to_num(tmp["receita"])
        grp = tmp.groupby(uf_col).agg(receita=("receita", "sum"), pedidos=("pedido_id", "nunique"))
        s = (grp["receita"] / grp["pedidos"]).replace([np.inf, -np.inf], np.nan)

    elif metric == "Lucro Líquido" and "lucro_liquido" in df.columns:
        tmp = df[[uf_col, "lucro_liquido"]].copy()
        tmp["lucro_liquido"] = to_num(tmp["lucro_liquido"])
        s = tmp.groupby(uf_col)["lucro_liquido"].sum()

    elif metric == "Valor de Comissão" and "valor_comissao" in df.columns:
        tmp = df[[uf_col, "valor_comissao"]].copy()
        tmp["valor_comissao"] = to_num(tmp["valor_comissao"])
        s = tmp.groupby(uf_col)["valor_comissao"].sum()

    else:  # Receita (default)
        tmp = df[[uf_col, "receita"]].copy()
        tmp["receita"] = to_num(tmp["receita"])
        s = tmp.groupby(uf_col)["receita"].sum()

    s = pd.to_numeric(s, errors="coerce").fillna(0.0).astype(float)
    return s.clip(lower=0.0)

# ---------- Utilitários de bolhas ----------
def _trace_labels(tr):
    if hasattr(tr, "hovertext") and isinstance(tr.hovertext, (list, tuple, np.ndarray)):
        return [str(x).split("<")[0].strip().upper() for x in tr.hovertext]
    if hasattr(tr, "locations") and tr.locations is not None:
        return [str(x).strip().upper() for x in tr.locations]
    if hasattr(tr, "text") and isinstance(tr.text, (list, tuple, np.ndarray)):
        return [str(x).split("<")[0].strip().upper() for x in tr.text]
    return None

def _align_series_to_trace(series_by_uf: pd.Series, tr) -> np.ndarray:
    """Retorna valores numéricos na mesma ordem dos pontos do trace."""
    labels = _trace_labels(tr)
    def key(x): return str(x).strip().upper()[:2]
    if labels:
        vals = [float(series_by_uf.get(key(k), np.nan)) for k in labels]
    else:
        vals = series_by_uf.values.tolist()
    arr = np.array([0 if (pd.isna(v) or v < 0) else v for v in vals], dtype=float)
    return arr

def adjust_bubble_sizes(fig, values_by_uf: pd.Series, size_max_px: int = 22, size_min_px: int = 3):
    if not fig.data: return fig
    tr = fig.data[0]
    arr = _align_series_to_trace(values_by_uf, tr)
    maxv = float(arr.max()) if arr.size else 0.0
    tr.marker.sizemode = "area"
    tr.marker.sizemin = size_min_px
    tr.marker.size = arr
    tr.marker.sizeref = 2.0 * maxv / (size_max_px ** 2) if maxv > 0 else 1.0
    return fig

def _format_brl(v: float, decimals: int = 0) -> str:
    s = f"{v:,.{decimals}f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"

def apply_bubble_hover(fig, values_by_uf: pd.Series, metric: str):
    """Configura o hover:
       - Receita: R$ x.y MM
       - Demais métricas: BRL sem conversão (1.234.567,89)"""
    if not fig.data: return fig
    tr = fig.data[0]
    arr = _align_series_to_trace(values_by_uf, tr)

    label_expr = "%{hovertext}" if getattr(tr, "hovertext", None) is not None else "%{location}"

    if metric == "Receita":
        tr.customdata = (arr / 1e6).astype(float)
        tr.hovertemplate = f"{label_expr}<br>{metric}=R$ " + "%{customdata:.1f} MM<extra></extra>"
    else:
        decimals = 2 if metric == "Ticket Médio" else 0
        formatted = np.array([_format_brl(v, decimals=decimals) for v in arr], dtype=object)
        tr.customdata = formatted
        tr.hovertemplate = f"{label_expr}<br>{metric}=%{{customdata}}<extra></extra>"
    return fig

# ---------------- Sidebar (filtros) ----------------
st.sidebar.header("Filtros")
anos  = st.sidebar.multiselect("Ano", options=opts["anos"], default=opts["anos"])
meses = st.sidebar.multiselect("Mês (YYYY-MM)", options=opts["meses"], default=[])
cats  = st.sidebar.multiselect("Categoria", options=opts["categororias"] if "categororias" in opts else opts["categorias"], default=[])

# Canal
base_canais = (opts.get("canais") or []) or canal_opts
label_canal = "Canal (Forma de Pagamento)" if CANAL_FALLBACK_ACTIVE else "Canal"
canais = st.sidebar.multiselect(label_canal, options=base_canais, default=[])
if CANAL_FALLBACK_ACTIVE:
    st.sidebar.caption("↳ Canal mapeado a partir de **Forma de Pagamento**.")

# Centro de Distribuição
if CENTRO_COL:
    centros = st.sidebar.multiselect("Centro de Distribuição", options=centro_opts, default=[])
else:
    centros = []
    st.sidebar.caption("↳ Colunas de centro não encontradas no dataset.")

ufs   = st.sidebar.multiselect("UF", options=opts["estados"], default=[])
resps = st.sidebar.multiselect("Responsável do Pedido", options=opts["responsaveis"], default=[])

# Opções do mapa de bolhas
with st.sidebar.expander("Mapa de bolhas – opções", expanded=False):
    metric_options = ["Receita", "Ticket Médio"]
    if "lucro_liquido" in df.columns:  metric_options.append("Lucro Líquido")
    if "valor_comissao" in df.columns: metric_options.append("Valor de Comissão")
    metric_choice = st.selectbox("Métrica", options=metric_options, index=0)
    size_max_px = st.slider("Tamanho máximo (px)", min_value=8, max_value=60, value=22, step=1)
    size_min_px = st.slider("Tamanho mínimo (px)", min_value=0, max_value=10, value=3, step=1)
    use_log_size = st.checkbox("Escala logarítmica (tamanho)", value=False)

# Aplica filtros principais
df_f = filter_df(df, anos=anos, meses=meses, categorias=cats, canais=canais, estados=ufs, responsaveis=resps)
# Filtro adicional por Centro
if CENTRO_COL and centros:
    df_f = df_f[df_f[CENTRO_COL].astype(str).str.strip().isin(centros)]

# ---------------- KPIs ----------------
ref_mes = meses[0] if len(meses) == 1 else None
m = kpis(df_f, ref_mes=ref_mes)
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Receita", f"R$ {m['Receita']:,.0f}".replace(",", "."))
k2.metric("Pedidos", f"{m['Pedidos']:,}".replace(",", "."))
k3.metric("Itens",   f"{m['Itens']:,.0f}".replace(",", "."))
k4.metric("Ticket Médio", f"R$ {m['Ticket Médio']:,.2f}".replace(",", ".") if pd.notna(m['Ticket Médio']) else "—")
k5.metric("Crescimento YoY", f"{m['YoY']:.2%}" if pd.notna(m['YoY']) else "—")

st.divider()

tab1, tab2 = st.tabs(["📈 Visão Geral", "🗺️ Mapas"])

with tab1:
    left, right = st.columns([2, 1])

    # Série temporal
    s = (
        df_f.dropna(subset=["_data_pedido"]).sort_values("_data_pedido")
            .groupby("mes").agg(
                Receita=("receita", "sum"),
                Pedidos=("pedido_id", "nunique"),
                Itens=("itens", "sum")
            ).reset_index()
    )
    fig_ts = px.line(s, x="mes", y=["Receita", "Pedidos", "Itens"], markers=True, title="Série Temporal Mensal")
    fig_ts.update_layout(legend_title=None, xaxis_title="", yaxis_title="")
    left.plotly_chart(fig_ts, use_container_width=True)

    # Barras por categoria — maior->menor (maiores no topo)
    if "categoria" in df_f.columns and not df_f["categoria"].dropna().empty:
        g = (
            df_f.groupby("categoria", dropna=False)["receita"]
                .sum()
                .sort_values(ascending=False)
                .reset_index()
        )
        fig_cat = px.bar(g, x="receita", y="categoria", orientation="h", title="Receita por Categoria")
        fig_cat.update_layout(xaxis_title="Receita", yaxis_title="")
        fig_cat.update_yaxes(autorange="reversed")
        right.plotly_chart(fig_cat, use_container_width=True)

    # Donut por canal
    with right:
        donut_canal_streamlit(df_f)

    # Top responsável do pedido (maior no topo)
    if "responsavelpedido" in df_f.columns and not df_f["responsavelpedido"].dropna().empty:
        g = (
            df_f.groupby("responsavelpedido", dropna=False)["receita"]
                .sum()
                .sort_values(ascending=False)
                .head(10)
                .reset_index()
        )
        fig_resp = px.bar(
            g, x="receita", y="responsavelpedido", orientation="h",
            title="Top 10 Faturamento Bruto por Responsável do Pedido"
        )
        fig_resp.update_layout(xaxis_title="Receita", yaxis_title="", yaxis=dict(autorange="reversed"))
        left.plotly_chart(fig_resp, use_container_width=True)

with tab2:
    c1, c2 = st.columns(2)

    # Choropleth — Receita com hover em MM
    fig_ch = choropleth_receita_por_uf(df_f)
    fig_ch = format_choropleth_hover_mm(fig_ch)
    c1.plotly_chart(fig_ch, use_container_width=True)

    # Bubble map — métrica escolhida
    fig_bu = bubblemap_receita_por_uf(df_f, size_max=45, use_log=False)

    metric_series = compute_metric_by_uf(df_f, metric_choice)
    if use_log_size:
        metric_series = np.log1p(metric_series)

    fig_bu = adjust_bubble_sizes(fig_bu, metric_series, size_max_px=size_max_px, size_min_px=size_min_px)
    fig_bu = apply_bubble_hover(fig_bu, metric_series, metric_choice)

    # título dinâmico (para Receita, inclui sufixo R$ MM)
    title = f"{metric_choice} por UF" + (" – R$ MM" if metric_choice == "Receita" else "")
    fig_bu.update_layout(title=title)

    c2.plotly_chart(fig_bu, use_container_width=True)

st.caption("Preview em Streamlit — filtros no painel lateral, gráficos interativos e mapas sem dependências pesadas.")
