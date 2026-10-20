"""Uso: python -m generador [--fichero datos.json] [--salida publico] [--no-guardar-historico]"""
import argparse
import gzip
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from . import datos as datos_mod
from . import historico
from .config import RAIZ, ZONA, cargar_sitio
from .web import Web


def main() -> int:
    ap = argparse.ArgumentParser(description="Genera la web de precios de carburantes.")
    ap.add_argument("--fichero", help="JSON de la API ya descargado (para pruebas sin red)")
    ap.add_argument("--salida", default=str(RAIZ / "publico"))
    ap.add_argument("--historico", default=str(RAIZ / "historico"))
    ap.add_argument("--no-guardar-historico", action="store_true")
    ap.add_argument("--respaldo", default=str(RAIZ / "respaldo" / "ultimo.json.gz"),
                    help="copia de la última descarga buena, para cuando la API no responde")
    args = ap.parse_args()

    t0 = time.time()
    sitio = cargar_sitio()
    respaldo = Path(args.respaldo)
    if args.fichero:
        bruto = datos_mod.cargar_fichero(Path(args.fichero))
    else:
        try:
            bruto = datos_mod.descargar()
            respaldo.parent.mkdir(parents=True, exist_ok=True)
            with gzip.open(respaldo, "wt", encoding="utf-8") as f:
                json.dump(bruto, f, ensure_ascii=False)
        except RuntimeError as e:
            # El Ministerio corta a veces las conexiones: se publica con la última descarga buena.
            if not respaldo.exists():
                raise
            print(f"::warning::{e}. Se usan los precios de la última descarga buena.")
            with gzip.open(respaldo, "rt", encoding="utf-8") as f:
                bruto = json.load(f)
            args.no_guardar_historico = True
    datos = datos_mod.interpretar(bruto)
    print(f"Datos del {datos.actualizado:%d/%m/%Y %H:%M}: {len(datos.estaciones)} gasolineras, "
          f"{len(datos.municipios)} municipios, {len(datos.provincias)} provincias, {len(datos.marcas)} marcas")

    carpeta_hist = Path(args.historico)
    hist = historico.cargar(carpeta_hist)
    hist.pop(datos.actualizado.date(), None)  # el día de hoy se calcula con los datos actuales
    snap = historico.instantanea(datos)
    if not args.no_guardar_historico:
        guardado = historico.guardar(snap, carpeta_hist, datetime.now(ZONA))
        print("Histórico del día guardado." if guardado else "Histórico del día ya guardado (se actualiza desde las 20:00).")

    web = Web(datos, hist, sitio, Path(args.salida))
    web.construir(snap)
    print(f"Web generada en {args.salida}: {len(web.paginas)} páginas en {time.time() - t0:.1f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
