"""Guarda un resumen diario de precios para poder mostrar evolución y escribir las noticias."""
import gzip
import json
from datetime import date, datetime
from pathlib import Path

from .config import COMBUSTIBLES, FISCALIDAD_ESPECIAL, PRINCIPALES
from .datos import Datos, Estacion, mas_baratas, resumen


def _cuartiles(estaciones, clave):
    v = sorted(e.precios[clave] for e in estaciones if clave in e.precios)
    if len(v) < 4:
        return None, None
    q = lambda p: v[min(len(v) - 1, max(0, round(p * (len(v) - 1))))]  # noqa: E731
    return q(0.25), q(0.75)


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
        "ciudades": [],
    }
    for c in COMBUSTIBLES:
        r = resumen(datos.estaciones, c.clave)
        if r.n:
            p25, p75 = _cuartiles(datos.estaciones, c.clave)
            snap["nac"][c.clave] = {"media": r.media, "min": r.minimo, "max": r.maximo, "n": r.n, "p25": p25, "p75": p75}
        rp = resumen(peninsula, c.clave)
        if rp.n:
            p25, p75 = _cuartiles(peninsula, c.clave)
            snap["pen"][c.clave] = {"media": rp.media, "min": rp.minimo, "max": rp.maximo, "n": rp.n, "p25": p25, "p75": p75}
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
    # Las grandes ciudades (la de más gasolineras de cada provincia, hasta 12): rango de precios del día.
    vistas = set()
    for m in sorted(datos.municipios, key=lambda m: -len(m.estaciones)):
        if m.provincia.id in vistas:
            continue
        vistas.add(m.provincia.id)
        fila = {"nombre": m.nombre, "ruta": m.ruta, "n": len(m.estaciones), "prov": m.provincia.nombre}
        for clave in PRINCIPALES:
            r = resumen(m.estaciones, clave)
            barata = mas_baratas(m.estaciones, clave, 1)
            if r.n and barata:
                fila[clave] = {"min": barata[0].precios[clave], "max": r.maximo, "media": r.media, "n": r.n,
                               "rotulo": barata[0].rotulo, "dir": barata[0].direccion,
                               "top": [{"rotulo": e.rotulo, "dir": e.direccion, "precio": e.precios[clave],
                                        "h24": e.abierta_24h} for e in mas_baratas(m.estaciones, clave, 5)]}
        snap["ciudades"].append(fila)
        if len(snap["ciudades"]) == 12:
            break
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


LIGERO = ("fecha", "actualizado", "nac", "pen", "prov")


def cargar(carpeta: Path, completo_desde: date | None = None) -> dict[date, dict]:
    """Los días anteriores a completo_desde se cargan solo con las medias (lo que usan los gráficos)."""
    historico = {}
    if not carpeta.exists():
        return historico
    for ruta in sorted(carpeta.glob("*.json.gz")):
        try:
            snap = json.loads(gzip.decompress(ruta.read_bytes()).decode("utf-8"))
            f = date.fromisoformat(snap["fecha"])
            if completo_desde and f < completo_desde:
                snap = {k: snap[k] for k in LIGERO if k in snap}
            historico[f] = snap
        except (OSError, ValueError, KeyError):
            continue
    return historico
