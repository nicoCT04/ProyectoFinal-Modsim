# Decisiones metodológicas

Cada decisión indica la fecha, qué se decidió y por qué.

## D1. Fuente: API oficial de Clash Royale (3 nov 2026)

Se usa `/v1/players/{tag}/battlelog`, que devuelve las últimas 30 batallas de cada jugador con los
trofeos al iniciar de **ambos** rivales. Con IP dinámica se usa el proxy de RoyaleAPI
(`CR_BASE_URL=https://proxy.royaleapi.dev`). Ver `CONTEXTO_Y_HALLAZGOS.md`, secciones 2 y 4.

## D2. Recolector con base SQLite en lugar de JSON por corrida (5 nov 2026)

`recolector_cr.py` reemplaza a `recolectar.py` (piloto) para la recolección del estudio:

- Una sola base (`data/raw/clash_royale.db`) que se puede reanudar y detener con Ctrl+C.
- Deduplica en el momento: el id de batalla es `battleTime` más los tags ordenados, así que la
  misma batalla vista desde los dos jugadores se guarda una vez.
- Solo biblioteca estándar.

`cliente.py` y `recolectar.py` se conservan como registro de la extracción piloto.

## D3. Filtro de Trophy Road (5 nov 2026)

Trophy Road = `type = "PvP"` y `gameMode.name = "Ladder"`. Verificado con una cuenta real.
Se excluyen guerras de clanes, eventos, desafíos y amistosas. Ranked queda fuera del modelo.

## D4. Muestreo: bola de nieve y luego panel fijo (5 nov 2026)

1. Semilla: una cuenta propia y 14 miembros del clan `#8G8C0` (5,000–12,000 trofeos).
2. Bola de nieve de 2 h: los rivales dentro de la franja 5,000–12,000 entran a la cola.
3. Panel fijo de 2,744 jugadores, estratificado por franjas de 1,000 trofeos (`panel --n 3000`,
   semilla 42).
4. Refresco del panel cada ~4 h hasta el 6 nov a mediodía (más de 24 h continuas).

Sesgo declarado: las franjas 7,000–9,999 quedaron con menos jugadores porque la semilla venía de
un clan de 5,000–7,000.

## D5. Perfil horario con las batallas del 1 al 4 de noviembre (revisada el 6 nov 2026)

Primero se propuso usar las batallas del panel posteriores a su creación. Se descartó por la
decisión D8: esas batallas se concentran justo antes de cada consulta. El perfil de llegadas por
hora se arma con las batallas de Trophy Road del 1 al 4 de noviembre (hora de Guatemala; 42,694
batallas), que quedaron lejos de cualquier consulta. El perfil sale suave: mínimo a la 1:00 y
máximo entre las 11:00 y las 13:00.

## D6. Ventanas fijas de referencia: ±20, ±40 y ±60 (5 nov 2026)

En 79,419 batallas la diferencia máxima fue 64 trofeos (media 10.8, P90 31). Las referencias
±100/±300/±600 del informe quedan fuera de rango; se cambian por ±20/±40/±60.

## D7. Tags sin anonimizar (5 nov 2026)

El equipo decidió no anonimizar: el CSV exporta los tags tal como los da la API, que son datos
públicos del juego. Así se puede rastrear cada batalla y jugador hasta la API. Se descarta
`CR_SALT`. La base SQLite no se sube por tamaño (~360 MB), no por privacidad.

## D8. Sesgo en las batallas cercanas a cada consulta (6 nov 2026)

Al refrescar el panel cada ~3.7 h, las batallas guardadas se concentran en los 30–60 min previos
a la consulta de cada jugador, y repiten ese patrón en cada ciclo. Esas batallas además tienen
diferencias de trofeos mucho menores:

| Período (hora de Guatemala) | Batallas | Media | Mediana | P90 | Máximo |
|---|---|---|---|---|---|
| 1–3 nov | 25,170 | 11.6 | 6 | 32 | 60 |
| 4 nov | 17,524 | 11.8 | 6 | 32 | 63 |
| 5–6 nov (con refrescos del panel) | 54,013 | 7.3 | 1 | 26 | 62 |
| 6 nov, 07:00–08:30 (cerca de una consulta) | 4,008 | 5.8 | 1 | 22 | 49 |

Lo que se descartó: no son batallas duplicadas (solo 41 casos con 1 s de diferencia); los rivales
son distintos y tienen cartas evolucionadas; solo ~3 % de los jugadores llena el límite de 30
batallas entre consultas. El mecanismo no está claro; se declara como limitación.

Consecuencia: las batallas del 5 y 6 de noviembre no se usan ni para calibrar ni para el perfil
horario. **Ajuste: 1–3 nov. Validación (reservado): 4 nov.** El pico de 8:00–9:00 del 5 nov
(sección 7.2 del contexto) es el mismo fenómeno, causado por la primera corrida.

## D9. Filtros y parámetros del estudio (6 nov 2026)

- **Franja:** se conservan las batallas en que **ambos** jugadores están en 5,000–11,999 trofeos
  (se excluyen 2,348). La franja de una batalla es la de su promedio de trofeos.
- **Duplicados:** misma pareja, mismos trofeos y cambio, con 2 s o menos de diferencia en
  `battleTime` (8 casos en 1–4 nov).
- **Trofeos de las solicitudes:** cada batalla de ajuste aporta los trofeos de sus dos jugadores
  (47,596 valores). Refleja la muestra, no la población: las franjas de 7,000–9,999 están
  subrepresentadas (D4).
- **Percentiles:** interpolación lineal, igual que `numpy.percentile` por defecto.
- **Referencias resultantes:** ajuste media 11.51, mediana 6, P90 32, P99 42, máximo 60;
  validación media 11.65, mediana 6, P90 32, P99 42, máximo 63.
