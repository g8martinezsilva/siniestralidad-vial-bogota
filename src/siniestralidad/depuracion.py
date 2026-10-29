"""Depuración, estandarización y variables derivadas (meta 1.3).

Cada paso que descarta registros queda anotado en una tabla de trazabilidad,
como pide el OE1.
"""

import numpy as np
import pandas as pd

from . import config
from .corredores import asignar_corredor, vias
from .texto import normalizar, normalizar_serie


class Trazabilidad:
    """Lleva la cuenta de cuántos registros se descartan en cada paso."""

    def __init__(self, n_inicial: int):
        self.pasos = [{"paso": "base cruda", "descartados": 0, "quedan": n_inicial}]

    def registrar(self, paso: str, antes: int, despues: int) -> None:
        self.pasos.append({"paso": paso, "descartados": antes - despues, "quedan": despues})

    def tabla(self) -> pd.DataFrame:
        tabla = pd.DataFrame(self.pasos)
        tabla["descartados_%"] = (100 * tabla["descartados"] / self.pasos[0]["quedan"]).round(2)
        return tabla


# --- Conversión de tipos -------------------------------------------------

def _a_numero(serie: pd.Series) -> pd.Series:
    """Convierte texto a número aceptando coma decimal."""
    if pd.api.types.is_numeric_dtype(serie):
        return serie.astype(float)
    return pd.to_numeric(serie.astype(str).str.strip().str.replace(",", ".", regex=False),
                         errors="coerce")


def parsear_fecha(df: pd.DataFrame) -> pd.Series:
    """Fecha del siniestro; si ``Fecha_Acc`` no se entiende, usa año, mes y día."""
    crudo = df[config.COL_FECHA]
    fecha = pd.to_datetime(crudo, errors="coerce", format="%d/%m/%Y")
    faltan = fecha.isna() & crudo.notna()
    if faltan.any():
        fecha[faltan] = pd.to_datetime(crudo[faltan], errors="coerce", dayfirst=True)
    partes = ["AA_Acc", "MM_Acc", "DD_Mes_Acc"]
    if fecha.isna().any() and all(p in df.columns for p in partes):
        compuesta = pd.to_datetime(
            pd.DataFrame({
                "year": _a_numero(df["AA_Acc"]),
                "month": _a_numero(df["MM_Acc"]),
                "day": _a_numero(df["DD_Mes_Acc"]),
            }),
            errors="coerce",
        )
        fecha = fecha.fillna(compuesta)
    return fecha.dt.normalize()


def parsear_hora(serie: pd.Series) -> pd.Series:
    """Hora entera 0-23. Acepta ``7``, ``"07"``, ``"07:35"`` o ``"07:35:00"``."""
    texto = serie.astype("string").str.strip()
    hora = _a_numero(texto.str.split(":").str[0])
    hora = hora.where(hora.between(0, 23) & (hora % 1 == 0))
    return hora.astype("Int64")


def parsear_si_no(serie: pd.Series) -> pd.Series:
    """Indicadores ``Con_*``. La base solo marca "SI"; la celda vacía significa que no."""
    mapa = {"s": True, "si": True, "1": True, "1.0": True, "true": True, "x": True,
            "n": False, "no": False, "0": False, "0.0": False, "false": False}
    return normalizar_serie(serie.astype("string")).map(mapa).fillna(False).astype(bool)


def parsear_gravedad(serie: pd.Series) -> pd.Series:
    """Lleva la gravedad a las tres categorías ordinales del estudio."""
    def categoria(valor):
        texto = normalizar(valor)
        if not texto:
            return None
        for palabra, cat in config.GRAVEDAD_PALABRAS.items():
            if palabra in texto:
                return cat
        return None

    return pd.Categorical(serie.map(categoria), categories=config.GRAVEDAD_ORDEN, ordered=True)


# --- Flujo principal -----------------------------------------------------

