"""
Pruebas de las métricas de los experimentos finales y de su agregación (R4, Parte 5 y 7).

  python -m pytest tests/test_analisis.py
"""

import math

import pytest

from src.matchmaking.analisis.metricas import comparacion_pareada, resumir
from src.matchmaking.experimentos.ejecutar import _agrupar, _comparar, _resumir_corridas


def test_resumir_valores_iguales_desviacion_cero():
    r = resumir([10.0] * 5)
    assert r["n"] == 5
    assert r["media"] == 10.0
    assert r["desv"] == 0.0
    assert r["ic95_inf"] == r["ic95_sup"] == 10.0


def test_resumir_ic95_contiene_la_media_y_se_angosta_con_mas_datos():
    pocos = resumir([8.0, 9.0, 11.0, 12.0])
    muchos = resumir([8.0, 9.0, 11.0, 12.0] * 10)
    for r in (pocos, muchos):
        assert r["ic95_inf"] < r["media"] < r["ic95_sup"]
    assert (muchos["ic95_sup"] - muchos["ic95_inf"]) < (pocos["ic95_sup"] - pocos["ic95_inf"])


def test_comparacion_pareada_exige_mismo_numero_de_corridas():
    with pytest.raises(ValueError):
        comparacion_pareada([1.0, 2.0], [1.0, 2.0, 3.0])


def test_comparacion_pareada_reduccion_y_significancia():
    referencia = [20.0] * 30
    candidata = [10.0] * 30  # la mitad de la espera, siempre: diferencia sin variación
    c = comparacion_pareada(candidata, referencia)
    assert c["reduccion_%"] == pytest.approx(50.0)
    assert c["significativa"] is True

    c_igual = comparacion_pareada(referencia, referencia)
    assert c_igual["reduccion_%"] == 0.0
    assert c_igual["significativa"] is False


def _corrida(escenario, politica, semilla, espera_media, dif_media=10.0, cobertura=1.0):
    return {"escenario": escenario, "politica": politica, "semilla": semilla,
            "espera_media": espera_media, "espera_p95": espera_media * 2,
            "dif_media": dif_media, "dif_p90": dif_media * 2, "dif_max": dif_media * 3,
            "cobertura": cobertura, "pendientes": 0, "cola_media": 5.0}


def test_agrupar_separa_por_escenario_y_politica_y_ordena_por_semilla():
    corridas = [_corrida("base", "fija_20", 2, 20), _corrida("base", "fija_20", 1, 21),
                _corrida("base", "base", 1, 15)]
    g = _agrupar(corridas)
    assert [c["semilla"] for c in g[("base", "fija_20")]] == [1, 2]
    assert len(g[("base", "base")]) == 1


def test_resumir_corridas_agrega_media_por_metrica():
    corridas = [_corrida("base", "fija_20", s, espera) for s, espera in enumerate([10.0, 20.0, 30.0])]
    resumen = _resumir_corridas(corridas, ["base"], ["fija_20"])
    assert len(resumen) == 1
    assert resumen[0]["n"] == 3
    assert resumen[0]["espera_media_media"] == pytest.approx(20.0)


def test_comparar_declara_mejora_solo_si_cumple_los_tres_umbrales():
    umbrales = {"d_max": 15, "cobertura_min": 0.95, "reduccion_espera_min": 0.10}
    semillas = list(range(30))
    corridas = (
        [_corrida("base", "fija_20", s, 20.0, dif_media=8.0) for s in semillas]
        + [_corrida("base", "base", s, 18.0, dif_media=12.0) for s in semillas]
        + [_corrida("base", "nsga_codo", s, 14.0, dif_media=11.0) for s in semillas]           # mejora
        + [_corrida("base", "nsga_menor_espera", s, 19.9, dif_media=20.0) for s in semillas]     # excede D_max
        + [_corrida("base", "nsga_intermedia", s, 19.9, dif_media=11.0) for s in semillas]       # reducción < 10 %
        + [_corrida("base", "nsga_menor_dif", s, 14.0, dif_media=11.0, cobertura=0.5) for s in semillas]  # cobertura baja
        + [_corrida("base", "aleatoria_mejor", s, 14.0, dif_media=11.0) for s in semillas]      # mejora
    )
    politicas = ["base", "fija_20", "nsga_codo", "nsga_menor_espera", "nsga_intermedia",
                "nsga_menor_dif", "aleatoria_mejor"]  # subconjunto: no hace falta fija_40/fija_60
    comparacion = _comparar(corridas, ["base"], politicas, umbrales)

    por_politica = {f["politica"]: f for f in comparacion if f["referencia"] == "fija_20"}
    assert por_politica["nsga_codo"]["mejora_declarada"] is True
    assert por_politica["aleatoria_mejor"]["mejora_declarada"] is True
    assert por_politica["nsga_menor_espera"]["mejora_declarada"] is False  # no cumple D_max
    assert por_politica["nsga_intermedia"]["mejora_declarada"] is False   # reducción irrelevante
    assert por_politica["nsga_menor_dif"]["mejora_declarada"] is False    # no cumple cobertura
