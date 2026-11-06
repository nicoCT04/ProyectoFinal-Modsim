"""
Simulación de eventos discretos de la cola de emparejamiento de Trophy Road.

Interfaz única para optimización y experimentos:

    simular(politica, escenario, semilla) -> dict

Eventos
  - Llegada de una solicitud (tiempo a_i, trofeos r_i): entra a la cola.
  - Revisión de la cola cada dt segundos: se recorre la cola de la solicitud más antigua a la más
    reciente; para cada solicitud i aún en espera se busca el rival j con trofeos más cercanos que
    cumpla |r_i - r_j| <= min(Delta(w_i), Delta(w_j)). Empates: el más antiguo y luego el menor id.
  - Formación de pareja: i y j salen de la cola con espera w = t - a.

Escenario (dict)
  tasa_media        solicitudes por segundo, promedio del día            [1/s]
  duracion_s        horizonte de simulación                               [s]
  hora_inicio       hora de Guatemala en t = 0 (0-23)                      [h]
  dt                periodo de revisión de la cola (por defecto 1)         [s]
  calentamiento_s   las llegadas anteriores no entran a las métricas       [s]
  margen_cierre_s   las llegadas de los últimos segundos no entran         [s]

Optimización exacta: en cada revisión solo se examinan las solicitudes cuya situación pudo
cambiar (las recién llegadas, las que tienen una recién llegada a menos de delta_max trofeos y las
que todavía están ampliando su ventana). Las demás ya fallaron con la misma ventana y la misma
cola, así que volver a revisarlas no puede formar parejas. El resultado es idéntico al de revisar
toda la cola.
"""

import math
import time
from bisect import bisect_left, insort

import numpy as np

from .llegadas import cargar_parametros, generar_solicitudes
from .politicas import tiempo_hasta_tope, validar

ESCENARIO_POR_DEFECTO = {
    "dt": 1.0,
    "hora_inicio": 0,
    "calentamiento_s": 600.0,
    "margen_cierre_s": 300.0,
}
INTERVALO_SERIE_S = 60.0

_PARAMETROS = None


def _parametros_por_defecto():
    global _PARAMETROS
    if _PARAMETROS is None:
        _PARAMETROS = cargar_parametros()
    return _PARAMETROS


def _percentil(valores, p):
    return float(np.percentile(valores, p)) if len(valores) else math.nan


def simular(politica, escenario, semilla, parametros=None, detalle=False):
    t0_reloj = time.perf_counter()
    d0, alfa, dmax = validar(politica)
    esc = {**ESCENARIO_POR_DEFECTO, **escenario}
    dt = float(esc["dt"])
    duracion = float(esc["duracion_s"])
    parametros = parametros or _parametros_por_defecto()

    rng = np.random.default_rng(semilla)
    tiempos, trofeos = generar_solicitudes(esc, parametros, rng)
    llegada = tiempos.tolist()
    r = trofeos.tolist()
    n = len(llegada)

    t_tope = tiempo_hasta_tope(politica)

    def ventana(espera):
        return min(dmax, d0 + alfa * espera)

    emparejada_en = [math.nan] * n
    rival = [-1] * n
    en_cola = [False] * n
    por_trofeo = []        # (trofeos, llegada, id) ordenado: búsqueda del rival más cercano
    cola = []              # ids en orden de llegada (puede tener ids ya emparejados)
    activos = 0
    parejas = []           # (t, i, j)
    serie_t, serie_cola = [], []
    proxima_muestra = 0.0
    siguiente = 0

    n_revisiones = int(math.floor(duracion / dt + 1e-9))
    for k in range(1, n_revisiones + 1):
        t = k * dt

        # 1. Llegadas hasta t.
        nuevos = []
        while siguiente < n and llegada[siguiente] <= t:
            i = siguiente
            insort(por_trofeo, (r[i], llegada[i], i))
            cola.append(i)
            en_cola[i] = True
            nuevos.append(i)
            siguiente += 1
        activos += len(nuevos)

        # 2. Solicitudes a revisar.
        revisar = set(nuevos)
        for i in nuevos:
            lo = bisect_left(por_trofeo, (r[i] - dmax, -math.inf, -1))
            hi = bisect_left(por_trofeo, (r[i] + dmax, math.inf, n))
            for _, _, j in por_trofeo[lo:hi]:
                revisar.add(j)
        if t_tope > 0:
            # Las que siguen ampliando su ventana: llegaron después de t - dt - t_tope (sufijo de cola).
            desde = bisect_left(cola, t - dt - t_tope, key=lambda x: llegada[x])
            for i in cola[desde:]:
                if en_cola[i]:
                    revisar.add(i)

        # 3. Revisión de la más antigua a la más reciente.
        for i in sorted(revisar):
            if not en_cola[i]:
                continue
            ri, ai = r[i], llegada[i]
            di = ventana(t - ai)
            p = bisect_left(por_trofeo, (ri, ai, i))
            izq, der = p - 1, p + 1
            mejor = None
            while True:
                dl = ri - por_trofeo[izq][0] if izq >= 0 else math.inf
                dr = por_trofeo[der][0] - ri if der < len(por_trofeo) else math.inf
                d = min(dl, dr)
                if d > di or (mejor is not None and d > mejor[0]):
                    break
                if dl <= dr:
                    _, aj, j = por_trofeo[izq]
                    izq -= 1
                else:
                    _, aj, j = por_trofeo[der]
                    der += 1
                if d <= ventana(t - aj):
                    cand = (d, aj, j)
                    if mejor is None or cand < mejor:
                        mejor = cand
            if mejor is None:
                continue
            _, aj, j = mejor
            for x in (i, j):
                del por_trofeo[bisect_left(por_trofeo, (r[x], llegada[x], x))]
                en_cola[x] = False
                emparejada_en[x] = t
            rival[i], rival[j] = j, i
            parejas.append((t, i, j))
            activos -= 2

        # 4. Mantenimiento y serie de la cola.
        if len(cola) > 4 * activos + 64:
            cola = [x for x in cola if en_cola[x]]
        while proxima_muestra <= t:
            serie_t.append(proxima_muestra)
            serie_cola.append(activos)
            proxima_muestra += INTERVALO_SERIE_S

    return _resultados(esc, llegada, r, emparejada_en, en_cola, parejas, siguiente,
                       serie_t, serie_cola, politica, semilla, detalle, t0_reloj)


