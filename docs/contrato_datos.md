# Contrato de datos

## `data/processed/batallas.csv`

Generado con `python -m src.matchmaking.datos.recolector_cr exportar`. Una fila por batalla única
de Trophy Road (`type = PvP`, `gameMode = Ladder`), ordenada por hora.

| Columna | Tipo | Unidad / valores | Descripción |
|---|---|---|---|
| `batalla` | texto | `battleTime\|tag\|tag` | Id de la batalla: hora más los dos tags ordenados |
| `battle_time_utc` | texto | `YYYYMMDDTHHMMSS.000Z`, UTC | Hora de la batalla según la API |
| `tipo` | texto | `PvP` | Tipo de batalla |
| `modo` | texto | `Ladder` | Modo de juego |
| `arena_id` | entero | id de la API | Arena |
| `j1`, `j2` | texto | `#TAG` | Tags de los jugadores (`team` y `opponent`) |
| `j*_trofeos_inicio` | entero | trofeos | Trofeos al iniciar la batalla |
| `j*_cambio` | entero | trofeos | Trofeos ganados o perdidos |
| `j*_coronas` | entero | 0–3 | Coronas obtenidas |
| `j*_nivel_rey` | entero | nivel | Nivel de la torre del rey |
| `j*_nivel_cartas_medio` | decimal | escala relativa | Nivel medio del mazo, `nivel + (16 − nivel_max)` |
| `dif_trofeos_abs` | entero | trofeos | `|j1_trofeos_inicio − j2_trofeos_inicio|` |

`j1` es el lado `team` del battlelog de quien se consultó; no implica nada sobre quién buscó
rival primero.

## Base SQLite (no se sube)

`data/raw/clash_royale.db`, tablas `jugadores`, `batallas` y `participantes`. Ver
`CONTEXTO_Y_HALLAZGOS.md`, sección 5.

## Procedencia

- API oficial de Clash Royale, vía `proxy.royaleapi.dev`.
- Período: 1 sep a 6 nov 2026 (UTC); el estudio usa principalmente 1–6 nov.
- Muestreo y bitácora de corridas: `decisiones.md` (D4) y `avances.md`.
