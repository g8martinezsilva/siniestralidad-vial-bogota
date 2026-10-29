import pandas as pd

from siniestralidad.depuracion import depurar, filtrar_corredores
from siniestralidad.descriptivo import frecuencias, por_actor, por_franja, resumen, tablas

from test_preparacion import base_sintetica


def base():
    df, traza = depurar(base_sintetica())
    final, _ = filtrar_corredores(df, traza, ["KR 68", "KR 30", "KR 7"])
    return final


def test_frecuencias_suman_100():
    tabla = frecuencias(base()["gravedad"])
    assert tabla["siniestros"].sum() == 4
    assert abs(tabla["%"].sum() - 100) < 0.01
    assert tabla["gravedad"].tolist() == ["solo danos", "con heridos", "con muertos"]


def test_franja_por_hora_usa_la_duracion():
    tabla = por_franja(base()).set_index("franja")
    assert tabla.loc["madrugada", "horas"] == 6
    assert tabla.loc["noche", "siniestros_por_hora"] == 0.2


def test_actores_y_resumen():
    df = base()
    actores = por_actor(df).set_index("actor")
    assert actores.loc["Motocicleta", "siniestros"] == 2
    r = resumen(df)
    assert r["n"] == 4
    assert r["top3_corredores_total"][0] == "Avenida Carrera 68"
    assert set(tablas(df)) >= {"oe2_corredores", "oe2_franjas", "oe2_dia_por_hora"}
