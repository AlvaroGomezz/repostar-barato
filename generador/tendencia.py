"""¿Repostar hoy o esperar? La tendencia de los últimos días a partir del histórico diario.

No es una previsión: dice hacia dónde se ha movido el precio medio y, con datos de varias semanas,
qué día de la semana suele estar más barato."""
from datetime import date, timedelta
from statistics import fmean

from .texto import DIAS, centimos

UMBRAL = 0.01  # un céntimo en una semana ya es una tendencia


def calcular(puntos: list[tuple[date, float]], nombre: str, articulo: str = "el") -> dict:
    """puntos: [(fecha, precio medio)] ordenados, el último es hoy. nombre: "diésel", "gasolina 95"…"""
    puntos = [(f, v) for f, v in puntos if v is not None]
    if len(puntos) < 3:
        return {"estado": "pocos", "titulo": "Estamos reuniendo datos",
                "texto": f"Guardamos el precio cada día. En unos días verás aquí si {articulo} {nombre} sube o baja.",
                "linea": ""}
    hoy_f, hoy_v = puntos[-1]
    desde = hoy_f - timedelta(days=7)
    base_f, base_v = next((f, v) for f, v in puntos if f >= desde)
    dias = max(1, (hoy_f - base_f).days)
    cambio = hoy_v - base_v

    # Días seguidos en la misma dirección, contando desde hoy.
    racha, signo = 0, 0
    for (f0, v0), (f1, v1) in zip(reversed(puntos[:-1]), reversed(puntos[1:])):
        d = v1 - v0
        s = 1 if d > 0.0005 else -1 if d < -0.0005 else 0
        if s == 0 or (signo and s != signo):
            break
        signo, racha = s, racha + 1

    sube = cambio >= UMBRAL or (racha >= 3 and signo > 0)
    baja = cambio <= -UMBRAL or (racha >= 3 and signo < 0)
    comp = "que ayer" if dias == 1 else f"que hace {dias} días"
    en = "desde ayer" if dias == 1 else f"en {dias} días"
    if sube:
        estado, titulo = "sube", "Mejor hoy que mañana"
        texto = (f"{articulo.capitalize()} {nombre} sube: {centimos(cambio)} más {comp}"
                 + (f", y lleva {racha} días seguidos subiendo" if racha >= 2 else "")
                 + ". Si tienes que repostar pronto, no esperes.")
    elif baja:
        estado, titulo = "baja", "Si puedes, espera"
        texto = (f"{articulo.capitalize()} {nombre} baja: {centimos(cambio)} menos {comp}"
                 + (f", y lleva {racha} días seguidos bajando" if racha >= 2 else "")
                 + ". Si no tienes prisa, puede que en unos días pagues algo menos.")
    else:
        estado, titulo = "estable", "Sin prisa"
        texto = (f"{articulo.capitalize()} {nombre} apenas se mueve ({centimos(cambio)} de diferencia {en}). "
                 "Lo que más ahorra es elegir bien la gasolinera.")

    # Con tres semanas o más: el día de la semana que suele estar más barato.
    dia = ""
    if len(puntos) >= 21:
        valores = dict(puntos)
        desv: dict[int, list[float]] = {}
        for f, v in puntos:
            vecinos = [valores[f + timedelta(days=k)] for k in range(-3, 4) if (f + timedelta(days=k)) in valores]
            if len(vecinos) >= 5:
                desv.setdefault(f.weekday(), []).append(v - fmean(vecinos))
        medias = {d: fmean(x) for d, x in desv.items() if len(x) >= 3}
        if len(medias) == 7:
            mejor = min(medias, key=medias.get)
            if medias[mejor] <= -0.002:
                dia = (f"En las últimas semanas, el {DIAS[mejor]} ha sido el día más barato: "
                       f"{centimos(medias[mejor])} por debajo de lo normal.")

    # Línea de los últimos 14 días para un gráfico pequeño (coordenadas en un lienzo de 120 × 32).
    ultimos = puntos[-14:]
    vmin, vmax = min(v for _, v in ultimos), max(v for _, v in ultimos)
    rango = (vmax - vmin) or 1
    paso = 120 / max(1, len(ultimos) - 1)
    linea = " ".join(f"{i * paso:.1f},{30 - (v - vmin) / rango * 28:.1f}" for i, (_, v) in enumerate(ultimos))
    return {"estado": estado, "titulo": titulo, "texto": texto, "dia": dia, "linea": linea,
            "cambio": cambio, "dias": dias, "nota": "Es la tendencia de los últimos días, no una previsión."}
