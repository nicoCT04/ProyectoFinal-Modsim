"""
Genera data/processed/parametros.json, la entrada del simulador, a partir de las batallas limpias.

Entrada: data/processed/batallas_estudio.csv (generado con procesar.py)

Contenido de parametros.json:
  trofeos_solicitudes     Distribución empírica de los trofeos de quien busca rival (ambos jugadores
                          de cada batalla de ajuste), como 101 cuantiles para muestrear por la inversa.
  perfil_horario          Peso relativo de cada hora de Guatemala (24 valores que suman 1), con las
                          batallas de ajuste y validación (1-4 nov; decisiones.md, D5). Solo da la forma:
                          la tasa absoluta de llegadas no se observa y se fija por escenario.
  diferencias_referencia  Distribución de |r_i - r_j| en ajuste (para calibrar) y en validación
                          (referencia real de la Parte 6), total, por franja y por hora.

Uso (desde la raíz del repositorio):
  python -m src.matchmaking.datos.caracterizar
"""

import argparse
import csv
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
PROCESADOS = RAIZ / "data" / "processed"
ANCHO_HISTOGRAMA = 5  # trofeos


def percentil(ordenados, p):
    """Percentil con interpolación lineal (igual que numpy por defecto)."""
    k = (len(ordenados) - 1) * p / 100
    i = int(k)
    j = min(i + 1, len(ordenados) - 1)
    return ordenados[i] + (ordenados[j] - ordenados[i]) * (k - i)


def describir(valores):
    v = sorted(valores)
    n = len(v)
    media = sum(v) / n
    desv = math.sqrt(sum((x - media) ** 2 for x in v) / (n - 1)) if n > 1 else 0.0
    return {
        "n": n,
        "media": round(media, 3),
        "desv": round(desv, 3),
        "mediana": round(percentil(v, 50), 2),
        "p75": round(percentil(v, 75), 2),
        "p90": round(percentil(v, 90), 2),
        "p95": round(percentil(v, 95), 2),
        "p99": round(percentil(v, 99), 2),
        "max": v[-1],
        "prop_cero": round(sum(1 for x in v if x == 0) / n, 4),
    }


