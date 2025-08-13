import streamlit as st, plotly.express as px, pandas as pd
from pathlib import Path
from core_dataviz import load_df, filter_df, kpis, choices
from maps_plotly import choropleth_receita_por_uf, bubblemap_receita_por_uf

# --- Paths para assets ---
BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "DashImg"
LOGO_PATH = ASSETS_DIR / "LogoMelhoresComprasPET_NEW.png"  # ajuste se o nome for outro

# --- Configuração da página ---
st.set_page_config(
    page_title="Melhores Compras – Dashboard de Vendas",
    page_icon="📊",
    layout="wide"
)

# --- Header com logo + título ---
col_logo, col_title = st.columns([1, 6])
with col_logo:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), use_container_width=True)
with col_title:
    st.markdown("# 📊 Melhores Compras – Dashboard de Vendas")
    st.caption("Preview em Streamlit — filtros no painel lateral, gráficos interativos e mapas")

@st.cache_data(show_spinner=False)
def _load():
    df = load_df()
    return df, choices(df)

df, opts = _load()

# ---------------- Sidebar (filtros) ----------------
st.sidebar.header("Filtros")
anos = st.sidebar.multiselect("Ano", options=opts["anos"], default=opts["anos"])
meses = st.sidebar.multiselect("Mês (YYYY-MM)", options=opts["meses"], default=[])
cats  = st.sidebar.multiselect("Categoria", options=opts["categorias"], default=[])
canais= st.sidebar.multiselect("Canal", options=opts["canais"], default=[])
ufs   = st.sidebar.multiselect("UF", options=opts["estados"], default=[])
resps = st.sidebar.multiselect("Responsável do Pedido", options=opts["responsaveis"], default=[])

df_f = filter_df(df, anos=anos, meses=meses, categorias=cats, canais=canais, estados=ufs, responsaveis=resps)

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

    # Barras por categoria (ordem decrescente sem limite)
    if "categoria" in df_f.columns and not df_f["categoria"].dropna().empty:
        g = (
            df_f.groupby("categoria", dropna=False)["receita"]
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )
        fig_cat = px.bar(
            g,
            x="receita",
            y="categoria",
            orientation="h",
            title="Receita por Categoria (ordem decrescente)"
        )
        fig_cat.update_layout(xaxis_title="Receita", yaxis_title="")
        right.plotly_chart(fig_cat, use_container_width=True)

    # Donut por canal
    if "canal" in df_f.columns and not df_f["canal"].dropna().empty:
        g = (
            df_f.groupby("canal", dropna=False)["receita"]
            .sum().sort_values(ascending=False)
        ).reset_index()
        fig_dn = px.pie(g, names="canal", values="receita", hole=0.6, title="Receita por Canal")
        right.plotly_chart(fig_dn, use_container_width=True)

    # Top responsável do pedido
    if "responsavelpedido" in df_f.columns and not df_f["responsavelpedido"].dropna().empty:
        g = (
            df_f.groupby("responsavelpedido", dropna=False)["receita"]
            .sum().sort_values(ascending=False).head(10)
        ).reset_index()
        fig_resp = px.bar(g, x="receita", y="responsavelpedido", orientation="h",
                          title="Top 10 Faturamento Bruto por Responsável do Pedido")
        fig_resp.update_layout(xaxis_title="Receita", yaxis_title="")
        left.plotly_chart(fig_resp, use_container_width=True)

with tab2:
    c1, c2 = st.columns(2)
    c1.plotly_chart(choropleth_receita_por_uf(df_f), use_container_width=True)
    c2.plotly_chart(bubblemap_receita_por_uf(df_f, size_max=45, use_log=False), use_container_width=True)

st.caption("Preview em Streamlit — filtros no painel lateral, gráficos interativos e mapas sem dependências pesadas.")

