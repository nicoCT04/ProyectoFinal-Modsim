# Guía de recolección (5–6 nov 2026)

Proceso para refrescar el panel cada ~4 h, registrar cada corrida y cerrar con el CSV exportado.

## 1. Preparación (una sola vez)

En la raíz del repositorio, crear `.env` a partir de `.env.example`:

```dotenv
CR_API_TOKEN=la_clave
CR_BASE_URL=https://proxy.royaleapi.dev
CR_SALT=texto_secreto_compartido_por_el_equipo
```

El recolector usa solo la biblioteca estándar; no hay que instalar nada.

## 2. Cada corrida

Desde la raíz del repositorio (PowerShell):

```powershell
python -m src.matchmaking.datos.recolector_cr --db "C:\Users\Owner\Downloads\clash_royale.db" recolectar --solo-panel --minutos 75 --refrescar-horas 3
```

- `--refrescar-horas 3` y no 4: si la corrida anterior empezó hace menos de 4 h, con 4 se saltaría
  a los jugadores consultados al inicio de esa corrida.
- `--minutos 75` es un tope; la corrida termina sola con "Todo el panel está al día".
- Mientras la base siga en `Downloads`, se pasa con `--db`. Al terminar el estudio se puede mover
  a `data/raw/clash_royale.db` y omitir `--db`.
- No correr dos recolectores sobre la misma base al mismo tiempo.

Al terminar, revisar el estado:

```powershell
python -m src.matchmaking.datos.caracterizar --db "C:\Users\Owner\Downloads\clash_royale.db" --desde-perfil 2026-11-05T16:17
```

### Qué anotar en `docs/avances.md`

Una fila por corrida: número, fecha, hora de inicio y fin, comando, y de la línea final
`Listo. Consultados: X. Batallas nuevas: Y`. Las batallas totales y de Trophy Road salen de
`caracterizar`. Un commit por corrida: `docs: bitácora de la corrida N del panel`.

## 3. Calendario

| # | Cuándo (Guatemala) | Qué esperar |
|---|---|---|
| 3 | 5 nov 14:00 | Unos 2,400 jugadores, ~40 min |
| 4 | 5 nov 18:00 | Panel completo, ~45 min |
| 5 | 5 nov 22:00 | Panel completo |
| 6 | 6 nov 7:00–8:00 | Panel completo; cubre la noche |
| 7 | 6 nov 12:00 | Última corrida |

Si una corrida se atrasa, no pasa nada: el battlelog guarda las últimas 30 batallas de cada
jugador, y un jugador del panel juega ~1.4 batallas cada 4 h. Solo se perderían batallas de quien
juegue más de 30 entre dos corridas.

## 4. Cierre (6 nov, después de la última corrida)

1. `caracterizar` final; copiar los números a `CONTEXTO_Y_HALLAZGOS.md` (sección 7) si cambian.
2. Exportar el CSV anonimizado:
   ```powershell
   python -m src.matchmaking.datos.recolector_cr --db "C:\Users\Owner\Downloads\clash_royale.db" exportar
   ```
   Queda en `data/processed/batallas.csv`.
3. Revisar que el CSV no tenga tags reales (columnas `j1`, `j2` y `batalla` de 16 caracteres
   hexadecimales) y su tamaño. Si pasa de 100 MB, comprimirlo o filtrarlo al período de estudio.
4. Commit: `data: exportar batallas de Trophy Road anonimizadas`.

## 5. Qué nunca se sube

`*.db`, `.env`, el valor de `CR_SALT` y cualquier captura o registro con la clave. El
`.gitignore` ya excluye `*.db`, `.env` y `data/raw/`.
