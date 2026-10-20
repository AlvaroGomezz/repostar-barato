"""Avisa a Bing (y a los buscadores que usan IndexNow: Yandex, Seznam, Naver…) de las páginas que cambian.

Uso, después de publicar la web:
    python -m generador.indexnow          la portada, las noticias y las noticias de hoy
    python -m generador.indexnow --todo   todas las páginas del sitemap (solo al principio o tras grandes cambios)

La clave se publica en la web como /<clave>.txt (la genera web.py) para que el buscador compruebe que el
aviso viene de nosotros. Un fallo aquí nunca hace fallar la publicación."""
import re
import sys
from datetime import datetime
from urllib.parse import urlparse

import requests

from .config import ZONA, cargar_sitio

API = "https://api.indexnow.org/indexnow"


def urls_de_hoy(sitio, todas: bool) -> list[str]:
    r = requests.get(f"{sitio.url}/sitemap.xml", timeout=60)
    r.raise_for_status()
    lista = re.findall(r"<loc>([^<]+)</loc>", r.text)
    if todas:
        return lista[:10000]
    hoy = datetime.now(ZONA).date().isoformat()
    fijas = {f"{sitio.url}/", f"{sitio.url}/noticias/"}
    return [u for u in lista if u in fijas or f"/noticias/{hoy}-" in u]


def main() -> int:
    sitio = cargar_sitio()
    if not sitio.indexnow:
        print("IndexNow sin configurar.")
        return 0
    try:
        urls = urls_de_hoy(sitio, "--todo" in sys.argv)
        if not urls:
            print("Nada que avisar.")
            return 0
        r = requests.post(API, timeout=60, json={
            "host": urlparse(sitio.url).netloc, "key": sitio.indexnow,
            "keyLocation": f"{sitio.url}/{sitio.indexnow}.txt", "urlList": urls,
        })
        print(f"IndexNow: {len(urls)} direcciones enviadas, respuesta {r.status_code}.")
        if r.status_code >= 400:
            print(f"::warning::IndexNow respondió {r.status_code}: {r.text[:200]}")
    except Exception as e:  # noqa: BLE001 - un aviso fallido no debe parar nada
        print(f"::warning::No se pudo avisar a IndexNow: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
