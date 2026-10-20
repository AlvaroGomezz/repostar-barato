"""Ajustes del sitio, leídos de sitio.toml (y SITE_URL del entorno para previsualizar en local)."""
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

RAIZ = Path(__file__).resolve().parent.parent
ZONA = ZoneInfo("Europe/Madrid")
API_URL = ("https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/"
           "PreciosCarburantes/EstacionesTerrestres/")


@dataclass(frozen=True)
class Combustible:
    clave: str
    nombre: str        # nombre corto para tablas
    nombre_largo: str  # nombre para textos
    campo: str         # columna de la API


COMBUSTIBLES = [
    Combustible("diesel", "Diésel", "diésel (gasóleo A)", "Precio Gasoleo A"),
    Combustible("g95", "Gasolina 95", "gasolina 95", "Precio Gasolina 95 E5"),
    Combustible("g98", "Gasolina 98", "gasolina 98", "Precio Gasolina 98 E5"),
    Combustible("dieselp", "Diésel Premium", "diésel premium", "Precio Gasoleo Premium"),
    Combustible("glp", "GLP", "GLP (autogás)", "Precio Gases licuados del petróleo"),
    Combustible("hvo", "Diésel renovable", "diésel renovable (HVO)", "Precio Diésel Renovable"),
    Combustible("adblue", "AdBlue", "AdBlue", "Precio Adblue"),
]
POR_CLAVE = {c.clave: c for c in COMBUSTIBLES}
FEMENINO = {"g95", "g98"}  # la gasolina; el diésel, el GLP, el AdBlue


def con_articulo(clave: str, adjetivo: str = "") -> str:
    """con_articulo("g95", "barat") -> "la gasolina 95 más barata"; sin adjetivo, solo el artículo."""
    c = POR_CLAVE[clave]
    fem = clave in FEMENINO
    texto = f"{'la' if fem else 'el'} {c.nombre_largo}"
    if adjetivo:
        texto += f" más {adjetivo}{'a' if fem else 'o'}"
    return texto
PRINCIPALES = ["diesel", "g95"]

# Canarias, Ceuta y Melilla tienen impuestos distintos: se separan en los rankings.
FISCALIDAD_ESPECIAL = {"35", "38", "51", "52"}


@dataclass(frozen=True)
class Sitio:
    nombre: str
    lema: str
    url: str
    base: str  # ruta dentro del dominio, "" o "/repostar-barato"
    adsense: str
    search_console: str
    titular: str
    nif: str
    email: str
    telegram: str = ""
    domicilio: str = ""
    goatcounter: str = ""  # canal público, p. ej. "@gasvia"


def cargar_sitio() -> Sitio:
    with open(RAIZ / "sitio.toml", "rb") as f:
        d = tomllib.load(f)
    url = os.getenv("SITE_URL", d.get("url", "")).rstrip("/")
    return Sitio(
        nombre=d.get("nombre", "GASVIA"),
        lema=d.get("lema", ""),
        url=url,
        base=urlparse(url).path.rstrip("/"),
        adsense=os.getenv("ADSENSE", d.get("adsense", "")).strip(),
        search_console=d.get("search_console", "").strip(),
        titular=d.get("titular", "").strip(),
        nif=d.get("nif", "").strip(),
        email=d.get("email", "").strip(),
        telegram=d.get("telegram", "").strip(),
        domicilio=d.get("domicilio", "").strip(),
        goatcounter=d.get("goatcounter", "").strip(),
    )
