"""Perfiles de siniestralidad con K-means y zonas densas con DBSCAN (OE4).

K-means agrupa los siniestros por sus características (franja, tipo de día,
clase y actores involucrados). La gravedad no entra al modelo: se usa después
para ver si la composición de gravedad cambia entre perfiles.
"""

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import DBSCAN, KMeans
from sklearn.metrics import silhouette_score

from .corredores import NOMBRES
from .hipotesis import magnitud_v, v_cramer

K_MIN, K_MAX = 3, 8
SEMILLA = 42

# Indicadores de actor y circunstancia que entran al modelo.
INDICADORES = {
    "con_moto": "moto",
    "con_peaton": "peatón",
    "con_bicicleta": "bicicleta",
    "con_tpp": "transporte público",
    "con_tpi": "taxi",
    "con_carga": "carga",
    "con_persona_mayor": "persona mayor",
    "con_menores": "menor de edad",
    "con_embriaguez": "embriaguez",
    "con_velocidad": "velocidad",
}
CLASES = ["choque", "atropello", "caida de ocupante", "volcamiento"]

RADIO_TIERRA_M = 6_371_000


def matriz(df: pd.DataFrame) -> pd.DataFrame:
    """Codifica cada siniestro como un vector de 0 y 1 (variables dicotómicas y one-hot)."""
    partes = [
        pd.get_dummies(df["franja"].astype(str), prefix="franja"),
        df["fin_semana"].astype(int).rename("fin_semana"),
        pd.get_dummies(df["clase"].where(df["clase"].isin(CLASES), "otra"), prefix="clase"),
    ]
    partes += [df[c].astype(int).rename(c) for c in INDICADORES if c in df.columns]
    return pd.concat(partes, axis=1).astype(float)


def evaluar_k(x: pd.DataFrame, k_min: int = K_MIN, k_max: int = K_MAX) -> pd.DataFrame:
    """Inercia (método del codo) y coeficiente de silueta para cada k."""
    filas = []
    for k in range(k_min, k_max + 1):
        modelo = KMeans(n_clusters=k, n_init=20, random_state=SEMILLA).fit(x)
        filas.append({
            "k": k,
            "inercia": round(modelo.inertia_, 1),
            "silueta": round(silhouette_score(x, modelo.labels_, sample_size=min(len(x), 3000),
                                              random_state=SEMILLA), 4),
        })
    return pd.DataFrame(filas)


def kmeans(x: pd.DataFrame, k: int) -> np.ndarray:
    return KMeans(n_clusters=k, n_init=20, random_state=SEMILLA).fit_predict(x)


def fichas(df: pd.DataFrame, x: pd.DataFrame, etiquetas: np.ndarray, n_rasgos: int = 4) -> pd.DataFrame:
    """Ficha de cada perfil: tamaño, rasgos dominantes, corredor sobrerrepresentado
    y composición de gravedad.

    Los rasgos dominantes son las variables cuya proporción en el perfil más se
    aleja (por encima) de la proporción en toda la base.
    """
    global_ = x.mean()
    peso_corredor = df["corredor"].value_counts(normalize=True)
    filas = []
    for perfil in sorted(np.unique(etiquetas)):
        mascara = etiquetas == perfil
        sub, xs = df[mascara], x[mascara]
        diferencia = (xs.mean() - global_).sort_values(ascending=False)
        rasgos = [f"{_nombre_variable(v)} ({100 * xs[v].mean():.0f} %)"
                  for v in diferencia.index[:n_rasgos] if diferencia[v] > 0.05]
        gravedad = sub["gravedad"].value_counts(normalize=True).mul(100)
        # Corredor con mayor peso en el perfil que en toda la base (no el más grande).
        lift = sub["corredor"].value_counts(normalize=True) / peso_corredor
        corredor = lift.idxmax()
        filas.append({
            "perfil": int(perfil) + 1,
            "siniestros": int(mascara.sum()),
            "%": round(100 * mascara.mean(), 1),
            "rasgos_dominantes": "; ".join(rasgos),
            "corredor_sobrerrepresentado": f"{NOMBRES.get(corredor, corredor)} (×{lift.max():.2f})",
            "%_fin_de_semana": round(100 * sub["fin_semana"].astype(bool).mean(), 1),
            "%_solo_danos": round(gravedad.get("solo danos", 0), 1),
            "%_con_heridos": round(gravedad.get("con heridos", 0), 1),
            "%_con_muertos": round(gravedad.get("con muertos", 0), 1),
        })
    return pd.DataFrame(filas)


def _nombre_variable(v: str) -> str:
    if v in INDICADORES:
        return INDICADORES[v]
    if v.startswith("franja_"):
        return f"franja {v.removeprefix('franja_')}"
    if v.startswith("clase_"):
        return v.removeprefix("clase_")
    return v.replace("_", " ")


def gravedad_por_perfil(df: pd.DataFrame, etiquetas: np.ndarray) -> dict:
    """Chi-cuadrado: ¿la composición de gravedad difiere entre perfiles?"""
    tabla = pd.crosstab(etiquetas + 1, df["gravedad"])
    chi2, p, gl, esperados = stats.chi2_contingency(tabla)
    v = v_cramer(chi2, int(tabla.values.sum()), min(tabla.shape))
    return {"chi2": round(chi2, 3), "gl": gl, "p_valor": p, "v_cramer": round(v, 3),
            "magnitud": magnitud_v(v), "esperados_>=5": bool((esperados >= 5).all())}


def zonas_densas(df: pd.DataFrame, radio_m: float = 150, minimo: int = 15) -> np.ndarray:
    """DBSCAN sobre coordenadas con distancia haversine. -1 = siniestro aislado."""
    coords = np.radians(df[["latitud", "longitud"]].to_numpy())
    modelo = DBSCAN(eps=radio_m / RADIO_TIERRA_M, min_samples=minimo, metric="haversine",
                    algorithm="ball_tree")
    return modelo.fit_predict(coords)


def resumen_zonas(df: pd.DataFrame, zonas: np.ndarray) -> pd.DataFrame:
    """Una fila por zona densa: tamaño, centro, corredor principal y gravedad."""
    sub = df.assign(zona=zonas)[zonas >= 0]
    if sub.empty:
        return pd.DataFrame()
    tabla = sub.groupby("zona").agg(
        siniestros=("zona", "size"),
        latitud=("latitud", "mean"),
        longitud=("longitud", "mean"),
        corredor=("corredor", lambda s: NOMBRES.get(s.mode()[0], s.mode()[0])),
        cruce=("Direccion", lambda s: s.str.replace(r"\s+\d+$", "", regex=True)
               .str.replace(r"\s*-\s*", " - ", regex=True).str.replace(r"\s+", " ", regex=True)
               .str.replace("AV AVENIDA ", "AV ").mode()[0]),
        localidad=("localidad", lambda s: s.mode()[0]),
        pct_con_muertos=("gravedad", lambda s: round(100 * (s == "con muertos").mean(), 1)),
        pct_con_moto=("con_moto", lambda s: round(100 * s.astype(bool).mean(), 1)),
    ).sort_values("siniestros", ascending=False)
    tabla["latitud"] = tabla["latitud"].round(5)
    tabla["longitud"] = tabla["longitud"].round(5)
    tabla.insert(0, "posicion", range(1, len(tabla) + 1))
    return tabla.reset_index(drop=True)
