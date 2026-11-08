"""
Tabla de la Parte 6: real, base calibrada y política mejorada, con cambio absoluto y porcentual
(PLANIFICACION.md, R1 y R4).

Reutiliza results/calibracion.json (real contra base, generado por simulacion/calibrar.py contra
el día de validación reservado, 4 nov) y results/experimentos_comparacion.csv (candidata declarada
mejor que la referencia por los umbrales de D10, generado por experimentos/ejecutar.py), para no
repetir la calibración ni el experimento final.

    python -m src.matchmaking.analisis.validacion
    python -m src.matchmaking.analisis.validacion --politica nsga_intermedia

Guarda results/tabla_parte6.csv.
"""

import argparse
import csv
import json

import numpy as np

from ..simulacion.calibrar import CUANTILES, RAIZ, SEMILLAS_VALIDACION, diferencias_reales, resumen
from ..simulacion.escenarios import cargar
from ..simulacion.motor import simular

RESULTADOS = RAIZ / "results"
COLUMNAS = ("estadistico", "real", "base", "base_error_%", "mejorada", "mejorada_error_%",
           "cambio_base_a_mejorada_%")


def _mejor_candidata(referencia="fija_20"):
    """La candidata declarada mejor que la referencia (D10) en más escenarios de
    `experimentos_comparacion.csv`; a igualdad, la de mayor reducción media de espera entre esos
    escenarios. Una candidata que solo gana en un escenario (por ejemplo, por la demanda) no es
    una mejora robusta (docs/tecnica_nsga2.md, Parte 7); None si ninguna lo logra nunca."""
    ruta = RESULTADOS / "experimentos_comparacion.csv"
    with open(ruta, newline="", encoding="utf-8") as f:
        filas = [r for r in csv.DictReader(f) if r["referencia"] == referencia]
    reducciones_por_politica = {}
    for r in filas:
        if r["mejora_declarada"] == "True":
            reducciones_por_politica.setdefault(r["politica"], []).append(float(r["reduccion_%"]))
    if not reducciones_por_politica:
        return None
    return max(reducciones_por_politica,
              key=lambda p: (len(reducciones_por_politica[p]), np.mean(reducciones_por_politica[p])))


def tabla_parte6(nombre_politica=None):
    estudio = cargar()
    calibracion = json.loads((RESULTADOS / "calibracion.json").read_text(encoding="utf-8"))
    real_resumen = resumen(diferencias_reales("validacion"))

    nombre_politica = nombre_politica or _mejor_candidata()
    if nombre_politica is None:
        raise RuntimeError("Ninguna candidata tiene mejora_declarada=True en el escenario base "
                           "(results/experimentos_comparacion.csv); corre antes experimentos/ejecutar.py.")
    politica = estudio["politicas"][nombre_politica]
    escenario = calibracion["escenario"]

    difs = []
    for s in SEMILLAS_VALIDACION:
        r = simular(politica, escenario, s, detalle=True)
        difs += r["detalle"]["diferencias"]
    mejorada_resumen = resumen(np.array(difs))

    base_estad = calibracion["validacion"]["estadisticos"]
    filas = []
    for k in ("media", "prop_cero", "max", *[f"p{q}" for q in CUANTILES]):
        r, b, m = real_resumen[k], base_estad[k]["simulado"], mejorada_resumen[k]
        filas.append({
            "estadistico": k, "real": round(r, 3), "base": round(b, 3),
            "base_error_%": round(100 * (b - r) / r, 1) if r else None,
            "mejorada": round(m, 3), "mejorada_error_%": round(100 * (m - r) / r, 1) if r else None,
            "cambio_base_a_mejorada_%": round(100 * (m - b) / b, 1) if b else None,
        })
    return nombre_politica, filas


def main():
    ap = argparse.ArgumentParser(description="Tabla de la Parte 6: real, base y política mejorada")
    ap.add_argument("--politica", default=None,
                    help="Nombre en configs/escenarios.yaml (por defecto, la mejor candidata de D10)")
    a = ap.parse_args()
    nombre, filas = tabla_parte6(a.politica)

    ruta = RESULTADOS / "tabla_parte6.csv"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS)
        w.writeheader()
        w.writerows(filas)

    print(f"Política mejorada: {nombre}")
    for fila in filas:
        print(f"  {fila['estadistico']:<8} real={fila['real']:7.2f}  base={fila['base']:7.2f} "
              f"({fila['base_error_%']:+.1f} %)  mejorada={fila['mejorada']:7.2f} "
              f"({fila['mejorada_error_%']:+.1f} %)  cambio base->mejorada {fila['cambio_base_a_mejorada_%']:+.1f} %")
    print(f"Escrito en {ruta}")


if __name__ == "__main__":
    main()
