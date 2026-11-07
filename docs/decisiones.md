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

## D10. Umbrales del experimento, fijados antes de evaluar (6 nov 2026)

Se fijan antes de calibrar el simulador y de correr NSGA-II, para que no se ajusten a los resultados.

| Umbral | Valor | Justificación |
|---|---|---|
| **D_max**: diferencia media de trofeos máxima aceptable | **15 trofeos** | La referencia real (ajuste, 1–3 nov) es 11.5. Un margen de ~30 % deja espacio para el compromiso entre espera y equilibrio, y 15 trofeos es la mitad de lo que se gana en una victoria (~30), por lo que el jugador no percibe la diferencia. Sigue por debajo del P90 real (32). |
| **Cobertura mínima**: emparejadas / llegadas | **95 %** | Una política que deja sin rival a más de 1 de cada 20 solicitudes no es aceptable para el operador, aunque su espera media sea baja. Se mide sin contar las solicitudes que llegan en los primeros 600 s (cola vacía) ni en los últimos 300 s de la simulación (no alcanzan a emparejarse); el margen es el mismo para todas las políticas. |
| **Reducción relevante de la espera media** | **≥ 10 %** frente a la ventana fija de referencia **y** el intervalo de confianza del 95 % de la diferencia pareada excluye el 0 | Menos de 10 % es difícil de defender como mejora práctica. Las políticas se comparan con las mismas semillas (números aleatorios comunes), por lo que la diferencia se evalúa par a par en las 30 repeticiones. |

Una política adaptativa solo se declara mejor si cumple D_max y la cobertura mínima en el escenario
evaluado y además alcanza la reducción relevante. Si ninguna lo logra, se reporta así.

## D11. Escenario base: réplica calibrada con ventana creciente (6 nov 2026)

**Cambio respecto de la planificación.** La planificación proponía que el escenario base fuera una
ventana fija. Con el simulador se comprobó que **ninguna ventana fija reproduce los datos reales**:
con ±D la diferencia queda casi uniforme entre 0 y D (±60 da media ~28 con cualquier demanda),
mientras que la real tiene 25 % de ceros, mediana 6 y cola hasta ~42 (P99). Esa forma la produce
una ventana que crece con la espera. Por eso:

- **Base** = réplica del sistema real: Δ(w) = min(Δmax, Δ0 + α·w), calibrada.
- **Ventanas fijas ±20, ±40 y ±60** = políticas de referencia (lo que pregunta el informe).
- **Mejora** = políticas que encuentre NSGA-II, comparadas contra la base y contra las fijas.

**Unidad de tiempo.** Si la tasa de llegadas y α se multiplican por k, las diferencias no cambian
y las esperas se dividen entre k: los datos solo identifican α / tasa. Se fija
`tasa_media = 5 solicitudes/s` y se calibra α. Las esperas en segundos dependen de ese supuesto;
las comparaciones relativas entre políticas no. Si el equipo mide esperas reales con cronómetro
(espera media real W), se reescala multiplicando tasa y α por (espera simulada de la base / W).

**Calibración** (`python -m src.matchmaking.simulacion.calibrar`, `results/calibracion.json`):
rejilla de α ∈ {1.25, …, 3} y Δmax ∈ {44, …, 64}, Δ0 = 0, dos días simulados por punto contra
la distribución de 1–3 nov. Elegida: **Δ0 = 0, α = 1.75 trofeos/s, Δmax = 44 trofeos**.

**Validación contra el 4 nov** (cinco días simulados con semillas nuevas):

| Estadístico | Real | Simulado | Error |
|---|---|---|---|
| Media | 11.65 | 12.36 | +0.72 (+6 %) |
| Mediana | 6 | 9 | +3 |
| P75 | 21 | 19 | −2 |
| P90 | 32 | 29 | −3 |
| P95 | 37 | 35 | −2 |
| P99 | 42 | 42 | 0 |
| Proporción de ceros | 0.26 | 0.07 | −0.18 |
| Máximo | 63 | 44 | −19 |

MAE del histograma (cajas de 5 trofeos): 0.030. Kolmogórov-Smirnov: 0.20. MAE del perfil horario:
0.0001. La media y la cola se reproducen bien. El modelo **subestima las batallas con diferencia 0**:
en el juego hay muchos más jugadores con exactamente los mismos trofeos esperando a la vez de lo que
produce una muestra de 5 solicitudes/s. Los máximos de 60–64 son casos raros (menos del 1 %) que
una ventana de 44 no genera. Ambas cosas se declaran como limitación.


