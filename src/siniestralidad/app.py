"""Tablero analítico del estudio (OE6).

Uso::

    streamlit run src/siniestralidad/app.py

Cinco vistas: mapa, comportamiento temporal, hipótesis, perfiles y reglas. Los
filtros de la fila superior cambian el mapa, la vista temporal y los perfiles;
las hipótesis y las reglas se calcularon sobre toda la base.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from siniestralidad import config, tablero
from siniestralidad.asociacion import legible
from siniestralidad.descriptivo import MESES
from siniestralidad.graficos import (AZUL, AZULES, GRAVEDAD_COLORES, GRAVEDAD_ETIQUETAS, REJILLA,
                                     TEXTO, TEXTO_2)

NARANJA = "#eb6834"
FRANJAS = {"madrugada": "Madrugada (0–6 h)", "manana": "Mañana (6–10 h)",
           "mediodia": "Mediodía (10–16 h)", "tarde": "Tarde (16–20 h)", "noche": "Noche (20–24 h)"}
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
ESCALA = [[i / (len(AZULES) - 1), c] for i, c in enumerate(AZULES)]
# Densidad: transparente donde no hay siniestros, para que se vea el mapa debajo.
ESCALA_DENSIDAD = [[0, "rgba(205,226,251,0)"]] + [[i / (len(AZULES) - 1), c] for i, c in enumerate(AZULES)][1:]


def estilo(fig: go.Figure, alto: int = 380) -> go.Figure:
    fig.update_layout(
        height=alto, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family="Inter, sans-serif", size=13, color=TEXTO), legend_title_text="",
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
    fig.update_xaxes(gridcolor=REJILLA, zeroline=False, title_font_color=TEXTO_2)
    fig.update_yaxes(gridcolor=REJILLA, zeroline=False, title_font_color=TEXTO_2)
    return fig


@st.cache_data
def datos():
    return tablero.cargar()


def filtros(df: pd.DataFrame) -> pd.DataFrame:
    c1, c2, c3, c4 = st.columns([3, 2, 1.4, 2])
    corredores = c1.multiselect("Corredor", sorted(df["nombre_corredor"].unique()), placeholder="Todos")
    franjas = c2.multiselect("Franja", list(FRANJAS), format_func=FRANJAS.get, placeholder="Todas")
    dia = c3.selectbox("Tipo de día", ["Todos", "Entre semana", "Fin de semana"])
    gravedades = c4.multiselect("Gravedad", config.GRAVEDAD_ORDEN, format_func=GRAVEDAD_ETIQUETAS.get,
                                placeholder="Todas")
    return tablero.filtrar(df, corredores, franjas, None if dia == "Todos" else [dia], gravedades)


def cifras(sub: pd.DataFrame, total: int) -> None:
    k = tablero.indicadores(sub)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Siniestros", f"{k['siniestros']:,}".replace(",", "."),
              help=f"{100 * k['siniestros'] / total:.1f} % de los {total:,} de los 10 corredores")
    c2.metric("Con víctimas", f"{k['pct_con_victimas']} %")
    c3.metric("Con muertos", k["con_muertos"])
    c4.metric("Con motocicleta", f"{k['pct_con_moto']} %")


def vista_mapa(sub: pd.DataFrame, zonas: pd.DataFrame) -> None:
    izq, der = st.columns([3, 2])
    with izq:
        modo = st.radio("Mostrar", ["Densidad", "Siniestros por gravedad"], horizontal=True,
                        label_visibility="collapsed")
        centro = dict(lat=4.65, lon=-74.1)
        if modo == "Densidad":
            fig = px.density_map(sub, lat="latitud", lon="longitud", radius=7, zoom=10.3, center=centro,
                                 map_style="open-street-map", color_continuous_scale=ESCALA_DENSIDAD)
            # Tope fijo para que los cruces más densos resalten sobre el resto del corredor.
            fig.update_coloraxes(showscale=False, cmin=0, cmax=5)
        else:
            fig = px.scatter_map(
                sub.assign(Gravedad=sub["gravedad"].astype(str).map(GRAVEDAD_ETIQUETAS)),
                lat="latitud", lon="longitud", color="Gravedad", zoom=10.3, center=centro,
                map_style="open-street-map", opacity=0.75,
                color_discrete_map={GRAVEDAD_ETIQUETAS[g]: c for g, c in GRAVEDAD_COLORES.items()},
                category_orders={"Gravedad": [GRAVEDAD_ETIQUETAS[g] for g in config.GRAVEDAD_ORDEN]},
                hover_data={"nombre_corredor": True, "Direccion": True, "fecha": "|%d/%m/%Y",
                            "latitud": False, "longitud": False},
                labels={"nombre_corredor": "Corredor", "Direccion": "Dirección", "fecha": "Fecha"})
            fig.update_traces(marker_size=7)
            fig.update_layout(legend=dict(orientation="h", y=1.02, x=0))
        st.plotly_chart(estilo(fig, 560), use_container_width=True)
    with der:
        tabla = tablero.por_km(sub)
        fig = px.bar(tabla.sort_values("siniestros_por_km"), x="siniestros_por_km", y="nombre",
                     orientation="h", text="siniestros_por_km", color_discrete_sequence=[AZUL],
                     hover_data={"siniestros": True, "longitud_km": True},
                     labels={"siniestros_por_km": "Siniestros por km", "nombre": "",
                             "siniestros": "Siniestros", "longitud_km": "Longitud (km)"})
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_yaxes(showgrid=False)
        fig.update_xaxes(range=[0, tabla["siniestros_por_km"].max() * 1.2])
        st.markdown("**Siniestros por km de corredor**")
        st.plotly_chart(estilo(fig, 330), use_container_width=True)
        st.markdown("**Zonas densas (DBSCAN, toda la base)**")
        st.dataframe(zonas.head(10)[["posicion", "cruce", "siniestros", "pct_con_muertos"]],
                     hide_index=True, use_container_width=True,
                     column_config={"posicion": "#", "cruce": "Cruce", "siniestros": "Siniestros",
                                    "pct_con_muertos": st.column_config.NumberColumn("% con muertos",
                                                                                     format="%.1f")})


def vista_temporal(sub: pd.DataFrame) -> None:
    matriz = tablero.dia_hora(sub)
    fig = px.imshow(matriz.values, x=list(range(24)), y=DIAS, color_continuous_scale=ESCALA, aspect="auto",
                    labels=dict(x="Hora", y="", color="Siniestros"))
    fig.update_traces(hovertemplate="%{y}, %{x}:00 h<br>%{z} siniestros<extra></extra>", xgap=2, ygap=2)
    fig.update_xaxes(dtick=2, showgrid=False)
    fig.update_yaxes(showgrid=False)
    st.markdown("**Siniestros por día y hora**")
    st.plotly_chart(estilo(fig, 320), use_container_width=True)

    izq, der = st.columns(2)
    meses = sub["mes"].value_counts().reindex(range(1, 13), fill_value=0)
    fig = px.bar(x=MESES, y=meses.values, labels={"x": "", "y": "Siniestros"},
                 color_discrete_sequence=[AZUL])
    fig.update_traces(hovertemplate="%{x}: %{y} siniestros<extra></extra>")
    fig.update_xaxes(showgrid=False)
    izq.markdown("**Por mes**")
    izq.plotly_chart(estilo(fig, 300), use_container_width=True)

    horas = dict(zip(config.FRANJAS, [b - a for a, b in zip(config.FRANJAS_BORDES, config.FRANJAS_BORDES[1:])]))
    conteo = sub["franja"].value_counts().reindex(config.FRANJAS, fill_value=0)
    franjas = pd.DataFrame({"franja": [FRANJAS[f] for f in config.FRANJAS],
                            "por_hora": (conteo / pd.Series(horas)).round(1).values,
                            "siniestros": conteo.values})
    fig = px.bar(franjas, x="franja", y="por_hora", text="por_hora", color_discrete_sequence=[AZUL],
                 hover_data={"siniestros": True},
                 labels={"franja": "", "por_hora": "Siniestros por hora de la franja", "siniestros": "Siniestros"})
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_xaxes(showgrid=False)
    der.markdown("**Por franja (ajustado por las horas que cubre)**")
    der.plotly_chart(estilo(fig, 300), use_container_width=True)


def vista_hipotesis(t: dict[str, pd.DataFrame]) -> None:
    r = t["oe3_resultados"]
    tabla = pd.DataFrame({
        "Hipótesis": r["hipotesis"],
        "Prueba": r["prueba"].str.replace("Prueba z unilateral de proporciones", "z de proporciones"),
        "Estadístico": r["estadistico"],
        "p": r["p_bonferroni"].fillna(r["p_valor"]),
        "Efecto": r["efecto"].str.replace(" (IC 95 %)", "") + " = " + r["valor_efecto"].round(2).astype(str),
        "Magnitud o IC 95 %": r["magnitud_o_ic"],
        "Decisión": r["decision"],
    })
    st.dataframe(tabla, hide_index=True, use_container_width=True,
                 column_config={"Prueba": st.column_config.TextColumn(width="large"),
                                "p": st.column_config.NumberColumn("p", format="%.2e")})
    st.caption("En las cuatro pruebas principales, p ya incluye la corrección de Bonferroni; "
               "las complementarias usan su p-valor. α = 0,05.")
    h1 = t["oe3_h1_corredores"].sort_values("residuo_estandarizado")
    fig = px.bar(h1, x="residuo_estandarizado", y="nombre", orientation="h",
                 color=h1["residuo_estandarizado"] > 0, color_discrete_map={True: NARANJA, False: AZUL},
                 hover_data={"observados": True, "esperados": True},
                 labels={"residuo_estandarizado": "Residuo estandarizado", "nombre": "",
                         "observados": "Observados", "esperados": "Esperados por longitud"})
    fig.update_layout(showlegend=False)
    fig.update_yaxes(showgrid=False)
    st.markdown("**H1: siniestros observados frente a los esperados por la longitud del corredor**")
    st.plotly_chart(estilo(fig, 360), use_container_width=True)


def vista_perfiles(sub: pd.DataFrame, fichas: pd.DataFrame) -> None:
    st.dataframe(fichas[["perfil", "siniestros", "%", "rasgos_dominantes", "corredor_sobrerrepresentado",
                         "%_con_muertos"]],
                 hide_index=True, use_container_width=True,
                 column_config={"perfil": "Perfil", "siniestros": "Siniestros", "%": "% de la base",
                                "rasgos_dominantes": st.column_config.TextColumn("Rasgos dominantes",
                                                                                 width="large"),
                                "corredor_sobrerrepresentado": "Corredor sobrerrepresentado",
                                "%_con_muertos": "% con muertos"})
    composicion = pd.crosstab(sub["perfil"], sub["gravedad"], normalize="index").mul(100).round(1)
    largo = composicion.reset_index().melt(id_vars="perfil", var_name="gravedad", value_name="pct")
    largo["Perfil"] = "Perfil " + largo["perfil"].astype(str)
    largo["Gravedad"] = largo["gravedad"].astype(str).map(GRAVEDAD_ETIQUETAS)
    fig = px.bar(largo, x="Perfil", y="pct", color="Gravedad",
                 color_discrete_map={GRAVEDAD_ETIQUETAS[g]: c for g, c in GRAVEDAD_COLORES.items()},
                 category_orders={"Gravedad": [GRAVEDAD_ETIQUETAS[g] for g in config.GRAVEDAD_ORDEN]},
                 labels={"pct": "% de los siniestros del perfil", "Perfil": ""})
    fig.update_traces(marker_line_color="white", marker_line_width=2,
                      hovertemplate="%{x}<br>%{fullData.name}: %{y:.1f} %<extra></extra>")
    fig.update_layout(legend=dict(orientation="h", y=1.08, x=0))
    fig.update_xaxes(showgrid=False)
    st.markdown("**Gravedad dentro de cada perfil (con los filtros aplicados)**")
    st.plotly_chart(estilo(fig, 380), use_container_width=True)


def vista_reglas(t: dict[str, pd.DataFrame]) -> None:
    st.markdown("**Las 10 reglas interpretadas**")
    for i, texto in enumerate(t["oe5_reglas_seleccion"]["lectura"], 1):
        st.markdown(f"{i}. {texto}")

    st.markdown("**Explorar las reglas**")
    c1, c2, c3 = st.columns([2, 1, 1])
    fuente = c1.selectbox("Conjunto", ["Toda la base", "Hacia siniestros con muertos"]
                          + [f"Perfil {p}" for p in sorted(t["oe5_reglas_por_perfil"]["perfil"].unique())])
    confianza = c2.slider("Confianza mínima", 0.0, 1.0, 0.0, 0.05)
    lift = c3.slider("Lift mínimo", 1.0, 10.0, 1.2, 0.1)
    if fuente == "Toda la base":
        reglas = t["oe5_reglas_globales"]
    elif fuente.startswith("Hacia"):
        reglas = t["oe5_reglas_muertos"]
    else:
        reglas = t["oe5_reglas_por_perfil"].query("perfil == @int(@fuente.split()[1])")
    reglas = reglas[(reglas["confianza"] >= confianza) & (reglas["lift"] >= lift)]
    vista = pd.DataFrame({
        "Si se presenta": reglas["antecedentes"].map(legible),
        "también": reglas["consecuentes"].map(legible),
        "Soporte %": (100 * reglas["soporte"]).round(1),
        "Confianza %": (100 * reglas["confianza"]).round(1),
        "Lift": reglas["lift"].round(2),
    })
    st.caption(f"{len(vista)} reglas")
    st.dataframe(vista, hide_index=True, use_container_width=True, height=420,
                 column_config={"Lift": st.column_config.ProgressColumn(
                     "Lift", format="%.1f", min_value=0, max_value=float(max(vista["Lift"].max(), 1)))})


def main() -> None:
    st.set_page_config(page_title="Siniestralidad vial en corredores de Bogotá", page_icon="🚦", layout="wide")
    st.title("Siniestralidad vial en corredores de Bogotá")
    st.caption(f"Los 10 corredores con más siniestros. Base del SIMUR, {config.ANIO}. Los resultados describen asociaciones "
               "en los registros, no causas.")
    try:
        df, t = datos()
    except FileNotFoundError as e:
        st.error(str(e))
        st.stop()

    sub = filtros(df)
    cifras(sub, len(df))
    if sub.empty:
        st.warning("Ningún siniestro cumple los filtros.")
        st.stop()
    mapa, temporal, hipotesis, perfiles, reglas = st.tabs(
        ["Mapa", "Comportamiento temporal", "Hipótesis", "Perfiles", "Reglas"])
    with mapa:
        vista_mapa(sub, t["oe4_zonas_densas"])
    with temporal:
        vista_temporal(sub)
    with hipotesis:
        vista_hipotesis(t)
    with perfiles:
        vista_perfiles(sub, t["oe4_perfiles"])
    with reglas:
        vista_reglas(t)


if __name__ == "__main__":
    main()
