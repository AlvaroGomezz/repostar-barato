"""Vídeo vertical del día (1080 × 1920, unos 15 s) para Instagram Reels, TikTok y estados de WhatsApp.

Uso: python -m generador.video   (después de generar la web, que deja los datos en aviso/video.json)

Se dibuja fotograma a fotograma con Pillow, con la misma identidad que las imágenes de la web, y se
codifica con ffmpeg. No lleva sonido: la música se añade al subirlo desde la app. Si algo falla, avisa
y termina sin error, para no parar la publicación de la web."""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from .config import RAIZ
from .imagenes import AMARILLO, BLANCO, GRIS, ROJO, SUAVE, TINTA, VERDE, _lineas, fuente
from .texto import numero

ANCHO, ALTO = 1080, 1920
FPS = 30
MARGEN = 84
SALIDA_ANIM = 0.25  # segundos que tarda cada escena en desvanecerse
DATOS = RAIZ / "aviso" / "video.json"


# ---------- utilidades de animación ----------

def _suave(p: float) -> float:
    """Ease-out cúbico entre 0 y 1."""
    p = min(1.0, max(0.0, p))
    return 1 - (1 - p) ** 3


def _mezcla(fondo, color, a: float):
    return tuple(round(f + (c - f) * a) for f, c in zip(fondo, color))


class Escena:
    """Lo que dura una escena y cómo entra cada elemento (sube un poco y aparece)."""

    def __init__(self, t: float, duracion: float):
        self.t, self.duracion = t, duracion

    def alfa(self, inicio: float, dur: float = 0.45) -> float:
        entra = _suave((self.t - inicio) / dur)
        sale = 1 - _suave((self.t - (self.duracion - SALIDA_ANIM)) / SALIDA_ANIM)
        return min(entra, sale)

    def subida(self, inicio: float, dur: float = 0.45, px: int = 70) -> int:
        return round((1 - _suave((self.t - inicio) / dur)) * px)

    def progreso(self, inicio: float, dur: float) -> float:
        return _suave((self.t - inicio) / dur)


def _precio(v: float) -> str:
    return f"{v:.3f}".replace(".", ",")


def _texto(d, xy, texto, tam, peso, color, a, fondo=AMARILLO, anchor="la"):
    if a > 0:
        d.text(xy, texto, font=fuente(tam, peso), fill=_mezcla(fondo, color, a), anchor=anchor)


def _parrafo(d, x, y, texto, tam, peso, color, a, ancho, interlineado=1.18, fondo=AMARILLO, max_lineas=8):
    f = fuente(tam, peso)
    lineas = _lineas(d, texto, f, ancho)[:max_lineas]
    for linea in lineas:
        if a > 0:
            d.text((x, y), linea, font=f, fill=_mezcla(fondo, color, a))
        y += round(tam * interlineado)
    return y


def _caja(d, xy, a, color=BLANCO, radio=36, fondo=AMARILLO):
    if a > 0:
        d.rounded_rectangle(xy, radius=radio, fill=_mezcla(fondo, color, a))


def _recortar(d, texto: str, tam: int, peso: int, ancho: int) -> str:
    f = fuente(tam, peso)
    if d.textlength(texto, font=f) <= ancho:
        return texto
    while texto and d.textlength(texto + "…", font=f) > ancho:
        texto = texto[:-1]
    return texto.rstrip() + "…"


def _triangulo(d, x, y, sube: bool, color, tam=26):
    if sube:
        d.polygon([(x, y + tam), (x + tam, y + tam), (x + tam / 2, y)], fill=color)
    else:
        d.polygon([(x, y), (x + tam, y), (x + tam / 2, y + tam)], fill=color)


_logos: dict[int, Image.Image] = {}


