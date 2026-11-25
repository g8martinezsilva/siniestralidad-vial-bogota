"""Longitud de los corredores medida sobre la Malla Vial Integral de Bogotá (IDECA).

Uso::

    python -m siniestralidad.longitudes

La capa trae los tramos de cada vía, pero no el total por corredor. Aquí los
tramos se convierten en puntos, se unen los vecinos (así las calzadas paralelas
quedan como un solo eje) y se mide el recorrido más largo a lo largo del eje.
Si el corredor está partido, se suman sus piezas de más de 0,3 km. Una misma
avenida cambia de nomenclatura en su recorrido, así que se toma por su nombre
oficial y se agregan los tramos sin nombre que la continúan con su número.

Escribe ``data/external/longitudes_corredores.csv``. La descarga queda en
``data/external/cache_mvi``; para repetirla, borra esa carpeta.
"""

import json
from collections import Counter

import numpy as np
import pandas as pd
import requests
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components, dijkstra
from scipy.spatial import cKDTree

from . import config
from .corredores import NOMBRES

URL_MVI = ("https://serviciosgis.catastrobogota.gov.co/arcgis/rest/services/"
           "Mapa_Referencia/Mapa_Referencia/MapServer/13/query")
CACHE = config.EXTERNAL / "cache_mvi" / "tramos.json"
FUENTE = "Malla Vial Integral de Bogotá (IDECA)"
TRAMOS_POR_CONSULTA = 1000

PASO_M = 15
REJILLA_M = 8
UNION_M = 60
PIEZA_MIN_KM = 0.3

LAT_REF, LON_REF = 4.65, -74.10
METROS_POR_GRADO_LAT, METROS_POR_GRADO_LON = 110_582, 110_957

SIN_NOMBRE = ("SIN_NMG", "")

# ``nombres``: avenidas oficiales (MVINOMBRE) con cualquier nomenclatura.
# ``parciales``: avenidas de las que solo cuentan los tramos con ciertas etiquetas (MVIETIQUET).
# ``numero``: etiquetas con que sigue la vía donde no tiene nombre oficial.
CORREDORES = {
    "KR 72": {"nombres": ["AVENIDA BOYACA", "AUTOPISTA AL LLANO O AVENIDA BOYACA"],
              "numero": ["KR 72", "AK 72"]},
    "KR 14": {"nombres": ["AVENIDA CARACAS"], "numero": ["KR 14", "AK 14"]},
    "KR 86": {"nombres": ["AVENIDA CIUDAD DE CALI"], "numero": ["KR 86", "AK 86"]},
    "KR 30": {"nombres": ["AVENIDA CIUDAD DE QUITO"], "numero": ["KR 30", "AK 30"]},
    "KR 7": {"nombres": ["AVENIDA ALBERTO LLERAS CAMARGO"], "numero": ["KR 7", "AK 7"]},
    "KR 10": {"nombres": ["AVENIDA FERNANDO MAZUERA"], "numero": ["KR 10", "AK 10"]},
    "CL 26": {"nombres": ["AVENIDA JORGE ELIECER GAITAN"], "numero": ["CL 26", "AC 26"]},
    "CL 6": {"nombres": ["AVENIDA DE LOS COMUNEROS", "AVENIDA MANUEL CEPEDA VARGAS"],
             "parciales": {"AVENIDA DE LAS AMERICAS": ["AC 6"]}, "numero": ["CL 6", "AC 6"]},
    "KR 45": {"nombres": ["AVENIDA PASEO DE LOS LIBERTADORES"], "numero": ["KR 45", "AK 45"]},
    "CL 13": {"nombres": ["AVENIDA COLON", "AVENIDA CENTENARIO"],
              "parciales": {"AVENIDA JIMENEZ": ["CL 13"]}, "numero": ["CL 13", "AC 13"]},
}


def _condicion() -> str:
    nombres = sorted({n for c in CORREDORES.values()
                      for n in [*c["nombres"], *c.get("parciales", {})]})
    etiquetas = sorted({e for c in CORREDORES.values() for e in c["numero"]})
    lista = lambda valores: ",".join(f"'{v}'" for v in valores)
    return f"MVINOMBRE IN ({lista(nombres)}) OR MVIETIQUET IN ({lista(etiquetas)})"


def descargar() -> list[dict]:
    """Tramos de los corredores, desde la caché o desde el servicio de IDECA."""
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    tramos, sigue = [], True
    while sigue:
        respuesta = requests.post(URL_MVI, timeout=90, data={
            "where": _condicion(), "outFields": "MVINOMBRE,MVIETIQUET", "returnGeometry": "true",
            "outSR": 4326, "orderByFields": "OBJECTID", "resultOffset": len(tramos),
            "resultRecordCount": TRAMOS_POR_CONSULTA, "f": "json",
        })
        respuesta.raise_for_status()
        datos = respuesta.json()
        if "error" in datos:
            raise RuntimeError(f"IDECA respondió con error: {datos['error']}")
        tramos += datos["features"]
        sigue = bool(datos["features"]) and datos.get("exceededTransferLimit", False)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(tramos), encoding="utf-8")
    return tramos


