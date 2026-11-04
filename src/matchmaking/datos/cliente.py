import os
from pathlib import Path
from urllib.parse import quote

import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


RAIZ = Path(__file__).resolve().parents[3]


class ClienteClashRoyale:
    BASE_URL = "https://api.clashroyale.com/v1"

    def __init__(self):
        load_dotenv(RAIZ / ".env")

        token = os.getenv("CR_API_TOKEN", "").strip()
        if not token:
            raise ValueError("Falta CR_API_TOKEN en el archivo .env")

        self.sesion = requests.Session()
        self.sesion.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        })

        reintentos = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            respect_retry_after_header=True,
            raise_on_status=False,
        )

        self.sesion.mount(
            "https://",
            HTTPAdapter(max_retries=reintentos),
        )

    @staticmethod
    def normalizar_tag(tag):
        tag = tag.strip().upper()
        if not tag:
            raise ValueError("La etiqueta está vacía")
        return "#" + tag.lstrip("#")

    def consultar(self, ruta):
        respuesta = self.sesion.get(
            self.BASE_URL + ruta,
            timeout=(10, 30),
        )
        respuesta.raise_for_status()
        return respuesta.json()

    def historial(self, tag):
        tag = quote(self.normalizar_tag(tag), safe="")
        datos = self.consultar(f"/players/{tag}/battlelog")

        if not isinstance(datos, list):
            raise ValueError("El historial recibido no es una lista")

        return datos

    def miembros_clan(self, tag):
        tag = quote(self.normalizar_tag(tag), safe="")
        return self.consultar(f"/clans/{tag}/members")

    def cerrar(self):
        self.sesion.close()