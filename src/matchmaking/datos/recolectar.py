import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import requests

from .cliente import ClienteClashRoyale


RAIZ = Path(__file__).resolve().parents[3]


def guardar_json(ruta, contenido):
    ruta.write_text(
        json.dumps(contenido, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def recolectar(tags):
    cliente = ClienteClashRoyale()

    inicio = datetime.now(timezone.utc)
    ejecucion = inicio.strftime("%Y%m%dT%H%M%S%fZ")
    carpeta = RAIZ / "data" / "raw" / ejecucion
    carpeta.mkdir(parents=True, exist_ok=False)

    resumen = {
        "inicio_utc": inicio.isoformat(),
        "fuente": "Clash Royale API",
        "consultas": [],
    }

    # Evita consultar dos veces una misma etiqueta en esta ejecución.
    tags = list(dict.fromkeys(
        cliente.normalizar_tag(tag) for tag in tags
    ))

    try:
        for numero, tag in enumerate(tags, start=1):
            consulta = {"player_tag": tag}

            try:
                batallas = cliente.historial(tag)
                fecha = datetime.now(timezone.utc).isoformat()
                nombre = f"historial_{numero:04d}.json"

                guardar_json(carpeta / nombre, {
                    "fetched_at_utc": fecha,
                    "source_player_tag": tag,
                    "endpoint": "/players/{playerTag}/battlelog",
                    "payload": batallas,
                })

                tipos = Counter(
                    str(batalla.get("type", "ausente"))
                    for batalla in batallas
                )

                consulta.update({
                    "estado": "ok",
                    "archivo": nombre,
                    "fetched_at_utc": fecha,
                    "registros": len(batallas),
                    "tipos_observados": dict(tipos),
                })

                print(f"{tag}: {len(batallas)} registros guardados")

            except requests.HTTPError as error:
                codigo = error.response.status_code
                consulta.update({
                    "estado": "error",
                    "http_status": codigo,
                })
                print(f"{tag}: error HTTP {codigo}")

                if codigo in (401, 403):
                    consulta["detalle"] = "Revisar token e IP autorizada"
                    resumen["consultas"].append(consulta)
                    break

            except (requests.RequestException, ValueError) as error:
                consulta.update({
                    "estado": "error",
                    "detalle": str(error),
                })
                print(f"{tag}: consulta fallida; revisar resumen.json")

            resumen["consultas"].append(consulta)

    finally:
        cliente.cerrar()
        resumen["fin_utc"] = datetime.now(timezone.utc).isoformat()
        guardar_json(carpeta / "resumen.json", resumen)

    print(f"Resultados en: {carpeta}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Descarga historiales recientes de jugadores"
    )
    parser.add_argument(
        "tags",
        nargs="+",
        help="Etiquetas de jugadores, entre comillas",
    )
    argumentos = parser.parse_args()
    recolectar(argumentos.tags)