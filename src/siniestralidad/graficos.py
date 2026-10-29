"""Gráficos y mapa del análisis descriptivo (OE2).

Los PNG están pensados para el documento: fondo blanco, un solo color por
serie y la escala azul del proyecto para magnitudes.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

from . import config  # noqa: E402
from .asociacion import legible  # noqa: E402
from .descriptivo import MESES, dia_por_hora, por_actor, por_corredor, por_franja, por_mes  # noqa: E402

TEXTO = "#0b0b0b"
TEXTO_2 = "#52514e"
REJILLA = "#e6e5e0"
SUPERFICIE = "#ffffff"
AZUL = "#2a78d6"
# Escala azul secuencial (de casi cero a máximo).
AZULES = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
# Gravedad es ordinal: tres pasos de la misma escala, del más claro al más oscuro.
GRAVEDAD_COLORES = {"solo danos": "#86b6ef", "con heridos": "#2a78d6", "con muertos": "#104281"}
GRAVEDAD_ETIQUETAS = {"solo danos": "Solo daños", "con heridos": "Con heridos", "con muertos": "Con muertos"}
FRANJA_ETIQUETAS = {
    "madrugada": "Madrugada\n0–6 h", "manana": "Mañana\n6–10 h", "mediodia": "Mediodía\n10–16 h",
    "tarde": "Tarde\n16–20 h", "noche": "Noche\n20–24 h",
}
DIAS_ETIQUETAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

plt.rcParams.update({
    "font.family": ["Inter", "DejaVu Sans"],
    "font.size": 10,
    "text.color": TEXTO,
    "axes.labelcolor": TEXTO_2,
    "axes.edgecolor": REJILLA,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "axes.titlepad": 12,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.spines.left": False,
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.color": REJILLA,
    "grid.linewidth": 0.8,
    "xtick.color": TEXTO_2,
    "ytick.color": TEXTO_2,
    "xtick.major.size": 0,
    "ytick.major.size": 0,
    "figure.facecolor": SUPERFICIE,
    "axes.facecolor": SUPERFICIE,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
})


def _guardar(fig, nombre: str, carpeta: Path) -> Path:
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"{nombre}.png"
    fig.savefig(ruta)
    plt.close(fig)
    return ruta


def corredores_por_km(df: pd.DataFrame, carpeta: Path = config.FIGURAS) -> Path:
    tabla = por_corredor(df).sort_values("siniestros_por_km")
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.barh(tabla["nombre"], tabla["siniestros_por_km"], color=AZUL, height=0.6,
            edgecolor=SUPERFICIE, linewidth=2)
    ax.grid(axis="y", visible=False)
    for y, (por_km, total) in enumerate(zip(tabla["siniestros_por_km"], tabla["siniestros"])):
        ax.text(por_km + 0.5, y, f"{por_km:.1f}  ({total} en total)", va="center",
                fontsize=8.5, color=TEXTO_2)
    ax.set_xlim(0, tabla["siniestros_por_km"].max() * 1.35)
    ax.set_xlabel("Siniestros por kilómetro")
    ax.set_title("Siniestros por kilómetro en cada corredor, 2024")
    return _guardar(fig, "oe2_corredores_por_km", carpeta)


def calor_dia_hora(df: pd.DataFrame, carpeta: Path = config.FIGURAS) -> Path:
    tabla = dia_por_hora(df)
    fig, ax = plt.subplots(figsize=(8, 3.2))
    mapa = LinearSegmentedColormap.from_list("azules", AZULES)
    img = ax.imshow(tabla.values, aspect="auto", cmap=mapa, vmin=0)
    ax.grid(False)
    ax.set_yticks(range(7), DIAS_ETIQUETAS)
    ax.set_xticks(range(0, 24, 2), [f"{h}" for h in range(0, 24, 2)])
    ax.set_xlabel("Hora del día")
    barra = fig.colorbar(img, ax=ax, pad=0.01, fraction=0.03)
    barra.outline.set_visible(False)
    barra.ax.tick_params(colors=TEXTO_2, size=0)
    barra.set_label("Siniestros", color=TEXTO_2)
    ax.set_title("Siniestros por día de la semana y hora, 2024")
    return _guardar(fig, "oe2_dia_por_hora", carpeta)


def franjas_por_hora(df: pd.DataFrame, carpeta: Path = config.FIGURAS) -> Path:
    tabla = por_franja(df)
    fig, ax = plt.subplots(figsize=(7, 3.6))
    etiquetas = [FRANJA_ETIQUETAS[f] for f in tabla["franja"]]
    ax.bar(etiquetas, tabla["siniestros_por_hora"], color=AZUL, width=0.55,
           edgecolor=SUPERFICIE, linewidth=2)
    ax.grid(axis="x", visible=False)
    for x, v in enumerate(tabla["siniestros_por_hora"]):
        ax.text(x, v + 2, f"{v:.0f}", ha="center", fontsize=9, color=TEXTO_2)
    ax.set_ylabel("Siniestros por hora de la franja")
    ax.set_title("Siniestros por franja horaria, ajustados por su duración")
    return _guardar(fig, "oe2_franjas", carpeta)


def gravedad_por_franja(df: pd.DataFrame, carpeta: Path = config.FIGURAS) -> Path:
    tabla = pd.crosstab(df["franja"], df["gravedad"], normalize="index").mul(100)
    fig, ax = plt.subplots(figsize=(7, 3.8))
    etiquetas = [FRANJA_ETIQUETAS[f] for f in tabla.index]
    base = pd.Series(0.0, index=tabla.index)
    for cat in config.GRAVEDAD_ORDEN:
        ax.bar(etiquetas, tabla[cat], bottom=base, width=0.55, color=GRAVEDAD_COLORES[cat],
               edgecolor=SUPERFICIE, linewidth=2, label=GRAVEDAD_ETIQUETAS[cat])
        base += tabla[cat]
    for x, v in enumerate(tabla["con muertos"]):
        ax.text(x, 103, f"{v:.1f} %\ncon muertos", ha="center", va="bottom", fontsize=8,
                color=TEXTO_2, linespacing=1.1)
    ax.set_ylim(0, 118)
    ax.set_yticks(range(0, 101, 20))
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("% de los siniestros de la franja")
    ax.legend(ncols=3, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.2))
    ax.set_title("Gravedad de los siniestros según la franja horaria")
    return _guardar(fig, "oe2_gravedad_por_franja", carpeta)


def meses(df: pd.DataFrame, carpeta: Path = config.FIGURAS) -> Path:
    tabla = por_mes(df)
    fig, ax = plt.subplots(figsize=(7, 3.2))
    ax.plot(tabla["nombre"], tabla["siniestros"], color=AZUL, linewidth=2, marker="o",
            markersize=5, markeredgecolor=SUPERFICIE, markeredgewidth=1.5)
    ax.grid(axis="x", visible=False)
    ax.set_ylim(0, tabla["siniestros"].max() * 1.2)
    maximo = tabla.loc[tabla["siniestros"].idxmax()]
    ax.annotate(f"{maximo['siniestros']}", (maximo["nombre"], maximo["siniestros"]),
                textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9, color=TEXTO_2)
    ax.set_ylabel("Siniestros")
    ax.set_title("Siniestros por mes, 2024")
    return _guardar(fig, "oe2_meses", carpeta)


def actores(df: pd.DataFrame, carpeta: Path = config.FIGURAS) -> Path:
    tabla = por_actor(df).sort_values("%_de_siniestros")
    fig, ax = plt.subplots(figsize=(7, 3.8))
    ax.barh(tabla["actor"], tabla["%_de_siniestros"], color=AZUL, height=0.6,
            edgecolor=SUPERFICIE, linewidth=2)
    ax.grid(axis="y", visible=False)
    for y, v in enumerate(tabla["%_de_siniestros"]):
        ax.text(v + 0.8, y, f"{v:.1f} %", va="center", fontsize=8.5, color=TEXTO_2)
    ax.set_xlim(0, tabla["%_de_siniestros"].max() * 1.15)
    ax.set_xlabel("% de siniestros en que participa (un siniestro puede tener varios)")
    ax.set_title("Actores viales y vehículos involucrados")
    return _guardar(fig, "oe2_actores", carpeta)


def mapa_concentracion(df: pd.DataFrame, carpeta: Path = config.FIGURAS) -> Path:
    """Mapa de calor estático: densidad de siniestros en celdas hexagonales."""
    # Se recortan las coordenadas extremas para que un punto aislado no aplaste el mapa.
    lat, lon = df["latitud"], df["longitud"]
    dentro = lat.between(*lat.quantile([0.002, 0.998])) & lon.between(*lon.quantile([0.002, 0.998]))
    lat, lon = lat[dentro], lon[dentro]
    nx = 30
    ny = max(1, round(nx * (lat.max() - lat.min()) / (lon.max() - lon.min()) / 3 ** 0.5))
    fig, ax = plt.subplots(figsize=(6, 7.5))
    mapa = LinearSegmentedColormap.from_list("azules", AZULES)
    hb = ax.hexbin(lon, lat, gridsize=(nx, ny), cmap=mapa, mincnt=1,
                   linewidths=0.4, edgecolors=SUPERFICIE)
    ax.set_aspect("equal")
    ax.grid(False)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    barra = fig.colorbar(hb, ax=ax, pad=0.01, fraction=0.035)
    barra.outline.set_visible(False)
    barra.ax.tick_params(colors=TEXTO_2, size=0)
    barra.set_label("Siniestros por celda", color=TEXTO_2)
    ax.set_title("Concentración de siniestros en los 10 corredores, 2024")
    return _guardar(fig, "oe2_mapa_concentracion", carpeta)


def mapa_interactivo(df: pd.DataFrame, carpeta: Path = config.FIGURAS) -> Path:
    """Mapa de calor sobre OpenStreetMap (HTML), con los siniestros con muertos marcados."""
    import folium
    from folium.plugins import HeatMap

    centro = [df["latitud"].median(), df["longitud"].median()]
    mapa = folium.Map(location=centro, zoom_start=12, tiles="OpenStreetMap")
    HeatMap(df[["latitud", "longitud"]].values.tolist(), radius=9, blur=12,
            name="Todos los siniestros").add_to(mapa)
    muertos = folium.FeatureGroup(name="Siniestros con muertos")
    for _, fila in df[df["gravedad"] == "con muertos"].iterrows():
        folium.CircleMarker(
            [fila["latitud"], fila["longitud"]], radius=4, color="#104281", weight=1,
            fill=True, fill_opacity=0.8,
            tooltip=f"{fila['corredor']} · {fila['fecha']:%d/%m/%Y} {fila['hora']}:00",
        ).add_to(muertos)
    muertos.add_to(mapa)
    folium.LayerControl().add_to(mapa)
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / "oe2_mapa_interactivo.html"
    mapa.save(ruta)
    return ruta


def residuos_h1(tabla: pd.DataFrame, carpeta: Path = config.FIGURAS) -> Path:
    """Residuos estandarizados de H1: qué corredores tienen más siniestros de los
    esperados por su longitud (positivos) y cuáles menos (negativos)."""
    tabla = tabla.sort_values("residuo_estandarizado")
    colores = ["#eb6834" if r > 0 else AZUL for r in tabla["residuo_estandarizado"]]
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.barh(tabla["nombre"], tabla["residuo_estandarizado"], color=colores, height=0.6,
            edgecolor=SUPERFICIE, linewidth=2)
    ax.axvline(0, color=TEXTO_2, linewidth=0.8)
    ax.grid(axis="y", visible=False)
    for y, (r, obs, esp) in enumerate(zip(tabla["residuo_estandarizado"], tabla["observados"],
                                          tabla["esperados"])):
        ax.text(r + (0.4 if r > 0 else -0.4), y, f"{obs} vs. {esp:.0f}", va="center",
                ha="left" if r > 0 else "right", fontsize=8.5, color=TEXTO_2)
    limite = tabla["residuo_estandarizado"].abs().max() * 1.45
    ax.set_xlim(-limite, limite)
    ax.set_xlabel("Residuo estandarizado (observados vs. esperados por longitud)")
    ax.set_title("H1: siniestros observados frente a los esperados por longitud")
    return _guardar(fig, "oe3_h1_residuos", carpeta)


def seleccion_k(evaluacion: pd.DataFrame, k: int, carpeta: Path = config.FIGURAS) -> Path:
    """Método del codo y coeficiente de silueta, en dos paneles (no doble eje)."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 3.4))
    for ax, col, titulo in ((ax1, "inercia", "Método del codo (inercia)"),
                            (ax2, "silueta", "Coeficiente de silueta")):
        ax.plot(evaluacion["k"], evaluacion[col], color=AZUL, linewidth=2, marker="o",
                markersize=5, markeredgecolor=SUPERFICIE, markeredgewidth=1.5)
        elegido = evaluacion.loc[evaluacion["k"] == k, col].iloc[0]
        ax.plot([k], [elegido], marker="o", markersize=10, color="#eb6834",
                markeredgecolor=SUPERFICIE, markeredgewidth=2)
        ax.set_xticks(evaluacion["k"])
        ax.set_xlabel("Número de perfiles (k)")
        ax.grid(axis="x", visible=False)
        ax.set_title(titulo, fontsize=11)
    ax2.annotate(f"k = {k}", (k, evaluacion.loc[evaluacion["k"] == k, "silueta"].iloc[0]),
                 textcoords="offset points", xytext=(0, 10), ha="center", fontsize=9, color=TEXTO_2)
    fig.tight_layout()
    return _guardar(fig, "oe4_seleccion_k", carpeta)


