"""Descarga y organiza los precios oficiales del Ministerio para la Transición Ecológica."""
import json
import math
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import requests

from .config import API_URL, COMBUSTIBLES, ZONA
from .texto import capitalizar, nombre_bonito, slug

PROVINCIAS = {
    "01": "Álava", "02": "Albacete", "03": "Alicante", "04": "Almería", "05": "Ávila",
    "06": "Badajoz", "07": "Illes Balears", "08": "Barcelona", "09": "Burgos", "10": "Cáceres",
    "11": "Cádiz", "12": "Castellón", "13": "Ciudad Real", "14": "Córdoba", "15": "A Coruña",
    "16": "Cuenca", "17": "Girona", "18": "Granada", "19": "Guadalajara", "20": "Gipuzkoa",
    "21": "Huelva", "22": "Huesca", "23": "Jaén", "24": "León", "25": "Lleida", "26": "La Rioja",
    "27": "Lugo", "28": "Madrid", "29": "Málaga", "30": "Murcia", "31": "Navarra", "32": "Ourense",
    "33": "Asturias", "34": "Palencia", "35": "Las Palmas", "36": "Pontevedra", "37": "Salamanca",
    "38": "Santa Cruz de Tenerife", "39": "Cantabria", "40": "Segovia", "41": "Sevilla",
    "42": "Soria", "43": "Tarragona", "44": "Teruel", "45": "Toledo", "46": "Valencia",
    "47": "Valladolid", "48": "Bizkaia", "49": "Zamora", "50": "Zaragoza", "51": "Ceuta",
    "52": "Melilla",
}

# Precios fuera de este rango se consideran errores de la fuente.
PRECIO_MIN, PRECIO_MAX = 0.30, 4.00


@dataclass(eq=False)
class Estacion:
    id: str
    rotulo: str
    direccion: str
    cp: str
    horario: str
    lat: float | None
    lon: float | None
    municipio_id: str
    provincia_id: str
    precios: dict[str, float]
    municipio: "Municipio | None" = None

    @property
    def abierta_24h(self) -> bool:
        return "24H" in self.horario.upper().replace(" ", "")

    @property
    def mapa(self) -> str:
        if self.lat is None:
            return ""
        return f"https://www.google.com/maps/search/?api=1&query={self.lat:.6f},{self.lon:.6f}"


@dataclass(eq=False)
class Municipio:
    id: str
    nombre: str
    slug: str
    provincia: "Provincia"
    estaciones: list[Estacion] = field(default_factory=list)
    lat: float | None = None
    lon: float | None = None
    cercanas: list[tuple[Estacion, float]] = field(default_factory=list)

    @property
    def ruta(self) -> str:
        return f"/gasolineras/{self.provincia.slug}/{self.slug}/"


@dataclass(eq=False)
class Provincia:
    id: str
    nombre: str
    slug: str
    municipios: list[Municipio] = field(default_factory=list)
    estaciones: list[Estacion] = field(default_factory=list)

    @property
    def ruta(self) -> str:
        return f"/gasolineras/{self.slug}/"


@dataclass(eq=False)
class Marca:
    nombre: str
    slug: str
    estaciones: list[Estacion] = field(default_factory=list)

    @property
    def ruta(self) -> str:
        return f"/marcas/{self.slug}/"


@dataclass(eq=False)
class Datos:
    actualizado: datetime
    estaciones: list[Estacion]
    provincias: list[Provincia]
    municipios: list[Municipio]
    marcas: list[Marca]


# ---------- descarga ----------

def descargar(intentos: int = 4) -> dict:
    ultimo_error = None
    for i in range(intentos):
        try:
            r = requests.get(API_URL, timeout=180, headers={"Accept": "application/json"})
            r.raise_for_status()
            datos = r.json()
            if datos.get("ResultadoConsulta") != "OK" or len(datos.get("ListaEESSPrecio", [])) < 5000:
                raise ValueError(f"Respuesta incompleta: {datos.get('ResultadoConsulta')}, "
                                 f"{len(datos.get('ListaEESSPrecio', []))} estaciones")
            return datos
        except Exception as e:  # noqa: BLE001 - reintentar cualquier fallo de red
            ultimo_error = e
            time.sleep(10 * (i + 1))
    raise RuntimeError(f"No se pudo descargar la API del Ministerio: {ultimo_error}")


def cargar_fichero(ruta: Path) -> dict:
    return json.loads(Path(ruta).read_text(encoding="utf-8"))


# ---------- interpretación ----------

def _num(valor: str) -> float | None:
    valor = (valor or "").strip().replace(",", ".")
    if not valor:
        return None
    try:
        return float(valor)
    except ValueError:
        return None


def _precios(fila: dict) -> dict[str, float]:
    precios = {}
    for c in COMBUSTIBLES:
        p = _num(fila.get(c.campo, ""))
        if p is not None and PRECIO_MIN <= p <= PRECIO_MAX:
            precios[c.clave] = round(p, 3)
    return precios


