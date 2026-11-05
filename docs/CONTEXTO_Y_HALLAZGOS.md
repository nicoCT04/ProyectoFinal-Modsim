# Proyecto 2 – Emparejamiento en Clash Royale: contexto y hallazgos

**Curso:** CC3074 Modelización y Simulación – UVG 2026
**Última actualización:** 5 de noviembre de 2026
**Propósito de este documento:** reunir las decisiones tomadas, los datos recolectados y lo que descubrimos hasta ahora, para integrarlo al repositorio y al informe.

---

## 1. Título y pregunta de investigación

**Título propuesto:**
> Evaluación de ventanas adaptativas de trofeos para equilibrar espera y equilibrio competitivo en el sistema de emparejamiento de Clash Royale

Se usa "trofeos" en lugar de "rating" porque es la medida que usa Clash Royale y la que traen los datos.

**Pregunta de investigación:** ¿qué criterio de ampliación de la ventana de trofeos permite reducir el tiempo medio de espera, sin superar un límite predefinido de diferencia media de trofeos entre rivales, frente a un criterio de ventana fija, en una simulación del emparejamiento de Trophy Road bajo distintos niveles de demanda?

**Dilema que resuelve el modelo:** si el sistema empareja rápido, las batallas salen desbalanceadas; si espera a encontrar rivales parejos, los jugadores esperan más.

---

## 2. Cómo llegamos a Clash Royale

El proyecto empezó con Lichess (ajedrez). Se evaluaron varias fuentes y se eligió Clash Royale por ser popular, tener API oficial y gratuita, y porque cada batalla trae los trofeos de **ambos** jugadores.

| Opción | Resultado de la evaluación |
|---|---|
| Lichess | Datos excelentes (CC0), pero solo 1v1 de ajedrez y poco llamativo. Fue la idea original. |
| League of Legends | MMR oculto y API con límites estrictos. Descartado. |
| Valorant | La API de partidas exige clave de producción y consentimiento de cada jugador. Descartado. |
| Overwatch | No hay API oficial ni historial de partidas. Descartado. |
| CS2 (FACEIT) | API gratis, pero el ELO no viene partida a partida y requiere recolector. Viable, pero más débil. |
| Deadlock | Volcados abiertos de la comunidad. Buena alternativa, pero no oficial. |
| **Clash Royale** | **API oficial y gratuita, trofeos de ambos jugadores al iniciar cada batalla, nivel de cartas. Elegido.** |

---

## 3. Contexto del juego (relevante para el modelo)

- **Trophy Road** es el modo principal: batallas 1 contra 1, se ganan trofeos al vencer y se pierden al perder. Desde marzo de 2026 llega hasta 14,000 trofeos.
- **Ranked** es un modo separado, por ligas y victorias. Se desbloquea con 13,500 trofeos en septiembre–octubre de 2026 y con 14,000 desde noviembre. **Queda fuera del modelo.**
- Según la información publicada, el emparejamiento de Trophy Road **busca rivales con trofeos similares y no usa el mazo ni el nivel de cartas**.
  - *Pendiente:* reemplazar la fuente actual (un blog que cita el soporte de Supercell) por el artículo oficial de Supercell Support antes de entregar.

---

## 4. Fuente de datos: API oficial de Clash Royale

- **Portal:** https://developer.clashroyale.com (clave gratuita, atada a direcciones IP).
- **Proxy usado para IP dinámica:** https://proxy.royaleapi.dev, con la IP `45.79.218.79` registrada en la clave. Es un proxy de la comunidad (RoyaleAPI); la clave solo da acceso de lectura a datos públicos.
- **Endpoint principal:** `/v1/players/{tag}/battlelog`. Devuelve las **últimas 30 batallas** de cada jugador. Por cada batalla trae:
  - `battleTime` (UTC), `type`, `gameMode`, `arena`
  - Por jugador: `startingTrophies`, `trophyChange`, `crowns`, `kingTowerLevel`, cartas con su nivel
- **Trophy Road se identifica como `type = PvP` y `gameMode = Ladder`.** Lo verificamos con una cuenta real.
- Los tags de Supercell **nunca usan la letra O**; siempre es cero.
- **Velocidad real observada:** cerca de **1 solicitud por segundo**, limitada por el tiempo de respuesta de la red.

---

## 5. El recolector (`recolector_cr.py`)

Script en Python que usa solo la biblioteca estándar. Guarda todo en una base SQLite (`clash_royale.db`) y se puede detener con Ctrl+C sin perder datos.

