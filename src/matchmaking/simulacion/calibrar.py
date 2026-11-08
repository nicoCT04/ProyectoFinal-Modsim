"""
Calibración del escenario base y validación contra los días reservados.

Escenario base = réplica del emparejamiento real: ventana que crece con la espera,
Delta(w) = min(delta_max, delta0 + alfa * w), con
  delta0    = 0    el juego busca primero el mismo número de trofeos (25 % de batallas con diferencia 0)
  alfa, delta_max  se calibran en una rejilla. La diferencia máxima observada (60-64) es un caso
                   raro (P99 = 42), así que delta_max no se fija en ese valor.

Identificabilidad: si la tasa de llegadas y alfa se multiplican por el mismo k, el proceso es el
mismo en una escala de tiempo k veces más rápida: las diferencias no cambian y las esperas se
dividen entre k. Las diferencias observadas solo fijan la razón alfa / tasa. Por eso la tasa se
fija (tasa_media, unidad de tiempo del estudio) y se calibra alfa. Una medición real de la espera
permitiría reescalar ambos (decisiones.md, D11).

Pasos:
  1. Ajuste (1-3 nov): rejilla de (alfa, delta_max); se elige la que minimiza la pérdida contra la
     distribución de diferencias de ajuste. La media pesa el doble porque es la métrica del estudio.
  2. Validación (4 nov): con semillas nuevas se compara la base calibrada con la distribución del
     día reservado (error por estadístico, MAE del histograma, Kolmogórov-Smirnov) y el perfil por hora.

Uso (desde la raíz del repositorio):
  python -m src.matchmaking.simulacion.calibrar
  python -m src.matchmaking.simulacion.calibrar --rapido      # 6 h simuladas, para probar
"""

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .llegadas import cargar_parametros
from .motor import simular
from .politicas import adaptativa

RAIZ = Path(__file__).resolve().parents[3]
TASA_MEDIA = 5.0
DELTA0 = 0.0
ALFAS = [1.25, 1.5, 1.75, 2.0, 2.5, 3.0]
DELTAS_MAX = [44.0, 48.0, 52.0, 56.0, 64.0]
SEMILLAS_AJUSTE = [101, 102]
SEMILLAS_VALIDACION = [201, 202, 203, 204, 205]
CUANTILES = (50, 75, 90, 95, 99)


def diferencias_reales(conjunto):
    ruta = RAIZ / "data" / "processed" / "batallas_estudio.csv"
    with open(ruta, newline="", encoding="utf-8") as f:
        return np.array([int(r["dif_trofeos_abs"]) for r in csv.DictReader(f) if r["conjunto"] == conjunto])

def perfil_horario_real(conjunto):
    """Perfil observado del conjunto indicado, por hora de Guatemala."""
    ruta = RAIZ / "data" / "processed" / "batallas_estudio.csv"
    conteo = np.zeros(24, dtype=int)

    with open(ruta, newline="", encoding="utf-8") as archivo:
        for fila in csv.DictReader(archivo):
            if fila["conjunto"] == conjunto:
                hora = int(fila["hora_gt"])
                conteo[hora] += 1

    total = conteo.sum()
    if total == 0:
        raise ValueError(f"No hay batallas para el conjunto {conjunto}")

    return conteo / total

def resumen(d):
    d = np.asarray(d)
    out = {"media": float(d.mean()), "prop_cero": float((d == 0).mean()), "max": float(d.max())}
    out.update({f"p{q}": float(np.percentile(d, q)) for q in CUANTILES})
    return out


def perdida(sim, real):
    """Error promedio en trofeos: media (peso 2), cuantiles P50-P99 y proporción de ceros (x100)."""
    s, r = resumen(sim), resumen(real)
    errores = [2 * abs(s["media"] - r["media"])] + [abs(s[f"p{q}"] - r[f"p{q}"]) for q in CUANTILES]
    errores.append(100 * abs(s["prop_cero"] - r["prop_cero"]))
    return float(np.mean(errores))


def ks(a, b):
    a, b = np.sort(a), np.sort(b)
    x = np.union1d(a, b)
    return float(np.max(np.abs(np.searchsorted(a, x, "right") / len(a) - np.searchsorted(b, x, "right") / len(b))))


def histograma(d, ancho=5, tope=65):
    h, _ = np.histogram(d, bins=np.arange(0, tope + ancho, ancho))
    return h / h.sum()


