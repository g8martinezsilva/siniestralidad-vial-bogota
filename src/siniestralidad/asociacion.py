"""Reglas de asociación con FP-Growth (OE5).

Cada siniestro se vuelve una transacción con sus características (corredor,
franja, tipo de día, clase, actores y gravedad). Las reglas se buscan en toda
la base y dentro de cada perfil del OE4, como en Sathiyanathan y Warnajith (2024).
"""

import warnings

import pandas as pd
from mlxtend.frequent_patterns import association_rules, fpgrowth

from .corredores import NOMBRES

SOPORTE_MIN = 0.01
CONFIANZA_MIN = 0.30
LIFT_MIN = 1.2

ACTORES = {
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

# Combinaciones que son ciertas por definición (un atropello siempre tiene peatón).
TRIVIALES = [{"clase=atropello", "actor=peatón"}]


def transacciones(df: pd.DataFrame) -> pd.DataFrame:
    """Tabla booleana: una fila por siniestro y una columna por ítem ("franja=noche")."""
    items = {
        "corredor": df["corredor"].map(lambda c: NOMBRES.get(c, c)),
        "franja": df["franja"].astype(str),
        "dia": df["fin_semana"].astype(bool).map({True: "fin de semana", False: "entre semana"}),
        "clase": df["clase"],
        "gravedad": df["gravedad"].astype(str),
    }
    columnas = [pd.get_dummies(serie, prefix=nombre, prefix_sep="=") for nombre, serie in items.items()]
    columnas += [df[c].astype(bool).rename(f"actor={nombre}") for c, nombre in ACTORES.items()
                 if c in df.columns]
    return pd.concat(columnas, axis=1).astype(bool)


def _es_trivial(regla: pd.Series) -> bool:
    items = set(regla["antecedentes"]) | set(regla["consecuentes"])
    return any(t <= items for t in TRIVIALES)


def reglas(trans: pd.DataFrame, soporte: float = SOPORTE_MIN, confianza: float = CONFIANZA_MIN,
           lift: float = LIFT_MIN, max_items: int = 3) -> pd.DataFrame:
    """Reglas que superan los umbrales, ordenadas por lift, sin las triviales.

    La gravedad es la variable de resultado, así que solo puede ir en el consecuente.
    """
    frecuentes = fpgrowth(trans, min_support=soporte, use_colnames=True, max_len=max_items)
    if frecuentes.empty:
        return pd.DataFrame()
    with warnings.catch_warnings():
        # mlxtend avisa de una división por cero en una métrica que no se usa.
        warnings.simplefilter("ignore", RuntimeWarning)
        r = association_rules(frecuentes, metric="confidence", min_threshold=confianza)
    r = r[r["lift"] > lift].rename(columns={
        "antecedents": "antecedentes", "consequents": "consecuentes",
        "support": "soporte", "confidence": "confianza",
    })
    r = r[~r.apply(_es_trivial, axis=1)]
    r = r[~r["antecedentes"].map(lambda s: any(i.startswith("gravedad=") for i in s))]
    r = r.assign(
        antecedentes=r["antecedentes"].map(lambda s: " + ".join(sorted(s))),
        consecuentes=r["consecuentes"].map(lambda s: " + ".join(sorted(s))),
    )
    columnas = ["antecedentes", "consecuentes", "soporte", "confianza", "lift"]
    return r[columnas].sort_values("lift", ascending=False).round(4).reset_index(drop=True)


def reglas_hacia(trans: pd.DataFrame, consecuente: str, soporte: float = 0.003,
                 lift: float = LIFT_MIN, max_items: int = 3) -> pd.DataFrame:
    """Reglas cuyo consecuente es un ítem dado (p. ej. ``gravedad=con muertos``).

    Los siniestros con muertos son pocos, así que aquí no se exige confianza
    mínima y el soporte baja; la regla se juzga por su lift.
    """
    r = reglas(trans, soporte=soporte, confianza=0.0, lift=lift, max_items=max_items)
    if r.empty:
        return r
    return r[r["consecuentes"] == consecuente].reset_index(drop=True)


def por_perfil(df: pd.DataFrame, **umbrales) -> pd.DataFrame:
    """Reglas dentro de cada perfil del OE4 (columna ``perfil``)."""
    partes = []
    for perfil, sub in df.groupby("perfil"):
        r = reglas(transacciones(sub), **umbrales)
        if not r.empty:
            partes.append(r.assign(perfil=perfil))
    if not partes:
        return pd.DataFrame()
    return pd.concat(partes, ignore_index=True)[["perfil", "antecedentes", "consecuentes",
                                                 "soporte", "confianza", "lift"]]


def _items(regla: pd.Series) -> frozenset:
    return frozenset(regla["antecedentes"].split(" + ") + regla["consecuentes"].split(" + "))


def seleccion(reglas_: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Las ``n`` reglas a interpretar: las de mayor lift, saltando las que comparten
    dos o más ítems con una ya elegida, para no contar la misma historia varias veces."""
    elegidas, filas = [], []
    for _, regla in reglas_.iterrows():
        items = _items(regla)
        if any(len(items & e) >= 2 for e in elegidas):
            continue
        elegidas.append(items)
        filas.append(regla)
        if len(filas) == n:
            break
    tabla = pd.DataFrame(filas).reset_index(drop=True)
    if not tabla.empty:
        tabla["lectura"] = tabla.apply(lectura, axis=1)
    return tabla


def legible(items: str) -> str:
    """Ítems de una regla en palabras, con tildes (``franja=manana`` → ``franja mañana``)."""
    textos = []
    for item in items.split(" + "):
        variable, valor = item.split("=", 1)
        valor = valor.replace("solo danos", "solo daños").replace("con muertos", "muertos") \
                     .replace("con heridos", "heridos").replace("manana", "mañana") \
                     .replace("mediodia", "mediodía").replace("caida", "caída")
        textos.append(f"franja {valor}" if variable == "franja" else valor)
    return " y ".join(textos)


def lectura(regla: pd.Series) -> str:
    """Frase para el informe: qué dice la regla en palabras."""
    return (f"Cuando se presenta {legible(regla['antecedentes'])}, el {100 * regla['confianza']:.0f} % "
            f"de los siniestros también tiene {legible(regla['consecuentes'])} "
            f"({regla['lift']:.1f} veces lo esperado; {100 * regla['soporte']:.1f} % de la base).")
