"""La marca GASVIA (gas + vía): isotipo, logo e iconos.

Los trazos salen del kit de identidad (GASVIA_Kit_Logos_Premium): la «V» amarilla y la barra carbón del
isotipo, y «GASVIA» en DejaVu Sans Bold convertido a trazos (así se ve igual en cualquier ordenador).
Este módulo vuelve a generar todos los ficheros con las proporciones correctas (iconos cuadrados para las
tiendas de apps, favicon nítido).

Uso: python -m generador.marca   (escribe en generador/estatico/marca/ y generador/estatico/icono.svg)"""
import re
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

from .config import RAIZ

AMARILLO = "#FFCF32"
CARBON = "#17191B"
BLANCO = "#FFFFFF"
DESTINO = RAIZ / "generador" / "estatico" / "marca"

# Isotipo, en un lienzo de 220 × 120 (contenido entre x 8–213 e y 4–111).
V = ("M16 25 L53 25 Q59 25 63 31 L90 78 L137 15 Q145 4 158 4 L175 4 Q182 4 185 11 L194 26 Q197 31 192 35 "
     "L154 35 Q147 35 142 42 L104 96 Q96 107 85 107 L78 107 Q68 107 62 98 L13 34 Q8 25 16 25Z")
BARRA = "M115 106 L171 43 Q177 37 184 37 L205 37 Q213 37 208 44 L162 105 Q158 111 150 111 L119 111 Q111 111 115 106Z"
# «GASVIA», en las mismas coordenadas que el logo horizontal del kit (lienzo de 730 × 150).
PALABRA = "M298 103.1Q291.6 106.2 284.7 107.7Q277.8 109.3 270.5 109.3Q253.9 109.3 244.2 100Q234.5 90.8 234.5 74.9Q234.5 58.9 244.4 49.7Q254.3 40.5 271.4 40.5Q278 40.5 284.1 41.7Q290.2 42.9 295.5 45.4V59.1Q290 56 284.5 54.4Q279 52.9 273.5 52.9Q263.3 52.9 257.7 58.6Q252.2 64.3 252.2 74.9Q252.2 85.4 257.5 91.2Q262.9 96.9 272.7 96.9Q275.4 96.9 277.7 96.6Q279.9 96.2 281.8 95.5V82.6H271.3V71.2H298ZM348.3 95.9H321.6L317.3 108H300.1L324.7 41.7H345.1L369.7 108H352.5ZM325.8 83.6H344L334.9 57.2ZM419.6 43.7V57.8Q414.2 55.3 409 54.1Q403.8 52.9 399.2 52.9Q393 52.9 390.1 54.5Q387.2 56.2 387.2 59.8Q387.2 62.5 389.1 63.9Q391.1 65.4 396.3 66.5L403.6 68Q414.7 70.2 419.3 74.7Q424 79.3 424 87.6Q424 98.6 417.5 103.9Q411 109.3 397.6 109.3Q391.3 109.3 384.9 108.1Q378.6 106.9 372.2 104.5V90.1Q378.6 93.5 384.5 95.2Q390.4 96.9 396 96.9Q401.6 96.9 404.5 95Q407.5 93.2 407.5 89.7Q407.5 86.6 405.5 84.9Q403.5 83.2 397.4 81.9L390.8 80.4Q380.8 78.3 376.3 73.6Q371.7 68.9 371.7 61Q371.7 51.1 378.1 45.8Q384.4 40.5 396.4 40.5Q401.9 40.5 407.7 41.3Q413.5 42.1 419.6 43.7ZM426.1 41.7H443.3L460.9 90.6L478.4 41.7H495.6L471.1 108H450.7ZM499.4 41.7H516.5V108H499.4ZM568.6 95.9H541.8L537.6 108H520.4L545 41.7H565.4L589.9 108H572.7ZM546.1 83.6H564.2L555.2 57.2Z"
ISO_LOGO = "translate(12 17) scale(0.91)"   # el isotipo dentro del logo horizontal
CAJA_LOGO = (10, 12, 590, 116)              # x, y, ancho, alto del logo horizontal, ajustado al dibujo
CAJA_ISO = (6, 2, 210, 112)

# Combinaciones de color según el fondo.
SOBRE_CLARO = {"v": AMARILLO, "barra": CARBON, "texto": CARBON}
SOBRE_AMARILLO = {"v": BLANCO, "barra": CARBON, "texto": CARBON}
SOBRE_OSCURO = {"v": AMARILLO, "barra": BLANCO, "texto": BLANCO}


# ---------- SVG ----------