def estandarizar(df: pd.DataFrame) -> pd.DataFrame:
    """Crea las columnas tipadas que usan los análisis, conservando las originales."""
    out = df.copy()
    out["fecha"] = parsear_fecha(df)
    out["hora"] = parsear_hora(df[config.COL_HORA])
    out["latitud"] = _a_numero(df[config.COL_LAT])
    out["longitud"] = _a_numero(df[config.COL_LON])
    out["gravedad"] = parsear_gravedad(df[config.COL_GRAVEDAD])
    out["con_moto"] = parsear_si_no(df[config.COL_MOTO])
    out["localidad"] = normalizar_serie(df[config.COL_LOCALIDAD]).str.upper()
    out["clase"] = normalizar_serie(df[config.COL_CLASE])
    out[["via_1", "via_2"]] = vias(df)
    # Los demás indicadores Con_* también se pasan a booleano (útiles para reglas).
    for col in df.columns:
        if col.startswith("Con_") and col != config.COL_MOTO:
            out[col.lower()] = parsear_si_no(df[col])
    return out


def derivar_variables(df: pd.DataFrame) -> pd.DataFrame:
    """Mes, día de la semana, fin de semana, franja horaria y víctimas."""
    out = df.copy()
    out["mes"] = out["fecha"].dt.month.astype("Int64")
    dow = out["fecha"].dt.dayofweek
    out["dia_semana"] = pd.Categorical(
        dow.map(lambda d: config.DIAS[int(d)] if pd.notna(d) else None),
        categories=config.DIAS, ordered=True,
    )
    out["fin_semana"] = (dow >= 5).astype("boolean").where(dow.notna())
    out["franja"] = pd.cut(
        out["hora"].astype(float), bins=config.FRANJAS_BORDES,
        labels=config.FRANJAS, right=False,
    )
    out["con_victimas"] = (out["gravedad"] != "solo danos").astype("boolean").where(
        out["gravedad"].notna()
    )
    return out


def depurar(df_crudo: pd.DataFrame,
            anio: int = config.ANIO) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Aplica los criterios de inclusión y exclusión de la metodología.

    Devuelve ``(base_limpia, trazabilidad)`` con los siniestros de toda la
    ciudad; la selección de corredores se hace después con
    :func:`filtrar_corredores`.
    """
    traza = Trazabilidad(len(df_crudo))
    df = estandarizar(df_crudo)

    def paso(nombre, mascara):
        nonlocal df
        antes = len(df)
        df = df[mascara.fillna(False).to_numpy(dtype=bool)]
        traza.registrar(nombre, antes, len(df))

    if config.COL_ID in df.columns:
        paso("duplicados (mismo código de accidente)", ~df.duplicated(subset=config.COL_ID))
    else:
        paso("duplicados (filas idénticas)", ~df_crudo.duplicated())
    paso("fecha inválida", df["fecha"].notna())
    paso(f"fuera del año {anio}", df["fecha"].dt.year == anio)
    paso("hora inválida", df["hora"].notna())
    b = config.BOGOTA_BBOX
    paso("coordenadas fuera de Bogotá",
         df["latitud"].between(b["lat_min"], b["lat_max"])
         & df["longitud"].between(b["lon_min"], b["lon_max"]))
    paso("gravedad sin registrar", df["gravedad"].notna())
    paso("dirección sin vía identificable", df["via_1"].notna() | df["via_2"].notna())

    df = derivar_variables(df).reset_index(drop=True)
    return df, traza.tabla()


def filtrar_corredores(df: pd.DataFrame, trazabilidad: pd.DataFrame,
                       corredores: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Asigna el corredor, conserva solo los seleccionados y lo anota en la trazabilidad."""
    df = df.assign(corredor=asignar_corredor(df, corredores))
    filtrada = df[df["corredor"].notna()].reset_index(drop=True)
    n_inicial = trazabilidad["quedan"].iloc[0]
    fila = {
        "paso": f"fuera de los {len(corredores)} corredores seleccionados",
        "descartados": len(df) - len(filtrada),
        "quedan": len(filtrada),
        "descartados_%": round(100 * (len(df) - len(filtrada)) / n_inicial, 2),
    }
    return filtrada, pd.concat([trazabilidad, pd.DataFrame([fila])], ignore_index=True)


def nulos_variables_clave(df: pd.DataFrame) -> pd.Series:
    """Porcentaje de nulos de las variables clave (indicador del OE1: < 5 %)."""
    cols = [c for c in config.VARIABLES_CLAVE if c in df.columns]
    return (100 * df[cols].isna().mean()).round(2)
