"""
Verificación por código de las políticas del frente (Parte 4 del enunciado).

    python -m src.matchmaking.optimizacion.verificar [results/pareto.csv]

Vuelve a simular cada política con las semillas de evaluación y comprueba que cumple
dif_media <= d_max y cobertura >= cobertura_min. Guarda results/verificacion_pareto.csv.
"""

import csv
import sys
from multiprocessing import Pool
from pathlib import Path

from ..simulacion.escenarios import cargar
from .problema import RESULTADOS, cargar_config, evaluar, guardar_csv, procesos

COLUMNAS = ("delta0", "alfa", "delta_max", "espera_media", "dif_media", "cobertura",
            "cumple_d_max", "cumple_cobertura")


def leer_politicas(ruta):
    with open(ruta, encoding="utf-8") as f:
        return [{k: float(fila[k]) for k in ("delta0", "alfa", "delta_max")} for fila in csv.DictReader(f)]


def verificar(politicas, config=None, starmap=None):
    config = config or cargar_config()
    estudio = cargar()
    escenario = estudio["escenarios"][config["escenario"]]
    umbrales = estudio["umbrales"]
    tareas = [(p, escenario, config["semillas_evaluacion"]) for p in politicas]
    metricas = (starmap or (lambda f, args: [f(*a) for a in args]))(evaluar, tareas)
    return [{**p, **m, "cumple_d_max": m["dif_media"] <= umbrales["d_max"],
             "cumple_cobertura": m["cobertura"] >= umbrales["cobertura_min"]}
            for p, m in zip(politicas, metricas)]


if __name__ == "__main__":
    ruta = Path(sys.argv[1]) if len(sys.argv) > 1 else RESULTADOS / "pareto.csv"
    config = cargar_config()
    with Pool(procesos(config)) as pool:
        filas = verificar(leer_politicas(ruta), config, pool.starmap)
    guardar_csv(filas, RESULTADOS / f"verificacion_{ruta.stem}.csv", COLUMNAS)
    fallan = [f for f in filas if not (f["cumple_d_max"] and f["cumple_cobertura"])]
    print(f"{len(filas)} políticas verificadas, {len(fallan)} no cumplen las restricciones")
    sys.exit(1 if fallan else 0)
