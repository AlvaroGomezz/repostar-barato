"""El logo de Repostar Barato: una gota de combustible con una flecha hacia abajo (el precio que baja).

Genera el favicon (SVG), el logo horizontal y los iconos para la web, la app de iOS y la de Android.
Uso: python -m generador.marca   (escribe en generador/estatico/marca/ y generador/estatico/icono.svg)"""
import math
from pathlib import Path

from PIL import Image, ImageDraw

from .config import RAIZ

AMARILLO = "#ffd43b"
TINTA = "#141414"
BLANCO = "#ffffff"
DESTINO = RAIZ / "generador" / "estatico" / "marca"

# Gota en un lienzo de 100 × 100: punta arriba, círculo de radio R centrado en (50, CY).
R, CY, PUNTA = 27, 62, 12
GROSOR = 9  # la flecha


def _tangentes():
    d = CY - PUNTA
    phi = math.acos(R / d)
    a1, a2 = -math.pi / 2 + phi, -math.pi / 2 - phi
    return a1, a2


def gota_svg(color=TINTA, hueco=AMARILLO, escala=1.0, dx=0.0, dy=0.0) -> str:
    a1, a2 = _tangentes()
    p = lambda x, y: f"{dx + x * escala:.2f} {dy + y * escala:.2f}"  # noqa: E731
    x1, y1 = 50 + R * math.cos(a1), CY + R * math.sin(a1)
    x2, y2 = 50 + R * math.cos(a2), CY + R * math.sin(a2)
    r = R * escala
    gota = f'<path d="M{p(50, PUNTA)} L{p(x1, y1)} A{r:.2f} {r:.2f} 0 1 1 {p(x2, y2)} Z" fill="{color}"/>'
    w = GROSOR * escala
    flecha = (f'<path d="M{p(50, 45)} L{p(50, 75)} M{p(38.5, 63.5)} L{p(50, 75)} L{p(61.5, 63.5)}" fill="none" '
              f'stroke="{hueco}" stroke-width="{w:.2f}" stroke-linecap="round" stroke-linejoin="round"/>')
    return gota + flecha


def gota_d() -> str:
    """El trazado de la gota (lienzo de 100 × 100), para dibujarla en la web."""
    a1, a2 = _tangentes()
    x1, y1 = 50 + R * math.cos(a1), CY + R * math.sin(a1)
    x2, y2 = 50 + R * math.cos(a2), CY + R * math.sin(a2)
    return f"M50 {PUNTA} L{x1:.2f} {y1:.2f} A{R} {R} 0 1 1 {x2:.2f} {y2:.2f} Z"


FLECHA_D = "M50 45 L50 75 M38.5 63.5 L50 75 L61.5 63.5"


def icono_svg(fondo=AMARILLO, redondeo=22) -> str:
    """Icono cuadrado (favicon, accesos directos)."""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            f'<rect width="100" height="100" rx="{redondeo}" fill="{fondo}"/>{gota_svg(escala=.86, dx=7, dy=7)}</svg>')


def simbolo_svg(clase="marca-simbolo") -> str:
    """Solo la gota, para la cabecera de la web (el color sale de currentColor)."""
    return (f'<svg class="{clase}" viewBox="10 8 80 84" width="22" height="24" aria-hidden="true">'
            + gota_svg(color="currentColor", hueco=AMARILLO) + "</svg>")


def logo_svg(fondo=None) -> str:
    """Logo horizontal: icono y nombre."""
    caja = f'<rect width="520" height="120" fill="{fondo}"/>' if fondo else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 520 120">{caja}'
            f'<rect x="10" y="10" width="100" height="100" rx="22" fill="{AMARILLO}"/>{gota_svg(escala=.86, dx=17, dy=17)}'
            f'<text x="134" y="78" font-family="Albert Sans, Helvetica Neue, Arial, sans-serif" font-weight="700" '
            f'font-size="50" letter-spacing="-1.5" fill="{TINTA}">Repostar Barato</text></svg>')


# ---------- versiones en PNG (dibujadas a 4× y reducidas, para bordes suaves) ----------

