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


def _filas_cursor(puntos, x, y, fecha_txt) -> list:
    filas = []
    for p in puntos:
        f, v = p[0], p[1]
        franja = f"{_fmt(p[2])} – {_fmt(p[3])}" if len(p) > 3 and p[2] is not None and p[3] is not None else ""
        filas.append([round(x(f), 2), round(y(v), 2), fecha_txt(f), _fmt(v), franja])
    return filas


def _datos_cursor(puntos, x, y, fecha_txt) -> str:
    import json
    return escape(json.dumps(_filas_cursor(puntos, x, y, fecha_txt), ensure_ascii=False, separators=(",", ":")))


def _fecha_larga(f) -> str:
    from .texto import fecha_media
    return fecha_media(f)


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
    datos = _datos_cursor(puntos, x, y, _fecha_larga)
    return Markup(f'<figure class="evolucion"><div class="evolucion-plot" role="img" aria-label="{escape(resumen)}" data-serie="{datos}">'
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

    # Antes era una línea por gasolinera (862 en Madrid, por cada combustible). Ahora las marcas se juntan
    # en 3 trazos según cuántas caen en el mismo sitio, para que las zonas con muchas sigan viéndose más oscuras.
    cuenta: dict[float, int] = {}
    for v in precios:
        if v != vmin:
            k = round(x(v) * 2) / 2
            cuenta[k] = cuenta.get(k, 0) + 1
    niveles = {1: [], 2: [], 3: []}
    for k, n in sorted(cuenta.items()):
        niveles[1 if n == 1 else 2 if n <= 3 else 3].append(f"M{k:g} 20V80")
    marcas = [f'<path class="marca m{nivel}" d="{"".join(d)}"/>' for nivel, d in niveles.items() if d]
    marcas.append(f'<line class="marca barata" x1="{x(vmin):.2f}" x2="{x(vmin):.2f}" y1="20" y2="80"/>')
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


def evolucion_banda(puntos: list[tuple], etiqueta: str = "", ref: str = "", almacen: dict | None = None) -> Markup:
    """Media diaria con la franja del 50 % central de gasolineras (percentiles 25 a 75).
    puntos: [(fecha, media, p25 | None, p75 | None)]."""
    puntos = sorted(p for p in puntos if p[1] is not None)
    if len(puntos) < 2:
        return Markup("")
    banda = [p for p in puntos if p[2] is not None and p[3] is not None]
    valores = [p[1] for p in puntos] + [p[2] for p in banda] + [p[3] for p in banda]
    vmin, vmax = min(valores), max(valores)
    paso = _paso(max(vmax - vmin, 0.004))
    bajo = math.floor(vmin / paso) * paso
    alto = math.ceil(vmax / paso) * paso
    if alto <= vmax:
        alto += paso
    if bajo >= vmin:
        bajo -= paso
    f0, f1 = puntos[0][0].toordinal(), puntos[-1][0].toordinal()
    span = max(f1 - f0, 1)

    def x(f) -> float:
        return (f.toordinal() - f0) / span * 100

    def y(v: float) -> float:
        return (alto - v) / (alto - bajo) * 100

    svg = ['<svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">']
    etiquetas = []
    for i in range(round((alto - bajo) / paso) + 1):
        v = bajo + i * paso
        svg.append(f'<line class="rejilla" x1="0" x2="100" y1="{y(v):.2f}" y2="{y(v):.2f}"/>')
        etiquetas.append(f'<span class="eje-y" style="top:{y(v):.2f}%">{_fmt(v, 3 if paso < 0.01 else 2)}</span>')
    if len(banda) >= 2:
        arriba = " ".join(f"{x(f):.2f},{y(p75):.2f}" for f, _, _, p75 in banda)
        abajo = " ".join(f"{x(f):.2f},{y(p25):.2f}" for f, _, p25, _ in reversed(banda))
        svg.append(f'<polygon class="banda" points="{arriba} {abajo}"/>')
    pts = " ".join(f"{x(f):.2f},{y(v):.2f}" for f, v, _, _ in puntos)
    svg.append(f'<polyline class="linea" points="{pts}"/>')
    svg.append("</svg>")
    n = len(puntos)
    indices = sorted({round(i * (n - 1) / 4) for i in range(5)}) if n > 5 else list(range(n))
    largo = span > 120
    for i in indices:
        f = puntos[i][0]
        borde = " primero" if i == indices[0] else (" ultimo" if i == indices[-1] else "")
        texto = f"{fecha_corta(f)} {str(f.year)[2:]}" if largo else fecha_corta(f)
        etiquetas.append(f'<span class="eje-x{borde}" style="left:{x(f):.2f}%">{texto}</span>')
    fu, vu = puntos[-1][0], puntos[-1][1]
    etiquetas.append(f'<span class="punto-hoy" style="left:{x(fu):.2f}%;top:{y(vu):.2f}%"></span>')
    resumen = (f"{etiqueta}: de {_fmt(puntos[0][1])} € el {fecha_corta(puntos[0][0])} a {_fmt(vu)} € el "
               f"{fecha_corta(fu)}")
    if ref and almacen is not None:
        # Los datos del cursor van en un archivo aparte (/datos/graficos.json) que se pide al tocar el
        # gráfico: en la portada eran 226 KB de HTML para 16 gráficos de los que solo se ve uno.
        almacen[ref] = _filas_cursor(puntos, x, y, _fecha_larga)
        atributo = f'data-serie-ref="{escape(ref)}"'
    else:
        atributo = f'data-serie="{_datos_cursor(puntos, x, y, _fecha_larga)}"'
    return Markup(f'<figure class="evolucion"><div class="evolucion-plot" role="img" aria-label="{escape(resumen)}" {atributo}>'
                  + "".join(svg) + "".join(etiquetas) + "</div></figure>")
