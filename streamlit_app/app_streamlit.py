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

# --- Configuração da página ---
st.set_page_config(
    page_title="Mapa de Oportunidades (Pet)",
    page_icon="📊",
    layout="wide"
)

# --- Header com logo + título ---
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

# ---------- Fallback: Canal = Forma de Pagamento (se 'canal' não existir) ----------
CANAL_FALLBACK_ACTIVE = False
if "canal" not in df.columns and "forma_pagamento" in df.columns:
    df = df.copy()
    df["canal"] = df["forma_pagamento"]
    CANAL_FALLBACK_ACTIVE = True

def _unique_sorted(series: pd.Series):
    return sorted(series.dropna().astype(str).str.strip().unique().tolist())

# opções calculadas a partir do DF (usadas se opts["canais"] vier vazio)
canal_opts = _unique_sorted(df["canal"]) if "canal" in df.columns else []

# ---------- Centro de Distribuição: detectar coluna e opções ----------
CENTRO_COL = next(
    (c for c in ["centro_distribuicao_normalizado", "centro_distribuicao", "centro_id", "centro"] if c in df.columns),
    None
)
centro_opts = _unique_sorted(df[CENTRO_COL]) if CENTRO_COL else []

# ---------- helper: donut robusto (matplotlib) ----------
def donut_canal_streamlit(df: pd.DataFrame):
    cand_cols = ["canal", "canal_venda", "canal_vendas", "forma_pagamento"]
    col = next((c for c in cand_cols if c in df.columns), None)
    if not col or "receita" not in df.columns:
        st.info("Colunas necessárias para o donut não encontradas.")
        return

    tmp = df[[col, "receita"]].copy()
    tmp[col] = tmp[col].astype(str).str.strip()
    tmp["receita"] = pd.to_numeric(tmp["receita"], errors="coerce")

    g = (tmp.dropna()
            .groupby(col, dropna=False)["receita"]
            .sum()
            .sort_values(ascending=False))

    g = g[g > 0]  # remove não-positivos
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

# ---------- Helper: hover dos mapas em R$ MM ----------
def format_hover_as_millions(fig, add_title_suffix=True, title_suffix=" – R$ MM"):
    if add_title_suffix and getattr(fig.layout, "title", None) and getattr(fig.layout.title, "text", None):
        if title_suffix not in fig.layout.title.text:
            fig.update_layout(title=str(fig.layout.title.text) + title_suffix)

    for tr in fig.data:
        vals = None
        if hasattr(tr, "z") and tr.z is not None:
            vals = np.array(tr.z, dtype=float)
        else:
            if hasattr(tr, "marker") and tr.marker is not None:
                if isinstance(getattr(tr.marker, "color", None), (list, tuple, np.ndarray)):
                    vals = np.array(tr.marker.color, dtype=float)
                elif isinstance(getattr(tr.marker, "size", None), (list, tuple, np.ndarray)):
                    vals = np.array(tr.marker.size, dtype=float)

        if vals is not None and vals.size:
            tr.customdata = vals / 1e6  # milhões
            label_expr = "%{hovertext}" if getattr(tr, "hovertext", None) is not None else "%{location}"
            tr.hovertemplate = f"{label_expr}<br>Receita=R$ " + "%{customdata:.1f} MM<extra></extra>"
    return fig

# ---------- Helpers para Mapa de Bolhas ----------
def compute_metric_by_uf(df: pd.DataFrame, metric: str) -> pd.Series:
    """Retorna série indexada por UF com a métrica escolhida."""
    uf_col = "estado" if "estado" in df.columns else ("uf" if "uf" in df.columns else None)
    if uf_col is None:
        return pd.Series(dtype=float)

    if metric == "Ticket Médio":
        grp = df.groupby(uf_col).agg(receita=("receita", "sum"),
                                     pedidos=("pedido_id", "nunique"))
        s = (grp["receita"] / grp["pedidos"]).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    elif metric == "Lucro Líquido" and "lucro_liquido" in df.columns:
        s = df.groupby(uf_col)["lucro_liquido"].sum()
    elif metric == "Valor de Comissão" and "valor_comissao" in df.columns:
        s = df.groupby(uf_col)["valor_comissao"].sum()
    else:  # Receita
        s = df.groupby(uf_col)["receita"].sum()

    return s.clip(lower=0)