def _logo(img: Image.Image, y: int, h: int, a: float):
    """El logo de GASVIA centrado arriba, con la transparencia de la animación."""
    if a <= 0:
        return
    if h not in _logos:
        from .marca import SOBRE_AMARILLO, logo_png
        _logos[h] = logo_png(h, SOBRE_AMARILLO)
    logo = _logos[h]
    if a < 1:
        logo = logo.copy()
        logo.putalpha(logo.getchannel("A").point(lambda v: round(v * a)))
    img.paste(logo, ((ANCHO - logo.width) // 2, y), logo)


def _cabecera(img, d, e: Escena, etiqueta: str):
    """Logo y una etiqueta pequeña encima del título de la escena."""
    _logo(img, 230, 58, e.alfa(0))
    if etiqueta:
        a = e.alfa(0.05)
        _texto(d, (ANCHO // 2, 360 + e.subida(0.05)), etiqueta.upper(), 38, 700, SUAVE, a, anchor="ma")


# ---------- escenas ----------

def escena_portada(img, d, e: Escena, datos):
    _logo(img, 250, 74, e.alfa(0))
    # La fecha, en una pastilla negra.
    a = e.alfa(0.12)
    if a > 0:
        f = fuente(40, 700)
        texto = datos["fecha_texto"].upper()
        w = d.textlength(texto, font=f)
        y = 400 + e.subida(0.12)
        x0 = (ANCHO - w) / 2 - 36
        d.rounded_rectangle([x0, y, x0 + w + 72, y + 82], radius=41, fill=_mezcla(AMARILLO, TINTA, a))
        d.text((ANCHO / 2, y + 41), texto, font=f, fill=_mezcla(AMARILLO, BLANCO, a), anchor="mm")
    # La pregunta que engancha, línea a línea.
    y = 640
    for i, linea in enumerate(["¿Dónde está", "la gasolina", "más barata", "HOY?"]):
        inicio = 0.3 + i * 0.14
        tam = 150 if i < 3 else 230
        _texto(d, (MARGEN, y + e.subida(inicio)), linea, tam, 800, TINTA, e.alfa(inicio))
        y += round(tam * 1.02)
    _texto(d, (MARGEN, y + 40 + e.subida(1.0)), "Precios oficiales de hoy en toda España", 44, 500, SUAVE, e.alfa(1.0))


def escena_medias(img, d, e: Escena, datos):
    _cabecera(img, d, e, "Precio medio en España")
    y = 470
    for i, m in enumerate(datos["medias"][:2]):
        inicio = 0.15 + i * 0.3
        a = e.alfa(inicio)
        dy = e.subida(inicio)
        alto = 420
        _caja(d, [MARGEN, y + dy, ANCHO - MARGEN, y + dy + alto], a)
        x = MARGEN + 56
        _texto(d, (x, y + dy + 52), m["nombre"], 54, 700, GRIS, a, fondo=BLANCO)
        # La cifra cuenta hacia arriba hasta el precio de hoy.
        p = e.progreso(inicio + 0.1, 1.1)
        valor = m["valor"] - 0.06 * (1 - p)
        fv = fuente(200, 800)
        txt = _precio(valor)
        _texto(d, (x - 6, y + dy + 130), txt, 200, 800, TINTA, a, fondo=BLANCO)
        _texto(d, (x + d.textlength(txt, font=fv) + 14, y + dy + 238), "€/l", 60, 600, GRIS, a, fondo=BLANCO)
        if m.get("nota"):
            color = ROJO if m["sentido"] > 0 else VERDE if m["sentido"] < 0 else GRIS
            an = e.alfa(inicio + 0.9)
            xn = x + (40 if m["sentido"] else 0)
            if m["sentido"] and an > 0:
                _triangulo(d, x, y + dy + 352, m["sentido"] > 0, _mezcla(BLANCO, color, an))
            _texto(d, (xn, y + dy + 344), m["nota"], 44, 700, color, an, fondo=BLANCO)
        y += alto + 60


def escena_ciudades(img, d, e: Escena, datos):
    _cabecera(img, d, e, "")
    a = e.alfa(0.05)
    _texto(d, (MARGEN, 330 + e.subida(0.05)), "El diésel más", 96, 800, TINTA, a)
    _texto(d, (MARGEN, 430 + e.subida(0.05)), "barato hoy en…", 96, 800, TINTA, a)
    filas = datos["ciudades"][:6]
    alto_fila = 162
    y0 = 590
    _caja(d, [MARGEN - 20, y0, ANCHO - MARGEN + 20, y0 + 30 + alto_fila * len(filas)], e.alfa(0.15))
    for i, c in enumerate(filas):
        inicio = 0.35 + i * 0.28
        af = e.alfa(inicio)
        y = y0 + 34 + i * alto_fila + e.subida(inicio, px=40)
        if i and af > 0:
            d.line([MARGEN + 20, y - 18, ANCHO - MARGEN - 20, y - 18], fill=_mezcla(BLANCO, (230, 226, 216), af), width=3)
        precio = _precio(c["precio"]) + " €"
        fp = fuente(76, 800)
        wp = d.textlength(precio, font=fp)
        ancho_nombre = ANCHO - 2 * MARGEN - wp - 60
        _texto(d, (MARGEN + 20, y), _recortar(d, c["nombre"], 56, 700, ancho_nombre), 56, 700, TINTA, af, fondo=BLANCO)
        _texto(d, (MARGEN + 20, y + 70), _recortar(d, c["rotulo"], 34, 500, ancho_nombre), 34, 500, GRIS, af, fondo=BLANCO)
        _texto(d, (ANCHO - MARGEN - 20, y + 16), precio, 76, 800, VERDE if i == 0 else TINTA, af, fondo=BLANCO, anchor="ra")


def escena_ahorro(img, d, e: Escena, datos):
    ah = datos["ahorro"]
    _cabecera(img, d, e, f"En {ah['ciudad']}")
    _texto(d, (MARGEN, 560 + e.subida(0.15)), "Te puedes ahorrar", 84, 700, TINTA, e.alfa(0.15))
    _texto(d, (MARGEN, 660 + e.subida(0.3)), "hasta", 84, 700, TINTA, e.alfa(0.3))
    p = e.progreso(0.4, 1.2)
    euros = numero(ah["euros"] * p) + " €"
    a = e.alfa(0.4)
    # La cifra en una franja negra, para que se lea de un vistazo.
    if a > 0:
        y = 800 + e.subida(0.4)
        d.rounded_rectangle([MARGEN - 20, y, ANCHO - MARGEN + 20, y + 300], radius=40, fill=_mezcla(AMARILLO, TINTA, a))
        d.text((ANCHO / 2, y + 150), euros, font=fuente(210, 800), fill=_mezcla(TINTA, AMARILLO, a), anchor="mm")
    _parrafo(d, MARGEN, 1170 + e.subida(1.0),
             f"en un depósito de {ah['litros']} litros de diésel, solo por elegir la gasolinera más barata en vez de la más cara.",
             56, 600, TINTA, e.alfa(1.0), ANCHO - 2 * MARGEN)


def escena_tendencia(img, d, e: Escena, datos):
    t = datos["tendencia"]
    _cabecera(img, d, e, "¿Repostar hoy o esperar?")
    color = ROJO if t["estado"] == "sube" else VERDE if t["estado"] == "baja" else TINTA
    y = _parrafo(d, MARGEN, 520 + e.subida(0.15), t["titulo"], 140, 800, color, e.alfa(0.15), ANCHO - 2 * MARGEN,
                 interlineado=1.02, max_lineas=3)
    _parrafo(d, MARGEN, y + 60 + e.subida(0.5), t["texto"], 54, 500, TINTA, e.alfa(0.5), ANCHO - 2 * MARGEN, max_lineas=7)


def escena_final(img, d, e: Escena, datos):
    _logo(img, 300, 74, e.alfa(0))
    y = 640
    for i, linea in enumerate(["Busca la", "más barata", "de tu pueblo"]):
        inicio = 0.1 + i * 0.12
        _texto(d, (ANCHO // 2, y + e.subida(inicio)), linea, 124, 800, TINTA, e.alfa(inicio), anchor="ma")
        y += 132
    a = e.alfa(0.55)
    if a > 0:
        y = 1100 + e.subida(0.55)
        f = fuente(104, 800)
        w = d.textlength("gasvia.es", font=f)
        d.rounded_rectangle([(ANCHO - w) / 2 - 60, y, (ANCHO + w) / 2 + 60, y + 170], radius=85, fill=_mezcla(AMARILLO, TINTA, a))
        d.text((ANCHO / 2, y + 85), "gasvia.es", font=f, fill=_mezcla(TINTA, AMARILLO, a), anchor="mm")
    _texto(d, (ANCHO // 2, 1330 + e.subida(0.8)), "Enlace en el perfil", 48, 600, SUAVE, e.alfa(0.8), anchor="ma")


def escenas(datos) -> list[tuple]:
    """Las escenas del vídeo con su duración en segundos. Se saltan las que no tienen datos."""
    lista = [(escena_portada, 2.6)]
    if datos.get("medias"):
        lista.append((escena_medias, 3.4))
    if datos.get("ciudades"):
        lista.append((escena_ciudades, 4.2))
    if datos.get("ahorro"):
        lista.append((escena_ahorro, 3.4))
    if datos.get("tendencia"):
        lista.append((escena_tendencia, 3.4))
    lista.append((escena_final, 2.8))
    return lista


def fotograma(datos, t: float, lista=None) -> Image.Image:
    """El fotograma del segundo t del vídeo."""
    lista = lista or escenas(datos)
    img = Image.new("RGB", (ANCHO, ALTO), AMARILLO)
    d = ImageDraw.Draw(img)
    inicio = 0.0
    for i, (dibujar, dur) in enumerate(lista):
        if t < inicio + dur or i == len(lista) - 1:
            dibujar(img, d, Escena(t - inicio, dur), datos)
            break
        inicio += dur
    return img


def duracion(datos) -> float:
    return sum(dur for _, dur in escenas(datos))


def _ffmpeg() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001 - si no está el paquete, se busca ffmpeg en el sistema
        exe = shutil.which("ffmpeg")
        if not exe:
            raise RuntimeError("No se encuentra ffmpeg")
        return exe


def crear(datos, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    lista = escenas(datos)
    total = round(duracion(datos) * FPS)
    temporal = destino.with_suffix(".tmp.mp4")
    orden = [_ffmpeg(), "-y", "-loglevel", "error",
             "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{ANCHO}x{ALTO}", "-r", str(FPS), "-i", "-",
             "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
             "-movflags", "+faststart", str(temporal)]
    proc = subprocess.Popen(orden, stdin=subprocess.PIPE)
    try:
        for i in range(total):
            proc.stdin.write(fotograma(datos, i / FPS, lista).tobytes())
    finally:
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError(f"ffmpeg terminó con el código {proc.returncode}")
    temporal.replace(destino)
    # Portada para la publicación: la lista de ciudades completa (o la portada si no la hay).
    t_portada, inicio = 1.8, 0.0
    for dibujar, dur in lista:
        if dibujar is escena_ciudades:
            t_portada = inicio + dur - SALIDA_ANIM - 0.05
        inicio += dur
    fotograma(datos, t_portada, lista).save(destino.parent / "portada.jpg", "JPEG", quality=88, optimize=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Crea el vídeo vertical del día.")
    ap.add_argument("--datos", default=str(DATOS))
    ap.add_argument("--salida", help="fichero .mp4 de destino (por defecto, el que indica la web)")
    args = ap.parse_args()
    ruta = Path(args.datos)
    if not ruta.exists():
        print("No hay datos para el vídeo: genera antes la web.")
        return 0
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    destino = Path(args.salida or datos["destino"])
    try:
        crear(datos, destino)
    except Exception as e:  # noqa: BLE001 - un fallo del vídeo no debe parar la web
        print(f"::warning::No se pudo crear el vídeo del día: {e}")
        return 0
    print(f"Vídeo del día: {destino} ({destino.stat().st_size // 1024} KB, {duracion(datos):.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
