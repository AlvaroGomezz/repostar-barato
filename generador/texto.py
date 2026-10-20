"""Utilidades de texto: slugs, nombres, fechas y precios en español."""
import re
import unicodedata
from datetime import date, datetime

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

_MINUSCULAS = {"de", "del", "la", "las", "el", "los", "y", "e", "a", "en", "con", "por", "al",
               "d'", "l'", "i", "o", "da", "do", "dos", "das", "s/n", "km", "km."}
_ROMANOS = {"ii", "iii", "iv", "vi", "vii", "viii", "ix", "xi", "xii"}


def slug(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t or "sin-nombre"


def nombre_bonito(nombre: str) -> str:
    """'Pastoriza (A)' -> 'A Pastoriza'; "Hospitalet de Llobregat (L')" -> "L'Hospitalet de Llobregat"."""
    nombre = " ".join(nombre.split())
    m = re.match(r"^(.*?)\s*\(([^)]+)\)$", nombre)
    if m:
        base, articulo = m.groups()
        separador = "" if articulo.endswith("'") else " "
        nombre = f"{articulo}{separador}{base}"
    return nombre


def capitalizar(texto: str) -> str:
    """'AVENIDA CASTILLA LA MANCHA, 26' -> 'Avenida Castilla la Mancha, 26'."""
    palabras = " ".join(texto.split()).lower().split(" ")
    salida = []
    for i, p in enumerate(palabras):
        limpia = p.strip(",.()")
        if limpia in _ROMANOS or re.match(r"^[a-z]{1,3}-[0-9ivx]+[a-z]?$", limpia):  # N-IV, AP-7, CV-500
            salida.append(p.upper())
        elif i > 0 and p in _MINUSCULAS:
            salida.append(p)
        else:
            salida.append(p[:1].upper() + p[1:])
    return " ".join(salida)


def precio(valor: float | None, decimales: int = 3) -> str:
    if valor is None:
        return "—"
    return f"{valor:.{decimales}f}".replace(".", ",") + " €"


def numero(valor: float, decimales: int = 2) -> str:
    return f"{valor:,.{decimales}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def centimos(diferencia: float) -> str:
    """0.0123 -> '1,2 céntimos'."""
    c = abs(diferencia) * 100
    unidad = "céntimo" if round(c, 1) == 1 else "céntimos"
    return f"{numero(c, 1)} {unidad}"


def fecha_larga(d: date | datetime) -> str:
    """'martes 20 de octubre de 2026'."""
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]} de {d.year}"


def fecha_media(d: date | datetime) -> str:
    """'20 de octubre de 2026'."""
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def fecha_corta(d: date | datetime) -> str:
    """'20 oct'."""
    return f"{d.day} {MESES_CORTOS[d.month - 1]}"


def hora(d: datetime) -> str:
    return d.strftime("%H:%M")
