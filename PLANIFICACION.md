# Planificación del proyecto

**Tema:** Ventanas adaptativas de trofeos para equilibrar la espera y la cercanía de nivel en el emparejamiento de Trophy Road (Clash Royale).

**Pregunta:** ¿qué criterio de ampliación de la ventana de trofeos reduce la espera media sin superar un límite de diferencia media de trofeos, frente a una ventana fija, bajo distintos niveles de demanda?

---

## 1. Idea metodológica (para que todos la expliquemos igual)

El sistema de colas de Supercell es una **caja negra**. La API no registra cuándo se pulsó "Batalla", cuánto se esperó ni quién más estaba en la cola. Por eso:

| Qué | De dónde sale | Tipo de dato |
|---|---|---|
| Distribución de trofeos de los jugadores | Battlelog de la API (`startingTrophies`) | Real observado |
| Perfil de actividad por hora | Hora de las batallas (`battleTime`) | Real observado (forma relativa) |
| Diferencia de trofeos entre rivales | `team.startingTrophies` contra `opponent.startingTrophies` | **Real observado, se usa para validar** |
| Tasa absoluta de llegadas a la cola | No se observa: solo vemos una muestra de jugadores | Escenarios (baja, media, alta) más sensibilidad |
| Tiempo de espera, P95, cobertura y pendientes | No se observan | **Resultado exclusivo de la simulación** |

- **Escenario base:** ventana fija `Δ(w) = Δ_fija`. Se calibra con días de entrenamiento para que la diferencia de trofeos simulada se parezca a la observada.
- **Mejora:** ventana adaptativa `Δ(w) = min(Δ_max, Δ_0 + α·w)`, con `(Δ_0, α, Δ_max)` elegidos por NSGA-II.
- **Comparación real (Parte 6):** diferencia de trofeos y batallas por hora, observadas en **días reservados** contra la simulación base y la mejorada (MAE y diferencia de cuantiles). La espera se reporta como "no observada" y se declara la limitación.
- **Controles adicionales:** ventanas fijas estrecha, intermedia y amplia, y una búsqueda aleatoria con el mismo número de evaluaciones que NSGA-II.

---

## 2. Roles

Cada rol tiene un responsable y un revisor. El revisor lee y prueba el trabajo antes de unirlo a `main`.

| Rol | Responsable | Partes del enunciado | Puntos en la rúbrica | Revisor |
|---|---|---|---|---|
| **R1. Datos y validación real** | José Donado | 1 (fuentes), 6 | 4 + 6 | Daniela |
| **R2. Modelo de eventos discretos** | Daniela Ramírez | 3, 5 (verificación) | 5 + 7 | Nicolás |
| **R3. Técnica adicional (NSGA-II)** | Nicolás | 2, 4 | 5 + 6 | Gadiel |
| **R4. Experimentos y resultados** | Gadiel | 5, 7 | 5 + 4 | Donado |
| **R5. Informe, repositorio y presentación** | Todos (ver abajo) | Entregables y criterio 9 de la rúbrica | 8 | Todos |

> R5 se reparte: cada quien escribe en el informe la sección de su rol, y las tareas comunes están en la sección R5.

**Parte 1:** ya está cubierta en el informe actual (secciones 1 a 7), según la planificación de la primera parte que aparece ahí. Lo que sigue son las Partes 2 a 7.

### R1. Datos y validación real (Donado)
- Obtener la API key (va ligada a una IP) y **no subirla al repo** (`.env` en `.gitignore`).
- Muestreo: semilla de jugadores (rankings, clanes) y luego su `battlelog` (últimas 25 batallas). Documentar el muestreo, porque introduce sesgo.
- Filtrar solo batallas 1 contra 1 de Trophy Road, dentro de la franja de trofeos elegida. Documentar el período en UTC.
- Separar **días de ajuste** y **días reservados** para validar.
- Entregar `data/processed/parametros.json` con:
  - Cuantiles o distribución ajustada de los trofeos.
  - Perfil relativo de llegadas por hora (24 valores).
  - Distribución observada de `|r_i − r_j|`, por franja si aplica.
- Al final, armar la tabla de la Parte 6 (referencia real, base, mejorado) con cambio absoluto y porcentual.
- **Para el informe:** fuente, fecha, período, tamaño de muestra, filtros y limitaciones del muestreo.

### R2. Modelo de eventos discretos (Daniela)
- Simulador con eventos de llegada, revisión de la cola cada Δt y formación de parejas.
- Regla: revisar primero la solicitud más antigua y elegir al rival más cercano con `|r_i − r_j| ≤ min(Δ(w_i), Δ(w_j))`. Los empates se resuelven por antigüedad.
- Llegadas Poisson no homogéneas por franja horaria.
- **Interfaz única** que usan R3 y R4:
  ```python
  simular(politica: dict, escenario: dict, semilla: int) -> dict
  # devuelve: espera_media, espera_p95, dif_media, cobertura, pendientes, ...
  ```
- Pruebas de verificación (Parte 5):
  - Las solicitudes llegadas son iguales a 2 × parejas + pendientes.
  - Con una ventana infinita, la diferencia es la de emparejar al azar.
  - Con una ventana de 0 casi no se forman parejas.
  - La espera nunca es negativa.
  - La misma semilla da el mismo resultado.
- **Para el informe:** el diagrama, las variables, los parámetros, las unidades y el pseudocódigo.

