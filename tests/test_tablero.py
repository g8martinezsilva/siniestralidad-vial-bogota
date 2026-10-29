import pandas as pd

from siniestralidad import tablero
from test_hipotesis import base_aleatoria


def base():
    df = base_aleatoria(300)
    df["nombre_corredor"] = df["corredor"]
    df["tipo_dia"] = df["fin_semana"].map({True: "Fin de semana", False: "Entre semana"})
    df["hora"] = pd.array(range(300), dtype="Int64") % 24
    df["dia_semana"] = pd.Categorical(["lunes", "martes", "domingo"] * 100,
                                      categories=["lunes", "martes", "miercoles", "jueves", "viernes",
                                                  "sabado", "domingo"])
    return df


def test_filtrar_combina_filtros_y_vacio_no_filtra():
    df = base()
    assert len(tablero.filtrar(df)) == len(df)
    sub = tablero.filtrar(df, corredores=["A"], franjas=["noche"], tipo_dia=["Fin de semana"])
    assert (sub["corredor"] == "A").all() and (sub["franja"] == "noche").all() and sub["fin_semana"].all()


def test_indicadores():
    df = base()
    k = tablero.indicadores(df)
    assert k["siniestros"] == len(df)
    assert k["con_muertos"] == (df["gravedad"] == "con muertos").sum()
    assert tablero.indicadores(df.iloc[:0])["pct_con_moto"] == 0.0


def test_por_km_ordena_por_tasa():
    tabla = tablero.por_km(base(), longitudes=pd.Series({"A": 100.0, "B": 1.0}))
    assert tabla["corredor"].tolist() == ["B", "A"]


def test_dia_hora_tiene_7_dias_y_24_horas():
    m = tablero.dia_hora(base())
    assert m.shape == (7, 24) and m.values.sum() == 300