| Comando | Qué hace |
|---|---|
| `probar --tag "#TAG"` | Verifica la clave y muestra los tipos y modos de batalla de un jugador. |
| `semilla --tags ... --clanes ...` | Agrega jugadores iniciales, sea por tag o por los miembros de un clan. |
| `semilla --buscar-clanes --min-miembros 40` | Agrega miembros de clanes encontrados por la API. |
| `recolectar --minutos N` | Descarga batallas; agrega a la cola a los rivales dentro de la franja de trofeos (*bola de nieve*). |
| `panel --n 3000` | Elige un panel fijo de jugadores ya consultados, estratificado por franjas de 1,000 trofeos. |
| `recolectar --solo-panel --minutos 60 --refrescar-horas 3` | Solo refresca el panel, sin agregar jugadores nuevos. |
| `resumen` | Muestra conteos por modo, por franja de trofeos y el rango de fechas. |
| `exportar` | Genera `datos_exportados/batallas.csv` con los tags anonimizados (HMAC con `CR_SALT`). |

**Variables de entorno:** `CR_API_TOKEN` (la clave), `CR_BASE_URL` (para usar el proxy) y `CR_SALT` (texto secreto para anonimizar).

**Estructura de la base:**
- `jugadores`: tag, trofeos, origen, fecha de la última consulta, número de consultas y si pertenece al panel.
- `batallas`: id, hora, tipo, modo, arena y la marca `es_ladder`.
- `participantes`: id de la batalla, lado (`team` u `opponent`), tag, trofeos al iniciar, cambio de trofeos, coronas, nivel del rey y cartas en JSON.

Una misma batalla vista desde los dos jugadores se guarda una sola vez: el id es la hora más los tags ordenados.

---

## 6. Recolección realizada (5 de noviembre de 2026)

**Semilla:** una cuenta propia (8,815 trofeos) más 14 miembros del clan `#8G8C0` en la franja de 5,000–12,000.

**Primera corrida (2 horas, de 07:58 a 09:58 hora de Guatemala):**

| Dato | Valor |
|---|---|
| Jugadores consultados | 6,977 |
| Jugadores en la base (incluye la cola sin consultar) | 138,045 |
| Batallas totales | 131,408 |
| **Batallas de Trophy Road** | **79,419** |
| Rango de fechas | 1 sep 2026 – 5 nov 2026 (la gran mayoría del 1 al 5 de noviembre) |
| Integridad de la base | Correcta; todas las batallas tienen sus dos participantes |
| Tamaño de la base | ~360 MB |

**Otros modos encontrados y excluidos:** guerras de clanes (`riverRacePvP`, `boatBattle`, `riverRaceDuel`), eventos y desafíos (`trail`), y amistosas (`friendly`).

**Panel creado** (`panel --n 3000`, semilla aleatoria 42): **2,744 jugadores**.

| Franja de trofeos | Disponibles | Elegidos |
|---|---|---|
| 5,000–5,999 | 1,759 | 428 |
| 6,000–6,999 | 1,575 | 428 |
| 7,000–7,999 | 312 | 312 |
| 8,000–8,999 | 303 | 303 |
| 9,000–9,999 | 417 | 417 |
| 10,000–10,999 | 709 | 428 |
| 11,000–11,999 | 1,052 | 428 |

Las franjas de 7,000 a 9,999 tenían menos jugadores disponibles porque la bola de nieve partió de un clan de 5,000–7,000. **Esto es sesgo de muestreo y se declara en el informe.**

### Bitácora de recolección

Horas en tiempo de Guatemala (UTC−6).

| # | Fecha | Hora | Comando | Consultados | Batallas nuevas | Notas |
|---|---|---|---|---|---|---|
| 1 | 5 nov 2026 | 07:58–09:58 | `recolectar --minutos 120` | 6,977 | 131,408 | Corrida inicial con bola de nieve desde la semilla. |
| — | 5 nov 2026 | 10:17 | `panel --n 3000` | — | — | Panel de 2,744 jugadores (semilla aleatoria 42). |
| 2 | 5 nov 2026 | ~12:00–12:10 | `recolectar --solo-panel --minutos 60 --refrescar-horas 4` | 343 | 486 | Solo se refrescaron los jugadores consultados antes de las ~08:30; el resto aún no cumplía 4 h. ≈1.4 batallas nuevas por jugador en 4 h. |

> Para agregar filas: anotar la fecha, la hora de inicio y fin, y copiar la línea final "Listo. Consultados: X. Batallas nuevas: Y" de cada corrida.

**Plan de cierre (sin esperar una semana):** refrescar el panel cada ~4 horas entre el 5 y el 6 de noviembre, hasta tener **más de 24 horas continuas** de batallas. La limitación (no hay diferencia entre días de semana y fin de semana) se declara.