def interpretar(bruto: dict) -> Datos:
    actualizado = datetime.strptime(bruto["Fecha"], "%d/%m/%Y %H:%M:%S").replace(tzinfo=ZONA)
    provincias: dict[str, Provincia] = {}
    municipios: dict[str, Municipio] = {}
    estaciones: list[Estacion] = []

    for fila in bruto["ListaEESSPrecio"]:
        if fila.get("Tipo Venta", "P") != "P":  # "R" = solo socios
            continue
        precios = _precios(fila)
        if not precios:
            continue
        pid = fila["IDProvincia"]
        if pid not in provincias:
            nombre = PROVINCIAS.get(pid) or capitalizar(nombre_bonito(fila["Provincia"]))
            provincias[pid] = Provincia(pid, nombre, slug(nombre))
        provincia = provincias[pid]

        mid = fila["IDMunicipio"]
        if mid not in municipios:
            nombre = nombre_bonito(fila["Municipio"])
            municipios[mid] = Municipio(mid, nombre, slug(nombre), provincia)
            provincia.municipios.append(municipios[mid])
        municipio = municipios[mid]

        lat, lon = _num(fila.get("Latitud", "")), _num(fila.get("Longitud (WGS84)", ""))
        if lat is None or lon is None or (lat == 0 and lon == 0):
            lat = lon = None
        rotulo = " ".join(fila.get("Rótulo", "").split()) or "Sin marca"
        e = Estacion(
            id=fila["IDEESS"], rotulo=rotulo, direccion=capitalizar(fila.get("Dirección", "")),
            cp=fila.get("C.P.", ""), horario=fila.get("Horario", "").strip(), lat=lat, lon=lon,
            municipio_id=mid, provincia_id=pid, precios=precios, municipio=municipio,
        )
        estaciones.append(e)
        municipio.estaciones.append(e)
        provincia.estaciones.append(e)

    # Slugs únicos dentro de cada provincia.
    for p in provincias.values():
        vistos: dict[str, int] = defaultdict(int)
        for m in sorted(p.municipios, key=lambda m: m.id):
            vistos[m.slug] += 1
            if vistos[m.slug] > 1:
                m.slug = f"{m.slug}-{m.id}"
        p.municipios.sort(key=lambda m: slug(m.nombre))

    for m in municipios.values():
        coords = [(e.lat, e.lon) for e in m.estaciones if e.lat is not None]
        if coords:
            m.lat = statistics.fmean(c[0] for c in coords)
            m.lon = statistics.fmean(c[1] for c in coords)

    _calcular_cercanas(list(municipios.values()), estaciones)

    return Datos(
        actualizado=actualizado,
        estaciones=estaciones,
        provincias=sorted(provincias.values(), key=lambda p: slug(p.nombre)),
        municipios=sorted(municipios.values(), key=lambda m: (m.provincia.slug, m.slug)),
        marcas=_agrupar_marcas(estaciones),
    )


def _agrupar_marcas(estaciones: list[Estacion], minimo: int = 20) -> list[Marca]:
    grupos: dict[str, list[Estacion]] = defaultdict(list)
    for e in estaciones:
        grupos[e.rotulo.upper()].append(e)
    marcas = [Marca(nombre, slug(nombre), lista) for nombre, lista in grupos.items()
              if len(lista) >= minimo and slug(nombre) != "sin-marca"]
    return sorted(marcas, key=lambda m: -len(m.estaciones))


# ---------- distancias ----------

def distancia_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _calcular_cercanas(municipios: list[Municipio], estaciones: list[Estacion], radio_km=15.0):
    """Para cada municipio, gasolineras de otros municipios a menos de radio_km de su centro."""
    celda = 0.25  # grados (~25 km)
    rejilla: dict[tuple[int, int], list[Estacion]] = defaultdict(list)
    for e in estaciones:
        if e.lat is not None:
            rejilla[(int(e.lat // celda), int(e.lon // celda))].append(e)
    for m in municipios:
        if m.lat is None:
            continue
        ci, cj = int(m.lat // celda), int(m.lon // celda)
        cerca = []
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for e in rejilla.get((ci + di, cj + dj), []):
                    if e.municipio_id == m.id:
                        continue
                    d = distancia_km(m.lat, m.lon, e.lat, e.lon)
                    if d <= radio_km:
                        cerca.append((e, d))
        m.cercanas = sorted(cerca, key=lambda x: x[1])


# ---------- estadísticas ----------

@dataclass(eq=False)
class Resumen:
    n: int
    media: float | None
    minimo: float | None
    maximo: float | None
    mas_barata: Estacion | None
    mas_cara: Estacion | None


def resumen(estaciones: list[Estacion], comb: str) -> Resumen:
    con = [e for e in estaciones if comb in e.precios]
    if not con:
        return Resumen(0, None, None, None, None, None)
    ordenadas = sorted(con, key=lambda e: (e.precios[comb], e.id))
    return Resumen(
        n=len(con),
        media=round(statistics.fmean(e.precios[comb] for e in con), 3),
        minimo=ordenadas[0].precios[comb],
        maximo=ordenadas[-1].precios[comb],
        mas_barata=ordenadas[0],
        mas_cara=ordenadas[-1],
    )


def mas_baratas(estaciones: list[Estacion], comb: str, n: int = 10) -> list[Estacion]:
    """Las n más baratas. Con muestras grandes se excluyen precios más de un 20 % por debajo de la
    mediana: casi siempre son errores al comunicar el precio y no deben encabezar un ranking."""
    con = [e for e in estaciones if comb in e.precios]
    if len(con) >= 20:
        suelo = statistics.median(e.precios[comb] for e in con) * 0.80
        con = [e for e in con if e.precios[comb] >= suelo]
    return sorted(con, key=lambda e: (e.precios[comb], e.id))[:n]
