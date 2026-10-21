"""Mapa fijo de la portada: el dibujo de España (estatico/mapa-espana.svg) y la posición de cada ciudad
sobre él. En el móvil se ve esto en lugar del mapa interactivo, que pesa unos 3 MB, hasta que se toca.

El SVG sale de Natural Earth 1:50m (dominio público) con la misma proyección (Mercator) y el mismo
recuadro que aquí; si se cambian, hay que volver a generar el dibujo."""
import math

LON0, LON1, LAT0, LAT1 = -9.9, 4.7, 35.6, 44.1
ANCHO, ALTO = 1000, 760


def _merc(lat: float) -> float:
    return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


def posicion(lat: float, lon: float) -> tuple[float, float] | None:
    """(izquierda %, arriba %) dentro del dibujo, o None si cae fuera (Canarias, Ceuta, Melilla)."""
    x = (lon - LON0) / (LON1 - LON0) * 100
    y = (_merc(LAT1) - _merc(lat)) / (_merc(LAT1) - _merc(LAT0)) * 100
    if not (0 <= x <= 100 and 0 <= y <= 100):
        return None
    return round(x, 2), round(y, 2)


def categoria(i: int, n: int, v: float, minimo: float) -> str:
    """La misma escala de colores que los marcadores del mapa interactivo (app.js)."""
    if v <= minimo + 0.0005:
        return "top"
    q = i / max(1, n - 1)
    return "barata" if q < 0.34 else "media" if q < 0.67 else "cara"


def pines(ciudades: list[dict], combustibles: list[str]) -> list[dict]:
    """ciudades: [{"nombre", "url", "lat", "lon", "precios": {c: valor}}]."""
    salida = []
    for c in ciudades:
        pos = posicion(c["lat"], c["lon"])
        if pos:
            salida.append({**c, "x": pos[0], "y": pos[1], "cat": {}})
    for comb in combustibles:
        con = sorted((p for p in salida if p["precios"].get(comb) is not None), key=lambda p: p["precios"][comb])
        if not con:
            continue
        minimo = con[0]["precios"][comb]
        for i, p in enumerate(con):
            p["cat"][comb] = categoria(i, len(con), p["precios"][comb], minimo)
    return salida
