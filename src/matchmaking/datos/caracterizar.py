"""
Estadísticos descriptivos de la base del recolector (recolector_cr.py).

Reproduce los hallazgos de docs/CONTEXTO_Y_HALLAZGOS.md (sección 7) y muestra
el estado del panel después de cada corrida. Solo lee la base: no la modifica.

Uso (desde la raíz del repositorio):
  python -m src.matchmaking.datos.caracterizar
  python -m src.matchmaking.datos.caracterizar --db "C:\\ruta\\clash_royale.db"
  python -m src.matchmaking.datos.caracterizar --desde 2026-11-01 --desde-perfil 2026-11-05T14:00
"""

import argparse
import sqlite3
from pathlib import Path

from .recolector_cr import DB_DEFAULT

DESFASE_GT = -6  # Guatemala es UTC-6 todo el año


def a_battle_time(texto):
    """'2026-11-05T14:00' o '2026-11-05' (UTC) -> '20261105T140000' para comparar con battle_time."""
    if not texto:
        return None
    t = texto.replace("-", "").replace(":", "")
    if "T" not in t:
        t += "T"
    fecha, hora = t.split("T", 1)
    return fecha + "T" + hora.ljust(6, "0")[:6]


def percentil(ordenados, p):
    """Percentil con interpolación lineal (igual que numpy por defecto)."""
    if not ordenados:
        return float("nan")
    k = (len(ordenados) - 1) * p / 100
    i = int(k)
    j = min(i + 1, len(ordenados) - 1)
    return ordenados[i] + (ordenados[j] - ordenados[i]) * (k - i)


def describir(valores):
    v = sorted(valores)
    if not v:
        return {"n": 0}
    return {
        "n": len(v),
        "media": sum(v) / len(v),
        "mediana": percentil(v, 50),
        "p90": percentil(v, 90),
        "p99": percentil(v, 99),
        "max": v[-1],
    }


def fila(etiqueta, d):
    if d["n"] == 0:
        return f"  {etiqueta:<14} n=0"
    return (f"  {etiqueta:<14} n={d['n']:>7,}  media={d['media']:5.1f}  mediana={d['mediana']:4.0f}"
            f"  p90={d['p90']:4.0f}  p99={d['p99']:4.0f}  max={d['max']:4.0f}")


def diferencias(con, desde=None):
    """(battle_time, trofeos del jugador 'team', |dif|) de cada batalla de Trophy Road."""
    sql = """
        SELECT b.battle_time, t.trofeos_inicio, ABS(t.trofeos_inicio - o.trofeos_inicio)
        FROM batallas b
        JOIN participantes t ON t.batalla_id = b.batalla_id AND t.lado = 'team'
        JOIN participantes o ON o.batalla_id = b.batalla_id AND o.lado = 'opponent'
        WHERE b.es_ladder = 1 AND t.trofeos_inicio IS NOT NULL AND o.trofeos_inicio IS NOT NULL
    """
    params = ()
    if desde:
        sql += " AND b.battle_time >= ?"
        params = (desde,)
    return con.execute(sql, params).fetchall()


def batallas_panel(con, desde=None):
    """battle_time de las batallas de Trophy Road en que participa al menos un jugador del panel."""
    sql = """
        SELECT DISTINCT b.batalla_id, b.battle_time
        FROM batallas b
        JOIN participantes p ON p.batalla_id = b.batalla_id
        JOIN jugadores j ON j.tag = p.tag
        WHERE b.es_ladder = 1 AND j.panel = 1
    """
    params = ()
    if desde:
        sql += " AND b.battle_time >= ?"
        params = (desde,)
    return [r[1] for r in con.execute(sql, params)]


def hora_gt(battle_time):
    return (int(battle_time[9:11]) + DESFASE_GT) % 24


def main():
    ap = argparse.ArgumentParser(description="Estadísticos de la base del recolector")
    ap.add_argument("--db", default=DB_DEFAULT)
    ap.add_argument("--desde", default="2026-11-01",
                    help="Fecha UTC desde la que se toman las batallas por franja y por hora")
    ap.add_argument("--desde-perfil", default=None,
                    help="Fecha UTC desde la que se arma el perfil por hora del panel")
    a = ap.parse_args()

    if not Path(a.db).exists():
        raise SystemExit(f"No existe la base {a.db}. Usen --db con la ruta correcta.")
    con = sqlite3.connect(f"file:{Path(a.db).as_posix()}?mode=ro", uri=True)
    q = lambda s: con.execute(s).fetchone()

    jug, consultados, panel = q("SELECT COUNT(*), SUM(ultima_consulta IS NOT NULL), SUM(panel) FROM jugadores")
    total, ladder, bt_min, bt_max = q("SELECT COUNT(*), SUM(es_ladder), MIN(battle_time), MAX(battle_time) FROM batallas")
    p_min, p_max = q("SELECT MIN(ultima_consulta), MAX(ultima_consulta) FROM jugadores WHERE panel = 1")
    print("== Estado de la base ==")
    print(f"  Jugadores: {jug:,} ({consultados:,} consultados, {panel:,} en el panel)")
    print(f"  Batallas: {total:,} ({ladder:,} de Trophy Road)")
    print(f"  Rango de battle_time (UTC): {bt_min} a {bt_max}")
    print(f"  Última consulta del panel (UTC): la más vieja {p_min}, la más reciente {p_max}")

    print("\n== Diferencia absoluta de trofeos, todas las batallas de Trophy Road ==")
    todas = diferencias(con)
    print(fila("total", describir([d for _, _, d in todas])))

    desde = a_battle_time(a.desde)
    recientes = diferencias(con, desde)
    print(f"\n== Por franja del jugador 'team', desde {a.desde} UTC ==")
    franjas = {}
    for _, t, d in recientes:
        franjas.setdefault(t // 1000 * 1000, []).append(d)
    for f in sorted(franjas):
        print(fila(f"{f:,}", describir(franjas[f])))

    print(f"\n== Por hora de Guatemala, desde {a.desde} UTC ==")
    horas = {}
    for bt, _, d in recientes:
        horas.setdefault(hora_gt(bt), []).append(d)
    for h in range(24):
        print(fila(f"{h:02d}:00", describir(horas.get(h, []))))

    desde_p = a_battle_time(a.desde_perfil) if a.desde_perfil else desde
    tiempos = batallas_panel(con, desde_p)
    print(f"\n== Perfil de actividad del panel (batallas de Trophy Road por hora de Guatemala) ==")
    print(f"  Desde {a.desde_perfil or a.desde} UTC; {len(tiempos):,} batallas")
    conteo = [0] * 24
    for bt in tiempos:
        conteo[hora_gt(bt)] += 1
    tope = max(conteo) or 1
    for h, n in enumerate(conteo):
        print(f"  {h:02d}:00 {n:>6,} {'#' * round(40 * n / tope)}")
    vacias = [h for h, n in enumerate(conteo) if n == 0]
    if vacias:
        print(f"  Horas sin batallas del panel: {', '.join(f'{h:02d}' for h in vacias)}")


if __name__ == "__main__":
    main()
