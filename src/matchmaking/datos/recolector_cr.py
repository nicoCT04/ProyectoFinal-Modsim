#!/usr/bin/env python3
"""
Recolector de batallas de Clash Royale para el Proyecto 2 de Modelización y Simulación.

Usa solo la biblioteca estándar de Python (no hay que instalar nada).
Guarda todo en una base SQLite local y permite reanudar donde se quedó.

Comandos:
  probar      Verifica que la clave funciona consultando un jugador.
  semilla     Agrega jugadores iniciales (desde etiquetas o desde clanes).
  recolectar  Descarga el historial de batallas de los jugadores en cola.
  resumen     Muestra cuántas batallas hay, por tipo, modo y franja de trofeos.
  exportar    Genera CSV anonimizados para subir al repositorio.

Configuración (variables de entorno):
  CR_API_TOKEN   Clave de developer.clashroyale.com (obligatoria).
  CR_BASE_URL    Opcional. Por defecto https://api.clashroyale.com
                 Con el proxy de RoyaleAPI: https://proxy.royaleapi.dev
  CR_SALT        Texto secreto para anonimizar etiquetas al exportar.

Ejemplos:
  python recolector_cr.py probar --tag "#ABC123"
  python recolector_cr.py semilla --tags "#ABC123" "#XYZ789"
  python recolector_cr.py semilla --buscar-clanes --min-miembros 40 --min-puntaje 60000
  python recolector_cr.py recolectar --minutos 60
  python recolector_cr.py recolectar --minutos 30 --refrescar-horas 6
  python recolector_cr.py resumen
  python recolector_cr.py exportar --salida datos_exportados
"""

import argparse
import csv
import hashlib
import hmac
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

DB_DEFAULT = "clash_royale.db"


