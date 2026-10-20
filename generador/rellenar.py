"""Rellena el histórico con los precios oficiales de días pasados (API histórica del Ministerio).

Uso: python -m generador.rellenar [--desde 2025-10-21] [--hasta 2026-10-19] [--forzar]
Por defecto, el último año hasta ayer, sin tocar los días que ya existan. Cada día son ~12 MB de descarga."""
import argparse
import gzip
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path

from . import historico
from .config import RAIZ, ZONA
from .datos import descargar_con_curl, interpretar

URL = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestresHist/{}"
CABECERAS = {"Accept": "application/json",
             "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"}


def descargar(dia: date) -> dict | None:
    for intento in range(4):
        try:
            datos = descargar_con_curl(URL.format(dia.strftime("%d-%m-%Y")))
            if len(datos.get("ListaEESSPrecio", [])) > 5000:
                return datos
        except Exception:  # noqa: BLE001 - reintentar
            pass
        time.sleep(5 * (intento + 1))
    return None


def main() -> int:
    hoy = datetime.now(ZONA).date()
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde", type=date.fromisoformat, default=hoy - timedelta(days=365))
    ap.add_argument("--hasta", type=date.fromisoformat, default=hoy - timedelta(days=1))
    ap.add_argument("--carpeta", default=str(RAIZ / "historico"))
    ap.add_argument("--forzar", action="store_true", help="vuelve a calcular los días que ya existen")
    args = ap.parse_args()
    carpeta = Path(args.carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    dias = []
    d = args.desde
    while d <= args.hasta:
        if args.forzar or not (carpeta / f"{d.isoformat()}.json.gz").exists():
            dias.append(d)
        d += timedelta(days=1)
    print(f"{len(dias)} días por rellenar.", flush=True)
    hechos = fallos = 0
    with ThreadPoolExecutor(max_workers=3) as pool:
        for dia, bruto in zip(dias, pool.map(descargar, dias)):
            if bruto is None:
                fallos += 1
                print(f"{dia}: no se pudo descargar", flush=True)
                continue
            snap = historico.instantanea(interpretar(bruto, cercanas=False))
            snap["fecha"] = dia.isoformat()  # la API pone la fecha pedida a las 0:00
            contenido = json.dumps(snap, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            (carpeta / f"{dia.isoformat()}.json.gz").write_bytes(gzip.compress(contenido, mtime=0))
            hechos += 1
            if hechos % 20 == 0:
                print(f"{hechos} días hechos (último: {dia})", flush=True)
    print(f"Listo: {hechos} días guardados, {fallos} fallidos.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
