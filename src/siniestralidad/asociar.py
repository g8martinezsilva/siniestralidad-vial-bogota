"""Etapa 7 del plan de trabajo: reglas de asociación (OE5).

Uso::

    python -m siniestralidad.asociar
    python -m siniestralidad.asociar --soporte 0.02 --confianza 0.4

Lee la base con los perfiles que deja ``agrupar`` y genera las tablas
``oe5_*.csv``: todas las reglas, las 10 seleccionadas con su lectura, las que
terminan en siniestros con muertos y las reglas dentro de cada perfil.
"""

import argparse

import pandas as pd

from . import asociacion, config, graficos


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--soporte", type=float, default=asociacion.SOPORTE_MIN)
    parser.add_argument("--confianza", type=float, default=asociacion.CONFIANZA_MIN)
    parser.add_argument("--lift", type=float, default=asociacion.LIFT_MIN)
    args = parser.parse_args(argv)
    umbrales = {"soporte": args.soporte, "confianza": args.confianza, "lift": args.lift}

    entrada = config.PROCESSED / f"siniestros_perfiles_{config.ANIO}.parquet"
    if not entrada.exists():
        raise SystemExit(f"No existe {entrada}. Corre primero: python -m siniestralidad.agrupar")
    df = pd.read_parquet(entrada)
    config.TABLAS.mkdir(parents=True, exist_ok=True)

    trans = asociacion.transacciones(df)
    globales = asociacion.reglas(trans, **umbrales)
    seleccion = asociacion.seleccion(globales)
    muertos = asociacion.reglas_hacia(trans, "gravedad=con muertos", lift=args.lift)
    perfiles = asociacion.por_perfil(df, **umbrales)

    globales.to_csv(config.TABLAS / "oe5_reglas_globales.csv", index=False)
    seleccion.to_csv(config.TABLAS / "oe5_reglas_seleccion.csv", index=False)
    muertos.to_csv(config.TABLAS / "oe5_reglas_muertos.csv", index=False)
    perfiles.to_csv(config.TABLAS / "oe5_reglas_por_perfil.csv", index=False)
    graficos.reglas_lift(seleccion)

    print(f"{len(globales)} reglas en toda la base y {len(perfiles)} dentro de los perfiles "
          f"(soporte >= {args.soporte}, confianza >= {args.confianza}, lift > {args.lift})\n")
    for i, texto in enumerate(seleccion["lectura"], 1):
        print(f"{i:>2}. {texto}")
    if not muertos.empty:
        print("\nHacia siniestros con muertos:")
        for _, r in muertos.head(5).iterrows():
            print(f"   {r['antecedentes']}  (lift {r['lift']:.1f}, {100 * r['confianza']:.1f} %)")
    print(f"\nTablas en {config.TABLAS}")


if __name__ == "__main__":
    main()