def isotipo_svg(v=AMARILLO, barra=CARBON) -> str:
    x, y, w, h = CAJA_ISO
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x} {y} {w} {h}">'
            f'<path d="{V}" fill="{v}"/><path d="{BARRA}" fill="{barra}"/></svg>')


def logo_svg(v=AMARILLO, barra=CARBON, texto=CARBON, fondo=None, atributos="") -> str:
    x, y, w, h = CAJA_LOGO
    caja = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fondo}"/>' if fondo else ""
    xmlns = "" if "aria-hidden" in atributos else ' xmlns="http://www.w3.org/2000/svg"'
    return (f'<svg{xmlns} viewBox="{x} {y} {w} {h}"{atributos}>{caja}'
            f'<g transform="{ISO_LOGO}"><path d="{V}" fill="{v}"/><path d="{BARRA}" fill="{barra}"/></g>'
            f'<path d="{PALABRA}" fill="{texto}"/></svg>')


def icono_svg(fondo=AMARILLO, v=BLANCO, barra=CARBON, redondeo=112, transformacion="translate(54 156) scale(1.86)") -> str:
    """Icono de app (512 × 512), como el del kit."""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">'
            f'<rect width="512" height="512" rx="{redondeo}" fill="{fondo}"/>'
            f'<g transform="{transformacion}"><path d="{V}" fill="{v}"/><path d="{BARRA}" fill="{barra}"/></g></svg>')


# ---------- dibujo en PNG (a 4× y reducido, para bordes suaves) ----------

def _subtrazos(d: str, transformar) -> list[list[tuple[float, float]]]:
    """Convierte un trazado SVG (M L H V Q Z, absolutos) en polígonos."""
    fichas = re.findall(r"[MLHVQZ]|-?\d+(?:\.\d+)?", d)
    polis, actual, i, cmd = [], [], 0, None
    x = y = 0.0
    while i < len(fichas):
        f = fichas[i]
        if f.isalpha():
            cmd = f
            i += 1
            if cmd == "Z":
                if actual:
                    polis.append(actual)
                actual = []
            continue
        if cmd == "M":
            if actual:
                polis.append(actual)
            x, y = float(fichas[i]), float(fichas[i + 1])
            i += 2
            actual = [(x, y)]
            cmd = "L"
        elif cmd == "L":
            x, y = float(fichas[i]), float(fichas[i + 1])
            i += 2
            actual.append((x, y))
        elif cmd == "H":
            x = float(fichas[i])
            i += 1
            actual.append((x, y))
        elif cmd == "V":
            y = float(fichas[i])
            i += 1
            actual.append((x, y))
        elif cmd == "Q":
            cx, cy, ex, ey = (float(fichas[i + k]) for k in range(4))
            i += 4
            for paso in range(1, 13):
                t = paso / 12
                actual.append(((1 - t) ** 2 * x + 2 * (1 - t) * t * cx + t * t * ex,
                               (1 - t) ** 2 * y + 2 * (1 - t) * t * cy + t * t * ey))
            x, y = ex, ey
        else:
            i += 1
    if actual:
        polis.append(actual)
    return [[transformar(px, py) for px, py in p] for p in polis]


def _pintar(img: Image.Image, d: str, color: str, transformar):
    """Rellena un trazado con la regla par-impar (los huecos de la A o la G quedan huecos)."""
    mascara = Image.new("1", img.size, 0)
    for poli in _subtrazos(d, transformar):
        capa = Image.new("1", img.size, 0)
        ImageDraw.Draw(capa).polygon(poli, fill=1)
        mascara = ImageChops.logical_xor(mascara, capa)
    img.paste(Image.new("RGBA", img.size, color), (0, 0), mascara.convert("L"))


def isotipo_png(ancho: int, colores=SOBRE_CLARO) -> Image.Image:
    k = 4
    x0, y0, w, h = CAJA_ISO
    alto = round(ancho * h / w)
    img = Image.new("RGBA", (ancho * k, alto * k), (0, 0, 0, 0))
    esc = ancho * k / w
    tr = lambda px, py: ((px - x0) * esc, (py - y0) * esc)  # noqa: E731
    _pintar(img, V, colores["v"], tr)
    _pintar(img, BARRA, colores["barra"], tr)
    return img.resize((ancho, alto), Image.LANCZOS)


def logo_png(alto: int, colores=SOBRE_CLARO) -> Image.Image:
    k = 4
    x0, y0, w, h = CAJA_LOGO
    ancho = round(alto * w / h)
    img = Image.new("RGBA", (ancho * k, alto * k), (0, 0, 0, 0))
    esc = alto * k / h
    tr = lambda px, py: ((px - x0) * esc, (py - y0) * esc)  # noqa: E731
    tr_iso = lambda px, py: tr(12 + px * 0.91, 17 + py * 0.91)  # noqa: E731
    _pintar(img, V, colores["v"], tr_iso)
    _pintar(img, BARRA, colores["barra"], tr_iso)
    _pintar(img, PALABRA, colores["texto"], tr)
    return img.resize((ancho, alto), Image.LANCZOS)