---

## 7. Hallazgos principales

### 7.1 El emparejamiento real es muy estricto

Diferencia absoluta de trofeos entre rivales, en 79,419 batallas de Trophy Road:

| Estadístico | Valor |
|---|---|
| Media | **10.8 trofeos** |
| Mediana | 5 |
| Percentil 90 | 31 |
| Percentil 99 | 42 |
| **Máximo** | **64** |

**En ninguna batalla la diferencia superó 64 trofeos.** Esto sugiere que el juego usa una ventana máxima de unos ±60 trofeos. Es una inferencia de los datos, no algo publicado por Supercell.

### 7.2 Con menos jugadores, la diferencia aumenta

Batallas desde el 1 de noviembre, por franja de trofeos del jugador:

| Franja | n | Media | P90 | Máximo |
|---|---|---|---|---|
| 5,000 | 13,715 | 7.8 | 27 | 58 |
| 6,000 | 15,602 | 9.2 | 30 | 60 |
| 7,000 | 3,777 | 13.6 | 34 | 53 |
| 8,000 | 3,342 | 12.9 | 33 | 47 |
| 9,000 | 4,660 | 12.4 | 32 | 63 |
| 10,000 | 7,646 | 11.8 | 32 | 59 |
| 11,000 | 11,158 | 11.6 | 32 | 51 |
| 12,000 | 1,990 | 13.4 | 32 | 42 |
| 13,000 | 410 | 15.0 | 35 | 43 |

Por hora (Guatemala), la diferencia media ronda 11 al mediodía y sube a 12–13 en la noche.

**Esto respalda la hipótesis central del proyecto:** cuando hay menos jugadores disponibles, el sistema acepta rivales más alejados.

> ⚠️ **No usar todavía el perfil por hora de estos datos.** Hay un pico artificial entre las 8:00 y las 9:00 porque fue cuando corrió el recolector. El perfil por hora debe salir del panel con 24 horas o más de cobertura.

### 7.3 Los datos no traen el tiempo de espera

La API no registra cuánto esperó cada jugador en la cola, y **por eso se simula**: el tiempo de espera es una **salida del modelo**, no un dato observado.

---

## 8. Cómo se usa cada dato en el modelo

| Dato real | Uso en el modelo |
|---|---|
| Distribución de trofeos de los jugadores | **Entrada:** trofeos de cada solicitud simulada |
| Perfil de actividad por hora (del panel) | **Entrada:** forma de la tasa de llegadas por hora (Poisson no homogéneo) |
| Diferencia de trofeos entre rivales | **Validación y calibración:** el escenario base debe reproducir media ≈ 11, P90 ≈ 31 y máximo ≈ 64 |
| Patrón por franja (más diferencia con menos jugadores) | **Validación cualitativa** del mecanismo del modelo |
| Tiempo de espera | **Salida estimada** por la simulación |
| Nivel de cartas | Fuera del modelo base; posible extensión |

### 8.1 Simulación (eventos discretos)

1. Llegan solicitudes a la cola, cada una con sus trofeos y su hora de llegada.
2. Cada segundo simulado se revisa la cola, empezando por la solicitud más antigua, y se le busca el rival con trofeos más cercanos que cumpla
   `|r_i − r_j| ≤ min{Δ(w_i), Δ(w_j)}`
3. La ventana crece con la espera: `Δ(w) = min(Δmax, Δ0 + α·w)`.
4. Se registran la espera, la diferencia de trofeos, la cobertura y las solicitudes pendientes.

### 8.2 Calibración sin tiempos de espera

Tanto la demanda real como la regla real del juego son desconocidas. Lo que sí se observa es su resultado: la distribución de diferencias de trofeos. Por eso **se ajustan la tasa de llegadas y la regla base hasta reproducir esa distribución**. Con el modelo calibrado, las esperas simuladas son la mejor estimación disponible.

**Limitación a declarar:** dos valores desconocidos (demanda y velocidad de ampliación) ajustados con una sola distribución no quedan totalmente determinados.

### 8.3 Verificación externa barata (recomendada)

Cada integrante juega entre 15 y 20 partidas de Trophy Road y anota con cronómetro **los segundos hasta encontrar rival**, sus trofeos y la hora. No es una muestra representativa, pero da un **orden de magnitud real** contra el cual comparar las esperas que estima el modelo. Suma en la Parte 6 de la rúbrica.

### 8.4 Optimización

