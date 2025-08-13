import json, unicodedata, numpy as np, pandas as pd, requests, plotly.express as px

GEOJSON_URL = "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson"

UF_POR_ESTADO = {
    "acre":"AC","amapa":"AP","amazonas":"AM","para":"PA","rondonia":"RO","roraima":"RR","tocantins":"TO",
    "alagoas":"AL","bahia":"BA","ceara":"CE","maranhao":"MA","paraiba":"PB","pernambuco":"PE",
    "piaui":"PI","rio grande do norte":"RN","sergipe":"SE",
    "distrito federal":"DF","goias":"GO","mato grosso":"MT","mato grosso do sul":"MS",
    "espirito santo":"ES","minas gerais":"MG","rio de janeiro":"RJ","sao paulo":"SP",
    "parana":"PR","rio grande do sul":"RS","santa catarina":"SC",
}
def _norm(txt): 
    if txt is None: return None
    return unicodedata.normalize("NFKD", str(txt)).encode("ascii","ignore").decode("ascii").lower().strip()

def get_geojson_brazil_states() -> dict:
    gj = requests.get(GEOJSON_URL, timeout=60).json()
    for f in gj["features"]:
        props = f.get("properties", {})
        uf = props.get("sigla") or props.get("abbrev")
        if not uf:
            nome = props.get("name")
            uf = UF_POR_ESTADO.get(_norm(nome), None)
        if "properties" not in f: f["properties"] = {}
        f["properties"]["uf"] = uf
    return gj

def choropleth_receita_por_uf(df: pd.DataFrame) -> "plotly.graph_objs._figure.Figure":
    gj = get_geojson_brazil_states()
    agg = (df.groupby("estado", dropna=False)["receita"].sum().reset_index())
    agg = agg[agg["estado"].notna()]

    # paleta sem branco (trimmed Blues)
    scale = ["#c6dbef", "#6baed6", "#4292c6", "#2171b5", "#084594"]

    fig = px.choropleth(
        agg, geojson=gj, featureidkey="properties.uf",
        locations="estado", color="receita",
        color_continuous_scale=scale, scope="south america",
        labels={"receita":"Receita"},
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(coloraxis_colorbar=dict(title="Range de Valores"))
    fig.update_layout(margin=dict(l=0,r=0,t=40,b=0), title="Receita por UF (Choropleth)")
    return fig

def bubblemap_receita_por_uf(df: pd.DataFrame, size_max: int = 40, use_log: bool = False) -> "plotly.graph_objs._figure.Figure":
    gj = get_geojson_brazil_states()
    agg = (df.groupby("estado", dropna=False)["receita"].sum().reset_index())
    agg = agg[agg["estado"].notna()]

    # centroides simples a partir do GeoJSON (média dos vértices do maior polígono)
    centroids = []
    for f in gj["features"]:
        uf = f["properties"].get("uf")
        geom = f.get("geometry", {})
        if not uf or not geom: continue
        coords = []
        if geom["type"] == "Polygon":
            coords = geom["coordinates"][0]
        elif geom["type"] == "MultiPolygon":
            coords = max(geom["coordinates"], key=lambda ring: len(ring[0]))[0]
        if coords:
            xs = [pt[0] for pt in coords]; ys = [pt[1] for pt in coords]
            centroids.append({"estado": uf, "lon": float(np.mean(xs)), "lat": float(np.mean(ys))})
    cent = pd.DataFrame(centroids)
    bubble = agg.merge(cent, on="estado", how="inner")

    val = bubble["receita"].astype(float)
    if use_log:
        val = np.log1p(val)

    fig = px.scatter_geo(
        bubble, lat="lat", lon="lon", size=val, hover_name="estado",
        projection="natural earth", scope="south america",
        title="Receita por UF (Bolhas nas Centroides)",
        size_max=size_max, opacity=0.85
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_traces(marker=dict(color="#6baed6", line=dict(width=0)))
    fig.update_layout(margin=dict(l=0,r=0,t=40,b=0))
    return fig
