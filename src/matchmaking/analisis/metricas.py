"""
Resumen estadístico de repeticiones independientes y comparación pareada entre políticas
que comparten las mismas semillas (números aleatorios comunes), para los experimentos finales
(R4, Parte 5 y 7 del enunciado; decisiones.md D10 y D13).

Con n = 30 repeticiones se usa la aproximación normal (z = 1.96) en vez de la t de Student; con
n >= 30 la diferencia frente al valor crítico de la t es menor al 2 %.
"""

import math

import numpy as np

Z95 = 1.959963984540054


def resumir(valores):
    """Media, desviación estándar (ddof=1) e IC95 % de una lista de repeticiones independientes."""
    v = np.asarray(valores, dtype=float)
    n = len(v)
    media = float(v.mean()) if n else math.nan
    desv = float(v.std(ddof=1)) if n > 1 else 0.0
    margen = Z95 * desv / math.sqrt(n) if n > 1 else 0.0
    return {"n": n, "media": media, "desv": desv, "ic95_inf": media - margen, "ic95_sup": media + margen}


def comparacion_pareada(candidata, referencia):
    """
    Diferencia pareada corrida a corrida (referencia - candidata), con las mismas semillas en
    ambas listas y en el mismo orden. Positivo: la candidata reduce la métrica de la referencia.

    reduccion_%   diferencia media como porcentaje de la media de la referencia
    significativa el IC95 % de la diferencia pareada excluye el 0 por el lado de la mejora (D10)
    """
    c, r = np.asarray(candidata, dtype=float), np.asarray(referencia, dtype=float)
    if len(c) != len(r):
        raise ValueError("candidata y referencia deben tener el mismo número de corridas pareadas")
    resumen = resumir(r - c)
    media_ref = float(r.mean())
    resumen["reduccion_%"] = 100 * resumen["media"] / media_ref if media_ref else math.nan
    resumen["significativa"] = resumen["ic95_inf"] > 0
    return resumen