def correr(alfa, delta_max, escenario, semillas, parametros):
    difs, horas, esperas = [], [], []
    for s in semillas:
        r = simular(adaptativa(DELTA0, alfa, delta_max), escenario, s, parametros, detalle=True)
        difs += r["detalle"]["diferencias"]
        esperas.append(r["espera_media"])
        h0 = escenario.get("hora_inicio", 0)
        horas += [int((h0 * 3600 + t) // 3600) % 24 for t, *_ in r["detalle"]["parejas"]]
    return np.array(difs), np.array(horas), esperas


def main():
    ap = argparse.ArgumentParser(description="Calibra la base y la valida contra el 4 de noviembre")
    ap.add_argument("--rapido", action="store_true", help="Simula 6 h en lugar de 24 h")
    ap.add_argument("--salida", default=str(RAIZ / "results" / "calibracion.json"))
    a = ap.parse_args()

    parametros = cargar_parametros()
    escenario = {"tasa_media": TASA_MEDIA, "duracion_s": 6 * 3600 if a.rapido else 86400,
                 "hora_inicio": 10 if a.rapido else 0}
    ajuste, validacion = diferencias_reales("ajuste"), diferencias_reales("validacion")

    print(f"Ajuste contra 1-3 nov ({len(ajuste):,} batallas). Tasa fija {TASA_MEDIA}/s.")
    rejilla = []
    for delta_max in DELTAS_MAX:
        for alfa in ALFAS:
            d, _, esperas = correr(alfa, delta_max, escenario, SEMILLAS_AJUSTE, parametros)
            fila = {"alfa": alfa, "delta_max": delta_max, "perdida": round(perdida(d, ajuste), 3),
                    "espera_media": round(float(np.mean(esperas)), 3),
                    **{k: round(v, 3) for k, v in resumen(d).items()}}
            rejilla.append(fila)
            print(f"  dmax={delta_max:4.0f}  alfa={alfa:4.2f}  pérdida={fila['perdida']:6.2f}  "
                  f"media={fila['media']:5.2f}  p90={fila['p90']:4.0f}  p99={fila['p99']:4.0f}  "
                  f"ceros={fila['prop_cero']:.3f}  espera={fila['espera_media']:5.1f} s", flush=True)
    mejor = min(rejilla, key=lambda f: f["perdida"])
    alfa, delta_max = mejor["alfa"], mejor["delta_max"]
    print(f"Elegido alfa = {alfa} trofeos/s, delta_max = {delta_max} trofeos")

    d, horas, esperas = correr(alfa, delta_max, escenario, SEMILLAS_VALIDACION, parametros)
    sim, real = resumen(d), resumen(validacion)
    comparacion = {k: {"real": round(real[k], 3), "simulado": round(sim[k], 3),
                       "error_abs": round(sim[k] - real[k], 3),
                       "error_rel_%": round(100 * (sim[k] - real[k]) / real[k], 1) if real[k] else None}
                   for k in real}
    perfil_sim = np.bincount(horas, minlength=24) / len(horas)
    # Referencia reservada: no se utiliza para generar las solicitudes.
    perfil_real = perfil_horario_real("validacion")
    validacion_res = {
        "semillas": SEMILLAS_VALIDACION,
        "batallas_simuladas": int(len(d)),
        "batallas_reales": int(len(validacion)),
        "estadisticos": comparacion,
        "mae_histograma_5_trofeos": round(float(np.abs(histograma(d) - histograma(validacion)).mean()), 5),
        "ks": round(ks(d, validacion), 4),
        "mae_perfil_horario": round(float(np.abs(perfil_sim - perfil_real).mean()), 5),
        "espera_media_s": {"media": round(float(np.mean(esperas)), 3), "desv": round(float(np.std(esperas, ddof=1)), 3)},
    }
    print(f"\nValidación contra 4 nov ({len(validacion):,} batallas reales, {len(d):,} simuladas):")
    for k, v in comparacion.items():
        print(f"  {k:<10} real={v['real']:7.2f}  sim={v['simulado']:7.2f}  error={v['error_abs']:+7.2f}")
    print(f"  MAE histograma={validacion_res['mae_histograma_5_trofeos']}  KS={validacion_res['ks']}  "
          f"MAE perfil horario={validacion_res['mae_perfil_horario']}")

    salida = {
        "generado_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "escenario": escenario,
        "politica_base": adaptativa(DELTA0, alfa, delta_max),
        "fijos": {"tasa_media": TASA_MEDIA, "delta0": DELTA0},
        "ajuste": {"semillas": SEMILLAS_AJUSTE, "rejilla": rejilla, "elegido": mejor},
        "validacion": validacion_res,
    }
    Path(a.salida).parent.mkdir(parents=True, exist_ok=True)
    Path(a.salida).write_text(json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Escrito en {a.salida}")


if __name__ == "__main__":
    main()