def _resultados(esc, llegada, r, emparejada_en, en_cola, parejas, n_llegadas,
                serie_t, serie_cola, politica, semilla, detalle, t0_reloj):
    duracion = float(esc["duracion_s"])
    desde = float(esc["calentamiento_s"])
    hasta = duracion - float(esc["margen_cierre_s"])

    medidas = [i for i in range(n_llegadas) if desde <= llegada[i] <= hasta]
    emparejadas = [i for i in medidas if not math.isnan(emparejada_en[i])]
    esperas = [emparejada_en[i] - llegada[i] for i in emparejadas]
    difs = [abs(r[i] - r[j]) for t, i, j in parejas if t >= desde]
    pendientes = [i for i in range(n_llegadas) if en_cola[i]]
    antig = [duracion - llegada[i] for i in pendientes]

    res = {
        "espera_media": float(np.mean(esperas)) if esperas else math.nan,
        "espera_p95": _percentil(esperas, 95),
        "dif_media": float(np.mean(difs)) if difs else math.nan,
        "dif_mediana": _percentil(difs, 50),
        "dif_p90": _percentil(difs, 90),
        "dif_p99": _percentil(difs, 99),
        "dif_max": float(max(difs)) if difs else math.nan,
        "dif_prop_cero": (sum(1 for d in difs if d == 0) / len(difs)) if difs else math.nan,
        "cobertura": len(emparejadas) / len(medidas) if medidas else math.nan,
        "pendientes": len(pendientes),
        "antiguedad_media_pendientes": float(np.mean(antig)) if antig else 0.0,
        "antiguedad_max_pendientes": float(max(antig)) if antig else 0.0,
        "cola_media": float(np.mean(serie_cola)) if serie_cola else 0.0,
        "cola_max": int(max(serie_cola)) if serie_cola else 0,
        "n_llegadas": n_llegadas,
        "n_parejas": len(parejas),
        "n_medidas": len(medidas),
        "politica": dict(politica),
        "semilla": semilla,
        "segundos_ejecucion": round(time.perf_counter() - t0_reloj, 3),
    }
    if detalle:
        res["detalle"] = {
            "parejas": [(t, i, j, llegada[i], llegada[j], r[i], r[j]) for t, i, j in parejas],
            "diferencias": difs,
            "esperas": esperas,
            "serie_cola": {"t": serie_t, "en_cola": serie_cola},
        }
    return res
