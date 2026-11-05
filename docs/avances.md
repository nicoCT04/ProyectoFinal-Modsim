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

Pendientes: corridas 3 a 6 (5 nov 14:00, 18:00, 22:00; 6 nov ~07:30 y 12:00), exportar el CSV.
