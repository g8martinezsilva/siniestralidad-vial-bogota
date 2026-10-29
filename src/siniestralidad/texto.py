"""Utilidades para normalizar texto de la base (tildes, mayúsculas, espacios)."""

import re
import unicodedata

import pandas as pd


def normalizar(valor) -> str | None:
    """Devuelve el texto en minúsculas, sin tildes y con espacios simples.

    Los nulos se conservan como ``None`` para no confundirlos con texto vacío.
    """
    if valor is None or (not isinstance(valor, str) and pd.isna(valor)):
        return None
    texto = unicodedata.normalize("NFKD", str(valor))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"\s+", " ", texto).strip().lower()
    return texto or None


def normalizar_serie(serie: pd.Series) -> pd.Series:
    return serie.map(normalizar)