def perfiles_gravedad(fichas: pd.DataFrame, carpeta: Path = config.FIGURAS) -> Path:
    """Composición de gravedad de cada perfil (barras apiladas al 100 %)."""
    tabla = fichas.set_index("perfil")[["%_solo_danos", "%_con_heridos", "%_con_muertos"]]
    tabla.columns = config.GRAVEDAD_ORDEN
    fig, ax = plt.subplots(figsize=(7, 3.8))
    etiquetas = [f"Perfil {p}" for p in tabla.index]
    base = pd.Series(0.0, index=tabla.index)
    for cat in config.GRAVEDAD_ORDEN:
        ax.bar(etiquetas, tabla[cat], bottom=base, width=0.55, color=GRAVEDAD_COLORES[cat],
               edgecolor=SUPERFICIE, linewidth=2, label=GRAVEDAD_ETIQUETAS[cat])
        base += tabla[cat]
    for x, v in enumerate(tabla["con muertos"]):
        ax.text(x, 103, f"{v:.1f} %", ha="center", va="bottom", fontsize=8, color=TEXTO_2)
    ax.set_ylim(0, 112)
    ax.set_yticks(range(0, 101, 20))
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("% de los siniestros del perfil")
    ax.legend(ncols=3, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    ax.set_title("Gravedad por perfil (arriba, % con muertos)")
    return _guardar(fig, "oe4_perfiles_gravedad", carpeta)


def mapa_zonas(df: pd.DataFrame, zonas, resumen: pd.DataFrame, carpeta: Path = config.FIGURAS,
               n_etiquetas: int = 5) -> Path:
    """Zonas densas de DBSCAN: siniestros en zona en azul, aislados en gris."""
    fig, ax = plt.subplots(figsize=(6, 7.5))
    en_zona = zonas >= 0
    ax.scatter(df.loc[~en_zona, "longitud"], df.loc[~en_zona, "latitud"], s=3, color="#d6d5d0",
               linewidths=0, label="Siniestro aislado")
    ax.scatter(df.loc[en_zona, "longitud"], df.loc[en_zona, "latitud"], s=5, color=AZUL,
               linewidths=0, label="Siniestro en zona densa")
    centro = df["longitud"].median()
    for _, z in resumen.head(n_etiquetas).iterrows():
        izquierda = z["longitud"] < centro  # las etiquetas del oeste van a la izquierda
        ax.annotate(f"{z['posicion']}. {z['cruce']} ({z['siniestros']})",
                    (z["longitud"], z["latitud"]), textcoords="offset points",
                    xytext=(-8 if izquierda else 8, 0), ha="right" if izquierda else "left",
                    fontsize=7.5, color=TEXTO, va="center")
    lat, lon = df["latitud"], df["longitud"]
    ax.set_xlim(*lon.quantile([0.002, 0.998]).add([-0.03, 0.03]))
    ax.set_ylim(*lat.quantile([0.002, 0.998]).add([-0.005, 0.005]))
    ax.set_aspect("equal")
    ax.grid(False)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.legend(frameon=False, loc="lower right", markerscale=3, fontsize=8.5)
    ax.set_title("Zonas densas de siniestros (DBSCAN)")
    return _guardar(fig, "oe4_zonas_densas", carpeta)


def reglas_lift(seleccion: pd.DataFrame, carpeta: Path = config.FIGURAS) -> Path:
    """Lift de las reglas seleccionadas: cuántas veces más frecuente es la
    combinación de lo que se esperaría si fuera independiente."""
    tabla = seleccion.iloc[::-1]
    etiquetas = [f"{legible(a)}  →  {legible(c)}" for a, c in
                 zip(tabla["antecedentes"], tabla["consecuentes"])]
    fig, ax = plt.subplots(figsize=(9, 0.45 * len(tabla) + 1.2))
    ax.barh(range(len(tabla)), tabla["lift"], color=AZUL, height=0.6, edgecolor=SUPERFICIE, linewidth=2)
    ax.axvline(1, color=TEXTO_2, linewidth=0.8)
    ax.set_yticks(range(len(tabla)), etiquetas, fontsize=8.5)
    ax.grid(axis="y", visible=False)
    for y, (l, c) in enumerate(zip(tabla["lift"], tabla["confianza"])):
        ax.text(l + 0.15, y, f"{l:.1f}×  ({100 * c:.0f} %)", va="center", fontsize=8.5, color=TEXTO_2)
    ax.set_xlim(0, tabla["lift"].max() * 1.25)
    ax.set_xlabel("Lift (1 = independencia); entre paréntesis, la confianza")
    ax.set_title("Reglas de asociación seleccionadas")
    return _guardar(fig, "oe5_reglas_lift", carpeta)


def todos(df: pd.DataFrame, carpeta: Path = config.FIGURAS) -> list[Path]:
    return [f(df, carpeta) for f in (
        corredores_por_km, calor_dia_hora, franjas_por_hora, gravedad_por_franja,
        meses, actores, mapa_concentracion, mapa_interactivo,
    )]
