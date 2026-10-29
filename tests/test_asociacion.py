import numpy as np

from siniestralidad import asociacion
from test_clustering import base


def base_reglas(n=600):
    df = base(n)
    rng = np.random.default_rng(2)
    # La embriaguez casi siempre ocurre de noche: debe aparecer como regla.
    df["con_embriaguez"] = rng.random(n) < 0.15
    df.loc[df["con_embriaguez"], "franja"] = "noche"
    df["perfil"] = rng.integers(1, 3, n)
    return df


def test_transacciones_booleanas_un_item_por_variable():
    trans = asociacion.transacciones(base_reglas())
    assert trans.dtypes.eq(bool).all()
    assert trans.filter(like="franja=").sum(axis=1).eq(1).all()
    assert "actor=embriaguez" in trans.columns


def test_encuentra_la_regla_plantada_y_respeta_umbrales():
    r = asociacion.reglas(asociacion.transacciones(base_reglas()), soporte=0.05, confianza=0.5)
    assert ((r["antecedentes"] == "actor=embriaguez") & (r["consecuentes"] == "franja=noche")).any()
    assert (r["confianza"] >= 0.5).all() and (r["lift"] > asociacion.LIFT_MIN).all()


def test_sin_triviales_ni_gravedad_en_el_antecedente():
    r = asociacion.reglas(asociacion.transacciones(base_reglas()), soporte=0.02, confianza=0.1)
    assert not r["antecedentes"].str.contains("gravedad=").any()
    assert not (r["antecedentes"].str.contains("clase=atropello")
                & r["consecuentes"].str.contains("actor=peatón")).any()


def test_seleccion_diversa_con_lectura():
    r = asociacion.reglas(asociacion.transacciones(base_reglas()), soporte=0.02, confianza=0.1)
    sel = asociacion.seleccion(r, n=5)
    items = [asociacion._items(f) for _, f in sel.iterrows()]
    assert all(len(a & b) < 2 for i, a in enumerate(items) for b in items[i + 1:])
    assert sel["lectura"].str.startswith("Cuando se presenta").all()


def test_por_perfil_marca_el_perfil():
    r = asociacion.por_perfil(base_reglas(), soporte=0.05, confianza=0.5)
    assert set(r["perfil"]) <= {1, 2}
