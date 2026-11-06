"""
Limpieza de las batallas exportadas y separación en conjuntos de ajuste y validación.

Entrada:  data/processed/batallas.csv            (generado con recolector_cr exportar)
Salidas:  data/processed/batallas_estudio.csv    una fila por batalla válida, con su conjunto
          data/processed/calidad_datos.json      conteo de exclusiones por motivo

Filtros, en este orden (cada batalla se cuenta en el primer motivo que la excluye):
  1. no_trophy_road      tipo distinto de PvP o modo distinto de Ladder
  2. trofeos_faltantes   falta startingTrophies de alguno de los dos jugadores
  3. fuera_de_periodo    fecha (hora de Guatemala) fuera de los días de ajuste y validación
  4. fuera_de_franja     alguno de los dos jugadores fuera de [min_trofeos, max_trofeos)
  5. duplicada           la misma batalla vista desde los dos jugadores con 1-2 s de diferencia
                         en battleTime (mismos jugadores, trofeos y cambio de trofeos)

Los días se fijan antes de calibrar (decisiones.md, D8): ajuste 1-3 nov, validación 4 nov.
Las batallas del 5 y 6 nov se excluyen por el sesgo cerca de cada consulta.

Uso (desde la raíz del repositorio):
  python -m src.matchmaking.datos.procesar
"""

import argparse
import csv
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
PROCESADOS = RAIZ / "data" / "processed"

DESFASE_GT = timedelta(hours=-6)  # Guatemala: UTC-6 todo el año
DIAS_AJUSTE = ("2026-11-01", "2026-11-03")
DIAS_VALIDACION = ("2026-11-04", "2026-11-04")
MIN_TROFEOS, MAX_TROFEOS = 5000, 12000
TOLERANCIA_DUPLICADO_S = 2

COLUMNAS = [
    "batalla", "battle_time_utc", "fecha_gt", "hora_gt", "conjunto",
    "j1", "j1_trofeos_inicio", "j1_cambio",
    "j2", "j2_trofeos_inicio", "j2_cambio",
    "trofeos_medios", "franja", "dif_trofeos_abs",
]


def a_fecha(texto):
    return date.fromisoformat(texto)


