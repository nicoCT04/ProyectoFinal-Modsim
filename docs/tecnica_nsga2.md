# Técnica adicional: NSGA-II

Material para la Parte 2 del informe (investigación técnica). Código en
`src/matchmaking/optimizacion/`.

## 1. Objetivo del algoritmo

NSGA-II (*Non-dominated Sorting Genetic Algorithm II*, Deb et al., 2002) es un algoritmo genético
para problemas con varios objetivos en conflicto. No devuelve una sola solución, sino una
aproximación al **frente de Pareto**: el conjunto de soluciones en las que no se puede mejorar un
objetivo sin empeorar otro.

En este estudio busca políticas de emparejamiento Δ(w) = min(Δmax, Δ0 + α·w) que minimicen a la vez:

| Objetivo | Métrica del simulador | Unidad |
|---|---|---|
| f1 | espera media de las solicitudes emparejadas | s |
| f2 | diferencia media de trofeos entre rivales | trofeos |

Las dos métricas se contraponen: una ventana más amplia empareja antes, pero con rivales más
lejanos. Sujeto a los umbrales de D10:

| Restricción (forma g ≤ 0) | Significado |
|---|---|
| g1 = f2 − 15 ≤ 0 | diferencia media de 15 trofeos como máximo (D_max) |
| g2 = 0.95 − cobertura ≤ 0 | al menos el 95 % de las solicitudes medidas encuentra rival |

## 2. Representación de las soluciones

Cada individuo es un vector real de tres variables:

| Variable | Límites | Unidad | Significado |
|---|---|---|---|
| Δ0 | [0, 40] | trofeos | ventana inicial |
| α | [0.05, 10] | trofeos/s | velocidad de ampliación |
| e | [0, 80] | trofeos | ampliación total permitida |

La política se decodifica como **Δmax = Δ0 + e**. Con esta codificación cualquier vector dentro de
los límites es una política válida (Δ0 ≤ Δmax siempre), así que no hace falta reparar ni descartar
individuos. Los límites incluyen a la base calibrada (0, 1.75, e = 44) y a las ventanas fijas ±20
y ±40 (e = 0); el tope de 40 + 80 = 120 trofeos de Δmax es casi el triple del P99 real de la
diferencia (42).

## 3. Procedimiento de búsqueda

1. **Población inicial.** N vectores al azar, uniformes dentro de los límites.
2. **Evaluación.** Cada vector se decodifica y se simula con las semillas 1000, 1001 y 1002 en el
   escenario `optimizacion`. f1, f2 y la cobertura son el promedio de las tres corridas.
3. **Ordenamiento no dominado.** La población se divide en frentes: el frente 1 son las soluciones
   que ninguna otra domina; el frente 2, las que solo domina el frente 1, y así sucesivamente.
4. **Distancia de hacinamiento.** Dentro de cada frente se mide qué tan aislada está cada solución
   de sus vecinas en el espacio de objetivos. Se prefieren las más aisladas, para cubrir todo el
   frente y no solo una parte.
5. **Selección por torneo binario.** Se comparan dos individuos al azar; gana el de mejor frente y,
   si empatan, el de mayor distancia de hacinamiento.
6. **Cruce SBX** (*Simulated Binary Crossover*): combina dos padres para producir hijos cerca de
   ellos, con una dispersión controlada por el índice η.
7. **Mutación polinomial:** perturba cada variable con una distribución cuya forma también controla
   un índice η.
8. **Supervivencia elitista.** Padres e hijos se juntan (2N) y pasan los N mejores según frente y
   hacinamiento. Una buena solución no se pierde de una generación a otra.
9. Se repiten los pasos 3 a 8 hasta cumplir el criterio de terminación.

**Restricciones.** NSGA-II usa la *dominancia con restricciones* de Deb et al. (2002): una solución
factible siempre gana a una infactible; entre dos infactibles gana la que viola menos las
restricciones; entre dos factibles se aplica la dominancia normal. Si una política no forma ninguna
pareja, el simulador devuelve `nan`; esa solución se marca con f = (10⁶, 10⁶) y g = (10⁶, 10⁶)
para que quede al fondo.

## 4. Parámetros

| Parámetro | Valor | Justificación |
|---|---|---|
| Tamaño de población N | 40 | Con 3 variables basta para cubrir el frente; Deb et al. usan 100 para problemas de prueba de hasta 30 variables. |
| Generaciones | 25 | 40 × 25 = 1,000 evaluaciones × 3 semillas = 3,000 simulaciones, que caben en el tiempo de cómputo del equipo. |
| Cruce SBX | probabilidad 0.9, η = 15 | Valores por defecto de pymoo, los recomendados por Deb et al. |
| Mutación polinomial | η = 20, probabilidad 1/n por variable | Valores por defecto de pymoo. |
| Semillas de evaluación | 1000, 1001, 1002 | Las mismas para todas las soluciones (números aleatorios comunes): dos políticas se comparan con las mismas solicitudes. |
| Semilla del algoritmo | 1 | Hace reproducible la población inicial y los operadores. |

