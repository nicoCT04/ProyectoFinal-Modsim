"""
Problema de optimización de la ventana de trofeos para pymoo.

Variables   x = (delta0, alfa, e), con delta_max = delta0 + e (así delta0 <= delta_max siempre)
Objetivos   f1 = espera media [s], f2 = diferencia media [trofeos], ambos a minimizar
Restricciones (g <= 0)
            g1 = dif_media - d_max
            g2 = cobertura_min - cobertura

Cada evaluación promedia las semillas de configs/optimizacion.yaml, iguales para todas las
soluciones (números aleatorios comunes). Si no se forma ninguna pareja, la solución es infactible.
"""

import math
import os
from pathlib import Path

import numpy as np
import yaml
from pymoo.core.problem import ElementwiseProblem
from pymoo.indicators.hv import HV
from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting

from ..simulacion.escenarios import RAIZ, cargar
from ..simulacion.motor import simular

CONFIG = RAIZ / "configs" / "optimizacion.yaml"
RESULTADOS = RAIZ / "results"
INFACTIBLE = 1e6
METRICAS = ("espera_media", "espera_p95", "dif_media", "cobertura")
COLUMNAS = ("delta0", "alfa", "delta_max", *METRICAS, "factible")


def cargar_config(ruta=CONFIG):
    return yaml.safe_load(Path(ruta).read_text(encoding="utf-8"))


def procesos(config):
    return config.get("procesos") or max(1, (os.cpu_count() or 2) - 1)


def decodificar(x):
    delta0, alfa, e = (float(v) for v in x)
    return {"delta0": delta0, "alfa": alfa, "delta_max": delta0 + e}


def evaluar(politica, escenario, semillas):
    corridas = [simular(politica, escenario, s) for s in semillas]
    return {k: float(np.mean([c[k] for c in corridas])) for k in METRICAS}


def objetivos_y_restricciones(metricas, umbrales):
    if any(math.isnan(metricas[k]) for k in METRICAS):
        return [INFACTIBLE, INFACTIBLE], [INFACTIBLE, INFACTIBLE]
    f = [metricas["espera_media"], metricas["dif_media"]]
    g = [metricas["dif_media"] - umbrales["d_max"], umbrales["cobertura_min"] - metricas["cobertura"]]
    return f, g


class ProblemaVentana(ElementwiseProblem):
    def __init__(self, config=None, **kwargs):
        config = config or cargar_config()
        estudio = cargar()
        self.escenario = estudio["escenarios"][config["escenario"]]
        self.umbrales = estudio["umbrales"]
        self.semillas = tuple(config["semillas_evaluacion"])
        xl, xu = zip(*(config["limites"][k] for k in ("delta0", "alfa", "e")))
        super().__init__(n_var=3, n_obj=2, n_ieq_constr=2, xl=np.array(xl, float),
                         xu=np.array(xu, float), **kwargs)

    def _evaluate(self, x, out, *args, **kwargs):
        metricas = evaluar(decodificar(x), self.escenario, self.semillas)
        out["F"], out["G"] = objetivos_y_restricciones(metricas, self.umbrales)
        for k in METRICAS:
            out[k] = metricas[k]


def tabla(X, metricas, G):
    """Una fila por solución con las columnas de COLUMNAS."""
    filas = []
    for x, m, g in zip(X, metricas, G):
        p = decodificar(x)
        filas.append({**p, **m, "factible": bool(np.all(np.asarray(g) <= 0))})
    return filas


def frente_factible(filas):
    """Soluciones factibles no dominadas en (espera_media, dif_media), ordenadas por espera."""
    factibles = [f for f in filas if f["factible"]]
    if not factibles:
        return []
    F = np.array([[f["espera_media"], f["dif_media"]] for f in factibles])
    idx = NonDominatedSorting().do(F, only_non_dominated_front=True)
    return sorted((factibles[i] for i in idx), key=lambda f: f["espera_media"])


def hipervolumen(frente, referencia):
    F = np.array([[f["espera_media"], f["dif_media"]] for f in frente]).reshape(-1, 2)
    F = F[np.all(F < np.asarray(referencia), axis=1)]
    return float(HV(ref_point=np.asarray(referencia, float))(F)) if len(F) else 0.0


def guardar_csv(filas, ruta, columnas=COLUMNAS):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    lineas = [",".join(columnas)]
    for f in filas:
        lineas.append(",".join(_formato(f[c]) for c in columnas))
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def _formato(v):
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    return f"{float(v):.6g}"
