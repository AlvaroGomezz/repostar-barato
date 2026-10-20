"""Gráficos de evolución de precios en SVG, generados en el servidor (sin librerías externas)."""
from datetime import date

from markupsafe import Markup, escape

from .texto import fecha_corta, precio


def evolucion(series: list[tuple[str, str, list[tuple[date, float]]]], ancho=640, alto=220) -> Markup:
    """series: [(nombre, clase_css, [(fecha, valor), ...]), ...]. Devuelve '' si hay menos de 2 días."""
    series = [(n, c, sorted(p)) for n, c, p in series if len(p) >= 2]
    if not series:
        return Markup("")
    fechas = sorted({f for _, _, p in series for f, _ in p})
    valores = [v for _, _, p in series for _, v in p]
    vmin, vmax = min(valores), max(valores)
    margen = max((vmax - vmin) * 0.12, 0.005)
    vmin, vmax = vmin - margen, vmax + margen
    izq, der, arr, aba = 64, 12, 12, 28
    f0, f1 = fechas[0].toordinal(), fechas[-1].toordinal()
    span = max(f1 - f0, 1)

    def x(f: date) -> float:
        return izq + (f.toordinal() - f0) / span * (ancho - izq - der)

    def y(v: float) -> float:
        return arr + (vmax - v) / (vmax - vmin) * (alto - arr - aba)

    partes = [f'<svg class="grafico" viewBox="0 0 {ancho} {alto}" role="img" '
              f'aria-label="Evolución del precio" preserveAspectRatio="none">']
    for i in range(4):
        v = vmin + (vmax - vmin) * i / 3
        partes.append(f'<line class="rejilla" x1="{izq}" x2="{ancho - der}" y1="{y(v):.1f}" y2="{y(v):.1f}"/>')
        partes.append(f'<text class="eje" x="{izq - 6}" y="{y(v) + 4:.1f}" text-anchor="end">'
                      f'{escape(precio(v))}</text>')
    partes.append(f'<text class="eje" x="{izq}" y="{alto - 8}">{fecha_corta(fechas[0])}</text>')
    partes.append(f'<text class="eje" x="{ancho - der}" y="{alto - 8}" text-anchor="end">'
                  f'{fecha_corta(fechas[-1])}</text>')
    for nombre, clase, puntos in series:
        pts = " ".join(f"{x(f):.1f},{y(v):.1f}" for f, v in puntos)
        partes.append(f'<polyline class="linea {clase}" points="{pts}"><title>{escape(nombre)}</title></polyline>')
        fu, vu = puntos[-1]
        partes.append(f'<circle class="punto {clase}" cx="{x(fu):.1f}" cy="{y(vu):.1f}" r="3.5"/>')
    partes.append("</svg>")
    return Markup("".join(partes))
