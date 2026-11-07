"""
Políticas de ampliación de la ventana de trofeos.

Ventana permitida para una solicitud que lleva w segundos esperando:

    Delta(w) = min(delta_max, delta0 + alfa * w)        [trofeos]

  delta0     ventana inicial                       [trofeos]
  alfa       velocidad de ampliación               [trofeos / s]
  delta_max  ventana máxima                        [trofeos]

Una ventana fija de +-D es el caso delta0 = delta_max = D, alfa = 0.

Regla de compatibilidad entre i y j en el instante t:

    |r_i - r_j| <= min(Delta(t - a_i), Delta(t - a_j))
"""

import math


def ventana_fija(delta):
    return {"delta0": float(delta), "alfa": 0.0, "delta_max": float(delta)}


def adaptativa(delta0, alfa, delta_max):
    return {"delta0": float(delta0), "alfa": float(alfa), "delta_max": float(delta_max)}


def validar(politica):
    d0, a, dm = politica["delta0"], politica["alfa"], politica["delta_max"]
    if d0 < 0 or a < 0 or dm < 0:
        raise ValueError(f"Los parámetros de la política no pueden ser negativos: {politica}")
    if d0 > dm:
        raise ValueError(f"delta0 no puede superar a delta_max: {politica}")
    return d0, a, dm


def ventana(politica, espera):
    d0, a, dm = politica["delta0"], politica["alfa"], politica["delta_max"]
    return min(dm, d0 + a * espera)


def tiempo_hasta_tope(politica):
    """Segundos de espera tras los cuales la ventana ya no crece."""
    d0, a, dm = politica["delta0"], politica["alfa"], politica["delta_max"]
    if a == 0 or d0 >= dm:
        return 0.0
    return (dm - d0) / a if math.isfinite(dm) else math.inf
