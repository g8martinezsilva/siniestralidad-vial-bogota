import numpy as np
import pandas as pd
import pytest

from siniestralidad import config
from siniestralidad.hipotesis import contrastar, h1_concentracion, h3_moto, magnitud_v


def base_aleatoria(n=2000, semilla=0):
    rng = np.random.default_rng(semilla)
    moto = rng.random(n) < 0.6
    # Con moto hay más víctimas (para que H3 se rechace).
    victimas = rng.random(n) < np.where(moto, 0.95, 0.80)
    muertos = victimas & (rng.random(n) < 0.06)
    gravedad = np.where(muertos, "con muertos", np.where(victimas, "con heridos", "solo danos"))
    return pd.DataFrame({
        "corredor": rng.choice(["A", "B"], n, p=[2 / 3, 1 / 3]),
        "franja": pd.Categorical(rng.choice(config.FRANJAS, n), categories=config.FRANJAS),
        "fin_semana": rng.random(n) < 2 / 7,
        "con_moto": moto,
        "con_victimas": victimas,
        "gravedad": pd.Categorical(gravedad, categories=config.GRAVEDAD_ORDEN, ordered=True),
    })


def test_h1_no_rechaza_si_los_siniestros_siguen_la_longitud():
    r = h1_concentracion(base_aleatoria(), longitudes=pd.Series({"A": 20.0, "B": 10.0}))
    assert r["p_valor"] > 0.05
    assert r["gl"] == 1


def test_h3_detecta_mas_victimas_con_moto():
    r = h3_moto(base_aleatoria())
    assert r["p_valor"] < 0.001
    assert r["valor_efecto"] > 1


def test_contrastar_aplica_bonferroni(monkeypatch):
    import siniestralidad.hipotesis as h

    monkeypatch.setattr(h, "cargar_longitudes", lambda: pd.Series({"A": 20.0, "B": 10.0}))
    resultados, apoyo = contrastar(base_aleatoria())
    principales = resultados[resultados["p_bonferroni"].notna()]
    assert len(principales) == 4
    assert (principales["p_bonferroni"] >= principales["p_valor"]).all()
    assert "oe3_h1_corredores" in apoyo


@pytest.mark.parametrize("v, esperado", [(0.05, "despreciable"), (0.2, "pequeño"), (0.4, "mediano"), (0.6, "grande")])
def test_magnitud_v(v, esperado):
    assert magnitud_v(v) == esperado
