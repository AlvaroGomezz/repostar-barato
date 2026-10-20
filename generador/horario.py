"""Convierte el horario del Ministerio ("L-V: 06:00-22:00; S-D: 07:00-22:00") en una semana compacta
que el navegador puede comparar con la hora actual para decir si la gasolinera está abierta.

Formato de salida (texto corto, para estaciones.json):
- "24"                       abierta siempre
- "360-1320"                 el mismo horario los siete días (minutos desde las 00:00; varios tramos con ",")
- "360-1320|...|"            siete campos de lunes a domingo; "" = cerrada ese día, "*" = 24 horas,
                             "?" = no se sabe
- None                       horario que no se entiende: no se dice nada
"""
import re

DIAS = "LMXJVSD"
_TRAMO = re.compile(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})")
_SEGMENTO = re.compile(r"^\s*([LMXJVSD])(?:\s*-\s*([LMXJVSD]))?\s*:\s*(.+?)\s*$")


def _tramos(texto: str) -> str | None:
    t = texto.upper().replace(" ", "")
    if t in ("24H", "24HORAS"):
        return "*"
    tramos = []
    for parte in re.split(r"Y|,", texto, flags=re.IGNORECASE):
        m = _TRAMO.search(parte)
        if not m:
            return None
        h1, m1, h2, m2 = (int(x) for x in m.groups())
        ini, fin = h1 * 60 + m1, h2 * 60 + m2
        if ini > 1440 or fin > 1440:
            return None
        if fin == 0 or (h2 == 23 and m2 == 59):  # hasta medianoche
            fin = 1440
        if ini == 0 and fin == 1440:
            return "*"
        if fin <= ini:  # cruza la medianoche
            fin += 1440
        tramos.append(f"{ini}-{fin}")
    return ",".join(tramos) if tramos else None


def semana(horario: str) -> str | None:
    if not horario or not horario.strip():
        return None
    dias: list[str | None] = [None] * 7
    for seg in horario.split(";"):
        m = _SEGMENTO.match(seg)
        if not m:
            return None
        d1, d2, cuerpo = m.groups()
        i, j = DIAS.index(d1), DIAS.index(d2 or d1)
        valor = _tramos(cuerpo)
        if valor is None:
            return None
        rango = range(i, j + 1) if i <= j else list(range(i, 7)) + list(range(0, j + 1))
        for k in rango:
            dias[k] = valor
    cubiertos = sum(1 for x in dias if x is not None)
    if cubiertos == 1 and dias[0] is not None:
        # "L: 24H" o "L: 06:00-22:00" solo: casi siempre es que se rellenó un único día. Se toma como diario.
        dias = [dias[0]] * 7
        cubiertos = 7
    # Los días que faltan en un horario de varios días se entienden como cerrados ("L-S: ..." = cierra el domingo).
    dias = [("" if x is None else x) for x in dias]
    if all(x == "*" for x in dias):
        return "24"
    if len(set(dias)) == 1:
        return dias[0]
    return "|".join(dias)
