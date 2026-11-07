"""
Pruebas del problema de optimización y de la verificación de restricciones (Parte 4).

  python -m pytest tests/test_optimizacion.py
"""

import math

import numpy as np
import pytest

from src.matchmaking.optimizacion.problema import (INFACTIBLE, ProblemaVentana, decodificar,
                                                   frente_factible, hipervolumen,
                                                   objetivos_y_restricciones)
from src.matchmaking.optimizacion.verificar import verificar
from src.matchmaking.simulacion.escenarios import cargar

POLITICAS = cargar()["politicas"]
UMBRALES = cargar()["umbrales"]


def codificar(p):
    return [p["delta0"], p["alfa"], p["delta_max"] - p["delta0"]]


@pytest.fixture(scope="module")
def evaluadas():
    problema = ProblemaVentana()
    X = np.array([codificar(POLITICAS["base"]), codificar(POLITICAS["fija_60"])])
    return problema.evaluate(X, return_values_of=["F", "G", "cobertura"], return_as_dictionary=True)


def test_delta_max_nunca_menor_que_delta0():
    problema = ProblemaVentana()
    rng = np.random.default_rng(0)
    X = problema.xl + rng.random((10_000, 3)) * (problema.xu - problema.xl)
    assert all(decodificar(x)["delta_max"] >= decodificar(x)["delta0"] for x in X)


def test_problema_evalua_sin_errores(evaluadas):
    assert evaluadas["F"].shape == (2, 2) and evaluadas["G"].shape == (2, 2)
    assert np.all(np.isfinite(evaluadas["F"]))


def test_base_calibrada_es_factible(evaluadas):
    assert np.all(evaluadas["G"][0] <= 0)


def test_ventana_fija_60_es_infactible(evaluadas):
    dif = evaluadas["F"][1, 1]
    assert dif == pytest.approx(28, abs=2)
    assert evaluadas["G"][1, 0] > 0


def test_sin_parejas_es_infactible():
    metricas = {"espera_media": math.nan, "espera_p95": math.nan, "dif_media": math.nan,
                "cobertura": 0.0}
    f, g = objetivos_y_restricciones(metricas, UMBRALES)
    assert f == [INFACTIBLE, INFACTIBLE] and g == [INFACTIBLE, INFACTIBLE]


def test_frente_factible_e_hipervolumen():
    filas = [
        {"espera_media": 30, "dif_media": 5, "factible": True},
        {"espera_media": 40, "dif_media": 6, "factible": True},    # dominada por la primera
        {"espera_media": 10, "dif_media": 20, "factible": False},  # infactible
    ]
    frente = frente_factible(filas)
    assert frente == [filas[0]]
    assert hipervolumen(frente, [60, 15]) == pytest.approx(30 * 10)


def test_verificacion_detecta_quien_cumple():
    filas = verificar([POLITICAS["base"], POLITICAS["fija_60"]])
    assert filas[0]["cumple_d_max"] and filas[0]["cumple_cobertura"]
    assert not filas[1]["cumple_d_max"]
