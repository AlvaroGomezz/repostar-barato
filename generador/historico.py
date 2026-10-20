"""Guarda un resumen diario de precios para poder mostrar evolución y escribir las noticias."""
import gzip
import json
from datetime import date, datetime
from pathlib import Path

from .config import COMBUSTIBLES, FISCALIDAD_ESPECIAL, PRINCIPALES
from .datos import Datos, Estacion, mas_baratas, resumen


def _ficha(e: Estacion, comb: str) -> dict:
    return {
        "id": e.id, "rotulo": e.rotulo, "dir": e.direccion,
        "mun": e.municipio.nombre, "prov": e.municipio.provincia.nombre,
        "ruta": e.municipio.ruta, "precio": e.precios[comb],
    }


def instantanea(datos: Datos) -> dict:
    peninsula = [e for e in datos.estaciones if e.provincia_id not in FISCALIDAD_ESPECIAL]
    snap = {
        "fecha": datos.actualizado.date().isoformat(),
        "actualizado": datos.actualizado.isoformat(),
        "nac": {}, "pen": {}, "prov": {}, "mun": {}, "top": {}, "top_pen": {}, "marcas": {},
    }
    for c in COMBUSTIBLES:
        r = resumen(datos.estaciones, c.clave)
        if r.n:
            snap["nac"][c.clave] = {"media": r.media, "min": r.minimo, "max": r.maximo, "n": r.n}
        rp = resumen(peninsula, c.clave)
        if rp.n:
            snap["pen"][c.clave] = {"media": rp.media, "min": rp.minimo, "max": rp.maximo, "n": rp.n}
    for p in datos.provincias:
        fila = {"nombre": p.nombre, "slug": p.slug}
        for c in COMBUSTIBLES:
            r = resumen(p.estaciones, c.clave)
            if r.n:
                fila[c.clave] = [r.media, r.minimo, r.n]
        snap["prov"][p.id] = fila
    for m in datos.municipios:
        fila = {}
        for clave in PRINCIPALES:
            r = resumen(m.estaciones, clave)
            if r.n:
                fila[clave] = r.media
        snap["mun"][m.id] = fila
    for clave in PRINCIPALES:
        snap["top"][clave] = [_ficha(e, clave) for e in mas_baratas(datos.estaciones, clave, 10)]
        snap["top_pen"][clave] = [_ficha(e, clave) for e in mas_baratas(peninsula, clave, 10)]
    for marca in datos.marcas:
        fila = {"nombre": marca.nombre, "n": len(marca.estaciones)}
        for clave in PRINCIPALES:
            r = resumen(marca.estaciones, clave)
            if r.n:
                fila[clave] = r.media
        snap["marcas"][marca.slug] = fila
    return snap


def guardar(snap: dict, carpeta: Path, ahora: datetime) -> bool:
    """Guarda la instantánea del día. La primera del día siempre; después, solo a partir de las
    20:00 (así el resumen refleja el cierre del día sin crear un commit en cada ejecución)."""
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"{snap['fecha']}.json.gz"
    if ruta.exists() and ahora.hour < 20:
        return False
    contenido = json.dumps(snap, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ruta.write_bytes(gzip.compress(contenido, mtime=0))
    return True


def cargar(carpeta: Path) -> dict[date, dict]:
    historico = {}
    if not carpeta.exists():
        return historico
    for ruta in sorted(carpeta.glob("*.json.gz")):
        try:
            snap = json.loads(gzip.decompress(ruta.read_bytes()).decode("utf-8"))
            historico[date.fromisoformat(snap["fecha"])] = snap
        except (OSError, ValueError, KeyError):
            continue
    return historico
