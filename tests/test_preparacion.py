import pandas as pd
import pytest

from siniestralidad.corredores import seleccionar_corredores, via_principal
from siniestralidad.depuracion import (
    depurar, filtrar_corredores, parsear_gravedad, parsear_hora, parsear_si_no,
)
from siniestralidad.diccionario import perfil_variables


@pytest.mark.parametrize("direccion, esperado", [
    ("AK 68-AC 26 02", "KR 68"),
    ("KR 68-CL 13", "KR 68"),
    ("CL 26 - KR 50", "CL 26"),
    ("AC 13 SUR-KR 30", "CL 13 SUR"),
    ("KR 7 BIS-CL 45", "KR 7 BIS"),
    ("CL 45A-KR 7", "CL 45A"),
    ("Avenida Boyacá con calle 63", "KR 72"),
    ("AUTOPISTA NORTE - CL 170", "KR 45"),
    ("Avenida Calle 80 con Kr 100", "CL 80"),
    ("AV AVENIDA CIUDAD DE CALI-KR 55 S 02", "KR 86"),
    ("AV AVENIDA CIUDAD DE VILLAVICENCIO-KR 80", "AV CIUDAD DE VILLAVICENCIO"),
    ("AU SUR-KR 68", "AUTOPISTA SUR"),
    ("AU NORTE-CL 127", "KR 45"),
    ("KR 12DBIS-CL 24 02", "KR 12D BIS"),
    ("TR 33-CL 56C S 02", "TV 33"),
    ("KR 51-CL 58 S 2", "KR 51"),
    ("CL 58 S-KR 51", "CL 58 SUR"),
    ("KR 11 E - CL 42 A S 02", "KR 11 ESTE"),
    ("sin dato", None),
    (None, None),
])
def test_via_principal(direccion, esperado):
    assert via_principal(direccion) == esperado


def test_parseos_basicos():
    assert parsear_hora(pd.Series(["7", "07:35", "23:59:00", "25", "x"])).tolist()[:3] == [7, 7, 23]
    assert parsear_hora(pd.Series(["25", "x"])).isna().all()
    assert parsear_si_no(pd.Series(["SI", "N", "1", "no", None])).tolist() == [True, False, True, False, False]
    grav = parsear_gravedad(pd.Series(["CON MUERTOS", "Con heridos", "SOLO DAÑOS", "?"]))
    assert list(grav[:3]) == ["con muertos", "con heridos", "solo danos"]
    assert pd.isna(grav[3])


def base_sintetica():
    filas = [
        # codigo, fecha, hora, lat, lon, direccion, gravedad, moto
        ("1", "1/03/2024", "08:10", "4.65", "-74.10", "AK 68-AC 26", "SOLO DAÑOS", "N"),
        ("2", "2/03/2024", "22:00", "4.60", "-74.12", "AK 68-CL 13", "CON HERIDOS", "S"),
        ("2", "2/03/2024", "22:00", "4.60", "-74.12", "AK 68-CL 13", "CON HERIDOS", "S"),  # duplicado
        ("3", "31/12/2023", "10:00", "4.60", "-74.12", "AK 30-CL 13", "SOLO DAÑOS", "N"),  # otro año
        ("4", "5/05/2024", "99", "4.60", "-74.12", "AK 30-CL 13", "SOLO DAÑOS", "N"),  # hora inválida
        ("5", "6/05/2024", "03:00", "0", "0", "AK 30-CL 13", "SOLO DAÑOS", "N"),  # sin coordenadas
        ("6", "7/05/2024", "13:00", "4,61", "-74,08", "AK 30-CL 13", "CON MUERTOS", "S"),
        ("7", "8/05/2024", "18:00", "4.70", "-74.05", "KR 7-CL 72", "", "N"),  # sin gravedad
        ("8", "9/05/2024", "18:00", "4.70", "-74.05", "PARQUEADERO", "SOLO DAÑOS", "N"),  # sin corredor
        ("9", "1/06/2024", "05:00", "4.70", "-74.05", "KR 7-CL 72", "SOLO DAÑOS", "N"),
    ]
    cols = ["Codigo_Accidente", "Fecha_Acc", "Hora_Acc", "Latitud", "Longitud", "Direccion",
            "Gravedad_Indicador_Tradicional", "Con_Moto"]
    df = pd.DataFrame(filas, columns=cols)
    df["Localidad"] = "KENNEDY"
    df["Clase_Acc"] = "CHOQUE"
    df["Con_Peaton"] = "N"
    return df


def test_depurar_trazabilidad_y_derivadas():
    base, traza = depurar(base_sintetica())
    assert base["Codigo_Accidente"].tolist() == ["1", "2", "6", "9"]
    assert traza["descartados"].sum() == 6
    assert traza["quedan"].iloc[-1] == 4

    fila = base.set_index("Codigo_Accidente")
    assert fila.loc["2", "franja"] == "noche"
    assert fila.loc["2", "dia_semana"] == "sabado"
    assert bool(fila.loc["2", "fin_semana"])
    assert bool(fila.loc["2", "con_moto"])
    assert bool(fila.loc["6", "con_victimas"])
    assert not bool(fila.loc["1", "con_victimas"])
    assert fila.loc["9", "franja"] == "madrugada"
    assert fila.loc["6", "latitud"] == pytest.approx(4.61)


def test_seleccion_y_filtro_de_corredores():
    base, traza = depurar(base_sintetica())
    ranking = seleccionar_corredores(base, n=1)
    assert ranking["corredor"].tolist() == ["KR 68"]
    assert ranking["nombre"].iloc[0] == "Avenida Carrera 68"
    final, traza = filtrar_corredores(base, traza, ranking["corredor"].tolist())
    assert len(final) == 2
    assert traza["quedan"].iloc[-1] == 2


def test_corredor_como_via_que_cruza():
    base, traza = depurar(base_sintetica())
    # "AK 30-CL 13" (código 6) entra por la Calle 13 aunque no sea la vía principal.
    final, _ = filtrar_corredores(base, traza, ["KR 68", "CL 13"])
    asignados = final.set_index("Codigo_Accidente")["corredor"].to_dict()
    assert asignados == {"1": "KR 68", "2": "KR 68", "6": "CL 13"}


def test_perfil_variables():
    perfil = perfil_variables(base_sintetica()).set_index("variable")
    assert perfil.loc["Gravedad_Indicador_Tradicional", "nulos"] == 1
    assert perfil.loc["Codigo_Accidente", "distintos"] == 9


def test_cargar_zip_de_csv_exportados_de_excel(tmp_path):
    import zipfile

    from siniestralidad.carga import cargar_anuario

    archivo = tmp_path / "anuario.zip"
    siniestros = "﻿Codigo_Accidente;Latitud\n1;4,65\n2;4,60\n"
    with zipfile.ZipFile(archivo, "w") as z:
        z.writestr("siniestros.csv", siniestros.encode("utf-8"))
        z.writestr("Actores.csv", "Codigo_Accidente,Condicion\n1,CONDUCTOR\n".encode("latin-1"))
    hojas = cargar_anuario(archivo)
    assert hojas["siniestros"].columns.tolist() == ["Codigo_Accidente", "Latitud"]
    assert hojas["siniestros"]["Latitud"].tolist() == ["4,65", "4,60"]
    assert len(hojas["actores"]) == 1
    assert "vehiculos" not in hojas
