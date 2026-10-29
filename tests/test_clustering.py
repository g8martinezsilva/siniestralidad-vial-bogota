import numpy as np
import pandas as pd

from siniestralidad import clustering
from test_hipotesis import base_aleatoria


def base(n=400):
    df = base_aleatoria(n)
    rng = np.random.default_rng(1)
    df["clase"] = rng.choice(["choque", "atropello", "incendio"], n)
    for c in ["con_peaton", "con_bicicleta", "con_tpp"]:
        df[c] = rng.random(n) < 0.2
    # 60 siniestros en un mismo cruce (radio de ~30 m) y el resto dispersos.
    df["latitud"] = np.r_[4.60 + rng.normal(0, 0.0002, 60), rng.uniform(4.55, 4.75, n - 60)]
    df["longitud"] = np.r_[-74.08 + rng.normal(0, 0.0002, 60), rng.uniform(-74.15, -74.05, n - 60)]
    df["Direccion"] = "KR 10-CL 1 02"
    df["localidad"] = "SANTA FE"
    return df


def test_matriz_es_binaria_y_agrupa_clases_raras():
    x = clustering.matriz(base())
    assert set(np.unique(x.values)) <= {0.0, 1.0}
    assert "clase_otra" in x.columns and "clase_incendio" not in x.columns


def test_fichas_una_por_perfil():
    df = base()
    x = clustering.matriz(df)
    etiquetas = clustering.kmeans(x, 3)
    fichas = clustering.fichas(df, x, etiquetas)
    assert fichas["perfil"].tolist() == [1, 2, 3]
    assert fichas["siniestros"].sum() == len(df)


def test_dbscan_encuentra_el_cruce():
    df = base()
    zonas = clustering.zonas_densas(df, radio_m=100, minimo=15)
    resumen = clustering.resumen_zonas(df, zonas)
    assert resumen["siniestros"].iloc[0] >= 60
    assert resumen["cruce"].iloc[0] == "KR 10 - CL 1"