## 5. Criterio de terminación

Un número fijo de **25 generaciones**. Se prefiere a un criterio de convergencia porque fija el
presupuesto de antemano y permite comparar con la búsqueda aleatoria al mismo número de
evaluaciones (1,000). La convergencia se revisa después con el hipervolumen por generación
(`results/nsga2_historial.csv`): si deja de crecer en las últimas generaciones, el presupuesto fue
suficiente.

**Hipervolumen.** Es el área del espacio de objetivos que domina el frente factible, medida hasta un
punto de referencia fijo: espera = 60 s y diferencia = 15 trofeos (el límite D_max). Más área
significa un frente mejor. Es la medida con la que se comparan NSGA-II y la búsqueda aleatoria.

## 6. Por qué NSGA-II y no otra alternativa

| Alternativa | Por qué no se eligió |
|---|---|
| Suma ponderada (w·f1 + (1 − w)·f2) con un algoritmo genético simple | Da una sola solución por corrida y hay que elegir los pesos antes, aunque las unidades (segundos y trofeos) no son comparables. Para reconstruir el frente habría que correrlo muchas veces, y no encuentra las partes no convexas del frente. |
| Búsqueda en rejilla | Con 3 variables continuas, una rejilla de 10 valores por variable ya son 1,000 evaluaciones y deja huecos de 4 trofeos y 1 trofeo/s. NSGA-II gasta el mismo presupuesto concentrándose en las zonas prometedoras. |
| Búsqueda aleatoria | Se incluye como **control** con el mismo presupuesto, para medir cuánto aporta NSGA-II. |

NSGA-II es además el algoritmo multiobjetivo más usado y tiene una implementación mantenida y
documentada en pymoo (Blank y Deb, 2020).

## 7. Limitaciones y casos en los que puede fallar

1. **Ruido de la simulación.** Cada evaluación es estocástica. Si dos políticas difieren menos que
   el ruido, el ordenamiento entre ellas puede ser falso. Se mitiga promediando 3 semillas y con
   números aleatorios comunes; en el escenario `optimizacion` la variación entre semillas es menor
   al 1 %. Aun así, el frente se vuelve a evaluar después con semillas independientes (las de los
   experimentos finales).
2. **Presupuesto pequeño.** 1,000 evaluaciones pueden no bastar para que el frente converja. NSGA-II
   no garantiza encontrar el frente de Pareto verdadero, solo una aproximación. El historial de
   hipervolumen y la comparación con la búsqueda aleatoria indican si el presupuesto alcanzó.
3. **Dependencia del escenario.** El frente se busca en 4 horas de máxima demanda (10:00–14:00).
   Con mucha demanda casi siempre hay un rival cercano, así que la ampliación de la ventana pesa
   poco; en las horas de poca demanda pesa mucho más. Una política óptima en hora pico puede no
   serlo en el día completo ni en el escenario de baja demanda. Por eso las candidatas se validan
   en esos escenarios.
4. **Forma de la política.** NSGA-II solo busca dentro de la familia lineal con tope
   Δ0 + α·w. Si una forma distinta (por ejemplo, por escalones) fuera mejor, este estudio no la
   encontraría.

## 8. Qué hace pymoo y qué programó el equipo

| Lo hace pymoo | Lo programó el equipo |
|---|---|
| Ordenamiento no dominado | Simulador de eventos discretos (`simulacion/`) |
| Distancia de hacinamiento | Problema de optimización (`problema.py`): codificación (Δ0, α, e) → política, función de evaluación que promedia semillas, restricciones y manejo de `nan` |
| Selección por torneo, cruce SBX y mutación polinomial | Ejecución de NSGA-II con paralelización y registro del hipervolumen por generación (`nsga2.py`) |
| Dominancia con restricciones | Búsqueda aleatoria de control con el mismo presupuesto (`aleatoria.py`) |
| Cálculo del hipervolumen | Verificación de que las políticas del frente cumplen las restricciones y pruebas (`tests/test_optimizacion.py`) |

## Fuentes

- Deb, K., Pratap, A., Agarwal, S., & Meyarivan, T. (2002). A fast and elitist multiobjective
  genetic algorithm: NSGA-II. *IEEE Transactions on Evolutionary Computation, 6*(2), 182–197.
- Blank, J., & Deb, K. (2020). pymoo: Multi-objective optimization in Python. *IEEE Access, 8*,
  89497–89509.
- pymoo. (s.f.). NSGA-II. https://pymoo.org/algorithms/moo/nsga2.html
