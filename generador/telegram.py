"""Publica cada mañana en un canal de Telegram el precio del día (la imagen de la noticia y un resumen).

Uso: python -m generador.telegram   (después de generar la web)

Necesita dos ajustes en GitHub (Settings → Secrets and variables → Actions):
- el secreto TELEGRAM_TOKEN, con el token del bot que da @BotFather;
- la variable TELEGRAM_CHAT, con el canal ("@nombredelcanal"), donde el bot debe ser administrador.
Sin ellos no hace nada. Publica una vez al día, a partir de las 8:00 (hora de Madrid), y nunca hace
fallar la publicación de la web."""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

from .config import RAIZ, ZONA, cargar_sitio

AVISO = RAIZ / "aviso" / "telegram.json"
REGISTRO = RAIZ / "historico" / "telegram.json"


def main() -> int:
    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    chat = os.getenv("TELEGRAM_CHAT", "").strip() or cargar_sitio().telegram
    if not token or not chat:
        print("Telegram sin configurar: no se publica nada.")
        return 0
    if not AVISO.exists():
        print("No hay aviso preparado.")
        return 0
    aviso = json.loads(AVISO.read_text(encoding="utf-8"))
    ahora = datetime.now(ZONA)
    if ahora.hour < 8:
        print("Antes de las 8:00: el aviso se publica más tarde.")
        return 0
    registro = json.loads(REGISTRO.read_text(encoding="utf-8")) if REGISTRO.exists() else {}
    if registro.get("ultimo") == aviso["fecha"]:
        print("El aviso de hoy ya está publicado.")
        return 0
    try:
        with open(aviso["imagen"], "rb") as foto:
            r = requests.post(f"https://api.telegram.org/bot{token}/sendPhoto", timeout=60,
                              data={"chat_id": chat, "caption": aviso["texto"], "parse_mode": "HTML"},
                              files={"photo": foto})
        r.raise_for_status()
        if not r.json().get("ok"):
            raise RuntimeError(r.text[:200])
    except Exception as e:  # noqa: BLE001 - un fallo de Telegram no debe parar la web
        print(f"::warning::No se pudo publicar en Telegram: {e}")
        return 0
    REGISTRO.parent.mkdir(parents=True, exist_ok=True)
    REGISTRO.write_text(json.dumps({"ultimo": aviso["fecha"]}), encoding="utf-8")
    print(f"Publicado en Telegram ({chat}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