## D12. Configuración de la optimización (6 nov 2026)

Se fija antes de correr NSGA-II. Configuración en `configs/optimizacion.yaml`; la técnica está
documentada en `docs/tecnica_nsga2.md`.

| Elemento | Valor | Justificación |
|---|---|---|
| Variables | x = (Δ0, α, e), con Δmax = Δ0 + e | Toda x dentro de los límites es una política válida (Δ0 ≤ Δmax); no hay que reparar soluciones. |
| Límites | Δ0 ∈ [0, 40] trofeos; α ∈ [0.05, 10] trofeos/s; e ∈ [0, 80] trofeos | Incluyen a la base (0, 1.75, 44) y a las ventanas fijas ±20 y ±40; Δmax llega a 120, casi el triple del P99 real (42). |
| Objetivos | espera media y diferencia media, promedio de 3 semillas | Las dos métricas del compromiso (D10). |
| Restricciones | dif_media ≤ 15; cobertura ≥ 0.95 | D10. Si no se forma ninguna pareja (`nan`), la solución es infactible. |
| Escenario | `optimizacion` (10:00–14:00, tasa media 5/s) | ~1.5 s por corrida con la base; el día completo es demasiado lento para 3,000 simulaciones. |
| Semillas | evaluación 1000–1002 (iguales para todas); NSGA-II 1; búsqueda aleatoria 2 | Números aleatorios comunes; no se tocan las de calibración, validación ni experimentos. |
| Presupuesto | NSGA-II con población 40 y 25 generaciones = 1,000 evaluaciones; búsqueda aleatoria con 1,000 | Mismo presupuesto para comparar. |
| Operadores | SBX (p = 0.9, η = 15), mutación polinomial (η = 20), torneo binario | Valores por defecto de pymoo (Deb et al., 2002). |
| Hipervolumen | punto de referencia (60 s, 15 trofeos), sobre el frente factible de todas las evaluaciones | Mide la parte útil del frente: espera razonable y dentro de D_max. |
| Paralelización | `multiprocessing.Pool` con 11 procesos (`StarmapParallelization` de pymoo) | Tiempo real en una Mac de 12 núcleos: NSGA-II 12.5 min, búsqueda aleatoria 5.2 min. |

**Resultado.** Hipervolumen final: NSGA-II 540.07, búsqueda aleatoria 527.14 (+2.5 %). El de NSGA-II
deja de crecer desde la generación 17 (539.2 → 540.1), así que el presupuesto alcanzó. Las 344
políticas del frente de NSGA-II y las 88 del de la búsqueda aleatoria cumplen las restricciones al
volver a simularlas (`results/verificacion_*.csv`).

**Candidatas para los experimentos** (en `configs/escenarios.yaml`). Se eligieron dentro de la región
que responde la pregunta del estudio (espera ≤ la de la base en hora pico, 14.83 s); el codo es la
solución más cercana al punto ideal con los objetivos normalizados en esa región:

| Nombre | Δ0 | α | Δmax | Espera (opt.) | Dif. (opt.) | Criterio |
|---|---|---|---|---|---|---|
| `nsga_codo` | 18.70 | 0.564 | 39.54 | 11.13 | 10.99 | codo del frente |
| `nsga_menor_espera` | 20.83 | 1.322 | 75.32 | 8.64 | 14.96 | menor espera que cumple D_max |
| `nsga_intermedia` | 19.46 | 0.900 | 79.93 | 9.79 | 12.97 | menor espera con diferencia ≤ 13 |
| `nsga_menor_dif` | 15.23 | 0.198 | 35.17 | 14.73 | 7.95 | menor diferencia sin esperar más que la base |
| `aleatoria_mejor` | 17.64 | 0.659 | 92.83 | 10.99 | 11.29 | codo del frente aleatorio (control) |

**Hora pico frente a día completo.** En el escenario `optimizacion` la ventana fija ±20 domina a la
base (14.19 s y 8.74 trofeos frente a 14.83 s y 11.03). Con mucha demanda casi siempre hay un rival
cercano; la ventana creciente ayuda en las horas de poca demanda. Por eso las candidatas se validan
en el día completo y en baja demanda. Una vista previa con las semillas 1000–1002 (no sustituye a
los experimentos) muestra que `nsga_menor_espera` supera D_max fuera de la hora pico (16.5 en el día
completo, 20.2 en baja demanda) y que `nsga_codo` cumple y mejora a la base en los tres escenarios.
