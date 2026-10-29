"""Etapa 4 del plan de trabajo: análisis descriptivo espacio-temporal (OE2).

Uso::

    python -m siniestralidad.describir

Lee la base limpia que deja ``preparar`` y genera las tablas en
``reports/tablas`` (``oe2_*.csv``) y los gráficos y mapas en ``reports/figuras``.
"""

import pandas as pd

from . import config, graficos
from .descriptivo import resumen, tablas


def main() -> None:
    entrada = config.PROCESSED / f"siniestros_corredores_{config.ANIO}.parquet"
    if not entrada.exists():
        raise SystemExit(f"No existe {entrada}. Corre primero: python -m siniestralidad.preparar")
    df = pd.read_parquet(entrada)

    config.TABLAS.mkdir(parents=True, exist_ok=True)
    for nombre, tabla in tablas(df).items():
        tabla.to_csv(config.TABLAS / f"{nombre}.csv", index=False)
    figuras = graficos.todos(df)

    r = resumen(df)
    print(f"{r['n']:,} siniestros en los corredores seleccionados\n")
    print("Corredores con más siniestros:     ", ", ".join(r["top3_corredores_total"]))
    print("Corredores con más siniestros/km:  ", ", ".join(r["top3_corredores_por_km"]))
    print("Franjas con más siniestros:        ", ", ".join(r["top3_franjas_total"]))
    print("Franjas con más siniestros/hora:   ", ", ".join(r["top3_franjas_por_hora"]))
    print(f"\nTablas en {config.TABLAS}")
    print(f"Figuras en {config.FIGURAS}: {len(figuras)} archivos")


if __name__ == "__main__":
    main()
