"""
Generación de solicitudes de emparejamiento.

Llegadas: proceso de Poisson no homogéneo con tasa constante dentro de cada hora (supuesto del
informe). La tasa de la hora h es

    lambda_h = tasa_media * 24 * peso[h]        [solicitudes / s]

donde peso es perfil_horario.peso de parametros.json (24 valores que suman 1), de modo que el
promedio diario de lambda_h es tasa_media. Dentro de cada tramo, el número de llegadas es
Poisson(lambda_h * duración) y sus tiempos son uniformes (propiedad del proceso de Poisson).

Trofeos: se muestrean por la inversa de la distribución empírica, interpolando los 101 cuantiles
de trofeos_solicitudes.cuantiles, y se redondean a entero.
"""

import json
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[3]
PARAMETROS = RAIZ / "data" / "processed" / "parametros.json"


def cargar_parametros(ruta=PARAMETROS):
    return json.loads(Path(ruta).read_text(encoding="utf-8"))


def muestrear_trofeos(cuantiles, n, rng):
    """n trofeos enteros con la distribución empírica dada por 101 cuantiles (P0..P100)."""
    u = rng.random(n) * 100
    return np.rint(np.interp(u, np.arange(len(cuantiles)), cuantiles)).astype(np.int64)


def tasas_por_hora(tasa_media, peso):
    peso = np.asarray(peso, dtype=float)
    return tasa_media * 24 * peso / peso.sum()


def generar_solicitudes(escenario, parametros, rng):
    """
    Devuelve (tiempos, trofeos), ordenados por tiempo de llegada.

    tiempos: segundos desde el inicio de la simulación (float).
    El reloj de la simulación empieza a la hora escenario["hora_inicio"] (hora de Guatemala).
    """
    duracion = float(escenario["duracion_s"])
    hora_inicio = float(escenario.get("hora_inicio", 0))
    tasas = tasas_por_hora(escenario["tasa_media"], parametros["perfil_horario"]["peso"])

    tiempos = []
    t = 0.0
    while t < duracion:
        reloj = (hora_inicio * 3600 + t) % 86400
        hora = int(reloj // 3600)
        fin_tramo = min(duracion, t + (3600 - reloj % 3600))
        n = rng.poisson(tasas[hora] * (fin_tramo - t))
        tiempos.append(rng.uniform(t, fin_tramo, n))
        t = fin_tramo
    tiempos = np.sort(np.concatenate(tiempos)) if tiempos else np.empty(0)
    trofeos = muestrear_trofeos(parametros["trofeos_solicitudes"]["cuantiles"], len(tiempos), rng)
    return tiempos, trofeos
