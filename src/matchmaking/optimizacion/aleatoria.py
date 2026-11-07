"""
Búsqueda aleatoria de control: mismo presupuesto, límites y semillas de evaluación que NSGA-II.

    python -m src.matchmaking.optimizacion.aleatoria

Guarda en results/:
  aleatoria.csv             todas las soluciones evaluadas
  aleatoria_frente.csv      frente factible no dominado
  aleatoria_historial.csv   hipervolumen cada tantas evaluaciones como la población de NSGA-II
"""

import json
import time
from multiprocessing import Pool

import numpy as np
from pymoo.parallelization.starmap import StarmapParallelization

from .problema import (METRICAS, RESULTADOS, ProblemaVentana, cargar_config, frente_factible,
                       guardar_csv, hipervolumen, procesos, tabla)


def correr(config=None):
    config = config or cargar_config()
    n = config["aleatoria"]["evaluaciones"]
    lote = config["nsga2"]["poblacion"]
    referencia = config["hipervolumen"]["referencia"]
    inicio = time.perf_counter()
    evaluadas, historial = [], []
    with Pool(procesos(config)) as pool:
        problema = ProblemaVentana(config, elementwise_runner=StarmapParallelization(pool.starmap))
        rng = np.random.default_rng(config["aleatoria"]["semilla"])
        X = problema.xl + rng.random((n, problema.n_var)) * (problema.xu - problema.xl)
        for desde in range(0, n, lote):
            Xl = X[desde:desde + lote]
            out = problema.evaluate(Xl, return_values_of=["G", *METRICAS], return_as_dictionary=True)
            metricas = [{k: float(out[k][i]) for k in METRICAS} for i in range(len(Xl))]
            evaluadas.extend(tabla(Xl, metricas, out["G"]))
            frente = frente_factible(evaluadas)
            historial.append({"evaluaciones": len(evaluadas), "soluciones_frente": len(frente),
                              "hipervolumen": hipervolumen(frente, referencia),
                              "segundos": round(time.perf_counter() - inicio, 1)})
            print(f"evaluaciones {len(evaluadas):4d}  frente {len(frente):2d}  "
                  f"HV {historial[-1]['hipervolumen']:.1f}", flush=True)
    frente = frente_factible(evaluadas)
    guardar_csv(evaluadas, RESULTADOS / "aleatoria.csv")
    guardar_csv(frente, RESULTADOS / "aleatoria_frente.csv")
    guardar_csv(historial, RESULTADOS / "aleatoria_historial.csv", tuple(historial[0]))
    resumen = {"evaluaciones": len(evaluadas), "soluciones_frente": len(frente),
               "hipervolumen": historial[-1]["hipervolumen"], "segundos": historial[-1]["segundos"],
               "procesos": procesos(config)}
    print(json.dumps(resumen, indent=2))
    return resumen


if __name__ == "__main__":
    correr()