def histograma(valores, ancho):
    tope = max(valores)
    cajas = [0] * (tope // ancho + 1)
    for x in valores:
        cajas[x // ancho] += 1
    n = len(valores)
    return {
        "ancho": ancho,
        "desde": [i * ancho for i in range(len(cajas))],
        "proporcion": [round(c / n, 5) for c in cajas],
    }


def diferencias(filas):
    difs = [f["dif"] for f in filas]
    out = describir(difs)
    out["histograma"] = histograma(difs, ANCHO_HISTOGRAMA)
    por_franja = {}
    for f in filas:
        por_franja.setdefault(f["franja"], []).append(f["dif"])
    out["por_franja"] = {
        str(k): {kk: d[kk] for kk in ("n", "media", "mediana", "p90", "max")}
        for k, d in ((k, describir(v)) for k, v in sorted(por_franja.items()))
    }
    por_hora = [[] for _ in range(24)]
    for f in filas:
        por_hora[f["hora"]].append(f["dif"])
    out["media_por_hora_gt"] = [round(sum(h) / len(h), 3) if h else None for h in por_hora]
    return out


def leer(ruta):
    filas = []
    with open(ruta, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            filas.append({
                "conjunto": r["conjunto"],
                "fecha": r["fecha_gt"],
                "hora": int(r["hora_gt"]),
                "t1": int(r["j1_trofeos_inicio"]),
                "t2": int(r["j2_trofeos_inicio"]),
                "franja": int(r["franja"]),
                "dif": int(r["dif_trofeos_abs"]),
            })
    return filas


def caracterizar(filas):
    ajuste = [f for f in filas if f["conjunto"] == "ajuste"]
    validacion = [f for f in filas if f["conjunto"] == "validacion"]
    if not ajuste or not validacion:
        raise SystemExit("Faltan batallas de ajuste o de validación. Corran procesar.py primero.")

    trofeos = sorted([f["t1"] for f in ajuste] + [f["t2"] for f in ajuste])
    por_franja = {}
    for t in trofeos:
        por_franja[t // 1000 * 1000] = por_franja.get(t // 1000 * 1000, 0) + 1

    conteo_hora = [0] * 24
    for f in filas:
        conteo_hora[f["hora"]] += 1
    dias = len({f["fecha"] for f in filas})

    return {
        "metadatos": {
            "generado_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "fuente": "API oficial de Clash Royale, /v1/players/{tag}/battlelog (vía proxy.royaleapi.dev)",
            "entrada": "data/processed/batallas_estudio.csv",
            "unidades": "trofeos; horas de Guatemala (UTC-6)",
            "conjuntos": {
                "ajuste": {"batallas": len(ajuste), "dias_gt": sorted({f["fecha"] for f in ajuste})},
                "validacion": {"batallas": len(validacion), "dias_gt": sorted({f["fecha"] for f in validacion})},
            },
            "tipo_de_dato": {
                "trofeos_solicitudes": "real observado (muestra con sesgo de muestreo; ver decisiones.md D4)",
                "perfil_horario": "real observado, forma relativa; la tasa absoluta es un parámetro de escenario",
                "diferencias_referencia": "real observado; ajuste para calibrar, validación para la Parte 6",
                "tiempo_de_espera": "no observado; es una salida de la simulación",
            },
        },
        "trofeos_solicitudes": {
            "descripcion": "Trofeos al iniciar de cada jugador en las batallas de ajuste (2 por batalla). "
                           "Para muestrear se usa 'frecuencias' (distribución empírica exacta): conserva la "
                           "acumulación en los pisos de arena (6,500, 11,500, 5,500...), que explica parte de "
                           "las batallas con diferencia 0. 'cuantiles' es un resumen.",
            "conjunto": "ajuste",
            **{k: v for k, v in describir(trofeos).items() if k in ("n", "media", "desv", "mediana", "max")},
            "min": trofeos[0],
            "cuantiles": [round(percentil(trofeos, p), 2) for p in range(101)],
            "frecuencias": {
                "valores": sorted(set(trofeos)),
                "conteos": [c for _, c in sorted(Counter(trofeos).items())],
            },
            "proporcion_por_franja": {str(k): round(v / len(trofeos), 5) for k, v in sorted(por_franja.items())},
        },
        "perfil_horario": {
            "descripcion": "Peso relativo de llegadas por hora de Guatemala (índice 0 = 00:00-00:59). "
                           "Multiplicar por la tasa diaria del escenario para obtener la tasa por hora.",
            "conjunto": "ajuste + validacion",
            "dias": dias,
            "peso": [round(c / sum(conteo_hora), 5) for c in conteo_hora],
            "batallas_por_hora_promedio_en_muestra": [round(c / dias, 1) for c in conteo_hora],
        },
        "diferencias_referencia": {
            "descripcion": "Diferencia absoluta de trofeos entre rivales, |r_i - r_j|.",
            "ajuste": diferencias(ajuste),
            "validacion": diferencias(validacion),
        },
    }


def main():
    ap = argparse.ArgumentParser(description="Genera parametros.json para el simulador")
    ap.add_argument("--entrada", default=str(PROCESADOS / "batallas_estudio.csv"))
    ap.add_argument("--salida", default=str(PROCESADOS / "parametros.json"))
    a = ap.parse_args()

    p = caracterizar(leer(a.entrada))
    Path(a.salida).write_text(json.dumps(p, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    t = p["trofeos_solicitudes"]
    print(f"Trofeos de solicitudes (ajuste): n={t['n']:,}  media={t['media']:.0f}  "
          f"P5={t['cuantiles'][5]:.0f}  mediana={t['mediana']:.0f}  P95={t['cuantiles'][95]:.0f}")
    print("Perfil horario (peso):", " ".join(f"{h:02d}:{w:.3f}" for h, w in enumerate(p["perfil_horario"]["peso"])))
    for c in ("ajuste", "validacion"):
        d = p["diferencias_referencia"][c]
        print(f"Diferencias {c:<10} n={d['n']:>6,}  media={d['media']:5.2f}  mediana={d['mediana']:4.0f}  "
              f"p90={d['p90']:4.0f}  p99={d['p99']:4.0f}  max={d['max']}  prop_cero={d['prop_cero']:.3f}")
    print(f"Escrito en {a.salida}")


if __name__ == "__main__":
    main()
