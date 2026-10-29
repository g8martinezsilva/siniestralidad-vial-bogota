"""Etapa 6 del plan de trabajo: perfiles de siniestralidad (OE4).

Uso::

    python -m siniestralidad.agrupar
    python -m siniestralidad.agrupar --k 5

Sin ``--k`` se elige el número de perfiles con el mayor coeficiente de silueta
entre 3 y 8. Genera las tablas ``oe4_*.csv``, las figuras y la base con el
perfil y la zona de cada siniestro (``siniestros_perfiles_2024.parquet``), que
usan las reglas de asociación.
"""

import argparse

import pandas as pd

from . import clustering, config, graficos


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--k", type=int, default=None, help="número de perfiles de K-means")
    parser.add_argument("--radio", type=float, default=150, help="radio de DBSCAN en metros")
    parser.add_argument("--minimo", type=int, default=15, help="siniestros mínimos por zona")
    args = parser.parse_args(argv)

    entrada = config.PROCESSED / f"siniestros_corredores_{config.ANIO}.parquet"
    if not entrada.exists():
        raise SystemExit(f"No existe {entrada}. Corre primero: python -m siniestralidad.preparar")
    df = pd.read_parquet(entrada)
    config.TABLAS.mkdir(parents=True, exist_ok=True)

    x = clustering.matriz(df)
    evaluacion = clustering.evaluar_k(x)
    k = args.k or int(evaluacion.loc[evaluacion["silueta"].idxmax(), "k"])
    evaluacion.to_csv(config.TABLAS / "oe4_seleccion_k.csv", index=False)

    perfiles = clustering.kmeans(x, k)
    fichas = clustering.fichas(df, x, perfiles)
    fichas.to_csv(config.TABLAS / "oe4_perfiles.csv", index=False)
    prueba = clustering.gravedad_por_perfil(df, perfiles)
    pd.DataFrame([prueba]).to_csv(config.TABLAS / "oe4_gravedad_por_perfil.csv", index=False)

    zonas = clustering.zonas_densas(df, args.radio, args.minimo)
    resumen_zonas = clustering.resumen_zonas(df, zonas)
    resumen_zonas.to_csv(config.TABLAS / "oe4_zonas_densas.csv", index=False)

    graficos.seleccion_k(evaluacion, k)
    graficos.perfiles_gravedad(fichas)
    graficos.mapa_zonas(df, zonas, resumen_zonas)

    salida = config.PROCESSED / f"siniestros_perfiles_{config.ANIO}.parquet"
    df.assign(perfil=perfiles + 1, zona=zonas).to_parquet(salida, index=False)

    with pd.option_context("display.max_colwidth", 80, "display.width", 200):
        print(f"k = {k} (silueta {evaluacion.loc[evaluacion['k'] == k, 'silueta'].iloc[0]:.3f})\n")
        print(fichas[["perfil", "siniestros", "rasgos_dominantes", "%_con_muertos"]].to_string(index=False))
        print(f"\nGravedad por perfil: chi2 = {prueba['chi2']}, p = {prueba['p_valor']:.2e}, "
              f"V = {prueba['v_cramer']} ({prueba['magnitud']})")
        print(f"\nDBSCAN: {len(resumen_zonas)} zonas densas con {int((zonas >= 0).sum())} siniestros")
        print(resumen_zonas.head(5)[["posicion", "cruce", "siniestros", "pct_con_muertos"]].to_string(index=False))


if __name__ == "__main__":
    main()
