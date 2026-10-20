"""Uso: python -m generador [--fichero datos.json] [--salida publico] [--no-guardar-historico]"""
import argparse
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
    args = ap.parse_args()

    t0 = time.time()
    sitio = cargar_sitio()
    bruto = datos_mod.cargar_fichero(Path(args.fichero)) if args.fichero else datos_mod.descargar()
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