def hora_utc(battle_time):
    """'20261101T060403.000Z' -> datetime UTC."""
    return datetime.strptime(battle_time[:15], "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)


def entero(valor):
    return int(valor) if valor not in ("", None) else None


def conjunto_de(fecha, ajuste, validacion):
    if ajuste[0] <= fecha <= ajuste[1]:
        return "ajuste"
    if validacion[0] <= fecha <= validacion[1]:
        return "validacion"
    return None


def procesar(entrada, salida, ajuste, validacion, min_t, max_t, tolerancia_s):
    motivos = {k: 0 for k in ("no_trophy_road", "trofeos_faltantes", "fuera_de_periodo",
                              "fuera_de_franja", "duplicada")}
    validas = []
    total = 0
    with open(entrada, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            total += 1
            if r["tipo"] != "PvP" or r["modo"] != "Ladder":
                motivos["no_trophy_road"] += 1
                continue
            t1, t2 = entero(r["j1_trofeos_inicio"]), entero(r["j2_trofeos_inicio"])
            if t1 is None or t2 is None:
                motivos["trofeos_faltantes"] += 1
                continue
            utc = hora_utc(r["battle_time_utc"])
            local = utc + DESFASE_GT
            conjunto = conjunto_de(local.date(), ajuste, validacion)
            if conjunto is None:
                motivos["fuera_de_periodo"] += 1
                continue
            if not (min_t <= t1 < max_t and min_t <= t2 < max_t):
                motivos["fuera_de_franja"] += 1
                continue
            medios = (t1 + t2) / 2
            validas.append({
                "batalla": r["batalla"],
                "battle_time_utc": r["battle_time_utc"],
                "fecha_gt": local.date().isoformat(),
                "hora_gt": local.hour,
                "conjunto": conjunto,
                "j1": r["j1"], "j1_trofeos_inicio": t1, "j1_cambio": entero(r["j1_cambio"]),
                "j2": r["j2"], "j2_trofeos_inicio": t2, "j2_cambio": entero(r["j2_cambio"]),
                "trofeos_medios": medios,
                "franja": int(medios // 1000 * 1000),
                "dif_trofeos_abs": abs(t1 - t2),
                "_utc": utc,
            })

    # Duplicados: la API puede dar battleTime con 1 s de diferencia según desde qué jugador se vea.
    validas.sort(key=lambda v: v["_utc"])
    vistos = {}
    unicas = []
    for v in validas:
        clave = frozenset({(v["j1"], v["j1_trofeos_inicio"], v["j1_cambio"]),
                           (v["j2"], v["j2_trofeos_inicio"], v["j2_cambio"])})
        anterior = vistos.get(clave)
        if anterior is not None and (v["_utc"] - anterior).total_seconds() <= tolerancia_s:
            motivos["duplicada"] += 1
            continue
        vistos[clave] = v["_utc"]
        unicas.append(v)

    salida.mkdir(parents=True, exist_ok=True)
    with open(salida / "batallas_estudio.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS, extrasaction="ignore")
        w.writeheader()
        w.writerows(unicas)

    por_conjunto = {}
    for v in unicas:
        c = por_conjunto.setdefault(v["conjunto"], {"batallas": 0, "dias": set()})
        c["batallas"] += 1
        c["dias"].add(v["fecha_gt"])
    calidad = {
        "entrada": Path(entrada).relative_to(RAIZ).as_posix() if Path(entrada).is_relative_to(RAIZ) else str(entrada),
        "batallas_leidas": total,
        "excluidas_por_motivo": motivos,
        "batallas_validas": len(unicas),
        "por_conjunto": {k: {"batallas": c["batallas"], "dias_gt": sorted(c["dias"])}
                         for k, c in sorted(por_conjunto.items())},
        "configuracion": {
            "zona_horaria": "America/Guatemala (UTC-6)",
            "dias_ajuste": [d.isoformat() for d in ajuste],
            "dias_validacion": [d.isoformat() for d in validacion],
            "franja_trofeos": [min_t, max_t],
            "tolerancia_duplicado_s": tolerancia_s,
        },
    }
    (salida / "calidad_datos.json").write_text(
        json.dumps(calidad, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return calidad


def main():
    ap = argparse.ArgumentParser(description="Limpia las batallas y separa ajuste y validación")
    ap.add_argument("--entrada", default=str(PROCESADOS / "batallas.csv"))
    ap.add_argument("--salida", default=str(PROCESADOS))
    ap.add_argument("--ajuste", nargs=2, default=DIAS_AJUSTE, metavar=("DESDE", "HASTA"),
                    help="Días de ajuste, hora de Guatemala (inclusive)")
    ap.add_argument("--validacion", nargs=2, default=DIAS_VALIDACION, metavar=("DESDE", "HASTA"),
                    help="Días reservados para validar, hora de Guatemala (inclusive)")
    ap.add_argument("--min-trofeos", type=int, default=MIN_TROFEOS)
    ap.add_argument("--max-trofeos", type=int, default=MAX_TROFEOS)
    a = ap.parse_args()

    ajuste = tuple(a_fecha(d) for d in a.ajuste)
    validacion = tuple(a_fecha(d) for d in a.validacion)
    if not ajuste[1] < validacion[0]:
        ap.error("Los días de ajuste deben terminar antes de los de validación.")
    c = procesar(Path(a.entrada), Path(a.salida), ajuste, validacion,
                 a.min_trofeos, a.max_trofeos, TOLERANCIA_DUPLICADO_S)

    print(f"Leídas: {c['batallas_leidas']:,}")
    for motivo, n in c["excluidas_por_motivo"].items():
        print(f"  excluidas por {motivo:<18} {n:>7,}")
    print(f"Válidas: {c['batallas_validas']:,}")
    for k, v in c["por_conjunto"].items():
        print(f"  {k:<11} {v['batallas']:>7,} batallas  días {', '.join(v['dias_gt'])}")
    print(f"Escrito en {Path(a.salida) / 'batallas_estudio.csv'} y calidad_datos.json")


if __name__ == "__main__":
    main()
