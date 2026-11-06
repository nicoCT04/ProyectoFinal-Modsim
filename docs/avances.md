### Extracción piloto

- Fecha de ejecución: 03/11/2026 20:00
- Cantidad de jugadores consultados: 2
- Consultas exitosas y fallidas: 2 exitosa
- Cantidad de registros recuperados, antes de deduplicar: 3
- Tipos y modos observados: PvP y Ladder
- Disponibilidad de startingTrophies: 5116
- Siguiente tarea: identificar Trophy Road y procesar las batallas.

### Recolección del estudio (recolector SQLite)

Horas en tiempo de Guatemala (UTC−6). Datos de la última línea de cada corrida
("Listo. Consultados: X. Batallas nuevas: Y") y del `caracterizar` posterior.

| # | Fecha | Hora | Comando | Consultados | Batallas nuevas | Batallas totales | Trophy Road | Notas |
|---|---|---|---|---|---|---|---|---|
| 1 | 5 nov 2026 | 07:58–09:58 | `recolectar --minutos 120` | 6,977 | 131,408 | 131,408 | 79,419 | Bola de nieve desde la semilla. |
| — | 5 nov 2026 | 10:17 | `panel --n 3000` | — | — | — | — | Panel de 2,744 jugadores (semilla 42). |
| 2 | 5 nov 2026 | ~12:00–12:15 | `recolectar --solo-panel --minutos 60 --refrescar-horas 4` | 343 | 486 | 131,894 | 79,806 | Solo se refrescaron los consultados antes de ~08:30. |
| 3a | 5 nov 2026 | 14:06–14:21 | `recolectar --solo-panel --minutos 75 --refrescar-horas 3` | 1,143 | 3,269 | — | — | Se cortó al suspenderse la laptop (`RemoteDisconnected`); lo consultado quedó guardado. |
| 3b | 5 nov 2026 | 16:13–16:36 | `recolectar --solo-panel --minutos 75 --refrescar-horas 3` | 1,601 | 5,190 | 140,353 | 87,084 | Completa el panel (2,744). Ya con el arreglo de reintentos. |

| 4 | 5 nov 2026 | 20:53–21:32 | ciclo `recolectar --solo-panel --minutos 75 --refrescar-horas 2.5` cada 3 h | ≈2,744 | 7,121 | — | — | Primera vuelta del ciclo nocturno (`Downloads\corridas_nocturnas.log`). |
| 5 | 6 nov 2026 | 00:32–01:07 | ídem | 2,744 | 5,216 | — | — | Única vuelta cuya salida quedó en el log. |
| 6 | 6 nov 2026 | 04:07–04:44 | ídem | ≈2,744 | 5,141 | — | — | |
| 7 | 6 nov 2026 | 07:44–08:27 | ídem | ≈2,744 | 6,294 | — | — | |
| 8 | 6 nov 2026 | 11:27–12:07 | ídem | 2,744 | 6,578 | 170,703 | 114,079 | Última corrida. Integridad de la base: `quick_check` correcto. |

Las batallas nuevas de las corridas 4–8 salen de `recolectada_en` en la base; el log de PowerShell solo
guardó la salida de la corrida 5. "≈2,744": la corrida terminó en el tiempo esperado, pero la base solo
conserva la última consulta de cada jugador.

**Recolección cerrada el 6 nov 2026.** Ver la decisión D8 sobre el sesgo cerca de cada consulta.
