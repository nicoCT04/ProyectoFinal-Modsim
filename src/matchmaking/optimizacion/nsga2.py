"""
NSGA-II sobre el problema de la ventana de trofeos.

    python -m src.matchmaking.optimizacion.nsga2

Guarda en results/:
  nsga2_evaluaciones.csv   todas las soluciones evaluadas, con su generación
  pareto.csv               frente factible no dominado de todas las evaluaciones
  nsga2_historial.csv      por generación: evaluaciones acumuladas e hipervolumen del frente
"""

import json
import time
from multiprocessing import Pool

from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.callback import Callback
from pymoo.optimize import minimize
from pymoo.parallelization.starmap import StarmapParallelization

from .problema import (METRICAS, RESULTADOS, COLUMNAS, ProblemaVentana, cargar_config,
                       frente_factible, guardar_csv, hipervolumen, procesos, tabla)


def filas_de(individuos, generacion):
    metricas = [{k: float(ind.get(k)) for k in METRICAS} for ind in individuos]
    filas = tabla(individuos.get("X"), metricas, individuos.get("G"))
    return [{**f, "generacion": generacion} for f in filas]


class Registro(Callback):
    def __init__(self, referencia):
        super().__init__()
        self.referencia = referencia
        self.evaluadas = []
        self.historial = []
        self.inicio = time.perf_counter()

    def notify(self, algorithm):
        gen = algorithm.n_iter
        nuevas = algorithm.pop if algorithm.off is None else algorithm.off
        nuevas = nuevas[nuevas.get("n_gen") == gen]
        self.evaluadas.extend(filas_de(nuevas, gen))
        frente = frente_factible(self.evaluadas)
        self.historial.append({
            "generacion": gen,
            "evaluaciones": len(self.evaluadas),
            "soluciones_frente": len(frente),
            "hipervolumen": hipervolumen(frente, self.referencia),
            "segundos": round(time.perf_counter() - self.inicio, 1),
        })
        print(f"gen {gen:2d}  evaluaciones {len(self.evaluadas):4d}  "
              f"frente {len(frente):2d}  HV {self.historial[-1]['hipervolumen']:.1f}", flush=True)


def correr(config=None):
    config = config or cargar_config()
    ajustes = config["nsga2"]
    referencia = config["hipervolumen"]["referencia"]
    registro = Registro(referencia)
    with Pool(procesos(config)) as pool:
        problema = ProblemaVentana(config, elementwise_runner=StarmapParallelization(pool.starmap))
        minimize(problema, NSGA2(pop_size=ajustes["poblacion"]), ("n_gen", ajustes["generaciones"]),
                 seed=ajustes["semilla"], callback=registro, verbose=False)
    frente = frente_factible(registro.evaluadas)
    guardar_csv(registro.evaluadas, RESULTADOS / "nsga2_evaluaciones.csv", ("generacion", *COLUMNAS))
    guardar_csv(frente, RESULTADOS / "pareto.csv")
    guardar_csv(registro.historial, RESULTADOS / "nsga2_historial.csv", tuple(registro.historial[0]))
    resumen = {"evaluaciones": len(registro.evaluadas), "soluciones_frente": len(frente),
               "hipervolumen": registro.historial[-1]["hipervolumen"],
               "segundos": registro.historial[-1]["segundos"], "procesos": procesos(config)}
    print(json.dumps(resumen, indent=2))
    return resumen


if __name__ == "__main__":
    correr()
