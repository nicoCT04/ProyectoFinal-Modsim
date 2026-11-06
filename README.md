# Matchmaking adaptativo en Clash Royale

Proyecto del curso de Modelación y Simulación.

El objetivo es evaluar políticas que amplían la ventana de trofeos conforme aumenta la espera, buscando equilibrar el tiempo de emparejamiento y la diferencia de trofeos entre rivales.

Se utilizará simulación de eventos discretos y optimización multiobjetivo mediante NSGA-II.

## Estado actual

- [x] Estructura modular del repositorio.
- [x] Cliente para consultar la API oficial.
- [x] Recolector de historiales de varios jugadores.
- [x] Almacenamiento de respuestas originales y resumen de consultas.
- [x] Primera consulta exitosa; la cuenta consultada devolvió un historial vacío.
- [x] Identificar Trophy Road: `type = PvP` y `gameMode = Ladder`.
- [x] Recolector con base SQLite, deduplicación y panel fijo (`recolector_cr.py`).
- [x] Primera recolección: 131,408 batallas, 79,419 de Trophy Road (5 nov 2026).
- [x] Refrescar el panel cada ~4 h hasta el 6 nov a mediodía (8 corridas, ver `docs/avances.md`).
- [x] Exportar `data/processed/batallas.csv` (114,079 batallas de Trophy Road).
- [x] Generar `parametros.json`: ajuste 1–3 nov, validación 4 nov (ver `docs/decisiones.md`, D5, D8 y D9).
- [x] Implementar el simulador, verificarlo y calibrarlo (`docs/modelo.md`).
- [ ] Integrar NSGA-II.
- [ ] Ejecutar experimentos y validación.
- [ ] Generar tablas y gráficas.

Los archivos creados para los módulos pendientes pueden estar vacíos.

## Recolección del estudio

La recolección usa `src/matchmaking/datos/recolector_cr.py` (solo biblioteca estándar, base
SQLite en `data/raw/`). Los comandos, el calendario de corridas y el cierre están en
[`docs/guia_recoleccion.md`](docs/guia_recoleccion.md); el contexto y los hallazgos, en
[`docs/CONTEXTO_Y_HALLAZGOS.md`](docs/CONTEXTO_Y_HALLAZGOS.md).

```powershell
python -m src.matchmaking.datos.recolector_cr resumen
python -m src.matchmaking.datos.diagnostico_db
```

Las secciones siguientes describen la extracción piloto con `recolectar.py`, que se conserva
como registro pero ya no se usa para el estudio.

## Organización del código

| Ruta | Responsabilidad |
|---|---|
| `src/matchmaking/datos/` | Consultas, recolección y procesamiento |
| `src/matchmaking/simulacion/` | Llegadas, políticas y motor de eventos |
| `src/matchmaking/optimizacion/` | NSGA-II y búsqueda aleatoria |
| `src/matchmaking/analisis/` | Métricas, validación y gráficas |
| `src/matchmaking/experimentos/` | Ejecución de escenarios y repeticiones |
| `configs/` | Configuraciones de datos y experimentos |
| `tests/` | Pruebas de consistencia |
| `docs/` | Contratos, avances y decisiones |
| `results/` | Resultados de los experimentos |

## Preparación del entorno

Se necesita Python 3 y una clave de la API oficial:

https://developer.clashroyale.com/

Ejecutar los comandos desde la raíz del repositorio, donde está este README.

Crear un entorno virtual:

```powershell
python -m venv .venv
```

Instalar las dependencias utilizando el Python del entorno:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Este procedimiento no requiere activar el entorno virtual.

Las dependencias actuales son:

```text
requests
python-dotenv
```

## Configuración de la API

Crear un archivo `.env` en la raíz del repositorio:

```dotenv
CR_API_TOKEN=tu_token_real
```

La clave debe permitir la IP pública desde donde se ejecuta el recolector.

El archivo `.env` debe estar excluido mediante `.gitignore`.
No publicar claves en commits, capturas o registros.

El archivo `.env.example` contiene solamente el nombre de la variable:

```dotenv
CR_API_TOKEN=
```

## Recolectar datos

Consultar un jugador:

```powershell
.\.venv\Scripts\python.exe -m src.matchmaking.datos.recolectar "#ETIQUETA_REAL"
```

Consultar varios jugadores:

```powershell
.\.venv\Scripts\python.exe -m src.matchmaking.datos.recolectar "#ETIQUETA_1" "#ETIQUETA_2"
```

Reemplazar los ejemplos por etiquetas reales. Mantener las comillas
para que PowerShell interprete correctamente el carácter `#`.

Cada ejecución consulta una vez el historial de cada jugador y termina.
Todavía no hay ejecución periódica ni lectura de etiquetas desde un archivo.

## Archivos generados

Cada ejecución crea una carpeta dentro de `data/raw/`, identificada
por su fecha y hora UTC.

La carpeta contiene:

