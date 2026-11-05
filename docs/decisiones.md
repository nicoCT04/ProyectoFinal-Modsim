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

## D5. Perfil horario solo con batallas posteriores a la creación del panel (5 nov 2026)

Hay un pico artificial entre las 8:00 y las 9:00 (Guatemala) porque fue cuando corrió la bola de
nieve; el pico sigue apareciendo aunque se filtre solo al panel, porque el panel salió de los
jugadores encontrados en esa corrida. El perfil de llegadas por hora se arma con las batallas
del panel desde que se fijó (5 nov 10:17 Guatemala = `2026-11-05T16:17` UTC):

```
python -m src.matchmaking.datos.caracterizar --desde-perfil 2026-11-05T16:17
```

## D6. Ventanas fijas de referencia: ±20, ±40 y ±60 (5 nov 2026)

En 79,419 batallas la diferencia máxima fue 64 trofeos (media 10.8, P90 31). Las referencias
±100/±300/±600 del informe quedan fuera de rango; se cambian por ±20/±40/±60.

## D7. Tags sin anonimizar (5 nov 2026)

El equipo decidió no anonimizar: el CSV exporta los tags tal como los da la API, que son datos
públicos del juego. Así se puede rastrear cada batalla y jugador hasta la API. Se descarta
`CR_SALT`. La base SQLite no se sube por tamaño (~360 MB), no por privacidad.