# ----------------------------------------------------------------------------
# Cliente de la API
# ----------------------------------------------------------------------------
class ClienteCR:
    def __init__(self, token, base_url, rps):
        self.token = token
        self.base = base_url.rstrip("/")
        self.intervalo = 1.0 / rps
        self._ultimo = 0.0
        self.solicitudes = 0

    def get(self, ruta, params=None, intentos=5):
        url = f"{self.base}/v1{ruta}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        espera = 2.0
        for _ in range(intentos):
            pausa = self.intervalo - (time.time() - self._ultimo)
            if pausa > 0:
                time.sleep(pausa)
            self._ultimo = time.time()
            req = urllib.request.Request(url, headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
            })
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    self.solicitudes += 1
                    return json.loads(r.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                cuerpo = e.read().decode("utf-8", "ignore")
                if e.code == 404:
                    return None
                if e.code == 403:
                    sys.exit(
                        "Error 403: acceso denegado. Casi siempre significa que la IP desde la que "
                        "corren el script no está en la lista de la clave, o que la clave está mal "
                        f"copiada.\nDetalle: {cuerpo}"
                    )
                if e.code in (429, 500, 502, 503, 504):
                    print(f"  Aviso: HTTP {e.code}, reintentando en {espera:.0f} s")
                    time.sleep(espera)
                    espera *= 2
                    continue
                raise RuntimeError(f"HTTP {e.code} en {url}: {cuerpo}")
            except (urllib.error.URLError, TimeoutError) as e:
                print(f"  Aviso: error de red ({e}), reintentando en {espera:.0f} s")
                time.sleep(espera)
                espera *= 2
        raise RuntimeError(f"No se pudo obtener {url} después de {intentos} intentos")

    @staticmethod
    def cod(tag):
        tag = tag.strip().upper()
        if not tag.startswith("#"):
            tag = "#" + tag
        return urllib.parse.quote(tag, safe="")

    def jugador(self, tag):
        return self.get(f"/players/{self.cod(tag)}")

    def batallas(self, tag):
        return self.get(f"/players/{self.cod(tag)}/battlelog")

    def miembros_clan(self, tag):
        return self.get(f"/clans/{self.cod(tag)}/members")

    def buscar_clanes(self, **filtros):
        return self.get("/clans", {k: v for k, v in filtros.items() if v is not None})


# ----------------------------------------------------------------------------
# Base de datos
# ----------------------------------------------------------------------------
ESQUEMA = """
CREATE TABLE IF NOT EXISTS jugadores (
    tag             TEXT PRIMARY KEY,
    trofeos         INTEGER,
    origen          TEXT,
    agregado_en     TEXT,
    ultima_consulta TEXT,
    consultas       INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS batallas (
    batalla_id      TEXT PRIMARY KEY,
    battle_time     TEXT,
    tipo            TEXT,
    modo_id         INTEGER,
    modo_nombre     TEXT,
    arena_id        INTEGER,
    arena_nombre    TEXT,
    es_ladder       INTEGER,
    recolectada_en  TEXT
);
CREATE TABLE IF NOT EXISTS participantes (
    batalla_id        TEXT,
    lado              TEXT,      -- 'team' u 'opponent'
    tag               TEXT,
    trofeos_inicio    INTEGER,
    cambio_trofeos    INTEGER,
    coronas           INTEGER,
    nivel_rey         INTEGER,
    cartas_json       TEXT,
    PRIMARY KEY (batalla_id, tag)
);
CREATE INDEX IF NOT EXISTS idx_jug_consulta ON jugadores(ultima_consulta);
CREATE INDEX IF NOT EXISTS idx_bat_tiempo ON batallas(battle_time);
"""


def conectar(ruta):
    con = sqlite3.connect(ruta)
    con.executescript(ESQUEMA)
    columnas = [r[1] for r in con.execute("PRAGMA table_info(jugadores)")]
    if "panel" not in columnas:  # bases creadas con la primera versión
        con.execute("ALTER TABLE jugadores ADD COLUMN panel INTEGER DEFAULT 0")
        con.commit()
    return con


def ahora():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def agregar_jugador(con, tag, trofeos=None, origen=""):
    tag = tag.strip().upper()
    if not tag.startswith("#"):
        tag = "#" + tag
    con.execute(
        "INSERT OR IGNORE INTO jugadores(tag, trofeos, origen, agregado_en) VALUES (?,?,?,?)",
        (tag, trofeos, origen, ahora()),
    )


def id_batalla(b):
    tags = sorted(p.get("tag", "") for p in b.get("team", []) + b.get("opponent", []))
    return b.get("battleTime", "") + "|" + "|".join(tags)


def es_ladder(b):
    # Se marca, pero no se filtra: el valor exacto se verifica en la extracción de prueba.
    tipo = (b.get("type") or "").lower()
    modo = ((b.get("gameMode") or {}).get("name") or "").lower()
    return int(tipo == "pvp" and ("ladder" in modo or modo == ""))


def guardar_batallas(con, lista, min_trof, max_trof, permitir_nuevos=True):
    nuevas, nuevos_jug = 0, 0
    for b in lista or []:
        team, opp = b.get("team", []), b.get("opponent", [])
        bid = id_batalla(b)
        modo, arena = b.get("gameMode") or {}, b.get("arena") or {}
        cur = con.execute(
            "INSERT OR IGNORE INTO batallas VALUES (?,?,?,?,?,?,?,?,?)",
            (bid, b.get("battleTime"), b.get("type"), modo.get("id"), modo.get("name"),
             arena.get("id"), arena.get("name") if isinstance(arena.get("name"), str) else json.dumps(arena.get("name")),
             es_ladder(b), ahora()),
        )
        if cur.rowcount:
            nuevas += 1
        for lado, jugadores in (("team", team), ("opponent", opp)):
            for p in jugadores:
                cartas = [
                    {"nombre": c.get("name") if isinstance(c.get("name"), str) else c.get("id"),
                     "nivel": c.get("level"), "nivel_max": c.get("maxLevel"),
                     "rareza": c.get("rarity"), "evolucion": c.get("evolutionLevel")}
                    for c in p.get("cards", [])
                ]
                con.execute(
                    "INSERT OR IGNORE INTO participantes VALUES (?,?,?,?,?,?,?,?)",
                    (bid, lado, p.get("tag"), p.get("startingTrophies"), p.get("trophyChange"),
                     p.get("crowns"), p.get("kingTowerLevel"), json.dumps(cartas, ensure_ascii=False)),
                )
                t = p.get("startingTrophies")
                if permitir_nuevos and p.get("tag") and (t is None or min_trof <= t <= max_trof):
                    antes = con.total_changes
                    agregar_jugador(con, p["tag"], t, "rival")
                    nuevos_jug += con.total_changes - antes
    return nuevas, nuevos_jug


# ----------------------------------------------------------------------------
# Comandos
# ----------------------------------------------------------------------------
def cliente_desde_entorno(rps):
    token = os.environ.get("CR_API_TOKEN")
    if not token:
        sys.exit("Falta la variable de entorno CR_API_TOKEN con su clave de la API.")
    base = os.environ.get("CR_BASE_URL", "https://api.clashroyale.com")
    return ClienteCR(token, base, rps)


def cmd_probar(a):
    cli = cliente_desde_entorno(a.rps)
    j = cli.jugador(a.tag)
    if j is None:
        sys.exit(f"No existe el jugador {a.tag}. Revisen la etiqueta.")
    print(f"Conexión correcta. Jugador: {j.get('name')}  trofeos: {j.get('trophies')}")
    bl = cli.batallas(a.tag) or []
    print(f"Batallas recientes disponibles: {len(bl)}")
    tipos = {}
    for b in bl:
        k = (b.get("type"), (b.get("gameMode") or {}).get("name"))
        tipos[k] = tipos.get(k, 0) + 1
    print("Tipos y modos encontrados (anoten cuál corresponde a Trophy Road):")
    for (t, m), n in sorted(tipos.items(), key=lambda x: -x[1]):
        print(f"  type={t!s:<20} gameMode={m!s:<25} n={n}")
    if bl and a.mostrar_json:
        print(json.dumps(bl[0], indent=2, ensure_ascii=False)[:4000])


def cmd_semilla(a):
    con = conectar(a.db)
    total = 0
    for t in a.tags or []:
        agregar_jugador(con, t, None, "manual")
        total += 1
    clanes = list(a.clanes or [])
    if a.buscar_clanes:
        cli = cliente_desde_entorno(a.rps)
        r = cli.buscar_clanes(minMembers=a.min_miembros, minScore=a.min_puntaje,
                              locationId=a.location_id, limit=a.limite_clanes)
        clanes += [c["tag"] for c in (r or {}).get("items", [])]
        print(f"Clanes encontrados: {len(clanes)}")
    if clanes:
        cli = cliente_desde_entorno(a.rps)
        for ct in clanes:
            r = cli.miembros_clan(ct) or {}
            for m in r.get("items", []):
                if a.min_trofeos <= (m.get("trophies") or 0) <= a.max_trofeos:
                    agregar_jugador(con, m["tag"], m.get("trophies"), f"clan {ct}")
                    total += 1
    con.commit()
    n = con.execute("SELECT COUNT(*) FROM jugadores").fetchone()[0]
    print(f"Semilla agregada ({total} intentos). Jugadores en la base: {n}")


def cmd_recolectar(a):
    con = conectar(a.db)
    cli = cliente_desde_entorno(a.rps)
    fin = time.time() + a.minutos * 60
    limite = datetime.now(timezone.utc).timestamp() - a.refrescar_horas * 3600
    limite_txt = datetime.fromtimestamp(limite, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    tot_bat, tot_jug, consultados = 0, 0, 0
    n_jug = con.execute("SELECT COUNT(*) FROM jugadores").fetchone()[0]
    print(f"Recolectando durante {a.minutos} min (Ctrl+C para detener sin perder datos)...")
    if a.max_jugadores:
        print(f"Panel limitado a {a.max_jugadores} jugadores (actualmente {n_jug}).")
    try:
        while time.time() < fin:
            if a.solo_panel:
                # Solo refresca el panel fijo, del más antiguo al más reciente.
                filas = con.execute(
                    """SELECT tag FROM jugadores
                       WHERE panel=1 AND (ultima_consulta IS NULL OR ultima_consulta < ?)
                       ORDER BY ultima_consulta LIMIT 200""", (limite_txt,)).fetchall()
            else:
                # Primero los nunca consultados; luego los que toca refrescar.
                filas = con.execute(
                    """SELECT tag FROM jugadores
                       WHERE ultima_consulta IS NULL OR ultima_consulta < ?
                       ORDER BY ultima_consulta IS NOT NULL, ultima_consulta, agregado_en
                       LIMIT 200""", (limite_txt,)).fetchall()
            if not filas:
                if a.solo_panel:
                    print("Todo el panel está al día. El próximo refresco toca en unas horas.")
                else:
                    print("No hay jugadores pendientes. Agreguen semilla o esperen al próximo refresco.")
                break
            for (tag,) in filas:
                if time.time() >= fin:
                    break
                bl = cli.batallas(tag)
                permitir = not a.solo_panel and (not a.max_jugadores or n_jug < a.max_jugadores)
                n_b, n_j = guardar_batallas(con, bl, a.min_trofeos, a.max_trofeos, permitir)
                n_jug += n_j
                con.execute("UPDATE jugadores SET ultima_consulta=?, consultas=consultas+1 WHERE tag=?",
                            (ahora(), tag))
                tot_bat += n_b
                tot_jug += n_j
                consultados += 1
                if consultados % 25 == 0:
                    con.commit()
                    print(f"  {consultados} jugadores consultados | +{tot_bat} batallas nuevas | +{tot_jug} jugadores nuevos en cola")
    except KeyboardInterrupt:
        print("\nDetenido por el usuario.")
    finally:
        con.commit()
    print(f"Listo. Consultados: {consultados}. Batallas nuevas: {tot_bat}. Solicitudes a la API: {cli.solicitudes}")


def cmd_panel(a):
    """Elige un panel fijo de jugadores ya consultados, estratificado por franja de 1,000 trofeos."""
    import random
    con = conectar(a.db)
    # Trofeos más recientes de cada jugador consultado, según su última batalla de Trophy Road.
    # En SQLite, con MAX() y GROUP BY, las demás columnas vienen de la fila del máximo.
    filas = con.execute("""
        SELECT p.tag, p.trofeos_inicio, MAX(b.battle_time)
        FROM participantes p JOIN batallas b USING(batalla_id)
        JOIN jugadores j ON j.tag = p.tag
        WHERE b.es_ladder=1 AND j.ultima_consulta IS NOT NULL AND p.trofeos_inicio IS NOT NULL
        GROUP BY p.tag
    """).fetchall()
    franjas = {}
    for tag, t, _ in filas:
        if a.min_trofeos <= t < a.max_trofeos:
            franjas.setdefault(t // 1000 * 1000, set()).add(tag)
    if not franjas:
        sys.exit("No hay jugadores consultados en esa franja. Corran recolectar primero.")
    rnd = random.Random(a.semilla)
    por_franja = a.n // len(franjas)
    elegidos = []
    for f in sorted(franjas):
        candidatos = sorted(franjas[f])
        tomados = rnd.sample(candidatos, min(por_franja, len(candidatos)))
        elegidos += tomados
        print(f"  {f:>6}–{f+999:<6} disponibles {len(candidatos):>6}  elegidos {len(tomados)}")
    con.execute("UPDATE jugadores SET panel=0")
    con.executemany("UPDATE jugadores SET panel=1 WHERE tag=?", [(t,) for t in elegidos])
    con.commit()
    print(f"Panel creado con {len(elegidos)} jugadores (semilla aleatoria {a.semilla}).")


def cmd_resumen(a):
    con = conectar(a.db)
    q = lambda s, *p: con.execute(s, p).fetchall()
    print("Jugadores:", q("SELECT COUNT(*), SUM(ultima_consulta IS NOT NULL) FROM jugadores")[0])
    print("Batallas totales:", q("SELECT COUNT(*) FROM batallas")[0][0])
    print("\nPor tipo y modo:")
    for t, m, n in q("SELECT tipo, modo_nombre, COUNT(*) FROM batallas GROUP BY 1,2 ORDER BY 3 DESC LIMIT 20"):
        print(f"  {t!s:<22} {m!s:<28} {n}")
    print("\nBatallas marcadas como Trophy Road por franja de trofeos (del jugador 'team'):")
    for f, n in q("""SELECT (p.trofeos_inicio/1000)*1000 AS franja, COUNT(*)
                     FROM batallas b JOIN participantes p USING(batalla_id)
                     WHERE b.es_ladder=1 AND p.lado='team' AND p.trofeos_inicio IS NOT NULL
                     GROUP BY 1 ORDER BY 1"""):
        print(f"  {f:>6}–{f+999:<6} {n}")
    r = q("SELECT MIN(battle_time), MAX(battle_time) FROM batallas")[0]
    print(f"\nRango de fechas (UTC): {r[0]}  a  {r[1]}")


def cmd_exportar(a):
    sal = os.environ.get("CR_SALT")
    if not sal:
        sys.exit("Definan CR_SALT (un texto secreto) para anonimizar. No lo suban al repositorio.")
    anon = lambda t: hmac.new(sal.encode(), (t or "").encode(), hashlib.sha256).hexdigest()[:16] if t else ""
    con = conectar(a.db)
    os.makedirs(a.salida, exist_ok=True)
    filtro = "WHERE b.es_ladder=1" if not a.todos_los_modos else ""
    filas = con.execute(f"""
        SELECT b.batalla_id, b.battle_time, b.tipo, b.modo_nombre, b.arena_id,
               t.tag, t.trofeos_inicio, t.cambio_trofeos, t.coronas, t.nivel_rey, t.cartas_json,
               o.tag, o.trofeos_inicio, o.cambio_trofeos, o.coronas, o.nivel_rey, o.cartas_json
        FROM batallas b
        JOIN participantes t ON t.batalla_id=b.batalla_id AND t.lado='team'
        JOIN participantes o ON o.batalla_id=b.batalla_id AND o.lado='opponent'
        {filtro}
        ORDER BY b.battle_time""").fetchall()

    def nivel_medio(cj):
        cartas = json.loads(cj or "[]")
        # Escala relativa: la API da el nivel según la rareza; sumar (16 - nivel_max) pone todas
        # las rarezas en la misma escala. Sirve para comparar jugadores, no como nivel exacto del juego.
        vals = [c["nivel"] + (16 - c["nivel_max"]) for c in cartas if c.get("nivel") and c.get("nivel_max")]
        return round(sum(vals) / len(vals), 3) if vals else ""

    ruta = os.path.join(a.salida, "batallas.csv")
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["batalla", "battle_time_utc", "tipo", "modo", "arena_id",
                    "j1", "j1_trofeos_inicio", "j1_cambio", "j1_coronas", "j1_nivel_rey", "j1_nivel_cartas_medio",
                    "j2", "j2_trofeos_inicio", "j2_cambio", "j2_coronas", "j2_nivel_rey", "j2_nivel_cartas_medio",
                    "dif_trofeos_abs"])
        for r in filas:
            dif = abs(r[6] - r[12]) if r[6] is not None and r[12] is not None else ""
            w.writerow([anon(r[0]), r[1], r[2], r[3], r[4],
                        anon(r[5]), r[6], r[7], r[8], r[9], nivel_medio(r[10]),
                        anon(r[11]), r[12], r[13], r[14], r[15], nivel_medio(r[16]), dif])
    print(f"Exportadas {len(filas)} batallas a {ruta} (etiquetas anonimizadas).")


def main():
    ap = argparse.ArgumentParser(description="Recolector de batallas de Clash Royale")
    ap.add_argument("--db", default=DB_DEFAULT, help="Archivo SQLite (por defecto clash_royale.db)")
    ap.add_argument("--rps", type=float, default=4.0, help="Solicitudes por segundo (por defecto 4)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("probar")
    s.add_argument("--tag", required=True, help="Etiqueta de un jugador, p. ej. #ABC123")
    s.add_argument("--mostrar-json", action="store_true", help="Imprime una batalla completa")
    s.set_defaults(fn=cmd_probar)

    s = sub.add_parser("semilla")
    s.add_argument("--tags", nargs="*", help="Etiquetas de jugadores iniciales")
    s.add_argument("--clanes", nargs="*", help="Etiquetas de clanes cuyos miembros se agregan")
    s.add_argument("--buscar-clanes", action="store_true", help="Buscar clanes con la API")
    s.add_argument("--min-miembros", type=int, default=40)
    s.add_argument("--min-puntaje", type=int, default=None)
    s.add_argument("--location-id", type=int, default=None)
    s.add_argument("--limite-clanes", type=int, default=50)
    s.add_argument("--min-trofeos", type=int, default=5000)
    s.add_argument("--max-trofeos", type=int, default=12000)
    s.set_defaults(fn=cmd_semilla)

    s = sub.add_parser("recolectar")
    s.add_argument("--minutos", type=float, default=60)
    s.add_argument("--refrescar-horas", type=float, default=6,
                   help="Vuelve a consultar jugadores cuya última consulta tenga más de estas horas")
    s.add_argument("--max-jugadores", type=int, default=None,
                   help="Deja de agregar rivales nuevos al llegar a este total, para refrescar un panel fijo")
    s.add_argument("--min-trofeos", type=int, default=5000)
    s.add_argument("--max-trofeos", type=int, default=12000)
    s.add_argument("--solo-panel", action="store_true",
                   help="Solo refresca los jugadores del panel creado con el comando panel")
    s.set_defaults(fn=cmd_recolectar)

    s = sub.add_parser("panel")
    s.add_argument("--n", type=int, default=3000, help="Tamaño del panel (por defecto 3000)")
    s.add_argument("--min-trofeos", type=int, default=5000)
    s.add_argument("--max-trofeos", type=int, default=12000)
    s.add_argument("--semilla", type=int, default=42, help="Semilla aleatoria, para que sea reproducible")
    s.set_defaults(fn=cmd_panel)

    s = sub.add_parser("resumen")
    s.set_defaults(fn=cmd_resumen)

    s = sub.add_parser("exportar")
    s.add_argument("--salida", default="datos_exportados")
    s.add_argument("--todos-los-modos", action="store_true", help="No filtrar solo Trophy Road")
    s.set_defaults(fn=cmd_exportar)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