- **NSGA-II** (con `pymoo`) busca valores de (Δ0, α, Δmax) que minimicen a la vez la espera media y la diferencia media de trofeos.
- **Referencias de comparación (corregidas con los datos reales):** ventanas fijas de **±20, ±40 y ±60** trofeos, más una búsqueda aleatoria con el mismo presupuesto de evaluaciones.
- **Escenarios:** demanda base calibrada, baja demanda (como la madrugada o las franjas altas) y alta demanda.
- **30 repeticiones por condición**, con semillas registradas; se reportan media y desviación estándar.

---

## 9. Cambios necesarios en el informe

Ya se generó una versión del informe adaptada a Clash Royale (`Informe_Proyecto_2_MODSIM_ClashRoyale.docx`). Con los hallazgos del 5 de noviembre, hay que ajustar:

- [ ] Ventanas de referencia: cambiar ±100/±300/±600 por **±20/±40/±60**.
- [ ] Ejemplo del problema: cambiar "6,000 contra 6,250" por algo como **6,000 contra 6,050**.
- [ ] "Últimas 25 batallas" → **últimas 30 batallas**, si se menciona.
- [ ] Sección de validación: agregar los valores objetivo (media 10.8, P90 31, máximo 64) y el patrón por franja.
- [ ] Sección de fuentes: describir la recolección real (semilla, bola de nieve, panel estratificado, fechas y horas de corrida).
- [ ] Limitaciones: sesgo de muestreo hacia 5,000–7,000 trofeos, cobertura de un solo día para el perfil por hora, tiempo de espera no observado y calibración no única.
- [ ] Reemplazar la fuente sobre las reglas del emparejamiento por el artículo oficial de Supercell Support.
- [ ] Quitar la sección "Boletería bajo ataque", que pertenece a otro proyecto (si sigue en la versión del repositorio).
- [ ] Ajustar la declaración de uso de IA.

**Extensión opcional (solo si sobra tiempo):** detección de cuentas que suben o bajan trofeos a propósito (smurfs y *trophy dropping*), con CUSUM sobre las trayectorias del panel y el nivel de cartas en relación con los trofeos. Se valida con agentes sintéticos dentro de la simulación.

---

## 10. Qué subir al repositorio y qué no

**Sí subir:**
```
recolector/recolector_cr.py
datos/batallas.csv            # generado con "exportar", tags anonimizados
docs/CONTEXTO_Y_HALLAZGOS.md  # este documento
```

**No subir nunca:** agregar esto al `.gitignore`:
```
clash_royale.db
*.db
.env
```
La base tiene los tags reales de los jugadores. La clave de la API y `CR_SALT` tampoco deben aparecer en ningún archivo del repositorio.

**Nota sobre el tamaño:** si `batallas.csv` supera los 100 MB, GitHub lo rechaza. En ese caso, súbanlo comprimido (`.zip`) o filtrado al período de estudio.

---

## 11. Próximos pasos

| Tarea | Estado |
|---|---|
| Refrescar el panel cada ~4 h hasta el 6 de noviembre a mediodía | En curso (corrida 2 de ~6 hecha; próxima desde las 14:00) |
| Exportar el CSV anonimizado y subirlo al repositorio | Pendiente (6 nov) |
| Medir tiempos de espera reales con cronómetro (15–20 partidas por integrante) | Pendiente |
| Programar el simulador de eventos discretos | Se puede empezar ya con los datos actuales |
| Calibrar el escenario base contra la distribución de diferencias | Después del simulador |
| Integrar NSGA-II (`pymoo`) y la búsqueda aleatoria | Después de la calibración |
| Experimentos: 3 escenarios × políticas × 30 repeticiones | Después |
| Actualizar el informe con los puntos de la sección 9 | Pendiente |

---

## Referencias

- Deb, K., Pratap, A., Agarwal, S., & Meyarivan, T. (2002). A fast and elitist multiobjective genetic algorithm: NSGA-II. *IEEE Transactions on Evolutionary Computation, 6*(2), 182–197.
- Blank, J., & Deb, K. (2020). pymoo: Multi-objective optimization in Python. *IEEE Access, 8*, 89497–89509.
- Supercell. Clash Royale API. https://developer.clashroyale.com
- Supercell. Fan content policy. https://supercell.com/en/fan-content-policy/
- Supercell. (2026). March update 2026. https://supercell.com/en/games/clashroyale/blog/release-notes/march-update-2026/
- Supercell. (2026). Update to ranked trophy requirements. https://supercell.com/en/games/clashroyale/blog/news/update-to-ranked-trophy-requirements/
- RoyaleAPI. Proxy. https://docs.royaleapi.com/proxy
- RiggedRoyale. (2026). How Clash Royale matchmaking works in 2026. https://riggedroyale.com/blog/how-clash-royale-matchmaking-works *(reemplazar por la fuente oficial de Supercell Support)*
