"""Identificación y selección de corredores a partir de la dirección (meta 1.2).

La base no trae una columna de corredor: hay que deducirlo de ``Direccion``.
En el IPAT la dirección se escribe como "vía principal - vía que cruza"
(por ejemplo ``AK 68-AC 26 02``), así que el corredor se toma de la primera
parte. Se unifican las abreviaturas (AK y KR son la misma carrera, AC y CL la
misma calle) y las avenidas que la base escribe por su nombre
(``AV AVENIDA BOYACA`` es la Carrera 72).
"""

import re

import pandas as pd

from . import config
from .texto import normalizar

# Abreviaturas y nombres de tipo de vía -> eje normalizado.
TIPOS_VIA = {
    "KR": ["ak", "av carrera", "avenida carrera", "av cra", "kr", "kra", "cra", "cr", "carrera"],
    "CL": ["ac", "av calle", "avenida calle", "av cl", "cl", "cll", "calle"],
    "DG": ["dg", "diagonal"],
    "TV": ["tv", "tr", "transversal"],
}

# Avenidas que la base escribe por su nombre ("AV AVENIDA BOYACA", "AU NORTE").
# Las claves se buscan dentro del nombre; el valor es la vía equivalente.
ALIAS = {
    "norte": "KR 45",
    "boyaca": "KR 72",
    "caracas": "KR 14",
    "ciudad de cali": "KR 86",
    "ciudad de quito": "KR 30",
    "nqs": "KR 30",
    "centenario": "CL 13",
    "jorge eliecer gaitan": "CL 26",
    "el dorado": "CL 26",
    "jose celestino mutis": "CL 63",
    "primero de mayo": "CL 22 SUR",
    "de las americas": "AV AMERICAS",
    "de los cerros": "AV CIRCUNVALAR",
    "circunvalar": "AV CIRCUNVALAR",
}

# Nombres para mostrar en tablas y gráficos.
NOMBRES = {
    "KR 7": "Carrera Séptima",
    "KR 10": "Avenida Carrera 10",
    "KR 14": "Avenida Caracas",
    "KR 30": "Avenida NQS (Carrera 30)",
    "KR 45": "Autopista Norte",
    "KR 50": "Avenida Carrera 50",
    "KR 68": "Avenida Carrera 68",
    "KR 72": "Avenida Boyacá",
    "KR 80": "Avenida Carrera 80",
    "KR 86": "Avenida Ciudad de Cali",
    "CL 6": "Avenida Calle 6",
    "CL 13": "Avenida Centenario (Calle 13)",
    "CL 17": "Avenida Calle 17",
    "CL 26": "Avenida El Dorado (Calle 26)",
    "CL 63": "Avenida José Celestino Mutis (Calle 63)",
    "CL 72": "Avenida Chile (Calle 72)",
    "CL 80": "Avenida Calle 80",
    "CL 22 SUR": "Avenida Primero de Mayo",
    "AUTOPISTA SUR": "Autopista Sur",
    "AV AMERICAS": "Avenida de las Américas",
    "AV CIRCUNVALAR": "Avenida Circunvalar",
}

_TIPO_RE = "|".join(
    re.escape(alias)
    for alias in sorted((a for lista in TIPOS_VIA.values() for a in lista), key=len, reverse=True)
)
_VIA_RE = re.compile(rf"^(?P<tipo>{_TIPO_RE})\.?\s*(?P<num>\d{{1,3}})(?P<resto>.*)$")
_TIPO_A_EJE = {alias: eje for eje, lista in TIPOS_VIA.items() for alias in lista}
_CARDINAL = {"s": " SUR", "sur": " SUR", "e": " ESTE", "este": " ESTE"}


def _via_nombrada(texto: str) -> str | None:
    """Avenidas escritas por su nombre: ``av avenida boyaca``, ``au norte``."""
    m = re.match(r"^(?:av|avenida|au|autopista)\b\s*(?:avenida\s+)?(?P<nombre>.+)$", texto)
    if not m:
        return None
    nombre = m["nombre"].strip()
    if texto.startswith(("au", "autopista")) and nombre == "sur":
        return "AUTOPISTA SUR"
    for clave, via in ALIAS.items():
        if clave in nombre:
            return via
    return f"AV {nombre.upper()}"


def via_principal(direccion) -> str | None:
    """Devuelve la vía principal normalizada de una dirección, p. ej. ``"KR 68"``.

    >>> via_principal("AK 68-AC 26 02")
    'KR 68'
    >>> via_principal("AV AVENIDA BOYACA - CL 37 C  S 02")
    'KR 72'
    >>> via_principal("CL 42 A S- KR 11 E 02")
    'CL 42A SUR'
    """
    texto = normalizar(direccion)
    if not texto:
        return None
    primera = re.split(r"\s*-\s*|\s+con\s+|\s+x\s+", texto)[0].strip()

    m = _VIA_RE.match(primera)
    if not m:
        return _via_nombrada(primera)

    # Lo que sigue al número: letra, BIS y cuadrante (S = sur, E = este).
    tokens = [t for t in re.findall(r"bis|sur|este|[a-z]|\d+", m["resto"]) if not t.isdigit()]
    cardinal = _CARDINAL.get(tokens[-1], "") if tokens else ""
    if cardinal:
        tokens = tokens[:-1]
    via = f"{_TIPO_A_EJE[m['tipo']]} {int(m['num'])}"
    letra = next((t for t in tokens if len(t) == 1), None)
    if letra:
        via += letra.upper()
    if "bis" in tokens:
        via += " BIS"
    return via + cardinal


def vias(df: pd.DataFrame, col_direccion: str = config.COL_DIRECCION,
         ambas: bool = config.CORREDOR_AMBAS_VIAS) -> pd.DataFrame:
    """Vía principal (``via_1``) y vía que cruza (``via_2``) de cada dirección."""
    partes = df[col_direccion].astype("string").str.split(r"\s*-\s*", n=1, regex=True)
    out = pd.DataFrame({"via_1": partes.str[0].map(via_principal)}, index=df.index)
    out["via_2"] = partes.str[1].map(via_principal) if ambas else None
    out.loc[out["via_2"] == out["via_1"], "via_2"] = None
    return out


def seleccionar_corredores(df: pd.DataFrame, n: int = config.N_CORREDORES) -> pd.DataFrame:
    """Ranking de los ``n`` corredores con más siniestros (muestreo por criterio).

    Un siniestro cuenta para un corredor si este aparece como vía principal o
    como vía que cruza. La columna ``longitud_km`` queda vacía: se completa a
    mano para H1.
    """
    conteo = pd.concat([df["via_1"], df["via_2"]]).dropna().value_counts()
    top = conteo.head(n)
    return pd.DataFrame({
        "posicion": range(1, len(top) + 1),
        "corredor": top.index,
        "nombre": [NOMBRES.get(c, c.title()) for c in top.index],
        "siniestros": top.values,
        "participacion_%": (100 * top.values / len(df)).round(2),
        "longitud_km": pd.NA,
    })


def asignar_corredor(df: pd.DataFrame, corredores: list[str]) -> pd.Series:
    """Corredor de cada siniestro: la vía principal si está entre los seleccionados,
    si no la vía que cruza. Un cruce entre dos corredores seleccionados se asigna
    a la vía principal, así cada siniestro cuenta una sola vez."""
    via_1 = df["via_1"].where(df["via_1"].isin(corredores))
    via_2 = df["via_2"].where(df["via_2"].isin(corredores))
    return via_1.fillna(via_2)
