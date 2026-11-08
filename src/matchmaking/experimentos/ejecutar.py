"""
Experimentos finales (R4, Partes 5 y 7 del enunciado).

    python -m src.matchmaking.experimentos.ejecutar
    python -m src.matchmaking.experimentos.ejecutar --rapido   # 3 semillas, para probar

Evalúa, en cada escenario de `configs/escenarios.yaml`, las políticas de referencia (la base
calibrada y las tres ventanas fijas) y las cinco candidatas del frente de Pareto y la búsqueda
aleatoria (decisiones.md D12), con 30 repeticiones de semillas nuevas por condición.

Semillas 5000-5029: distintas de las de R2 (calibración: 101-102, 201-205) y R3 (optimización:
1000-1002), para no validar las candidatas con las mismas semillas con las que NSGA-II las
encontró. Las mismas 30 semillas se usan para todas las políticas de un escenario (números
aleatorios comunes), así que las corridas con el mismo índice de semilla son comparables en pareja.

Guarda en results/:
  experimentos_corridas.csv     una fila por (escenario, política, semilla)
  experimentos_resumen.csv      una fila por (escenario, política): n, media, desv., IC95 %
  experimentos_comparacion.csv  cada candidata contra las referencias (D10), por escenario
"""

import argparse
import csv
import time
from itertools import product
from multiprocessing import Pool
from pathlib import Path

from ..analisis.metricas import comparacion_pareada, resumir
from ..optimizacion.problema import procesos
from ..simulacion.escenarios import RAIZ, cargar
from ..simulacion.motor import simular

RESULTADOS = RAIZ / "results"
SEMILLAS = tuple(range(5000, 5030))
ESCENARIOS = ("base", "baja_demanda", "alta_demanda", "revision_5s")
REFERENCIAS = ("fija_20", "base")  # fija_20: única ventana fija que cumple D_max (D10, D13)
CANDIDATAS = ("nsga_codo", "nsga_menor_espera", "nsga_intermedia", "nsga_menor_dif", "aleatoria_mejor")
OTRAS_FIJAS = ("fija_40", "fija_60")  # se corren también, para la gráfica del frente

METRICAS_CORRIDA = ("espera_media", "espera_p95", "dif_media", "dif_p90", "dif_max",
                    "cobertura", "pendientes", "cola_media")
COLUMNAS_CORRIDA = ("escenario", "politica", "semilla", *METRICAS_CORRIDA)
METRICAS_RESUMEN = ("espera_media", "espera_p95", "dif_media", "cobertura")
COLUMNAS_RESUMEN = ("escenario", "politica", "n",
                    *(f"{m}_{s}" for m in METRICAS_RESUMEN for s in ("media", "desv", "ic95_inf", "ic95_sup")))
COLUMNAS_COMPARACION = ("escenario", "politica", "referencia", "n",
                        "espera_media_candidata", "espera_media_referencia", "reduccion_%",
                        "ic95_inf", "ic95_sup", "significativa",
                        "dif_media_candidata", "cobertura_candidata",
                        "cumple_d_max", "cumple_cobertura", "mejora_declarada")


def _guardar_csv(filas, ruta, columnas):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columnas, extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)


def _correr_una(nombre_escenario, nombre_politica, politica, escenario, semilla):
    r = simular(politica, escenario, semilla)
    return {"escenario": nombre_escenario, "politica": nombre_politica, "semilla": semilla,
            **{k: r[k] for k in METRICAS_CORRIDA}}


def _politicas_a_correr(todas):
    nombres = ["base", "fija_20", *OTRAS_FIJAS, *CANDIDATAS]
    faltan = [n for n in nombres if n not in todas]
    if faltan:
        raise ValueError(f"Políticas no encontradas en configs/escenarios.yaml: {faltan}")
    return nombres


def ejecutar(semillas=SEMILLAS, escenarios_a_correr=ESCENARIOS, n_procesos=None):
    estudio = cargar()
    todas_politicas = estudio["politicas"]
    umbrales = estudio["umbrales"]
    politicas = _politicas_a_correr(todas_politicas)

    tareas = [(esc, pol, todas_politicas[pol], estudio["escenarios"][esc], s)
              for esc, pol, s in product(escenarios_a_correr, politicas, semillas)]
    print(f"{len(tareas)} corridas: {len(escenarios_a_correr)} escenarios x {len(politicas)} "
          f"políticas x {len(semillas)} semillas", flush=True)

    inicio = time.perf_counter()
    with Pool(n_procesos or procesos({"procesos": 0})) as pool:
        corridas = pool.starmap(_correr_una, tareas)
    print(f"Listo en {time.perf_counter() - inicio:.0f} s", flush=True)

    resumen = _resumir_corridas(corridas, escenarios_a_correr, politicas)
    comparacion = _comparar(corridas, escenarios_a_correr, politicas, umbrales)
    return corridas, resumen, comparacion