def _texto(tramo: dict, campo: str) -> str:
    return (tramo["attributes"][campo] or "").strip().upper()


def _es_oficial(tramo: dict, criterio: dict) -> bool:
    nombre, etiqueta = _texto(tramo, "MVINOMBRE"), _texto(tramo, "MVIETIQUET")
    return nombre in criterio["nombres"] or etiqueta in criterio.get("parciales", {}).get(nombre, [])


def _es_continuacion(tramo: dict, criterio: dict) -> bool:
    return (_texto(tramo, "MVINOMBRE") in SIN_NOMBRE
            and _texto(tramo, "MVIETIQUET") in criterio["numero"])


def _a_metros(coordenadas: list) -> np.ndarray:
    lon, lat = np.array([c[:2] for c in coordenadas], dtype=float).T
    return np.column_stack([(lon - LON_REF) * METROS_POR_GRADO_LON,
                            (lat - LAT_REF) * METROS_POR_GRADO_LAT])


def puntos(tramos: list[dict]) -> np.ndarray:
    """Puntos cada ``PASO_M`` metros sobre los tramos, sin repetir."""
    salida = []
    for tramo in tramos:
        for linea in tramo.get("geometry", {}).get("paths", []):
            vertices = _a_metros(linea)
            for a, b in zip(vertices[:-1], vertices[1:]):
                n = max(1, int(np.ceil(np.hypot(*(b - a)) / PASO_M)))
                salida.append(a + (b - a) * np.arange(n)[:, None] / n)
            salida.append(vertices[-1:])
    return np.unique(np.round(np.vstack(salida) / REJILLA_M) * REJILLA_M, axis=0)


def _piezas(p: np.ndarray) -> tuple[coo_matrix, np.ndarray]:
    """Grafo de puntos vecinos y la pieza a la que pertenece cada punto."""
    pares = cKDTree(p).query_pairs(UNION_M, output_type="ndarray")
    distancias = np.hypot(*(p[pares[:, 0]] - p[pares[:, 1]]).T)
    grafo = coo_matrix((distancias, (pares[:, 0], pares[:, 1])), shape=(len(p), len(p))).tocsr()
    return grafo, connected_components(grafo, directed=False)[1]


def eje(tramos: list[dict], criterio: dict) -> np.ndarray:
    """Puntos del corredor: sus tramos oficiales y las continuaciones unidas a ellos."""
    oficiales = [t for t in tramos if _es_oficial(t, criterio)]
    if not oficiales:
        raise ValueError(f"La capa no trae tramos de {', '.join(criterio['nombres'])}")
    base = puntos(oficiales)
    p = puntos(oficiales + [t for t in tramos if _es_continuacion(t, criterio)])
    _, pieza = _piezas(p)
    propias = np.unique(pieza[cKDTree(base).query(p)[0] < 1])
    return p[np.isin(pieza, propias)]


def longitud_eje(p: np.ndarray) -> float:
    """Kilómetros del recorrido más largo de cada pieza del corredor, sumados."""
    grafo, pieza = _piezas(p)
    total = 0.0
    for i in np.unique(pieza):
        indices = np.flatnonzero(pieza == i)
        sub = grafo[indices][:, indices]
        extremo = dijkstra(sub, directed=False, indices=0).argmax()
        km = dijkstra(sub, directed=False, indices=extremo).max() / 1000
        if km >= PIEZA_MIN_KM:
            total += km
    return total


def _nota(tramos: list[dict], criterio: dict) -> str:
    oficiales = Counter(_texto(t, "MVIETIQUET") for t in tramos if _es_oficial(t, criterio))
    etiquetas = [e for e, _ in oficiales.most_common() if e]
    avenidas = [*criterio["nombres"], *(f"{n} (solo {', '.join(e)})"
                                        for n, e in criterio.get("parciales", {}).items())]
    return (f"Nombres oficiales: {'; '.join(avenidas)}. Nomenclaturas: {', '.join(etiquetas)}. "
            f"Más los tramos sin nombre de {'/'.join(criterio['numero'])} unidos al eje")


def medir(tramos: list[dict]) -> pd.DataFrame:
    """Tabla con la longitud de cada corredor, lista para guardar."""
    return pd.DataFrame([{
        "corredor": corredor,
        "nombre": NOMBRES[corredor],
        "longitud_km": round(longitud_eje(eje(tramos, criterio)), 1),
        "fuente": FUENTE,
        "nota": _nota(tramos, criterio),
    } for corredor, criterio in CORREDORES.items()])


def main() -> None:
    tabla = medir(descargar())
    tabla.to_csv(config.ARCHIVO_LONGITUDES, index=False, lineterminator="\n")
    print(tabla[["nombre", "longitud_km"]].to_string(index=False))
    print(f"\nLongitudes en {config.ARCHIVO_LONGITUDES}")


if __name__ == "__main__":
    main()
