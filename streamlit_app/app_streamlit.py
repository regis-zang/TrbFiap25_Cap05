import streamlit as st, plotly.express as px, pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from core_dataviz import load_df, filter_df, kpis, choices
from maps_plotly import choropleth_receita_por_uf, bubblemap_receita_por_uf

# --- Paths para assets ---
BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "DashImg"
LOGO_PATH = ASSETS_DIR / "LogoMelhoresComprasPET_NEW.png"

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

# ---------- Helper: donut robusto (matplotlib) ----------
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

# ---------- Helper: hover dos mapas em R$ MM ----------
def format_hover_as_millions(fig, add_title_suffix=True, title_suffix=" – R$ MM"):
    if add_title_suffix and getattr(fig.layout, "title", None) and getattr(fig.layout.title, "text", None):
        if title_suffix not in fig.layout.title.text:
            fig.update_layout(title=str(fig.layout.title.text) + title_suffix)

    for tr in fig.data:
        vals = None
        # choropleth normalmente usa 'z'
        if hasattr(tr, "z") and tr.z is not None:
            vals = np.array(tr.z, dtype=float)
        else:
            # bubble/scatter: tenta color > size
            if hasattr(tr, "marker") and tr.marker is not None:
                if isinstance(getattr(tr.marker, "color", None), (list, tuple, np.ndarray)):
                    vals = np.array(tr.marker.color, dtype=float)
                elif isinstance(getattr(tr.marker, "size", None), (list, tuple, np.ndarray)):
                    vals = np.array(tr.marker.size, dtype=float)

        if vals is not None and vals.size:
            tr.customdata = vals / 1e6  # milhões
            # tenta preservar o label original
            if getattr(tr, "hovertext", None) is not None:
                label_expr = "%{hovertext}"
            else:
                # fallback comum em choropleth
                label_expr = "%{location}"
            tr.hovertemplate = f"{label_expr}<br>Receita=R$ "+"%{customdata:.1f} MM<extra></extra>"
    return fig

# ---------------- Sidebar (filtros) ----------------
st.sidebar.header("Filtros")
anos = st.sidebar.multiselect("Ano", options=opts["anos"], default=opts["anos"])
meses = st.sidebar.multiselect("Mês (YYYY-MM)", options=opts["meses"], default=[])
cats  = st.sidebar.multiselect("Categoria", options=opts["categororias"] if "categororias" in opts else opts["categorias"], default=[])

base_canais = (opts.get("canais") or []) or canal_opts
label_canal = "Canal (Forma de Pagamento)" if CANAL_FALLBACK_ACTIVE else "Canal"
canais = st.sidebar.multiselect(label_canal, options=base_canais, default=[])
if CANAL_FALLBACK_ACTIVE:
    st.sidebar.caption("↳ Canal mapeado a partir de **Forma de Pagamento**.")

if CENTRO_COL:
    centros = st.sidebar.multiselect("Centro de Distribuição", options=centro_opts, default=[])
else:
    centros = []
    st.sidebar.caption("↳ Colunas de centro não encontradas no dataset.")

ufs   = st.sidebar.multiselect("UF", options=opts["estados"], default=[])
resps = st.sidebar.multiselect("Responsável do Pedido", options=opts["responsaveis"], default=[])

# filtros principais
df_f = filter_df(df, anos=anos, meses=meses, categorias=cats, canais=canais, estados=ufs, responsaveis=resps)
# filtro adicional por centro
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
        fig_resp = px.bar(g, x="receita", y="responsavelpedido", orientation="h",
                          title="Top 10 Faturamento Bruto por Responsável do Pedido")
        fig_resp.update_layout(xaxis_title="Receita", yaxis_title="", yaxis=dict(autorange="reversed"))
        left.plotly_chart(fig_resp, use_container_width=True)

with tab2:
    c1, c2 = st.columns(2)

    fig_ch = choropleth_receita_por_uf(df_f)
    fig_ch = format_hover_as_millions(fig_ch)  # hover: R$ x.y MM
    c1.plotly_chart(fig_ch, use_container_width=True)

    fig_bu = bubblemap_receita_por_uf(df_f, size_max=45, use_log=False)
    fig_bu = format_hover_as_millions(fig_bu)  # hover: R$ x.y MM
    c2.plotly_chart(fig_bu, use_container_width=True)

st.caption("Preview em Streamlit — filtros no painel lateral, gráficos interativos e mapas sem dependências pesadas.")