def _resumir_corridas(corridas, escenarios_a_correr, politicas):
    por_clave = _agrupar(corridas)
    filas = []
    for esc in escenarios_a_correr:
        for pol in politicas:
            grupo = por_clave[(esc, pol)]
            fila = {"escenario": esc, "politica": pol, "n": len(grupo)}
            for m in METRICAS_RESUMEN:
                r = resumir([g[m] for g in grupo])
                fila.update({f"{m}_media": r["media"], f"{m}_desv": r["desv"],
                            f"{m}_ic95_inf": r["ic95_inf"], f"{m}_ic95_sup": r["ic95_sup"]})
            filas.append(fila)
    return filas


def _agrupar(corridas):
    por_clave = {}
    for c in corridas:
        por_clave.setdefault((c["escenario"], c["politica"]), []).append(c)
    for grupo in por_clave.values():
        grupo.sort(key=lambda c: c["semilla"])
    return por_clave


def _comparar(corridas, escenarios_a_correr, politicas, umbrales):
    por_clave = _agrupar(corridas)
    filas = []
    for esc in escenarios_a_correr:
        for cand in CANDIDATAS:
            if cand not in politicas:
                continue
            g_cand = por_clave[(esc, cand)]
            dif_media = resumir([g["dif_media"] for g in g_cand])["media"]
            cobertura = resumir([g["cobertura"] for g in g_cand])["media"]
            cumple_d_max = dif_media <= umbrales["d_max"]
            cumple_cobertura = cobertura >= umbrales["cobertura_min"]
            for ref in REFERENCIAS:
                g_ref = por_clave[(esc, ref)]
                comp = comparacion_pareada([g["espera_media"] for g in g_cand],
                                           [g["espera_media"] for g in g_ref])
                reduccion_relevante = comp["significativa"] and comp["reduccion_%"] >= 100 * umbrales["reduccion_espera_min"]
                filas.append({
                    "escenario": esc, "politica": cand, "referencia": ref, "n": comp["n"],
                    "espera_media_candidata": resumir([g["espera_media"] for g in g_cand])["media"],
                    "espera_media_referencia": resumir([g["espera_media"] for g in g_ref])["media"],
                    "reduccion_%": comp["reduccion_%"], "ic95_inf": comp["ic95_inf"],
                    "ic95_sup": comp["ic95_sup"], "significativa": comp["significativa"],
                    "dif_media_candidata": dif_media, "cobertura_candidata": cobertura,
                    "cumple_d_max": cumple_d_max, "cumple_cobertura": cumple_cobertura,
                    "mejora_declarada": cumple_d_max and cumple_cobertura and reduccion_relevante,
                })
    return filas


def main():
    ap = argparse.ArgumentParser(description="Corre los experimentos finales y guarda los resultados")
    ap.add_argument("--rapido", action="store_true", help="Solo 3 semillas y el escenario base, para probar")
    a = ap.parse_args()

    semillas = SEMILLAS[:3] if a.rapido else SEMILLAS
    escenarios_a_correr = ("base",) if a.rapido else ESCENARIOS
    corridas, resumen, comparacion = ejecutar(semillas, escenarios_a_correr)

    _guardar_csv(corridas, RESULTADOS / "experimentos_corridas.csv", COLUMNAS_CORRIDA)
    _guardar_csv(resumen, RESULTADOS / "experimentos_resumen.csv", COLUMNAS_RESUMEN)
    _guardar_csv(comparacion, RESULTADOS / "experimentos_comparacion.csv", COLUMNAS_COMPARACION)

    mejores = [f for f in comparacion if f["referencia"] == "fija_20" and f["mejora_declarada"]]
    print(f"\n{len(comparacion)} comparaciones guardadas en experimentos_comparacion.csv")
    print(f"{len(mejores)} (escenario, política) declaradas mejores que fija_20 por los umbrales de D10:")
    for f in mejores:
        print(f"  {f['escenario']:<14} {f['politica']:<20} reducción {f['reduccion_%']:5.1f} %  "
              f"dif_media {f['dif_media_candidata']:5.2f}  cobertura {f['cobertura_candidata']:.3f}")


if __name__ == "__main__":
    main()
