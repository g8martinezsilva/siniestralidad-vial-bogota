"""Etapas 1 a 3 del plan de trabajo: construye la base de análisis (OE1).

Uso::

    python -m siniestralidad.preparar
    python -m siniestralidad.preparar --archivo ruta/a/la/base.xlsx

Genera en ``reports/tablas``:

- ``diccionario_variables.csv``: tipo, nulos y valores distintos de cada campo.
- ``corredores_seleccionados.csv``: los 10 corredores con más siniestros.
- ``trazabilidad_depuracion.csv``: registros descartados en cada paso.
- ``nulos_variables_clave.csv``: indicador del OE1 (menos del 5 %).

y en ``data/processed`` la base limpia ``siniestros_corredores_2024.parquet``.
"""

import argparse
from pathlib import Path

from . import config
from .carga import archivo_por_defecto, cargar_anuario
from .corredores import seleccionar_corredores
from .depuracion import depurar, filtrar_corredores, nulos_variables_clave
from .diccionario import perfil_variables


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--archivo", type=Path, default=None,
                        help="base del Anuario 2024 (.xlsx, .zip con CSV o .csv)")
    parser.add_argument("--n-corredores", type=int, default=config.N_CORREDORES)
    args = parser.parse_args(argv)

    config.TABLAS.mkdir(parents=True, exist_ok=True)
    config.PROCESSED.mkdir(parents=True, exist_ok=True)

    archivo = args.archivo or archivo_por_defecto()
    print(f"Leyendo {archivo} ...")
    hojas = cargar_anuario(archivo)
    crudo = hojas["siniestros"]
    print(f"  {len(crudo):,} siniestros, {crudo.shape[1]} columnas")

    perfil_variables(crudo).to_csv(config.TABLAS / "diccionario_variables.csv", index=False)

    base, traza = depurar(crudo)
    ranking = seleccionar_corredores(base, args.n_corredores)
    ranking.to_csv(config.TABLAS / "corredores_seleccionados.csv", index=False)

    final, traza = filtrar_corredores(base, traza, ranking["corredor"].tolist())
    traza.to_csv(config.TABLAS / "trazabilidad_depuracion.csv", index=False)
    nulos = nulos_variables_clave(final)
    nulos.rename("nulos_%").to_csv(config.TABLAS / "nulos_variables_clave.csv")

    salida = config.PROCESSED / f"siniestros_corredores_{config.ANIO}.parquet"
    final.to_parquet(salida, index=False)

    print("\nTrazabilidad de la depuración:")
    print(traza.to_string(index=False))
    print("\nCorredores seleccionados:")
    print(ranking[["posicion", "nombre", "siniestros", "longitud_km", "siniestros_por_km"]].to_string(index=False))
    print("\n% de nulos en variables clave:")
    print(nulos.to_string())
    print(f"\nBase limpia: {salida} ({len(final):,} siniestros)")


if __name__ == "__main__":
    main()
