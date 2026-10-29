"""Etapa 5 del plan de trabajo: contraste de hipótesis H1 a H3 (OE3).

Uso::

    python -m siniestralidad.contrastar

Genera ``reports/tablas/oe3_resultados.csv`` (estadístico, p-valor, tamaño del
efecto y decisión de cada prueba) y las tablas de apoyo ``oe3_*.csv``.
"""

import pandas as pd

from . import config, graficos
from .hipotesis import contrastar


def main() -> None:
    entrada = config.PROCESSED / f"siniestros_corredores_{config.ANIO}.parquet"
    if not entrada.exists():
        raise SystemExit(f"No existe {entrada}. Corre primero: python -m siniestralidad.preparar")
    df = pd.read_parquet(entrada)

    resultados, apoyo = contrastar(df)
    config.TABLAS.mkdir(parents=True, exist_ok=True)
    resultados.to_csv(config.TABLAS / "oe3_resultados.csv", index=False)
    for nombre, tabla in apoyo.items():
        tabla.to_csv(config.TABLAS / f"{nombre}.csv", index=False)
    graficos.residuos_h1(apoyo["oe3_h1_corredores"])

    with pd.option_context("display.max_colwidth", 60, "display.width", 200):
        print(resultados[["hipotesis", "prueba", "estadistico", "p_valor", "p_bonferroni",
                          "valor_efecto", "magnitud_o_ic", "decision"]].to_string(index=False))
    print(f"\nTablas en {config.TABLAS}")


if __name__ == "__main__":
    main()
