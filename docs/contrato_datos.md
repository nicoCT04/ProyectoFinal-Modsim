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

## `data/processed/batallas_estudio.csv`

Generado con `python -m src.matchmaking.datos.procesar`. Subconjunto limpio de `batallas.csv`
(filtros en `decisiones.md`, D9); las exclusiones por motivo están en `calidad_datos.json`.

| Columna | Tipo | Unidad / valores | Descripción |
|---|---|---|---|
| `batalla`, `battle_time_utc`, `j1`, `j2` | texto | igual que en `batallas.csv` | Identificación |
| `fecha_gt`, `hora_gt` | texto, entero | fecha y hora 0–23 de Guatemala (UTC−6) | Momento de la batalla |
| `conjunto` | texto | `ajuste` (1–3 nov) o `validacion` (4 nov) | Uso en el estudio |
| `j*_trofeos_inicio`, `j*_cambio` | entero | trofeos | Igual que en `batallas.csv` |
| `trofeos_medios` | decimal | trofeos | Promedio de los dos jugadores |
| `franja` | entero | 5000, 6000, …, 11000 | Franja de 1,000 de `trofeos_medios` |
| `dif_trofeos_abs` | entero | trofeos | `|j1_trofeos_inicio − j2_trofeos_inicio|` |

## `data/processed/parametros.json`

Generado con `python -m src.matchmaking.datos.caracterizar`. Entrada del simulador.

| Clave | Contenido | Uso |
|---|---|---|
| `metadatos` | Fuente, conjuntos, unidades y tipo de dato (real, forma relativa o no observado) | Trazabilidad en el informe |
| `trofeos_solicitudes.cuantiles` | 101 cuantiles (P0–P100) de los trofeos de ambos jugadores en ajuste | Muestrear trofeos: `u ~ U(0,1)`, interpolar `100u` |
| `trofeos_solicitudes.proporcion_por_franja` | Proporción por franja de 1,000 | Escenarios por franja |
| `perfil_horario.peso` | 24 pesos que suman 1 (índice 0 = 00:00–00:59 de Guatemala) | Forma de la tasa de llegadas no homogénea |
| `diferencias_referencia.ajuste` | n, media, desviación, mediana, P75–P99, máximo, proporción de ceros, histograma de 5 en 5, por franja y media por hora | Calibrar el escenario base |
| `diferencias_referencia.validacion` | Lo mismo para el 4 nov | Referencia real de la Parte 6 |

La tasa absoluta de llegadas y el tiempo de espera **no** están en el archivo: no se observan.

## Base SQLite (no se sube)

`data/raw/clash_royale.db`, tablas `jugadores`, `batallas` y `participantes`. Ver
`CONTEXTO_Y_HALLAZGOS.md`, sección 5.

## Procedencia

- API oficial de Clash Royale, vía `proxy.royaleapi.dev`.
- Período: 1 sep a 6 nov 2026 (UTC); el estudio usa principalmente 1–6 nov.
- Muestreo y bitácora de corridas: `decisiones.md` (D4) y `avances.md`.
