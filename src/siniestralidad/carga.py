"""Carga de la base del Anuario de Siniestralidad 2024 (SIMUR).

El archivo de datos abiertos es un .xlsx con tres hojas principales
(siniestros, vehículos y actor vial). También se acepta un .zip con las hojas
exportadas a CSV (``siniestros.csv``, ``vehiculos.csv``, ``actores.csv``).
Leer un .xlsx de más de 100 MB tarda varios minutos, así que la primera
lectura se guarda en parquet dentro de ``data/raw/cache`` y las siguientes la
toman de ahí.
"""

import io
import zipfile
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


def leer_csv(contenido: bytes) -> pd.DataFrame:
    """Lee un CSV exportado desde Excel, con separador "," o ";" y UTF-8 o Latin-1."""
    for codificacion in ("utf-8-sig", "latin-1"):
        try:
            texto = contenido.decode(codificacion)
            break
        except UnicodeDecodeError:
            continue
    primera = texto.split("\n", 1)[0]
    sep = ";" if primera.count(";") > primera.count(",") else ","
    return pd.read_csv(io.StringIO(texto), sep=sep, dtype=str)


def _cargar_zip(archivo: Path) -> dict[str, pd.DataFrame]:
    resultado = {}
    with zipfile.ZipFile(archivo) as z:
        csvs = [n for n in z.namelist() if n.lower().endswith(".csv")]
        for hoja, clave in HOJAS.items():
            nombre = _hoja_para(csvs, clave)
            if nombre is not None:
                resultado[hoja] = leer_csv(z.read(nombre))
    if "siniestros" not in resultado:
        raise ValueError(f"{archivo} no tiene un CSV de siniestros (se esperaba siniestros.csv).")
    return resultado


def archivo_por_defecto() -> Path:
    """El Excel del anuario si está en ``data/raw``; si no, el primer .zip que haya."""
    if config.ARCHIVO_ANUARIO.exists():
        return config.ARCHIVO_ANUARIO
    zips = sorted(config.RAW.glob("*.zip"))
    return zips[0] if zips else config.ARCHIVO_ANUARIO


def cargar_anuario(archivo: Path | str | None = None,
                   usar_cache: bool = True) -> dict[str, pd.DataFrame]:
    """Lee las hojas de siniestros, vehículos y actores viales.

    Devuelve un diccionario ``{"siniestros": df, "vehiculos": df, "actores": df}``;
    una hoja que no se encuentre en el archivo no aparece en el resultado.
    Todas las columnas se leen como texto, como las publica el diccionario de
    datos abiertos; los tipos se asignan en la depuración.
    """
    archivo = Path(archivo) if archivo else archivo_por_defecto()
    if not archivo.exists():
        raise FileNotFoundError(
            f"No se encontró {archivo}. Descarga la base desde\n{config.URL_ANUARIO}\n"
            f"y guárdala en {config.RAW}/ (ver data/README.md)."
        )

    if archivo.suffix.lower() == ".csv":
        return {"siniestros": leer_csv(archivo.read_bytes())}
    if archivo.suffix.lower() == ".zip":
        return _cargar_zip(archivo)

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
