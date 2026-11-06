"""
Pruebas de verificación del simulador (Parte 5 del enunciado).

  python -m pytest
"""

import math

import numpy as np
import pytest

from src.matchmaking.simulacion.llegadas import cargar_parametros, generar_solicitudes
from src.matchmaking.simulacion.motor import ESCENARIO_POR_DEFECTO, simular
from src.matchmaking.simulacion.politicas import adaptativa, validar, ventana, ventana_fija

PARAMETROS = cargar_parametros()
CORTO = {"tasa_media": 1.0, "duracion_s": 3600, "hora_inicio": 12}
POLITICAS = [ventana_fija(0), ventana_fija(20), ventana_fija(60), adaptativa(0, 1.5, 64),
             adaptativa(10, 0.2, 200)]


@pytest.mark.parametrize("politica", POLITICAS)
def test_conservacion_de_solicitudes(politica):
    """Toda solicitud que llega termina emparejada o pendiente: llegadas = 2 * parejas + pendientes."""
    r = simular(politica, CORTO, 7)
    assert r["n_llegadas"] == 2 * r["n_parejas"] + r["pendientes"]


@pytest.mark.parametrize("politica", POLITICAS)
def test_esperas_no_negativas_y_restriccion_de_ventana(politica):
    r = simular(politica, CORTO, 3, detalle=True)
    assert all(w >= 0 for w in r["detalle"]["esperas"])
    for t, i, j, ai, aj, ri, rj in r["detalle"]["parejas"]:
        assert t >= ai and t >= aj
        assert abs(ri - rj) <= min(ventana(politica, t - ai), ventana(politica, t - aj)) + 1e-9


def test_misma_semilla_mismo_resultado():
    a = simular(adaptativa(0, 1.5, 64), CORTO, 11)
    b = simular(adaptativa(0, 1.5, 64), CORTO, 11)
    c = simular(adaptativa(0, 1.5, 64), CORTO, 12)
    sin_tiempo = lambda r: {k: v for k, v in r.items() if k != "segundos_ejecucion"}
    assert sin_tiempo(a) == sin_tiempo(b)
    assert sin_tiempo(a) != sin_tiempo(c)


def test_ventana_cero_solo_empareja_trofeos_iguales():
    r = simular(ventana_fija(0), CORTO, 5, detalle=True)
    assert r["n_parejas"] > 0  # hay empates gracias a los pisos de arena
    assert all(d == 0 for d in r["detalle"]["diferencias"])
    assert r["cobertura"] < simular(ventana_fija(20), CORTO, 5)["cobertura"]


def test_ventana_infinita_equivale_a_emparejar_al_azar():
    """Con poca demanda y ventana infinita, cada pareja son dos llegadas consecutivas al azar."""
    esc = {"tasa_media": 0.05, "duracion_s": 2 * 86400, "calentamiento_s": 0}
    r = simular(ventana_fija(math.inf), esc, 1)
    rng = np.random.default_rng(99)
    frec = PARAMETROS["trofeos_solicitudes"]["frecuencias"]
    p = np.asarray(frec["conteos"], float) / sum(frec["conteos"])
    x = rng.choice(frec["valores"], 200_000, p=p)
    y = rng.choice(frec["valores"], 200_000, p=p)
    esperado = np.abs(x - y).mean()
    assert r["dif_media"] == pytest.approx(esperado, rel=0.05)
    assert r["cobertura"] > 0.99


def test_ventana_mas_amplia_reduce_la_espera():
    angosta = simular(ventana_fija(20), CORTO, 21)
    amplia = simular(ventana_fija(60), CORTO, 21)
    assert amplia["espera_media"] < angosta["espera_media"]
    assert amplia["dif_media"] > angosta["dif_media"]


def test_numeros_aleatorios_comunes():
    """Con la misma semilla, todas las políticas reciben exactamente las mismas solicitudes."""
    a = simular(ventana_fija(20), CORTO, 8, detalle=True)
    b = simular(adaptativa(0, 3, 64), CORTO, 8, detalle=True)
    assert a["n_llegadas"] == b["n_llegadas"]
    esc = {**ESCENARIO_POR_DEFECTO, **CORTO}
    t1, r1 = generar_solicitudes(esc, PARAMETROS, np.random.default_rng(8))
    t2, r2 = generar_solicitudes(esc, PARAMETROS, np.random.default_rng(8))
    assert np.array_equal(t1, t2) and np.array_equal(r1, r2)


def test_escenario_invalido():
    with pytest.raises(ValueError):
        simular(ventana_fija(20), {"tasa_media": 1, "duracion": 3600}, 1)


def test_politica_invalida():
    with pytest.raises(ValueError):
        validar(adaptativa(50, 1, 20))
    with pytest.raises(ValueError):
        validar(adaptativa(-1, 1, 20))


def _referencia_ingenua(politica, escenario, semilla):
    """Revisa toda la cola en cada revisión, sin atajos. Sirve para verificar el motor."""
    esc = {**ESCENARIO_POR_DEFECTO, **escenario}
    rng = np.random.default_rng(semilla)
    tiempos, trofeos = generar_solicitudes(esc, PARAMETROS, rng)
    a, r = tiempos.tolist(), trofeos.tolist()
    espera_cola, parejas, sig = [], [], 0
    for k in range(1, int(esc["duracion_s"] / esc["dt"]) + 1):
        t = k * esc["dt"]
        while sig < len(a) and a[sig] <= t:
            espera_cola.append(sig)
            sig += 1
        for i in list(espera_cola):
            if i not in espera_cola:
                continue
            di = ventana(politica, t - a[i])
            cands = [(abs(r[i] - r[j]), a[j], j) for j in espera_cola if j != i
                     and abs(r[i] - r[j]) <= min(di, ventana(politica, t - a[j]))]
            if cands:
                _, _, j = min(cands)
                espera_cola.remove(i)
                espera_cola.remove(j)
                parejas.append((t, i, j))
    return parejas


@pytest.mark.parametrize("politica", [ventana_fija(30), adaptativa(0, 2, 64), adaptativa(5, 0.5, 40)])
@pytest.mark.parametrize("tasa,semilla", [(0.5, 4), (2.0, 9)])
def test_motor_igual_a_la_referencia_ingenua(politica, tasa, semilla):
    """El motor optimizado forma exactamente las mismas parejas, en el mismo orden."""
    esc = {"tasa_media": tasa, "duracion_s": 1200, "hora_inicio": 3}
    r = simular(politica, esc, semilla, detalle=True)
    motor = [(t, i, j) for t, i, j, *_ in r["detalle"]["parejas"]]
    assert motor == _referencia_ingenua(politica, esc, semilla)
