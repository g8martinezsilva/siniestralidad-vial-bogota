"""Contraste de las hipótesis H1, H2 y H3 (OE3).

Cada prueba devuelve un diccionario con el estadístico, el p-valor, el tamaño
del efecto y la tabla que la sustenta. La decisión se toma con la corrección de
Bonferroni sobre las pruebas principales, como dice la metodología.
"""

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.contingency_tables import Table2x2
from statsmodels.stats.proportion import proportions_ztest

from .corredores import NOMBRES, cargar_longitudes

ALFA = 0.05
FRECUENCIA_MINIMA = 5


def magnitud_v(v: float) -> str:
    """Interpretación de la V de Cramér (0,1 pequeño; 0,3 mediano; 0,5 grande)."""
    if v < 0.1:
        return "despreciable"
    if v < 0.3:
        return "pequeño"
    if v < 0.5:
        return "mediano"
    return "grande"


def v_cramer(chi2: float, n: int, k: int) -> float:
    """V de Cramér; ``k`` es el mínimo entre filas y columnas (o categorías)."""
    return float(np.sqrt(chi2 / (n * (k - 1))))


def h1_concentracion(df: pd.DataFrame, longitudes: pd.Series | None = None) -> dict:
    """H1: chi-cuadrado de bondad de ajuste con esperados proporcionales a la longitud."""
    longitudes = cargar_longitudes() if longitudes is None else longitudes
    observados = df["corredor"].value_counts()
    km = longitudes.reindex(observados.index)
    if km.isna().any():
        raise ValueError(f"Falta la longitud de: {', '.join(km[km.isna()].index)}")
    esperados = observados.sum() * km / km.sum()
    chi2, p = stats.chisquare(observados, esperados)
    tabla = pd.DataFrame({
        "nombre": [NOMBRES.get(c, c) for c in observados.index],
        "longitud_km": km,
        "observados": observados,
        "esperados": esperados.round(1),
        "residuo_estandarizado": ((observados - esperados) / np.sqrt(esperados)).round(2),
    }).sort_values("residuo_estandarizado", ascending=False)
    v = v_cramer(chi2, int(observados.sum()), len(observados))
    return {
        "hipotesis": "H1",
        "prueba": "Chi-cuadrado de bondad de ajuste",
        "estadistico": chi2,
        "gl": len(observados) - 1,
        "p_valor": p,
        "efecto": "V de Cramér",
        "valor_efecto": v,
        "magnitud": magnitud_v(v),
        "supuesto_ok": bool((esperados >= FRECUENCIA_MINIMA).all()),
        "archivo": "oe3_h1_corredores",
        "tabla": tabla.reset_index(names="corredor"),
    }


def _independencia(df: pd.DataFrame, filas: str, hipotesis: str, archivo: str) -> dict:
    tabla = pd.crosstab(df[filas], df["gravedad"])
    chi2, p, gl, esperados = stats.chi2_contingency(tabla)
    v = v_cramer(chi2, int(tabla.values.sum()), min(tabla.shape))
    residuos = (tabla - esperados) / np.sqrt(esperados)
    return {
        "hipotesis": hipotesis,
        "prueba": f"Chi-cuadrado de independencia (gravedad × {filas})",
        "estadistico": chi2,
        "gl": gl,
        "p_valor": p,
        "efecto": "V de Cramér",
        "valor_efecto": v,
        "magnitud": magnitud_v(v),
        "supuesto_ok": bool((esperados >= FRECUENCIA_MINIMA).all()),
        "archivo": archivo,
        "tabla": tabla.join(residuos.round(2), rsuffix="_residuo").reset_index(),
    }


def tipo_dia(df: pd.DataFrame) -> pd.Series:
    return df["fin_semana"].map({True: "fin de semana", False: "entre semana"})


def h2_franja(df: pd.DataFrame) -> dict:
    """H2a: gravedad independiente de la franja horaria."""
    return _independencia(df, "franja", "H2a", "oe3_h2_franja")


def h2_tipo_dia(df: pd.DataFrame) -> dict:
    """H2b: gravedad independiente del tipo de día (entre semana o fin de semana)."""
    return _independencia(df.assign(tipo_dia=tipo_dia(df)), "tipo_dia", "H2b", "oe3_h2_tipo_dia")