def icono_png(tam: int, fondo=AMARILLO, colores=SOBRE_AMARILLO, redondeo=0.0, zona=0.745,
              transparente=False) -> Image.Image:
    """zona: parte del ancho que ocupa el isotipo (en el icono del kit, 0,745)."""
    img = Image.new("RGBA", (tam, tam), (0, 0, 0, 0))
    if not transparente:
        capa = Image.new("RGBA", (tam * 4, tam * 4), (0, 0, 0, 0))
        ImageDraw.Draw(capa).rounded_rectangle([0, 0, tam * 4 - 1, tam * 4 - 1],
                                               radius=round(tam * 4 * redondeo), fill=fondo)
        img = capa.resize((tam, tam), Image.LANCZOS)
    iso = isotipo_png(round(tam * zona), colores)
    img.paste(iso, ((tam - iso.width) // 2, (tam - iso.height) // 2 + round(tam * 0.01)), iso)
    return img


def generar(destino: Path = DESTINO) -> list[Path]:
    destino.mkdir(parents=True, exist_ok=True)
    for viejo in destino.glob("*"):
        viejo.unlink()
    hechos = []

    def png(img: Image.Image, nombre: str, opaco: bool = False):
        if opaco:
            fondo = Image.new("RGB", img.size, AMARILLO)
            fondo.paste(img, mask=img.split()[3])
            img = fondo
        img.save(destino / nombre, "PNG", optimize=True)
        hechos.append(destino / nombre)

    def svg(texto: str, nombre: str):
        (destino / nombre).write_text(texto, encoding="utf-8")
        hechos.append(destino / nombre)

    # Logos e isotipos en vectorial.
    svg(logo_svg(**SOBRE_CLARO), "logo.svg")
    svg(logo_svg(**SOBRE_AMARILLO), "logo-sobre-amarillo.svg")
    svg(logo_svg(**SOBRE_OSCURO), "logo-sobre-oscuro.svg")
    svg(logo_svg(**SOBRE_OSCURO, fondo=CARBON), "logo-fondo-oscuro.svg")
    svg(isotipo_svg(), "isotipo.svg")
    svg(isotipo_svg(CARBON, CARBON), "isotipo-negro.svg")
    svg(isotipo_svg(BLANCO, BLANCO), "isotipo-blanco.svg")
    svg(icono_svg(), "icono-app.svg")
    svg(icono_svg(CARBON, AMARILLO, BLANCO), "icono-app-oscuro.svg")
    # Logos en PNG (para documentos, prensa o la ficha de la tienda).
    png(logo_png(240, SOBRE_CLARO), "logo.png")
    png(logo_png(240, SOBRE_OSCURO), "logo-sobre-oscuro.png")
    # Apps: iOS (cuadrado y opaco; Apple redondea las esquinas) y Google Play.
    png(icono_png(1024), "app-ios-1024.png", opaco=True)
    png(icono_png(512), "app-play-512.png", opaco=True)
    # Android, icono adaptable: el isotipo dentro de la zona segura (66 %) y el fondo amarillo aparte.
    png(icono_png(432, zona=0.56, transparente=True), "android-adaptable-primer-plano-432.png")
    png(Image.new("RGBA", (432, 432), AMARILLO), "android-adaptable-fondo-432.png")
    # Web: pantalla de inicio del iPhone, web instalable (PWA) y favicon (en oscuro: se distingue mejor en pequeño).
    png(icono_png(180), "apple-touch-icon.png", opaco=True)
    png(icono_png(192, redondeo=0.22), "icono-192.png")
    png(icono_png(512, redondeo=0.22), "icono-512.png")
    png(icono_png(512, zona=0.6), "icono-maskable-512.png", opaco=True)
    oscuro = dict(fondo=CARBON, colores=SOBRE_OSCURO, redondeo=0.22, zona=0.8)
    png(icono_png(48, **oscuro), "favicon-48.png")
    icono_png(256, **oscuro).save(destino / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    hechos.append(destino / "favicon.ico")
    favicon = icono_svg(CARBON, AMARILLO, BLANCO, transformacion="translate(36 150) scale(2.0)")
    (RAIZ / "generador" / "estatico" / "icono.svg").write_text(favicon, encoding="utf-8")
    return hechos


if __name__ == "__main__":
    for r in generar():
        print(r.relative_to(RAIZ))
