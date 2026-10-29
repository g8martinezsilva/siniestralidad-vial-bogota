"""Datos del tablero analítico (OE6).

Funciones sin Streamlit, para poder probarlas: carga de la base con perfiles y
de las tablas que dejan las etapas anteriores, filtros e indicadores.
"""

import pandas as pd

from . import config
from .corredores import NOMBRES, cargar_longitudes

TABLAS = [
    "oe3_resultados", "oe3_h1_corredores", "oe4_perfiles", "oe4_zonas_densas",
    "oe5_reglas_seleccion", "oe5_reglas_globales", "oe5_reglas_muertos", "oe5_reglas_por_perfil",
]


def cargar() -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """Base con perfil y zona de cada siniestro, y las tablas de OE3 a OE5."""
    entrada = config.PROCESSED / f"siniestros_perfiles_{config.ANIO}.parquet"
    faltan = [entrada] if not entrada.exists() else []
    faltan += [config.TABLAS / f"{t}.csv" for t in TABLAS if not (config.TABLAS / f"{t}.csv").exists()]
    if faltan:
        raise FileNotFoundError("Faltan " + ", ".join(p.name for p in faltan)
                                + ". Corre antes los pasos 3 a 7 del README.")
    df = pd.read_parquet(entrada)
    df["nombre_corredor"] = df["corredor"].map(lambda c: NOMBRES.get(c, c))
    df["tipo_dia"] = df["fin_semana"].map({True: "Fin de semana", False: "Entre semana"})
    return df, {t: pd.read_csv(config.TABLAS / f"{t}.csv") for t in TABLAS}


def filtrar(df: pd.DataFrame, corredores=None, franjas=None, tipo_dia=None, gravedades=None) -> pd.DataFrame:
    """Aplica los filtros del tablero; una lista vacía o ``None`` no filtra."""
    mascara = pd.Series(True, index=df.index)
    for columna, valores in (("nombre_corredor", corredores), ("franja", franjas),
                             ("tipo_dia", tipo_dia), ("gravedad", gravedades)):
        if valores:
            mascara &= df[columna].isin(valores)
    return df[mascara]


def indicadores(df: pd.DataFrame) -> dict:
    """Cifras de la fila superior del tablero."""
    n = len(df)
    return {
        "siniestros": n,
        "pct_con_victimas": round(100 * df["con_victimas"].astype(bool).mean(), 1) if n else 0.0,
        "con_muertos": int((df["gravedad"] == "con muertos").sum()),
        "pct_con_moto": round(100 * df["con_moto"].astype(bool).mean(), 1) if n else 0.0,
    }


def por_km(df: pd.DataFrame, longitudes: pd.Series | None = None) -> pd.DataFrame:
    """Siniestros y siniestros por km de cada corredor, de mayor a menor tasa."""
    longitudes = cargar_longitudes() if longitudes is None else longitudes
    conteo = df["corredor"].value_counts()
    tabla = pd.DataFrame({
        "corredor": conteo.index,
        "nombre": [NOMBRES.get(c, c) for c in conteo.index],
        "siniestros": conteo.values,
        "longitud_km": longitudes.reindex(conteo.index).values,
    })
    tabla["siniestros_por_km"] = (tabla["siniestros"] / tabla["longitud_km"]).round(1)
    return tabla.sort_values("siniestros_por_km", ascending=False).reset_index(drop=True)


def dia_hora(df: pd.DataFrame) -> pd.DataFrame:
    """Siniestros por día de la semana (filas) y hora (columnas 0 a 23)."""
    return (pd.crosstab(df["dia_semana"], df["hora"].astype(int))
            .reindex(index=df["dia_semana"].cat.categories, columns=range(24), fill_value=0))
