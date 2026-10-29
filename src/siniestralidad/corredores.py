"""Identificación y selección de corredores a partir de la dirección (meta 1.2).

La base no trae una columna de corredor: hay que deducirlo de ``Direccion``.
En el IPAT la dirección suele escribirse como "vía principal - vía que cruza"
(por ejemplo ``AK 68-AC 26``), así que el corredor se toma de la primera
parte. Se unifican las abreviaturas (AK y KR son la misma carrera, AC y CL la
misma calle) y los nombres de las avenidas más conocidas.

Esta es una primera versión: las reglas y los alias deben revisarse con la
base real, mirando las direcciones que quedan sin corredor.
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
    "TV": ["tv", "transversal"],
}

# Avenidas que suelen escribirse por su nombre. Las claves se buscan dentro de
# la dirección normalizada; el valor es la vía equivalente.
ALIAS = {
    "autopista norte": "KR 45",
    "autonorte": "KR 45",
    "caracas": "KR 14",
    "boyaca": "KR 72",
    "ciudad de cali": "KR 86",
    "nqs": "KR 30",
    "norte quito sur": "KR 30",
    "av 68": "KR 68",
    "avenida 68": "KR 68",
    "el dorado": "CL 26",
    "eldorado": "CL 26",
    "primero de mayo": "CL 22 SUR",
    "1 de mayo": "CL 22 SUR",
    "calle 80": "CL 80",
    "medellin": "CL 80",
    "autopista sur": "AUTOPISTA SUR",
    "americas": "AV AMERICAS",
    "suba": "AV SUBA",
    "circunvalar": "AV CIRCUNVALAR",
}

# Nombres para mostrar en tablas y gráficos.
NOMBRES = {
    "KR 7": "Carrera Séptima",
    "KR 14": "Avenida Caracas",
    "KR 30": "Avenida NQS (Carrera 30)",
    "KR 45": "Autopista Norte",
    "KR 50": "Avenida Carrera 50",
    "KR 68": "Avenida Carrera 68",
    "KR 72": "Avenida Boyacá",
    "KR 86": "Avenida Ciudad de Cali",
    "CL 13": "Avenida Calle 13 (Centenario)",
    "CL 26": "Avenida El Dorado (Calle 26)",
    "CL 80": "Avenida Calle 80",
    "CL 22 SUR": "Avenida Primero de Mayo",
    "AUTOPISTA SUR": "Autopista Sur",
    "AV AMERICAS": "Avenida de las Américas",
    "AV SUBA": "Avenida Suba",
}

_TIPO_RE = "|".join(
    re.escape(alias)
    for alias in sorted((a for lista in TIPOS_VIA.values() for a in lista), key=len, reverse=True)
)
_VIA_RE = re.compile(
    rf"^(?P<tipo>{_TIPO_RE})\.?\s*(?P<num>\d{{1,3}})\s*(?P<letra>[a-z](?![a-z]))?\s*(?P<bis>bis)?"
)
_TIPO_A_EJE = {alias: eje for eje, lista in TIPOS_VIA.items() for alias in lista}


def via_principal(direccion) -> str | None:
    """Devuelve la vía principal normalizada de una dirección, p. ej. ``"KR 68"``.

    >>> via_principal("AK 68-AC 26 02")
    'KR 68'
    >>> via_principal("Avenida Boyacá con calle 63")
    'KR 72'
    """
    texto = normalizar(direccion)
    if not texto:
        return None
    primera = re.split(r"\s*-\s*|\s+con\s+|\s+x\s+", texto)[0].strip()

    for nombre, via in ALIAS.items():
        if nombre in primera:
            return via

    m = _VIA_RE.match(primera)
    if not m:
        return None
    via = f"{_TIPO_A_EJE[m['tipo']]} {int(m['num'])}"
    if m["letra"]:
        via += m["letra"].upper()
    if m["bis"]:
        via += " BIS"
    if re.search(r"\bsur\b", primera):
        via += " SUR"
    elif re.search(r"\beste\b", primera):
        via += " ESTE"
    return via


def asignar_corredor(df: pd.DataFrame, col_direccion: str = config.COL_DIRECCION) -> pd.Series:
    return df[col_direccion].map(via_principal)


def seleccionar_corredores(corredor: pd.Series, n: int = config.N_CORREDORES) -> pd.DataFrame:
    """Ranking de los ``n`` corredores con más siniestros (muestreo por criterio).

    La columna ``longitud_km`` queda vacía: se completa a mano para H1.
    """
    conteo = corredor.dropna().value_counts()
    top = conteo.head(n)
    return pd.DataFrame({
        "posicion": range(1, len(top) + 1),
        "corredor": top.index,
        "nombre": [NOMBRES.get(c, c) for c in top.index],
        "siniestros": top.values,
        "participacion_%": (100 * top.values / conteo.sum()).round(2),
        "longitud_km": pd.NA,
    })
