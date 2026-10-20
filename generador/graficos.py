"""Gráficos en SVG generados en el servidor (sin librerías). Las etiquetas van en HTML posicionado
en porcentajes, para que el texto no se deforme al estirar el gráfico al ancho del móvil."""
import math
from datetime import date

from markupsafe import Markup, escape

from .texto import fecha_corta


def _fmt(v: float, dec: int = 3) -> str:
    return f"{v:.{dec}f}".replace(".", ",")


def _paso(rango: float) -> float:
    """Paso redondo para 3-5 líneas de referencia."""
    for p in (0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5):
        if rango / p <= 4:
            return p
    return 1.0


def evolucion(puntos: list[tuple[date, float]]) -> Markup:
    """Línea de un solo combustible (últimos días). Vacío si hay menos de 2 días."""
    puntos = sorted(puntos)
    if len(puntos) < 2:
        return Markup("")
    valores = [v for _, v in puntos]
    vmin, vmax = min(valores), max(valores)
    paso = _paso(max(vmax - vmin, 0.004))
    bajo = math.floor(vmin / paso) * paso
    alto = math.ceil(vmax / paso) * paso
    if alto <= vmax:  # la línea de arriba queda por encima del máximo
        alto += paso
    if bajo >= vmin:
        bajo -= paso
    f0, f1 = puntos[0][0].toordinal(), puntos[-1][0].toordinal()
    span = max(f1 - f0, 1)

    def x(f: date) -> float:
        return (f.toordinal() - f0) / span * 100

    def y(v: float) -> float:
        return (alto - v) / (alto - bajo) * 100

    svg = ['<svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">']
    etiquetas = []
    n_lineas = round((alto - bajo) / paso)
    for i in range(n_lineas + 1):
        v = bajo + i * paso
        svg.append(f'<line class="rejilla" x1="0" x2="100" y1="{y(v):.2f}" y2="{y(v):.2f}"/>')
        etiquetas.append(f'<span class="eje-y" style="top:{y(v):.2f}%">{_fmt(v, 3 if paso < 0.01 else 2)}</span>')
    pts = " ".join(f"{x(f):.2f},{y(v):.2f}" for f, v in puntos)
    svg.append(f'<polyline class="linea" points="{pts}"/>')
    svg.append("</svg>")
    # Fechas: hasta 5, repartidas.
    n = len(puntos)
    indices = sorted({round(i * (n - 1) / 4) for i in range(5)}) if n > 5 else range(n)
    indices = list(indices)
    for i in indices:
        f = puntos[i][0]
        borde = " primero" if i == indices[0] else (" ultimo" if i == indices[-1] else "")
        etiquetas.append(f'<span class="eje-x{borde}" style="left:{x(f):.2f}%">{fecha_corta(f)}</span>')
    fu, vu = puntos[-1]
    etiquetas.append(f'<span class="punto-hoy" style="left:{x(fu):.2f}%;top:{y(vu):.2f}%"></span>')
    resumen = (f"De {_fmt(valores[0])} € el {fecha_corta(puntos[0][0])} a {_fmt(vu)} € el "
               f"{fecha_corta(fu)}")
    return Markup(f'<figure class="evolucion"><div class="evolucion-plot" role="img" aria-label="{escape(resumen)}">'
                  + "".join(svg) + "".join(etiquetas) + "</div></figure>")


def escalera(precios: list[float], media: float | None) -> Markup:
    """Una marca por gasolinera entre el precio más bajo y el más alto; la más barata en azul.
    Responde de un vistazo a «¿importa dónde reposte aquí?»."""
    if len(precios) < 2:
        return Markup("")
    vmin, vmax = min(precios), max(precios)
    if vmax - vmin < 0.0005:
        return Markup("")

    def x(v: float) -> float:
        return 2 + (v - vmin) / (vmax - vmin) * 96

    marcas = []
    for v in sorted(precios, reverse=True):
        clase = "marca barata" if v == vmin else "marca"
        marcas.append(f'<line class="{clase}" x1="{x(v):.2f}" x2="{x(v):.2f}" y1="20" y2="80"/>')
    svg = ('<svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">'
           '<line class="carril" x1="2" x2="98" y1="50" y2="50"/>' + "".join(marcas) + "</svg>")
    etiquetas = [
        f'<span class="esc-min">{_fmt(vmin)}</span>',
        f'<span class="esc-max">{_fmt(vmax)}</span>',
    ]
    if media is not None:
        pos = min(max(x(media), 14), 86)  # que la etiqueta no pise los extremos
        etiquetas.append(f'<span class="esc-media" style="left:{x(media):.2f}%"></span>'
                         f'<span class="esc-media-txt" style="left:{pos:.2f}%">media {_fmt(media)}</span>')
    resumen = (f"{len(precios)} gasolineras entre {_fmt(vmin)} y {_fmt(vmax)} € el litro")
    return Markup(f'<div class="escalera" role="img" aria-label="{escape(resumen)}">'
                  f'<div class="escalera-plot">{svg}</div>{"".join(etiquetas)}</div>')
