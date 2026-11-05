"""Gráficos y mapas de los objetivos específicos 2 a 5.

Los PNG utilizan verde, amarillo, naranja y rojo para magnitudes; la gravedad
conserva verde (daños), amarillo (heridos) y rojo (muertos).
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, Normalize, BoundaryNorm
from . import cartografia  # noqa: E402

from . import config  # noqa: E402
from .asociacion import legible  # noqa: E402
from .descriptivo import MESES, dia_por_hora, por_actor, por_corredor, por_franja, por_mes  # noqa: E402

TEXTO = "#0b0b0b"
TEXTO_2 = "#52514e"
REJILLA = "#e6e5e0"
SUPERFICIE = "#ffffff"
AZUL = "#2e7d32"
COLORES = ["#2e7d32", "#a6c96a", "#fdd835", "#fb8c00", "#c62828"]
ESCALA = LinearSegmentedColormap.from_list("concentracion", COLORES)

def colores_magnitud(valores):
    valores = list(valores)
    normalizar = Normalize(vmin=0, vmax=max(valores) or 1)
    return [ESCALA(normalizar(v)) for v in valores]
# Escala de magnitud; se mantienen alias para compatibilidad con el tablero.
AZULES = COLORES
# Gravedad es ordinal: tres pasos de la misma escala, del más claro al más oscuro.
GRAVEDAD_COLORES = {"solo danos": "#2e7d32", "con heridos": "#f9a825", "con muertos": "#c62828"}
GRAVEDAD_ETIQUETAS = {"solo danos": "Solo daños", "con heridos": "Con heridos", "con muertos": "Con muertos"}
FRANJA_ETIQUETAS = {
    "madrugada": "Madrugada\n0–6 h", "manana": "Mañana\n6–10 h", "mediodia": "Mediodía\n10–16 h",
    "tarde": "Tarde\n16–20 h", "noche": "Noche\n20–24 h",
}
DIAS_ETIQUETAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

plt.rcParams.update({
    "font.family": ["DejaVu Sans"],
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
    ax.barh(tabla["nombre"], tabla["siniestros_por_km"], color=colores_magnitud(tabla["siniestros_por_km"]), height=0.6,
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
    ax.bar(etiquetas, tabla["siniestros_por_hora"], color=colores_magnitud(tabla["siniestros_por_hora"]), width=0.55,
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
    ax.scatter(tabla["nombre"], tabla["siniestros"], c=colores_magnitud(tabla["siniestros"]), s=45, edgecolors="white", zorder=4)
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
    ax.barh(tabla["actor"], tabla["%_de_siniestros"], color=colores_magnitud(tabla["%_de_siniestros"]), height=0.6,
            edgecolor=SUPERFICIE, linewidth=2)
    ax.grid(axis="y", visible=False)
    for y, v in enumerate(tabla["%_de_siniestros"]):
        ax.text(v + 0.8, y, f"{v:.1f} %", va="center", fontsize=8.5, color=TEXTO_2)
    ax.set_xlim(0, tabla["%_de_siniestros"].max() * 1.15)
    ax.set_xlabel("% de siniestros en que participa (un siniestro puede tener varios)")
    ax.set_title("Actores viales y vehículos involucrados")
    return _guardar(fig, "oe2_actores", carpeta)


def mapa_concentracion(df: pd.DataFrame, carpeta: Path = config.FIGURAS) -> Path:
    """Conteos por celda sobre calles reales, con leyenda, norte y escala."""
    lat, lon = df["latitud"], df["longitud"]
    dentro = lat.between(*lat.quantile([0.002,0.998])) & lon.between(*lon.quantile([0.002,0.998]))
    x,y=cartografia.mercator(lon[dentro],lat[dentro])
    limites=(x.min()-1700,x.max()+1700,y.min()-1200,y.max()+1200)
    fig,ax=plt.subplots(figsize=(8,10))
    cartografia.fondo(ax,limites)
    cmap=LinearSegmentedColormap.from_list("concentracion_mapa",COLORES,N=5)
    norm=BoundaryNorm([1,5,10,20,40,10000],cmap.N)
    hb=ax.hexbin(x,y,gridsize=(34,42),mincnt=1,cmap=cmap,norm=norm,
                 alpha=.72,linewidths=.15,edgecolors="white",zorder=2)
    # Las etiquetas identifican el eje asignado; no reconstruyen su trazado.
    from .corredores import NOMBRES
    for corredor in ["KR 72","KR 14","KR 30","KR 86","KR 10","CL 26"]:
        sub=df[df.corredor==corredor]
        xx,yy=cartografia.mercator(sub.longitud.median(),sub.latitud.median())
        ax.annotate(NOMBRES[corredor].replace("Avenida ","Av. "),(xx,yy),xytext=(5,7),
                    textcoords="offset points",fontsize=7,zorder=8,
                    bbox=dict(facecolor="white",edgecolor="#777777",boxstyle="round,pad=.25",alpha=.92))
    from matplotlib.patches import Patch
    handles=[Patch(facecolor=COLORES[i],label=t) for i,t in enumerate(["1–4","5–9","10–19","20–39","40 o más"])]
    ax.legend(handles=handles,title="Siniestros por celda",loc="lower right",framealpha=.95,fontsize=8,title_fontsize=9)
    cartografia.marco(ax,limites)
    ax.set_title("Bogotá: concentración de siniestros, 2024",fontsize=13)
    ax.text(.01,.98,f"{dentro.sum():,} eventos en la vista urbana; {len(df)-dentro.sum()} fuera del encuadre",
            transform=ax.transAxes,fontsize=8,va="top",zorder=10,bbox=dict(facecolor="white",alpha=.9,edgecolor="none"))
    fig.tight_layout()
    return _guardar(fig,"oe2_mapa_concentracion",carpeta)


def mapa_detalle(df: pd.DataFrame, carpeta: Path = config.FIGURAS) -> Path:
    """Acercamiento al sector central; complementa el mapa general sin filtrar la base."""
    lon_min,lon_max,lat_min,lat_max=-74.17,-74.035,4.56,4.715
    xlim,ylim=cartografia.mercator(np.array([lon_min,lon_max]),np.array([lat_min,lat_max]))
    limites=(xlim[0],xlim[1],ylim[0],ylim[1])
    dentro=df.longitud.between(lon_min,lon_max) & df.latitud.between(lat_min,lat_max)
    x,y=cartografia.mercator(df.loc[dentro,"longitud"],df.loc[dentro,"latitud"])
    fig,ax=plt.subplots(figsize=(7.5,8))
    cartografia.fondo(ax,limites,zoom=13)
    cmap=LinearSegmentedColormap.from_list("detalle",COLORES,N=5)
    hb=ax.hexbin(x,y,gridsize=(24, max(1, round(24*(ylim[1]-ylim[0])/(xlim[1]-xlim[0])/3**.5))),extent=limites,mincnt=1,cmap=cmap,
                norm=BoundaryNorm([1,5,10,20,40,10000],5),alpha=.8,linewidths=.2,edgecolors="white",zorder=2)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(facecolor=COLORES[i],label=t) for i,t in enumerate(["1–4","5–9","10–19","20–39","40 o más"])],
              title="Eventos por celda",loc="lower right",framealpha=.96,fontsize=8,title_fontsize=9)
    cartografia.marco(ax,limites)
    ax.set_title("Detalle de Bogotá: sector central y occidental",fontsize=12)
    ax.text(.01,.98,f"{dentro.sum():,} eventos en este encuadre",transform=ax.transAxes,va="top",fontsize=8,zorder=10,
            bbox=dict(facecolor="white",alpha=.95,edgecolor="none"))
    fig.tight_layout()
    return _guardar(fig,"oe2_mapa_detalle",carpeta)


def mapa_interactivo(df: pd.DataFrame, carpeta: Path = config.FIGURAS) -> Path:
    """Mapa de calor sobre OpenStreetMap (HTML), con los siniestros con muertos marcados."""
    import folium
    from folium.plugins import HeatMap

    centro = [df["latitud"].median(), df["longitud"].median()]
    mapa = folium.Map(location=centro, zoom_start=12, tiles="OpenStreetMap")
    HeatMap(df[["latitud", "longitud"]].values.tolist(), radius=9, blur=12,
            gradient={0.2: "green", 0.45: "yellow", 0.7: "orange", 1.0: "red"},
            name="Todos los siniestros").add_to(mapa)
    muertos = folium.FeatureGroup(name="Siniestros con muertos")
    for _, fila in df[df["gravedad"] == "con muertos"].iterrows():
        folium.CircleMarker(
            [fila["latitud"], fila["longitud"]], radius=4, color="#c62828", weight=1,
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
    colores = ["#c62828" if r > 0 else "#2e7d32" for r in tabla["residuo_estandarizado"]]
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
        ax.plot([k], [elegido], marker="o", markersize=10, color="#c62828",
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
    """Zonas de DBSCAN en fondo vial; color representa tamaño de la zona."""
    lat,lon=df.latitud,df.longitud
    dentro=lat.between(*lat.quantile([.002,.998])) & lon.between(*lon.quantile([.002,.998]))
    x,y=cartografia.mercator(lon,lat)
    limites=(x[dentro].min()-1700,x[dentro].max()+1700,y[dentro].min()-1200,y[dentro].max()+1200)
    fig,ax=plt.subplots(figsize=(8,10)); cartografia.fondo(ax,limites)
    en_zona=zonas>=0
    ax.scatter(x[~en_zona],y[~en_zona],s=5,color="#777777",alpha=.5,linewidths=0,label="Sin agrupación",zorder=2)
    tamanos=pd.Series(zonas[en_zona]).value_counts()
    magnitudes=pd.Series(zonas[en_zona]).map(tamanos).to_numpy()
    puntos=ax.scatter(x[en_zona],y[en_zona],s=12,c=magnitudes,cmap=ESCALA,linewidths=.2,edgecolors="#333333",zorder=3)
    for _,z in resumen.head(n_etiquetas).iterrows():
        xx,yy=cartografia.mercator(z.longitud,z.latitud)
        ax.annotate(str(z.posicion),(xx,yy),xytext=(5,5),textcoords="offset points",fontsize=10,fontweight="bold",zorder=8,
                    bbox=dict(facecolor="white",edgecolor="#555555",boxstyle="circle,pad=.2"))
    cartografia.marco(ax,limites)
    cb=fig.colorbar(puntos,ax=ax,fraction=.035,pad=.02); cb.set_label("Eventos en la zona DBSCAN")
    ax.legend(loc="lower right",framealpha=.95,fontsize=8)
    ax.set_title("Bogotá: zonas densas identificadas con DBSCAN",fontsize=12)
    fig.tight_layout()
    return _guardar(fig,"oe4_zonas_densas",carpeta)


def reglas_lift(seleccion: pd.DataFrame, carpeta: Path = config.FIGURAS) -> Path:
    """Lift de las reglas seleccionadas: cuántas veces más frecuente es la
    combinación de lo que se esperaría si fuera independiente."""
    tabla = seleccion.iloc[::-1]
    etiquetas = [f"R{i}" for i in range(len(tabla), 0, -1)]
    fig, ax = plt.subplots(figsize=(7, 0.38 * len(tabla) + 1.3))
    ax.barh(range(len(tabla)), tabla["lift"], color=colores_magnitud(tabla["lift"]), height=0.6, edgecolor=SUPERFICIE, linewidth=2)
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
        meses, actores, mapa_concentracion, mapa_detalle, mapa_interactivo,
    )]
