"""Imágenes para compartir y para los resultados de Google (og:image): 1200 × 675, con los precios del día.

Se dibujan con Pillow a partir de los datos, en la identidad de la web: fondo amarillo, tinta negra y una
tarjeta blanca con las cifras. No llevan fotos de terceros."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .config import RAIZ

ANCHO, ALTO = 1200, 675
AMARILLO = (255, 226, 122)
TINTA = (23, 25, 27)
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


def _logo(img: Image.Image, x: int, y: int, h: int = 40):
    """El logo de GASVIA (versión sobre amarillo), pegado en la imagen."""
    from .marca import SOBRE_AMARILLO, logo_png
    logo = logo_png(h, SOBRE_AMARILLO)
    img.paste(logo, (x, y), logo)


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
    _logo(img, margen, 50, 42)
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


# ---------- con foto, como las de los periódicos ----------

FOTOS = RAIZ / "generador" / "fotos"
# Dónde está lo importante de cada foto (0 = izquierda, 1 = derecha), para recortarla sin perderlo.
ENCUADRE = {
    "gas-pump-in-lannion.jpg": 0.55,
    "petrol-pump-mp3h0354.jpg": 0.45,
    "gas-pump-handle-fueling-station-34825559585.jpg": 0.55,
    "red-gas-pump-handle-in-car-gas.jpg": 0.4,
    "gasolinera-en-ceutaa-1.jpg": 0.55,
    "olaberria-gasolinera-avia-1.jpg": 0.45,
    "gasolinera-y-estacion-de-servicio-repsol-torreblanca.jpg": 0.6,
    "gasolinera-repsol.jpg": 0.4,
    "gasolinera-cepsa1.jpg": 0.5,
    "gasolinera-cepsa.jpg": 0.45,
    "gasolinera-de-plaza-colon-cordoba.jpg": 0.5,
    "gasolinera-galp-01.jpg": 0.4,
    "miranda-de-ebro-calle-logrono-estacion-de.jpg": 0.5,
    "car-fuel-gauge-full-gas-tank-52958977635.jpg": 0.5,
    "fuel-gauge-running-on-empty.jpg": 0.55,
    "gasolinera-alaska-malaga-20240719-191625.jpg": 0.4,
}
# Grupos de fotos según el tema de la noticia.
GRUPOS = {
    "surtidor": ["gas-pump-in-lannion.jpg", "petrol-pump-mp3h0354.jpg", "gas-pump-handle-fueling-station-34825559585.jpg",
                 "red-gas-pump-handle-in-car-gas.jpg"],
    "gasolinera": ["gasolinera-en-ceutaa-1.jpg", "olaberria-gasolinera-avia-1.jpg",
                   "gasolinera-y-estacion-de-servicio-repsol-torreblanca.jpg", "gasolinera-repsol.jpg",
                   "gasolinera-cepsa1.jpg", "gasolinera-cepsa.jpg", "gasolinera-de-plaza-colon-cordoba.jpg",
                   "gasolinera-galp-01.jpg", "miranda-de-ebro-calle-logrono-estacion-de.jpg",
                   "gasolinera-alaska-malaga-20240719-191625.jpg"],
    "deposito": ["fuel-gauge-running-on-empty.jpg", "car-fuel-gauge-full-gas-tank-52958977635.jpg",
                 "red-gas-pump-handle-in-car-gas.jpg", "petrol-pump-mp3h0354.jpg"],
}
GRUPOS["todas"] = GRUPOS["surtidor"] + GRUPOS["gasolinera"]


def elegir(grupo: str, clave: int, usadas: set) -> str:
    """Una foto del grupo según la clave, sin repetir las ya usadas (p. ej. en el mismo día)."""
    lista = GRUPOS[grupo]
    for i in range(len(lista)):
        f = lista[(clave + i) % len(lista)]
        if f not in usadas:
            usadas.add(f)
            return f
    return lista[clave % len(lista)]


def solo_foto(destino: Path, foto: str) -> None:
    """La foto sola, recortada a 16:9, como la de un periódico."""
    original = Image.open(FOTOS / foto).convert("RGB")
    img = _recorte(original, ANCHO, ALTO, ENCUADRE.get(foto, .5))
    destino.parent.mkdir(parents=True, exist_ok=True)
    img.save(destino, "JPEG", quality=84, optimize=True, progressive=True)


def fotos() -> list[str]:
    return sorted(ENCUADRE)


def foto_para(clave: int) -> str:
    """Una foto distinta según la clave (el día, la provincia…), siempre la misma para la misma clave."""
    lista = fotos()
    return lista[clave % len(lista)]


def _recorte(foto: Image.Image, ancho: int, alto: int, x_rel: float) -> Image.Image:
    escala = max(ancho / foto.width, alto / foto.height)
    w, h = round(foto.width * escala), round(foto.height * escala)
    foto = foto.resize((w, h), Image.LANCZOS)
    x = round((w - ancho) * min(1, max(0, x_rel)))
    y = round((h - alto) / 2)
    return foto.crop((x, y, x + ancho, y + alto))


def portada_con_foto(destino: Path, antetitulo: str, titulo: str, filas: list[dict], foto: str,
                     etiqueta: str = "") -> None:
    img = Image.new("RGB", (ANCHO, ALTO), AMARILLO)
    x_foto = 520
    original = Image.open(FOTOS / foto).convert("RGB")
    img.paste(_recorte(original, ANCHO - x_foto, ALTO, ENCUADRE.get(foto, .5)), (x_foto, 0))
    # Unión suave entre el amarillo y la foto.
    franja = 90
    degradado = Image.new("L", (franja, ALTO))
    dg = ImageDraw.Draw(degradado)
    for i in range(franja):
        dg.line([(i, 0), (i, ALTO)], fill=round(255 * (1 - i / franja) ** 1.6))
    img.paste(Image.new("RGB", (franja, ALTO), AMARILLO), (x_foto, 0), degradado)

    d = ImageDraw.Draw(img)
    margen = 56
    _logo(img, margen, 44, 40)
    if etiqueta:
        f = fuente(24, 700)
        w = d.textlength(etiqueta, font=f)
        x1 = ANCHO - 40
        d.rounded_rectangle([x1 - w - 36, 40, x1, 86], radius=23, fill=TINTA)
        d.text((x1 - w - 18, 49), etiqueta, font=f, fill=BLANCO)

    ancho_texto = x_foto - margen - 10
    y = 150
    if antetitulo:
        d.text((margen, y), antetitulo.upper(), font=fuente(22, 700), fill=SUAVE)
        y += 42
    alto_titulo = ALTO - y - (70 + 84 * len(filas[:2]))
    f, lineas, tam = _titulo_que_cabe(d, titulo, ancho_texto, alto_titulo, tam_max=70, tam_min=40)
    for linea in lineas:
        d.text((margen, y), linea, font=f, fill=TINTA)
        y += round(tam * 1.05)

    # Los precios del día, en fichas blancas abajo a la izquierda.
    y = ALTO - 48 - 84 * len(filas[:2])
    for fila in filas[:2]:
        x0, x1 = margen, x_foto + 40
        d.rounded_rectangle([x0, y, x1, y + 72], radius=16, fill=BLANCO)
        d.text((x0 + 20, y + 22), fila["nombre"], font=fuente(24, 600), fill=GRIS)
        valor = fila["valor"] + " €/l"
        wn = d.textlength(fila["nombre"], font=fuente(24, 600))
        xv = x0 + 20 + max(wn, 150) + 14
        nota = fila.get("nota")
        wnota = (d.textlength(nota, font=fuente(22, 700)) + (24 if fila.get("sentido") else 0) + 16) if nota else 0
        # La cifra se encoge si no cabe junto a la nota; si ni así cabe, la nota se quita.
        for tam in (44, 40, 36, 32):
            fv = fuente(tam, 700)
            if xv + d.textlength(valor, font=fv) + wnota <= x1 - 18:
                break
        else:
            nota = None
        d.text((xv, y + 10 + (44 - tam) // 2), valor, font=fv, fill=TINTA)
        if nota:
            sentido = fila.get("sentido", 0)
            color = ROJO if sentido > 0 else VERDE if sentido < 0 else GRIS
            fn = fuente(22, 700)
            wnota = d.textlength(nota, font=fn)
            xn = x1 - 18 - wnota
            d.text((xn, y + 24), nota, font=fn, fill=color)
            if sentido:
                _triangulo(d, round(xn - 22), y + 29, sentido > 0, color)
        y += 84

    destino.parent.mkdir(parents=True, exist_ok=True)
    img.save(destino, "JPEG", quality=84, optimize=True, progressive=True)
