"""Distribución espacial y temporal de los siniestros (OE2).

Todas las funciones reciben la base limpia de los corredores
(``data/processed/siniestros_corredores_2024.parquet``) y devuelven tablas.
"""

import pandas as pd

from . import config
from .corredores import NOMBRES, cargar_longitudes

# Indicadores de actor vial y vehículo que trae la base (columnas ``con_*``).
ACTORES = {
    "con_moto": "Motocicleta",
    "con_peaton": "Peatón",
    "con_bicicleta": "Bicicleta",
    "con_tpp": "Transporte público de pasajeros",
    "con_tpi": "Taxi u otro público individual",
    "con_carga": "Vehículo de carga",
    "con_persona_mayor": "Persona mayor",
    "con_menores": "Menor de edad",
}

# Horas que cubre cada franja, para comparar franjas de distinto ancho.
HORAS_FRANJA = dict(zip(
    config.FRANJAS,
    [b - a for a, b in zip(config.FRANJAS_BORDES, config.FRANJAS_BORDES[1:])],
))

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def frecuencias(serie: pd.Series, nombre: str | None = None) -> pd.DataFrame:
    """Frecuencia absoluta, relativa y acumulada de una variable categórica."""
    conteo = serie.value_counts(sort=not isinstance(serie.dtype, pd.CategoricalDtype))
    if isinstance(serie.dtype, pd.CategoricalDtype):
        conteo = conteo.reindex(serie.cat.categories, fill_value=0)
    tabla = pd.DataFrame({"siniestros": conteo})
    tabla["%"] = (100 * tabla["siniestros"] / tabla["siniestros"].sum()).round(2)
    tabla["%_acumulado"] = tabla["%"].cumsum().round(2)
    tabla.index.name = nombre or serie.name
    return tabla.reset_index()


def _gravedad_por(df: pd.DataFrame, por: str) -> pd.DataFrame:
    tabla = pd.crosstab(df[por], df["gravedad"], normalize="index").mul(100).round(2)
    return tabla.rename(columns=lambda c: f"%_{c.replace(' ', '_')}")


def por_corredor(df: pd.DataFrame) -> pd.DataFrame:
    """Siniestros, tasa por kilómetro y composición de gravedad por corredor."""
    tabla = df.groupby("corredor").size().rename("siniestros").to_frame()
    tabla["%"] = (100 * tabla["siniestros"] / len(df)).round(2)
    tabla["longitud_km"] = tabla.index.map(cargar_longitudes())
    tabla["siniestros_por_km"] = (tabla["siniestros"] / tabla["longitud_km"]).round(2)
    tabla = tabla.join(_gravedad_por(df, "corredor"))
    tabla.insert(0, "nombre", [NOMBRES.get(c, c) for c in tabla.index])
    return tabla.sort_values("siniestros", ascending=False).reset_index()


def por_franja(df: pd.DataFrame) -> pd.DataFrame:
    """Siniestros por franja horaria, también por hora de franja (las franjas no
    tienen el mismo número de horas)."""
    tabla = frecuencias(df["franja"]).set_index("franja")
    tabla["horas"] = tabla.index.map(HORAS_FRANJA)
    tabla["siniestros_por_hora"] = (tabla["siniestros"] / tabla["horas"]).round(1)
    tabla = tabla.join(_gravedad_por(df, "franja"))
    return tabla.reset_index()


def por_mes(df: pd.DataFrame) -> pd.DataFrame:
    tabla = frecuencias(df["mes"].astype(int)).sort_values("mes")
    tabla.insert(1, "nombre", tabla["mes"].map(lambda m: MESES[m - 1]))
    return tabla.drop(columns="%_acumulado").reset_index(drop=True)


def por_dia(df: pd.DataFrame) -> pd.DataFrame:
    tabla = frecuencias(df["dia_semana"]).set_index("dia_semana")
    return tabla.drop(columns="%_acumulado").join(_gravedad_por(df, "dia_semana")).reset_index()


def por_actor(df: pd.DataFrame) -> pd.DataFrame:
    """Porcentaje de siniestros en que participa cada actor o vehículo.

    Un siniestro puede tener varios actores, así que los porcentajes no suman 100.
    """
    filas = []
    for col, nombre in ACTORES.items():
        if col not in df.columns:
            continue
        sub = df[df[col]]
        filas.append({
            "actor": nombre,
            "siniestros": len(sub),
            "%_de_siniestros": round(100 * len(sub) / len(df), 2),
            "%_con_muertos": round(100 * (sub["gravedad"] == "con muertos").mean(), 2) if len(sub) else 0.0,
        })
    return pd.DataFrame(filas).sort_values("siniestros", ascending=False).reset_index(drop=True)


def dia_por_hora(df: pd.DataFrame) -> pd.DataFrame:
    """Tabla de contingencia día de la semana × hora (para el mapa de calor)."""
    return pd.crosstab(df["dia_semana"], df["hora"].astype(int)).reindex(
        columns=range(24), fill_value=0
    )


def resumen(df: pd.DataFrame) -> dict:
    """Los tres corredores y las tres franjas de mayor concentración (meta del OE2)."""
    corredores = por_corredor(df)
    franjas = por_franja(df)
    return {
        "n": len(df),
        "top3_corredores_total": corredores.nlargest(3, "siniestros")["nombre"].tolist(),
        "top3_corredores_por_km": corredores.nlargest(3, "siniestros_por_km")["nombre"].tolist(),
        "top3_franjas_total": franjas.nlargest(3, "siniestros")["franja"].tolist(),
        "top3_franjas_por_hora": franjas.nlargest(3, "siniestros_por_hora")["franja"].tolist(),
    }


def tablas(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Todas las tablas del OE2, con el nombre de archivo con que se guardan."""
    return {
        "oe2_corredores": por_corredor(df),
        "oe2_franjas": por_franja(df),
        "oe2_meses": por_mes(df),
        "oe2_dias": por_dia(df),
        "oe2_actores": por_actor(df),
        "oe2_clase": frecuencias(df["clase"]),
        "oe2_gravedad": frecuencias(df["gravedad"]),
        "oe2_localidades": frecuencias(df["localidad"]),
        "oe2_dia_por_hora": dia_por_hora(df).reset_index(),
    }