- `historial_0001.json`, etc.: respuestas originales con fecha de consulta
  y etiqueta del jugador.
- `resumen.json`: consultas exitosas, errores, cantidad de registros y
  tipos de batalla observados.

En `resumen.json`:

- `estado: "ok"` indica que la consulta fue exitosa.
- `registros: 0` indica que el historial devuelto está vacío.
- `estado: "error"` indica que ocurrió un problema durante la consulta.

Un historial vacío no se debe interpretar como una falla de conexión.

Los registros descargados todavía pueden incluir otros modos de juego
y batallas repetidas. No son aún el conjunto final del estudio.

## Problemas frecuentes

| Problema | Acción |
|---|---|
| Falta `CR_API_TOKEN` | Revisar `.env` y el nombre de la variable |
| HTTP 401 o 403 | Revisar token e IP pública autorizada |
| HTTP 404 | Comprobar la etiqueta del jugador |
| HTTP 429 | Revisar la frecuencia de consultas |
| Historial vacío | Probar con jugadores que hayan jugado recientemente |
| No se encuentra el módulo `src` | Ejecutar desde la raíz del repositorio |

## Preparación de los datos para el simulador

Dos pasos, desde la raíz del repositorio y sin dependencias externas:

```powershell
python -m src.matchmaking.datos.procesar
python -m src.matchmaking.datos.caracterizar
```

| Paso | Lee | Escribe |
|---|---|---|
| `procesar.py` | `data/processed/batallas.csv` | `batallas_estudio.csv` (40,338 batallas) y `calidad_datos.json` (exclusiones por motivo) |
| `caracterizar.py` | `batallas_estudio.csv` | `parametros.json`: trofeos de las solicitudes, perfil horario y diferencias de referencia |

Filtros: Trophy Road, ambos trofeos presentes, ambos jugadores en 5,000–11,999, días 1–4 de
noviembre (hora de Guatemala) y sin duplicados. **Ajuste: 1–3 nov. Validación: 4 nov.** La
estructura de cada archivo está en `docs/contrato_datos.md`.

Los trofeos faltantes no se reemplazan por cero; esas batallas se excluyen.

## Simulador

```powershell
.\.venv\Scripts\python.exe -m pytest                                  # verificación (21 pruebas)
.\.venv\Scripts\python.exe -m src.matchmaking.simulacion.calibrar     # calibración y validación (~10 min)
```

Uso desde Python:

```python
from src.matchmaking.simulacion.escenarios import cargar
from src.matchmaking.simulacion.motor import simular

cfg = cargar()
r = simular(cfg["politicas"]["base"], cfg["escenarios"]["base"], semilla=1)
print(r["espera_media"], r["dif_media"], r["cobertura"])
```

`politica` es `{"delta0", "alfa", "delta_max"}`; las de referencia, los escenarios y los umbrales
de D10 están en `configs/escenarios.yaml`. El modelo completo (diagrama, variables, unidades,
pseudocódigo y verificación) está en [`docs/modelo.md`](docs/modelo.md).

## Trabajo paralelo del equipo

Mientras se completa la recolección:

- Simulación: implementar el motor con solicitudes sintéticas identificadas.
- Optimización: preparar la evaluación de políticas usando el simulador.
- Análisis: preparar métricas y gráficas con resultados de prueba.
- Datos: obtener la muestra piloto y documentar los filtros.

La interfaz propuesta para integrar los módulos es:

```python
solicitudes = generar_solicitudes(escenario, semilla)

resultado = simular(
    solicitudes=solicitudes,
    politica=politica,
    configuracion=configuracion,
)
```

Las políticas comparadas deben recibir las mismas solicitudes dentro
de cada repetición experimental.

## Alcance de los datos y validación

Los historiales permiten observar trofeos, emparejamientos y actividad
de la muestra. No proporcionan directamente tiempos de espera ni
llegadas a la cola del servidor.

Por tanto:

- La diferencia de trofeos se contrastará con batallas reales reservadas.
- El perfil horario describe actividad observada de la muestra.
- La tasa absoluta de llegadas será un parámetro de escenario.
- La espera real requerirá mediciones propias adicionales.
- Las mejoras del simulador se reportarán como mejoras simuladas.

Los experimentos finales incluirán al menos 30 repeticiones independientes
por condición, registrando semillas, parámetros y resultados.

## Registro de avances

Cada PR debe indicar qué cambió, cómo ejecutarlo y qué evidencia produce.

Actualizar:

- `docs/avances.md`: resultados obtenidos y siguiente tarea.
- `docs/decisiones.md`: decisiones metodológicas y justificación.
- `docs/contrato_datos.md`: columnas, unidades, filtros y procedencia.

Los datos originales están excluidos de Git. Antes de compartir una
muestra, revisar los identificadores incluidos y documentar su tratamiento.

El repositorio deberá incluir datos autorizados o instrucciones de acceso,
además de configuraciones, semillas y resultados necesarios para reproducir
los experimentos.