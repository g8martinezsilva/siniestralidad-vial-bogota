"""Carga de la base del Anuario de Siniestralidad 2024 (SIMUR).

El archivo de datos abiertos es un .xlsx con tres hojas principales
(siniestros, vehículos y actor vial). Leer un .xlsx de más de 100 MB tarda
varios minutos, así que la primera lectura se guarda en parquet dentro de
``data/raw/cache`` y las siguientes la toman de ahí.
"""

from pathlib import Path

import pandas as pd

from . import config
from .texto import normalizar

# Palabra que identifica cada hoja dentro del nombre normalizado de la hoja.
HOJAS = {
    "siniestros": "siniestro",
    "vehiculos": "vehiculo",
    "actores": "actor",
}


def _hoja_para(nombres: list[str], clave: str) -> str | None:
    for nombre in nombres:
        if clave in (normalizar(nombre) or ""):
            return nombre
    return None


def _ruta_cache(archivo: Path, hoja: str) -> Path:
    return archivo.parent / "cache" / f"{archivo.stem}__{hoja}.parquet"


def cargar_anuario(archivo: Path | str = config.ARCHIVO_ANUARIO,
                   usar_cache: bool = True) -> dict[str, pd.DataFrame]:
    """Lee las hojas de siniestros, vehículos y actores viales.

    Devuelve un diccionario ``{"siniestros": df, "vehiculos": df, "actores": df}``;
    una hoja que no se encuentre en el archivo no aparece en el resultado.
    Todas las columnas se leen como texto, como las publica el diccionario de
    datos abiertos; los tipos se asignan en la depuración.
    """
    archivo = Path(archivo)
    if not archivo.exists():
        raise FileNotFoundError(
            f"No se encontró {archivo}. Descarga la base desde\n{config.URL_ANUARIO}\n"
            f"y guárdala en {config.RAW}/ (ver data/README.md)."
        )

    if archivo.suffix.lower() == ".csv":
        return {"siniestros": pd.read_csv(archivo, dtype=str)}

    resultado = {}
    nombres = pd.ExcelFile(archivo).sheet_names
    for hoja, clave in HOJAS.items():
        cache = _ruta_cache(archivo, hoja)
        if usar_cache and cache.exists() and cache.stat().st_mtime >= archivo.stat().st_mtime:
            resultado[hoja] = pd.read_parquet(cache)
            continue
        nombre = _hoja_para(nombres, clave)
        if nombre is None:
            continue
        df = pd.read_excel(archivo, sheet_name=nombre, dtype=str)
        if usar_cache:
            cache.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(cache, index=False)
        resultado[hoja] = df

    if "siniestros" not in resultado:
        # Si las hojas tienen otros nombres, se toma la primera como siniestros.
        resultado["siniestros"] = pd.read_excel(archivo, sheet_name=0, dtype=str)
    return resultado
