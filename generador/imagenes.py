"""Imágenes para compartir y para los resultados de Google (og:image): 1200 × 675, con los precios del día.

Se dibujan con Pillow a partir de los datos, en la identidad de la web: fondo amarillo, tinta negra y una
tarjeta blanca con las cifras. No llevan fotos de terceros."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .config import RAIZ

ANCHO, ALTO = 1200, 675
AMARILLO = (255, 212, 59)
TINTA = (20, 20, 20)
SUAVE = (77, 68, 48)
BLANCO = (255, 255, 255)
GRIS = (89, 85, 77)
VERDE = (7, 102, 64)
ROJO = (180, 35, 24)
FUENTE = RAIZ / "generador" / "fuentes" / "AlbertSans.ttf"

_cache: dict[tuple[int, int], ImageFont.FreeTypeFont] = {}


def fuente(tam: int, peso: int = 400) -> ImageFont.FreeTypeFont:
    clave = (tam, peso)
    if clave not in _cache:
        f = ImageFont.truetype(str(FUENTE), tam)
        try:
            f.set_variation_by_axes([peso])
        except (OSError, AttributeError):
            pass
        _cache[clave] = f
    return _cache[clave]


def _lineas(d: ImageDraw.ImageDraw, texto: str, f, ancho: int) -> list[str]:
    palabras, lineas, actual = texto.split(), [], ""
    for p in palabras:
        prueba = f"{actual} {p}".strip()
        if d.textlength(prueba, font=f) <= ancho or not actual:
            actual = prueba
        else:
            lineas.append(actual)
            actual = p
    if actual:
        lineas.append(actual)
    return lineas


def _titulo_que_cabe(d, texto: str, ancho: int, alto: int, tam_max: int = 78, tam_min: int = 44):
    """El mayor tamaño con el que el titular cabe en la caja."""
    for tam in range(tam_max, tam_min - 1, -2):
        f = fuente(tam, 700)
        lineas = _lineas(d, texto, f, ancho)
        if len(lineas) * tam * 1.04 <= alto:
            return f, lineas, tam
    f = fuente(tam_min, 700)
    return f, _lineas(d, texto, f, ancho)[:4], tam_min


def _simbolo(d: ImageDraw.ImageDraw, x: int, y: int, h: int = 40):
    """El poste de precios del logo."""
    w = round(h * 14 / 21)
    d.rectangle([x, y, x + w, y + h], fill=TINTA)
    m = round(w * 2.5 / 14)
    d.rectangle([x + m, y + round(h * .14), x + w - m, y + round(h * .29)], fill=AMARILLO)
    d.rectangle([x + m, y + round(h * .40), x + w - m, y + round(h * .51)], fill=BLANCO)
    d.rectangle([x + m, y + round(h * .63), x + w - m, y + round(h * .74)], fill=BLANCO)


def _triangulo(d, x: int, y: int, sube: bool, color):
    if sube:
        d.polygon([(x, y + 14), (x + 16, y + 14), (x + 8, y)], fill=color)
    else:
        d.polygon([(x, y), (x + 16, y), (x + 8, y + 14)], fill=color)


def tarjeta(destino: Path, antetitulo: str, titulo: str, filas: list[dict], pie: str = "",
            etiqueta: str = "") -> None:
    """filas: [{"nombre": "Diésel", "valor": "1,887", "unidad": "€/l", "nota": "+2,2 cts desde ayer",
    "sentido": 1 | -1 | 0}], como mucho tres."""
    img = Image.new("RGB", (ANCHO, ALTO), AMARILLO)
    d = ImageDraw.Draw(img)
    margen = 64

    # Cabecera: logo y, a la derecha, la etiqueta (normalmente la fecha).
    _simbolo(d, margen, 52, 40)
    d.text((margen + 40, 50), "Repostar Barato", font=fuente(32, 700), fill=TINTA)
    if etiqueta:
        f = fuente(24, 600)
        w = d.textlength(etiqueta, font=f)
        x1 = ANCHO - margen
        d.rounded_rectangle([x1 - w - 36, 46, x1, 92], radius=23, fill=TINTA)
        d.text((x1 - w - 18, 55), etiqueta, font=f, fill=BLANCO)

    # Texto a la izquierda; tarjeta de cifras a la derecha.
    con_cifras = bool(filas)
    ancho_texto = 600 if con_cifras else ANCHO - 2 * margen
    y = 170
    if antetitulo:
        d.text((margen, y), antetitulo.upper(), font=fuente(24, 700), fill=SUAVE)
        y += 48
    f, lineas, tam = _titulo_que_cabe(d, titulo, ancho_texto, ALTO - y - 110,
                                      tam_max=78 if con_cifras else 92)
    for linea in lineas:
        d.text((margen, y), linea, font=f, fill=TINTA)
        y += round(tam * 1.04)
    if pie:
        d.text((margen, ALTO - 78), pie, font=fuente(24, 500), fill=SUAVE)

    if con_cifras:
        filas = filas[:3]
        x0, x1 = 712, ANCHO - margen
        alto_fila = 132
        y0 = 150
        y1 = y0 + 40 + alto_fila * len(filas)
        d.rounded_rectangle([x0, y0, x1, y1], radius=28, fill=BLANCO)
        y = y0 + 30
        for i, fila in enumerate(filas):
            if i:
                d.line([x0 + 32, y - 14, x1 - 32, y - 14], fill=(230, 226, 216), width=2)
            d.text((x0 + 34, y), fila["nombre"], font=fuente(26, 600), fill=GRIS)
            fv = fuente(70, 700)
            d.text((x0 + 32, y + 30), fila["valor"], font=fv, fill=TINTA)
            wv = d.textlength(fila["valor"], font=fv)
            if fila.get("unidad"):
                d.text((x0 + 40 + wv, y + 66), fila["unidad"], font=fuente(26, 500), fill=GRIS)
            nota = fila.get("nota")
            if nota:
                sentido = fila.get("sentido", 0)
                color = ROJO if sentido > 0 else VERDE if sentido < 0 else GRIS
                fn = fuente(22, 600)
                wn = d.textlength(nota, font=fn)
                xn = x1 - 34 - wn
                d.text((xn, y + 2), nota, font=fn, fill=color)
                if sentido:
                    _triangulo(d, round(xn - 24), y + 7, sentido > 0, color)
            y += alto_fila

    destino.parent.mkdir(parents=True, exist_ok=True)
    img.save(destino, "JPEG", quality=84, optimize=True, progressive=True)