def comparar_proporciones(exito: pd.Series, grupo: pd.Series, hipotesis: str,
                          descripcion: str, archivo: str) -> dict:
    """Prueba z unilateral (grupo > resto) y razón de momios con IC 95 %."""
    a = int((exito & grupo).sum())
    b = int((~exito & grupo).sum())
    c = int((exito & ~grupo).sum())
    d = int((~exito & ~grupo).sum())
    z, p = proportions_ztest([a, c], [a + b, c + d], alternative="larger")
    tabla = Table2x2(np.array([[a, b], [c, d]]))
    ic = tabla.oddsratio_confint()
    return {
        "hipotesis": hipotesis,
        "prueba": f"Prueba z unilateral de proporciones ({descripcion})",
        "estadistico": z,
        "gl": None,
        "p_valor": p,
        "efecto": "Razón de momios (IC 95 %)",
        "valor_efecto": tabla.oddsratio,
        "magnitud": f"{ic[0]:.2f} – {ic[1]:.2f}",
        "supuesto_ok": min(a, b, c, d) >= FRECUENCIA_MINIMA,
        "archivo": archivo,
        "tabla": pd.DataFrame({
            "grupo": ["sí", "no"],
            "con_evento": [a, c],
            "sin_evento": [b, d],
            "proporcion_%": [round(100 * a / (a + b), 2), round(100 * c / (c + d), 2)],
        }),
    }


def h3_moto(df: pd.DataFrame) -> dict:
    """H3: la proporción de siniestros con víctimas es mayor si hay motocicleta."""
    return comparar_proporciones(df["con_victimas"].astype(bool), df["con_moto"].astype(bool),
                                 "H3", "con víctimas, con moto vs. sin moto", "oe3_h3_moto")


def complementarias(df: pd.DataFrame) -> list[dict]:
    """Pruebas que precisan las hipótesis, sin entrar en la corrección de Bonferroni."""
    # "Noche de fin de semana": de 20:00 a 6:00 del sábado o el domingo.
    noche_finde = (df["franja"].isin(["noche", "madrugada"]) & df["fin_semana"].astype(bool))
    muertos = df["gravedad"] == "con muertos"
    return [
        comparar_proporciones(df["con_victimas"].astype(bool), noche_finde, "H2 (compl.)",
                              "con víctimas, noche o madrugada de fin de semana vs. resto",
                              "oe3_compl_noche_finde_victimas"),
        comparar_proporciones(muertos, noche_finde, "H2 (compl.)",
                              "con muertos, noche o madrugada de fin de semana vs. resto",
                              "oe3_compl_noche_finde_muertos"),
        comparar_proporciones(muertos, df["con_moto"].astype(bool), "H3 (compl.)",
                              "con muertos, con moto vs. sin moto", "oe3_compl_moto_muertos"),
    ]


def contrastar(df: pd.DataFrame, alfa: float = ALFA) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """Corre todas las pruebas. Devuelve la tabla de resultados y las tablas de apoyo."""
    principales = [h1_concentracion(df), h2_franja(df), h2_tipo_dia(df), h3_moto(df)]
    m = len(principales)
    filas, apoyo = [], {}
    for i, r in enumerate(principales + complementarias(df)):
        es_principal = i < m
        p_ajustado = min(1.0, r["p_valor"] * m) if es_principal else None
        p_decision = p_ajustado if es_principal else r["p_valor"]
        filas.append({
            "hipotesis": r["hipotesis"],
            "prueba": r["prueba"],
            "estadistico": round(r["estadistico"], 3),
            "gl": r["gl"],
            "p_valor": r["p_valor"],
            "p_bonferroni": p_ajustado,
            "efecto": r["efecto"],
            "valor_efecto": round(r["valor_efecto"], 3),
            "magnitud_o_ic": r["magnitud"],
            "supuesto_esperados_>=5": r["supuesto_ok"],
            "decision": "Se rechaza H0" if p_decision < alfa else "No se rechaza H0",
        })
        apoyo[r["archivo"]] = r["tabla"]
    return pd.DataFrame(filas), apoyo
