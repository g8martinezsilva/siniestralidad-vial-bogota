"""Diccionario de variables: tipo, nulos y valores distintos de cada campo (meta 1.1)."""

import pandas as pd


def perfil_variables(df: pd.DataFrame, n_ejemplos: int = 3) -> pd.DataFrame:
    """Resume la calidad de cada columna de ``df``.

    El campo ``descripcion`` queda vacío para que el equipo lo complete a mano
    con el significado de cada variable.
    """
    filas = []
    for col in df.columns:
        serie = df[col]
        # Las celdas vacías o con solo espacios también cuentan como nulas.
        vacia = serie.isna() | serie.astype(str).str.strip().eq("")
        valores = serie[~vacia]
        filas.append({
            "variable": col,
            "tipo": str(serie.dtype),
            "nulos": int(vacia.sum()),
            "nulos_%": round(100 * vacia.mean(), 2) if len(serie) else 0.0,
            "distintos": int(valores.nunique()),
            "ejemplos": " | ".join(map(str, valores.value_counts().index[:n_ejemplos])),
            "descripcion": "",
        })
    return pd.DataFrame(filas)