### R3. Técnica adicional: NSGA-II (Nicolás)
- Investigación (Parte 2): objetivo, representación `(Δ_0, α, Δ_max)`, operadores, parámetros, criterio de parada, 3 fuentes (Deb et al. 2002 más la documentación de pymoo) y 2 limitaciones.
- Implementar con `pymoo`. Los objetivos son minimizar la espera media y la diferencia media. Las restricciones son `D ≤ D_max` y `cobertura ≥ c_min`.
- Cada evaluación promedia varias semillas para reducir el ruido.
- Hacer una búsqueda aleatoria con el mismo número de evaluaciones, como control.
- Escribir en el informe qué hace pymoo y qué programamos nosotros (lo pide el enunciado).
- Entregar `results/pareto.csv` con las políticas candidatas.

### R4. Experimentos y resultados (Gadiel)
- **Antes de correr el experimento final**, fijar y escribir `D_max`, la cobertura mínima y la reducción de espera que consideramos relevante.
- Escenarios:
  - Ventanas fijas estrecha, intermedia y amplia.
  - Políticas adaptativas del frente de Pareto.
  - Sensibilidad con demanda baja, media y alta, y con otra frecuencia de revisión.
- 30 repeticiones por condición con **semillas nuevas** (distintas de las que usó NSGA-II), reportando la media, la desviación y el intervalo de confianza del 95%.
- Gráficas mínimas:
  1. La cola en el tiempo.
  2. El frente de Pareto contra las ventanas fijas.
  3. La sensibilidad a la demanda o el error.
- Responder: qué mejoró, cuánto, bajo qué condiciones, qué tan confiable es y qué limitaciones quedan.

### R5. Informe, repositorio y presentación (todos)
| Tarea | Quién |
|---|---|
| Correcciones pendientes del informe (lista abajo) | Donado |
| README desde un entorno limpio, `requirements.txt` y un comando para correr todo | Daniela |
| Integración final del informe y referencias en un solo formato | Nicolás |
| Presentación y ensayo cronometrado | Gadiel |
| Registro de contribuciones | Cada quien escribe la suya |

**Correcciones pendientes del informe actual:**
- La portada solo tiene a Donado y a Daniela; faltan Nicolás y Gadiel con su carné.
- Algunos subíndices salen como cuadros (`r□`, `D□ax`, `Δ□ax`, `w□`) en la tabla de métricas y en las secciones 4 y 6. Escribirlos con el editor de ecuaciones o como `D_max` y `r_j`.
- El índice no incluye las secciones 4 a 7.
- La tabla "Planificación de la primera parte" todavía dice "Integrante 1–4" en la columna Revisor.

**Presentación (15 min):** 2 de problema (Donado), 2 de modelo (Daniela), 3 de técnica (Nicolás), 3 de demo (Daniela y Nicolás), 3 de resultados y validación (Gadiel y Donado) y 2 de conclusiones (Gadiel).

---

## 3. Flujo de trabajo y dependencias

```
R1 datos ──► parametros.json ──┐
                               ▼
R2 modelo (empieza con parámetros inventados) ──► simular()
                                                       │
                     ┌─────────────────────────────────┤
                     ▼                                 ▼
          R3 NSGA-II ──► pareto.csv ──► R4 experimentos finales ──► tablas y gráficas
                                                       │
R1 tabla de la Parte 6 ◄───────────────────────────────┘
R5 integra todo en el informe, el README y la presentación
```

**Para no bloquearnos:** R2 arranca ya con parámetros sintéticos (trofeos normales y tasa constante). R3 y R4 programan contra `simular()` con esos mismos parámetros. Cuando R1 entregue `parametros.json`, solo se cambia el archivo de entrada.

### Hitos

| Hito | Qué tiene que estar | Responsable |
|---|---|---|
| H1 | Correcciones del informe; umbrales `D_max` y cobertura propuestos | Donado, todos |
| H2 | Extracción de prueba de la API; `simular()` funcionando con datos sintéticos y pruebas pasando | R1, R2 |
| H3 | `parametros.json` real; ventana fija calibrada contra los días de ajuste | R1, R2 |
| H4 | NSGA-II y búsqueda aleatoria corriendo; `pareto.csv` | R3 |
| H5 | Experimento final (30 repeticiones), tabla de la Parte 6, gráficas | R4, R1 |
| H6 | Informe, README reproducible, presentación ensayada en menos de 15 min | R5, todos |

---

## 4. Estructura propuesta del repositorio

```
ProyectoFinal-Modsim/
├── README.md
├── requirements.txt
├── .env.example            # CR_API_KEY=... (la clave real nunca se sube)
├── data/
│   ├── raw/                # extracciones de la API (o el script para regenerarlas)
│   └── processed/parametros.json
├── src/
│   ├── datos/              # R1: extracción, limpieza, ajuste de distribuciones
│   ├── modelo/             # R2: simulador de eventos discretos y políticas
│   ├── optimizacion/       # R3: NSGA-II y búsqueda aleatoria
│   └── experimentos/       # R4: escenarios, repeticiones, gráficas
├── tests/                  # R2: pruebas de verificación
├── results/                # CSV y figuras generadas
└── docs/                   # informe y presentación
```

**Convención de ramas:** una rama por rol (`datos`, `modelo`, `optimizacion`, `experimentos`), con un PR a `main` que aprueba el revisor.

---

## 5. Pendientes por decidir en grupo
- [ ] Franja de trofeos a estudiar (el informe propone 5,000 a 12,000; se fija tras la extracción de prueba).
- [ ] Período de datos y qué días quedan reservados.
- [ ] Simulador con SimPy o con un ciclo de eventos propio (`heapq`).
- [ ] Valores de `D_max`, la cobertura mínima y la reducción relevante de espera, fijados **antes** del experimento final.
- [ ] Fecha de entrega real (la portada dice 9 de noviembre de 2026).