def adjust_bubble_sizes(fig, values_by_uf: pd.Series, size_max_px: int = 22, size_min_px: int = 3):
    """Redimensiona bolhas do scatter_geo do Plotly para o range desejado."""
    if not fig.data:
        return fig
    tr = fig.data[0]

    # tenta descobrir a ordem dos UFs no trace
    labels = None
    if hasattr(tr, "hovertext") and isinstance(tr.hovertext, (list, tuple, np.ndarray)):
        labels = [str(x).split("<")[0].strip().upper() for x in tr.hovertext]
    elif hasattr(tr, "locations") and tr.locations is not None:
        labels = [str(x).strip().upper() for x in tr.locations]
    elif hasattr(tr, "text") and isinstance(tr.text, (list, tuple, np.ndarray)):
        labels = [str(x).split("<")[0].strip().upper() for x in tr.text]

    def norm_key(x): return str(x).strip().upper()[:2]
    if labels:
        sizes = [float(values_by_uf.get(norm_key(k), np.nan)) for k in labels]
    else:
        # fallback: usa os valores na mesma ordem (se bater)
        sizes = values_by_uf.values.tolist()

    arr = np.array([0 if (pd.isna(v) or v < 0) else v for v in sizes], dtype=float)
    maxv = float(arr.max()) if arr.size else 0.0
    tr.marker.sizemode = "area"
    tr.marker.sizemin = size_min_px
    tr.marker.size = arr
    tr.marker.sizeref = 2.0 * maxv / (size_max_px ** 2) if maxv > 0 else 1.0
    return fig

# ---------------- Sidebar (filtros) ----------------
st.sidebar.header("Filtros")
anos = st.sidebar.multiselect("Ano", options=opts["anos"], default=opts["anos"])
meses = st.sidebar.multiselect("Mês (YYYY-MM)", options=opts["meses"], default=[])
cats  = st.sidebar.multiselect("Categoria", options=opts["categororias"] if "categororias" in opts else opts["categorias"], default=[])

# Canal (usa opts se houver, senão fallback calculado)
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
    # opções de métrica disponíveis
    metric_options = ["Receita", "Ticket Médio"]
    if "lucro_liquido" in df.columns: metric_options.append("Lucro Líquido")
    if "valor_comissao" in df.columns: metric_options.append("Valor de Comissão")
    metric_choice = st.selectbox("Métrica", options=metric_options, index=0)
    size_max_px = st.slider("Tamanho máximo (px)", min_value=8, max_value=60, value=22, step=1)
    size_min_px = st.slider("Tamanho mínimo (px)", min_value=0, max_value=10, value=3, step=1)
    use_log_size = st.checkbox("Escala logarítmica (tamanho)", value=False)

# filtros principais (anos, meses, categorias, canais, UFs, responsáveis)
df_f = filter_df(df, anos=anos, meses=meses, categorias=cats, canais=canais, estados=ufs, responsaveis=resps)
# filtro adicional por centro (aplicado localmente)
if CENTRO_COL and centros:
    df_f = df_f[df_f[CENTRO_COL].astype(str).str.strip().isin(centros)]

# ---------------- KPIs ----------------
ref_mes = meses[0] if len(meses) == 1 else None
m = kpis(df_f, ref_mes=ref_mes)
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Receita", f"R$ {m['Receita']:,.0f}".replace(",", "."))
k2.metric("Pedidos", f"{m['Pedidos']:,}".replace(",", "."))
k3.metric("Itens", f"{m['Itens']:,.0f}".replace(",", "."))
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

    # Top responsável do pedido (maior valor no topo)
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

    # Choropleth (hover em MM)
    fig_ch = choropleth_receita_por_uf(df_f)
    fig_ch = format_hover_as_millions(fig_ch)
    c1.plotly_chart(fig_ch, use_container_width=True)

    # Bubble map com métrica escolhida e controle de tamanho
    # 1) base (usa sua função atual)
    fig_bu = bubblemap_receita_por_uf(df_f, size_max=45, use_log=False)

    # 2) valores por UF para a métrica escolhida
    metric_series = compute_metric_by_uf(df_f, metric_choice)
    if use_log_size:
        metric_series = np.log1p(metric_series)

    # 3) reescala as bolhas para o tamanho desejado
    fig_bu = adjust_bubble_sizes(fig_bu, metric_series, size_max_px=size_max_px, size_min_px=size_min_px)

    # 4) hover em MM (mantém padrão R$ x.y MM)
    fig_bu = format_hover_as_millions(fig_bu)

    c2.plotly_chart(fig_bu, use_container_width=True)

st.caption("Preview em Streamlit — filtros no painel lateral, gráficos interativos e mapas sem dependências pesadas.")