def _dibujar(tam: int, fondo: str | None, redondeo: float, zona: float, color=TINTA, hueco=AMARILLO) -> Image.Image:
    """zona: parte del lado que ocupa el dibujo de 100 × 100 de la gota (1 = todo)."""
    k = 4
    t = tam * k
    img = Image.new("RGBA", (t, t), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if fondo:
        d.rounded_rectangle([0, 0, t - 1, t - 1], radius=round(t * redondeo), fill=fondo)
    esc = t * zona / 100
    off = (t - 100 * esc) / 2
    q = lambda x, y: (off + x * esc, off + y * esc)  # noqa: E731
    a1, a2 = _tangentes()
    pts = [q(50, PUNTA)]
    pasos = 160
    total = (a2 + 2 * math.pi) - a1
    for i in range(pasos + 1):
        a = a1 + total * i / pasos
        pts.append(q(50 + R * math.cos(a), CY + R * math.sin(a)))
    d.polygon(pts, fill=color)
    w = round(GROSOR * esc)

    def trazo(puntos):
        d.line([q(*p) for p in puntos], fill=hueco, width=w, joint="curve")
        for p in (puntos[0], puntos[-1]):
            cx, cy = q(*p)
            d.ellipse([cx - w / 2, cy - w / 2, cx + w / 2, cy + w / 2], fill=hueco)

    trazo([(50, 45), (50, 75)])
    trazo([(38.5, 63.5), (50, 75), (61.5, 63.5)])
    return img.resize((tam, tam), Image.LANCZOS)


def generar(destino: Path = DESTINO) -> list[Path]:
    destino.mkdir(parents=True, exist_ok=True)
    hechos = []

    def guardar(img: Image.Image, nombre: str, opaco: bool = False):
        ruta = destino / nombre
        if opaco:
            fondo = Image.new("RGB", img.size, AMARILLO)
            fondo.paste(img, mask=img.split()[3])
            img = fondo
        img.save(ruta, "PNG", optimize=True)
        hechos.append(ruta)

    # iOS (App Store): 1024 × 1024, cuadrado y sin transparencia; Apple redondea las esquinas.
    guardar(_dibujar(1024, AMARILLO, 0, .86), "app-ios-1024.png", opaco=True)
    # Google Play: 512 × 512, cuadrado; Google aplica su propia máscara.
    guardar(_dibujar(512, AMARILLO, 0, .86), "app-play-512.png", opaco=True)
    # Android, icono adaptable: primer plano transparente (la gota dentro de la zona segura) y fondo amarillo.
    guardar(_dibujar(432, None, 0, .56), "android-adaptable-primer-plano-432.png")
    guardar(Image.new("RGBA", (432, 432), AMARILLO), "android-adaptable-fondo-432.png")
    # Web: favicon en PNG, icono de iPhone para la pantalla de inicio y los de la app web (PWA).
    guardar(_dibujar(180, AMARILLO, 0, .86), "apple-touch-icon.png", opaco=True)
    guardar(_dibujar(192, AMARILLO, .22, .86), "icono-192.png")
    guardar(_dibujar(512, AMARILLO, .22, .86), "icono-512.png")
    guardar(_dibujar(512, AMARILLO, 0, .62), "icono-maskable-512.png", opaco=True)
    guardar(_dibujar(48, AMARILLO, .22, .86), "favicon-48.png")
    for nombre, svg in (("logo.svg", logo_svg()), ("logo-fondo-blanco.svg", logo_svg(BLANCO)),
                        ("icono.svg", icono_svg()), ("icono-oscuro.svg", icono_svg(fondo=TINTA).replace(
                            f'fill="{TINTA}"/><path', f'fill="{AMARILLO}"/><path', 1))):
        ruta = destino / nombre
        ruta.write_text(svg, encoding="utf-8")
        hechos.append(ruta)
    (RAIZ / "generador" / "estatico" / "icono.svg").write_text(icono_svg(), encoding="utf-8")
    return hechos


if __name__ == "__main__":
    for r in generar():
        print(r.relative_to(RAIZ))
