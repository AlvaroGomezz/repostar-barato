"""Noticia diaria escrita a partir de los datos oficiales (sin IA: los números no se pueden inventar)."""
import random
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from markupsafe import Markup, escape

from . import tendencia as tendencia_mod
from .config import FISCALIDAD_ESPECIAL, POR_CLAVE, con_articulo
from .texto import DIAS, MESES, centimos, fecha_larga, hora, numero, precio

DEPOSITO_L = 55
UMBRAL = 0.0005  # menos de 0,05 céntimos = sin cambios


@dataclass
class Seccion:
    titulo: str
    parrafos: list[Markup] = field(default_factory=list)
    # {"cabecera": [...], "filas": [[celda, ...]]}; una celda es texto o (texto, ruta) para enlazar.
    tabla: dict | None = None


@dataclass
class Articulo:
    fecha: date
    titulo: str
    descripcion: str
    entradilla: Markup
    secciones: list[Seccion]
    actualizado: datetime
    titular: str = ""      # corto, para el h1 (cabe en dos líneas en el móvil)
    gancho: str = ""       # qué ha pasado hoy, en pocas palabras
    medias: dict = field(default_factory=dict)  # {"diesel": 1.887, ...}
    cambios: dict = field(default_factory=dict)  # {"diesel": 0.022, ...} desde el día anterior
    n_estaciones: int = 0
    slug: str = "precio-gasolina-diesel-hoy"
    tema: str = "Precio de la gasolina"   # antetítulo
    orden: int = 0                         # posición dentro del día (0 = la principal)
    # Cifras de su imagen: [{"nombre": "Diésel", "valor": 1.887, "var": 0.022 | None, "nota": "..."}]
    imagen_filas: list = field(default_factory=list)

    @property
    def ruta(self) -> str:
        return f"/noticias/{self.fecha.isoformat()}-{self.slug}/"

    @property
    def imagen(self) -> str:
        return f"/imagenes/noticias/{self.fecha.isoformat()}-{self.slug}.jpg"


def _mov(hoy: float, antes: float | None, rng: random.Random) -> tuple[str, float]:
    if antes is None:
        return "", 0.0
    d = hoy - antes
    if abs(d) < UMBRAL:
        return rng.choice(["sin cambios respecto a ayer", "igual que ayer", "estable frente a ayer"]), d
    if d > 0:
        verbo = rng.choice(["sube", "se encarece", "aumenta"])
    else:
        verbo = rng.choice(["baja", "se abarata", "cae"])
    return f"{verbo} {centimos(d)} respecto a ayer", d


def _dia_mes(d: date) -> str:
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]}"


def _buscar(historico: dict, fecha: date, dias: int) -> dict | None:
    return historico.get(fecha - timedelta(days=dias))


def _b(texto) -> Markup:
    return Markup("<strong>") + escape(texto) + Markup("</strong>")


def _enlace(ruta_fn, ruta: str, texto: str) -> Markup:
    return Markup('<a href="{}">{}</a>').format(ruta_fn(ruta), texto)


def escribir(snap: dict, historico: dict, ruta_fn) -> Articulo:
    fecha = date.fromisoformat(snap["fecha"])
    actualizado = datetime.fromisoformat(snap["actualizado"])
    rng = random.Random(fecha.toordinal())
    ayer = _buscar(historico, fecha, 1)
    semana = _buscar(historico, fecha, 7)

    nac = snap["nac"]
    d_hoy, g_hoy = nac["diesel"]["media"], nac["g95"]["media"]
    d_mov, d_dif = _mov(d_hoy, ayer and ayer["nac"].get("diesel", {}).get("media"), rng)
    g_mov, g_dif = _mov(g_hoy, ayer and ayer["nac"].get("g95", {}).get("media"), rng)

    # ---- titular ----
    def tendencia(nombre, dif):
        if not ayer or abs(dif) < UMBRAL:
            return None
        return f"{nombre} {'sube' if dif > 0 else 'baja'}"
    partes = [t for t in (tendencia("el diésel", d_dif), tendencia("la gasolina", g_dif)) if t]
    if len(partes) == 2 and partes[0].split()[-1] == partes[1].split()[-1]:
        gancho = f"diésel y gasolina {'suben' if d_dif > 0 else 'bajan'}"
    elif partes:
        gancho = " y ".join(partes)
    else:
        gancho = "así está el precio en tu provincia"
    titulo = f"Precio de la gasolina y el diésel hoy, {_dia_mes(fecha)}: {gancho}"

    n_est = max(v["n"] for v in nac.values())
    inicio = rng.choice([
        "El precio medio del diésel en España",
        "El litro de diésel en las gasolineras españolas",
        "El gasóleo de automoción",
    ])
    entradilla = Markup(
        "{inicio} se sitúa hoy, {fecha}, en {d}{dm}, mientras que la gasolina 95 marca {g}{gm}. "
        "Son los precios oficiales de {n} gasolineras que comunican sus tarifas al Ministerio "
        "para la Transición Ecológica, consultados a las {h}."
    ).format(
        inicio=inicio, fecha=fecha_larga(fecha), d=_b(precio(d_hoy) + "/l"),
        dm=Markup(", ") + d_mov if d_mov else "", g=_b(precio(g_hoy) + "/l"),
        gm=Markup(", ") + g_mov if g_mov else "", n=numero(n_est, 0), h=hora(actualizado),
    )
    descripcion = rng.choice([
        "Así cambia hoy el precio del diésel y la gasolina en España: las provincias y las gasolineras más baratas, "
        "y cuánto cuesta llenar el depósito.",
        "Consulta el precio de los carburantes hoy en tu provincia y en las grandes ciudades, y dónde está la "
        "gasolinera más barata de España.",
        "Las tarifas más altas y más bajas de hoy, provincia a provincia, y las gasolineras donde repostar más barato.",
    ])

    secciones: list[Seccion] = []

    # ---- evolución semanal y depósito ----
    s = Seccion("Cuánto cuesta llenar el depósito")
    lleno_d, lleno_g = d_hoy * DEPOSITO_L, g_hoy * DEPOSITO_L
    texto = Markup("Con estos precios, llenar un depósito de {l} litros cuesta de media {d} con diésel "
                   "y {g} con gasolina 95.").format(
        l=DEPOSITO_L, d=_b(precio(lleno_d, 2)), g=_b(precio(lleno_g, 2)))
    if semana:
        d_sem = semana["nac"].get("diesel", {}).get("media")
        g_sem = semana["nac"].get("g95", {}).get("media")
        if d_sem and g_sem:
            def frase(nombre, ahora, antes, fem=False):
                dif = ahora - antes
                if abs(dif) < UMBRAL:
                    return f"{nombre} está igual que hace una semana ({precio(antes)})"
                sentido = ("más car" if dif > 0 else "más barat") + ("a" if fem else "o")
                return (f"{nombre} está {centimos(dif)} {sentido} que hace una semana "
                        f"(entonces costaba {precio(antes)})")
            texto += Markup(" ") + escape(
                f"En comparación, {frase('el diésel', d_hoy, d_sem)}, y "
                f"{frase('la gasolina 95', g_hoy, g_sem, fem=True)}. "
                f"Para un depósito completo, la diferencia semanal es de "
                f"{precio(abs(d_hoy - d_sem) * DEPOSITO_L, 2)} en diésel.")
    s.parrafos.append(texto)
    secciones.append(s)

    # ---- ¿repostar hoy o esperar? ----
    previos = sorted((f, s2) for f, s2 in historico.items() if f <= fecha and fecha - f <= timedelta(days=30))
    t_d = tendencia_mod.calcular([(f, s2["nac"].get("diesel", {}).get("media")) for f, s2 in previos], "diésel", "el")
    t_g = tendencia_mod.calcular([(f, s2["nac"].get("g95", {}).get("media")) for f, s2 in previos], "gasolina 95", "la")
    if t_d["estado"] != "pocos":
        s = Seccion("¿Repostar hoy o esperar?")
        s.parrafos.append(escape(f"{t_d['titulo']}. {t_d['texto']}"))
        s.parrafos.append(escape(t_g["texto"] + (" " + t_d["dia"] if t_d.get("dia") else "") + " " + t_d["nota"]))
        secciones.append(s)

    # ---- grandes ciudades: lo que más se busca ("precio gasolina hoy en Madrid") ----
    for i, ciu in enumerate(snap.get("ciudades", [])):
        g, dd = ciu.get("g95"), ciu.get("diesel")
        if not g or not dd:
            continue
        s = Seccion(f"El precio de la gasolina hoy en {ciu['nombre']}")
        abre = rng.choice([f"Este {_dia_mes(fecha)}", "Hoy", f"A {_dia_mes(fecha)}"]) if i % 3 == 0 else             rng.choice(["En esta ciudad", "Aquí", "Hoy"])
        s.parrafos.append(Markup(
            "{abre}, la gasolina 95 cuesta en {ciudad} entre {gmin} y {gmax} euros por litro, con una media de "
            "{gmed}. El diésel va de {dmin} a {dmax} (media de {dmed})."
        ).format(abre=abre, ciudad=_enlace(ruta_fn, ciu["ruta"], ciu["nombre"]),
                 gmin=_b(precio(g["min"], 3).replace(" €", "")), gmax=precio(g["max"], 3).replace(" €", ""),
                 gmed=precio(g["media"]), dmin=_b(precio(dd["min"], 3).replace(" €", "")),
                 dmax=precio(dd["max"], 3).replace(" €", ""), dmed=precio(dd["media"])))
        dif = (dd["max"] - dd["min"]) * DEPOSITO_L
        mismo = g["rotulo"] == dd["rotulo"] and g["dir"] == dd["dir"]
        if mismo:
            donde = Markup("La más barata para los dos combustibles es {r} ({dir}).").format(r=_b(g["rotulo"]), dir=g["dir"])
        else:
            donde = Markup("La gasolina 95 más barata está en {rg} ({dg}) y el diésel más barato, en {rd} ({ddir}).").format(
                rg=_b(g["rotulo"]), dg=g["dir"], rd=_b(dd["rotulo"]), ddir=dd["dir"])
        s.parrafos.append(donde + Markup(" ") + escape(
            f"Entre la más cara y la más barata de sus {ciu['n']} gasolineras hay {precio(dif, 2)} de diferencia "
            f"al llenar {DEPOSITO_L} litros de diésel."))
        secciones.append(s)

    # ---- provincias ----
    provs = [(pid, p) for pid, p in snap["prov"].items() if "diesel" in p and "g95" in p]
    pen = [(pid, p) for pid, p in provs if pid not in FISCALIDAD_ESPECIAL]
    s = Seccion("Provincias más baratas y más caras")
    if pen:
        bar_d = min(pen, key=lambda x: x[1]["diesel"][0])
        car_d = max(pen, key=lambda x: x[1]["diesel"][0])
        bar_g = min(pen, key=lambda x: x[1]["g95"][0])
        car_g = max(pen, key=lambda x: x[1]["g95"][0])
        ruta_p = lambda p: f"/gasolineras/{p['slug']}/"  # noqa: E731
        s.parrafos.append(Markup(
            "En la Península y Baleares, {bd} es la provincia con el diésel más barato ({pbd} de media) "
            "y {cd} la más cara ({pcd}). En gasolina 95, la más económica es {bg} ({pbg}) y la más "
            "cara, {cg} ({pcg})."
        ).format(
            bd=_enlace(ruta_fn, ruta_p(bar_d[1]), bar_d[1]["nombre"]), pbd=precio(bar_d[1]["diesel"][0]),
            cd=_enlace(ruta_fn, ruta_p(car_d[1]), car_d[1]["nombre"]), pcd=precio(car_d[1]["diesel"][0]),
            bg=_enlace(ruta_fn, ruta_p(bar_g[1]), bar_g[1]["nombre"]), pbg=precio(bar_g[1]["g95"][0]),
            cg=_enlace(ruta_fn, ruta_p(car_g[1]), car_g[1]["nombre"]), pcg=precio(car_g[1]["g95"][0]),
        ))
        especiales = [p for pid, p in provs if pid in FISCALIDAD_ESPECIAL]
        if especiales:
            nombres = ", ".join(f"{p['nombre']} ({precio(p['diesel'][0])})" for p in
                                sorted(especiales, key=lambda p: p["diesel"][0]))
            s.parrafos.append(escape(
                f"Canarias, Ceuta y Melilla tienen una fiscalidad distinta y precios más bajos: el diésel "
                f"medio está en {nombres}."))
        filas = [[(p["nombre"], ruta_p(p)), precio(p["diesel"][0]), precio(p["g95"][0]),
                  numero(p["diesel"][2], 0)]
                 for pid, p in sorted(provs, key=lambda x: x[1]["diesel"][0])]
        s.tabla = {"cabecera": ["Provincia", "Diésel", "Gasolina 95", "Gasolineras"], "filas": filas}
    secciones.append(s)

    # ---- gasolineras más baratas ----
    for clave in ("diesel", "g95"):
        top = snap["top_pen"].get(clave, [])
        if not top:
            continue
        frase = con_articulo(clave, "barat")
        s = Seccion(f"Las 10 gasolineras con {frase} de la Península")
        primera = top[0]
        s.parrafos.append(Markup(
            "La gasolinera con {n} hoy es {r}, en {dir} ({m}, {p}), a {pr} el litro."
        ).format(n=frase, r=_b(primera["rotulo"]), dir=primera["dir"],
                 m=_enlace(ruta_fn, primera["ruta"], primera["mun"]), p=primera["prov"],
                 pr=_b(precio(primera["precio"]))))
        s.tabla = {
            "cabecera": ["Gasolinera", "Municipio", "Provincia", "Precio"],
            "filas": [[f"{e['rotulo']} · {e['dir']}", (e["mun"], e["ruta"]), e["prov"],
                       precio(e["precio"])] for e in top],
        }
        secciones.append(s)

    # ---- ahorro y marcas ----
    s = Seccion("Cuánto puedes ahorrar eligiendo bien")
    pen_d = snap["pen"].get("diesel")
    if pen_d:
        ahorro = (pen_d["max"] - pen_d["min"]) * DEPOSITO_L
        s.parrafos.append(escape(
            f"Entre la gasolinera más barata y la más cara de la Península hay hoy "
            f"{centimos(pen_d['max'] - pen_d['min'])} de diferencia por litro de diésel: "
            f"{precio(ahorro, 2)} en un depósito de {DEPOSITO_L} litros. Incluso dentro de la misma "
            f"ciudad la diferencia suele superar los 10 céntimos, así que compensa comparar antes de repostar."))
    marcas = [m for m in snap["marcas"].values() if m.get("n", 0) >= 50 and "diesel" in m]
    if len(marcas) >= 4:
        marcas.sort(key=lambda m: m["diesel"])
        barata, cara = marcas[0], marcas[-1]
        s.parrafos.append(escape(
            f"Por marcas, entre las cadenas con al menos 50 gasolineras, {barata['nombre']} es la que tiene "
            f"el diésel más barato de media ({precio(barata['diesel'])}) y {cara['nombre']} la más cara "
            f"({precio(cara['diesel'])})."))
    if s.parrafos:
        secciones.append(s)

    # ---- otros combustibles ----
    otros = [(POR_CLAVE[k].nombre_largo, v["media"], v["n"]) for k, v in nac.items()
             if k not in ("diesel", "g95") and v["n"] >= 50]
    if otros:
        lista = "; ".join(f"{n}, {precio(m)} ({numero(c, 0)} gasolineras)" for n, m, c in otros)
        secciones.append(Seccion("Otros combustibles", [escape(f"Precio medio en España de otros carburantes: {lista}.")]))

    secciones.append(Seccion("Sobre estos datos", [escape(
        "Los precios proceden del Geoportal de Hidrocarburos del Ministerio para la Transición "
        "Ecológica y el Reto Demográfico, al que las gasolineras están obligadas a comunicar sus tarifas. "
        "Las medias son aritméticas sobre las gasolineras de venta al público. El precio final puede "
        "variar por descuentos de fidelización o cambios posteriores; confírmalo en el surtidor.")]))

    titular = f"Gasolina y diésel hoy, {_dia_mes(fecha)}"
    medias = {k: v["media"] for k, v in nac.items() if k in ("diesel", "g95", "g98", "glp")}
    cambios = {"diesel": d_dif if ayer else None, "g95": g_dif if ayer else None}
    return Articulo(fecha, titulo, descripcion, entradilla, secciones, actualizado,
                    titular=titular, gancho=gancho[:1].upper() + gancho[1:], medias=medias,
                    cambios=cambios, n_estaciones=n_est)


# ======================================================================
# Más noticias cada día. Cada una sale de datos propios del día (nada de textos repetidos con otro
# nombre): si no hay datos suficientes para que aporte algo, no se publica.
# ======================================================================

def _serie_nac(historico: dict, fecha: date, clave: str, dias: int = 30) -> list[tuple[date, float]]:
    return [(f, s["nac"][clave]["media"]) for f, s in sorted(historico.items())
            if f <= fecha and (fecha - f).days <= dias and clave in s.get("nac", {})]


def _var_txt(d: float, fem: bool = False) -> str:
    if abs(d) < UMBRAL:
        return "sin cambios"
    return f"{'sube' if d > 0 else 'baja'} {centimos(d)}"


def _cts(d: float) -> str:
    c = d * 100
    if abs(c) < 0.05:
        return "0 cts"
    return f"{'+' if c > 0 else '−'}{abs(c):.1f}".replace(".", ",") + " cts"


def repostar_hoy(snap: dict, historico: dict, ruta_fn) -> "Articulo | None":
    """¿Merece la pena echar gasolina hoy o es mejor esperar?"""
    fecha = date.fromisoformat(snap["fecha"])
    actualizado = datetime.fromisoformat(snap["actualizado"])
    rng = random.Random(fecha.toordinal() * 7 + 1)
    s_d, s_g = _serie_nac(historico, fecha, "diesel"), _serie_nac(historico, fecha, "g95")
    t_d = tendencia_mod.calcular(s_d, "diésel", "el")
    t_g = tendencia_mod.calcular(s_g, "gasolina 95", "la")
    if t_d["estado"] == "pocos":
        return None
    dm = _dia_mes(fecha)
    titulo = rng.choice([
        f"¿Merece la pena echar gasolina hoy o es mejor esperar? Lo que dice el precio este {dm}",
        f"¿Lleno el depósito hoy o espero? Así se mueve el precio de la gasolina este {dm}",
        f"¿Repostar hoy o esperar unos días? La tendencia del diésel y la gasolina, {dm}",
    ])
    titular = f"¿Repostar hoy o esperar? {dm[:1].upper() + dm[1:]}"
    gancho = t_d["titulo"]
    descripcion = ("¿Conviene llenar el depósito hoy o esperar unos días? Te contamos hacia dónde va el precio del "
                   "diésel y la gasolina, dónde sube y dónde baja, y cómo ahorrar más.")
    entradilla = Markup("{t}. {d} En cuanto a la gasolina 95: {g}.").format(
        t=_b(t_d["titulo"]), d=t_d["texto"], g=t_g["texto"].split(".")[0].split(": ", 1)[-1])
    secciones = []

    s = Seccion("Así se ha movido el precio estos días")
    previos = sorted((f, x) for f, x in historico.items() if f <= fecha and (fecha - f).days <= 7)
    s.parrafos.append(escape("Precio medio del litro en las gasolineras de España, día a día:"))
    s.tabla = {"cabecera": ["Día", "Diésel", "Gasolina 95"],
               "filas": [[_dia_mes(f), precio(x["nac"]["diesel"]["media"]), precio(x["nac"]["g95"]["media"])]
                         for f, x in reversed(previos) if "diesel" in x["nac"] and "g95" in x["nac"]]}
    secciones.append(s)

    s = Seccion("Entonces, ¿lleno hoy o espero?")
    for t, nombre in ((t_d, "Diésel"), (t_g, "Gasolina 95")):
        s.parrafos.append(Markup("{n}: {t}. {x}").format(n=_b(nombre), t=t["titulo"], x=t["texto"]))
    if t_d.get("dia"):
        s.parrafos.append(escape(t_d["dia"]))
    s.parrafos.append(escape(t_d["nota"] + " Si tienes el depósito casi vacío, reposta ya: unos céntimos de "
                             "tendencia pesan mucho menos que elegir bien la gasolinera."))
    secciones.append(s)

    # Dónde sube y dónde baja más desde ayer (Península).
    ayer = historico.get(fecha - timedelta(days=1))
    if ayer:
        cambios = []
        for pid, p in snap["prov"].items():
            q = ayer.get("prov", {}).get(pid, {})
            if pid in FISCALIDAD_ESPECIAL or "diesel" not in p or "diesel" not in q:
                continue
            cambios.append((p["diesel"][0] - q["diesel"][0], p))
        if len(cambios) >= 6:
            cambios.sort(key=lambda x: x[0])
            ruta_p = lambda p: f"/gasolineras/{p['slug']}/"  # noqa: E731
            s = Seccion("Dónde sube y dónde baja el diésel hoy")
            baja = [x for x in cambios[:3] if x[0] < -UMBRAL]
            sube = [x for x in reversed(cambios[-3:]) if x[0] > UMBRAL]
            if baja:
                s.parrafos.append(Markup("Donde más baja desde ayer: ") + Markup(", ").join(
                    Markup("{} ({})").format(_enlace(ruta_fn, ruta_p(p), p["nombre"]), _cts(d)) for d, p in baja) + Markup("."))
            if sube:
                s.parrafos.append(Markup("Donde más sube: ") + Markup(", ").join(
                    Markup("{} ({})").format(_enlace(ruta_fn, ruta_p(p), p["nombre"]), _cts(d)) for d, p in sube) + Markup("."))
            if s.parrafos:
                secciones.append(s)

    # Lo que de verdad ahorra: elegir gasolinera dentro de la ciudad.
    ciudades = [c for c in snap.get("ciudades", []) if c.get("diesel")]
    if ciudades:
        s = Seccion("Lo que más ahorra: elegir bien dónde")
        frases = [Markup("en {} hay {} entre la más cara y la más barata").format(
            _enlace(ruta_fn, c["ruta"], c["nombre"]), precio((c["diesel"]["max"] - c["diesel"]["min"]) * DEPOSITO_L, 2))
            for c in ciudades[:4]]
        s.parrafos.append(Markup("Esperar un par de días puede ahorrarte unos céntimos; elegir gasolinera, varios euros. "
                                 "Al llenar {} litros de diésel, ").format(DEPOSITO_L) + Markup("; ").join(frases) + Markup(". ") +
                          _enlace(ruta_fn, "/", "Busca la más barata cerca de ti") + Markup("."))
        secciones.append(s)

    filas = []
    for clave, nombre, serie in (("diesel", "Diésel", s_d), ("g95", "Gasolina 95", s_g)):
        hoy_v = snap["nac"][clave]["media"]
        hace = next((v for f, v in serie if (fecha - f).days <= 7), None)
        filas.append({"nombre": nombre, "valor": hoy_v, "var": (hoy_v - hace) if hace is not None and len(serie) > 1 else None})
    return Articulo(fecha, titulo, descripcion, entradilla, secciones, actualizado, titular=titular, gancho=gancho,
                    medias={k: v["media"] for k, v in snap["nac"].items() if k in ("diesel", "g95", "g98", "glp")},
                    n_estaciones=max(v["n"] for v in snap["nac"].values()), slug="merece-la-pena-repostar-hoy",
                    tema="Repostar hoy o esperar", orden=1, imagen_filas=filas)


def ciudad(snap: dict, historico: dict, ruta_fn, c: dict, orden: int) -> "Articulo | None":
    """Gasolineras más baratas en una gran ciudad hoy, con su top 5 de cada combustible."""
    d, g = c.get("diesel"), c.get("g95")
    if not d or not g or not d.get("top") or not g.get("top"):
        return None
    fecha = date.fromisoformat(snap["fecha"])
    actualizado = datetime.fromisoformat(snap["actualizado"])
    rng = random.Random(fecha.toordinal() * 31 + orden)
    dm, nombre = _dia_mes(fecha), c["nombre"]
    titulo = rng.choice([
        f"Gasolineras más baratas en {nombre} hoy, {dm}: dónde repostar más barato",
        f"Dónde echar gasolina más barata en {nombre} hoy, {dm}: las cinco mejores de cada combustible",
        f"Precio de la gasolina en {nombre} hoy, {dm}: estas son las gasolineras más baratas",
    ])
    titular = f"Gasolina más barata en {nombre} hoy"
    slug = "gasolineras-mas-baratas-" + c["ruta"].strip("/").split("/")[-1] + "-hoy"
    ayer = historico.get(fecha - timedelta(days=1))
    c_ayer = next((x for x in (ayer or {}).get("ciudades", []) if x.get("ruta") == c["ruta"]), None)
    mov = ""
    if c_ayer and c_ayer.get("diesel"):
        dif = d["media"] - c_ayer["diesel"]["media"]
        mov = (f" El diésel medio de la ciudad {_var_txt(dif)} desde ayer." if abs(dif) >= UMBRAL
               else " El diésel medio está igual que ayer.")
    entradilla = Markup(
        "Repostar hoy en {ciudad} cuesta entre {gmin} y {gmax} el litro de gasolina 95, y entre {dmin} y {dmax} el de "
        "diésel, según los precios oficiales de sus {n} gasolineras a las {h}.{mov}"
    ).format(ciudad=_enlace(ruta_fn, c["ruta"], nombre), gmin=_b(precio(g["min"])), gmax=precio(g["max"]),
             dmin=_b(precio(d["min"])), dmax=precio(d["max"]), n=c["n"], h=hora(actualizado), mov=mov)
    descripcion = (f"Las cinco gasolineras más baratas de {nombre} hoy para diésel y gasolina 95, con su dirección, "
                   f"y cuánto te ahorras frente a la más cara de la ciudad.")
    secciones = []
    for clave, datos, frase in (("diesel", d, "el diésel más barato"), ("g95", g, "la gasolina 95 más barata")):
        s = Seccion(f"Las 5 gasolineras con {frase} de {nombre}")
        s.tabla = {"cabecera": ["Gasolinera", "Dirección", "Precio"],
                   "filas": [[e["rotulo"] + (" · 24 h" if e.get("h24") else ""), e["dir"], precio(e["precio"])]
                             for e in datos["top"]]}
        secciones.append(s)
    s = Seccion("Cuánto ahorras eligiendo bien")
    s.parrafos.append(escape(
        f"Llenar {DEPOSITO_L} litros de diésel en la gasolinera más barata de {nombre} cuesta "
        f"{precio(d['min'] * DEPOSITO_L, 2)}; en la más cara, {precio(d['max'] * DEPOSITO_L, 2)}. Son "
        f"{precio((d['max'] - d['min']) * DEPOSITO_L, 2)} de diferencia en un solo depósito."))
    nac = snap["nac"]
    dif = d["media"] - nac["diesel"]["media"]
    s.parrafos.append(escape(
        f"El diésel medio de {nombre} ({precio(d['media'])}) está "
        + ("igual que" if abs(dif) < UMBRAL else f"{centimos(dif)} {'por encima' if dif > 0 else 'por debajo'} de")
        + f" la media de España ({precio(nac['diesel']['media'])})."))
    s.parrafos.append(Markup("Consulta {} en la lista completa, ordenadas por precio o por cercanía.").format(
        _enlace(ruta_fn, c["ruta"], f"las {c['n']} gasolineras de {nombre}")))
    secciones.append(s)
    return Articulo(fecha, titulo, descripcion, entradilla, secciones, actualizado, titular=titular,
                    gancho=f"Las más baratas de {nombre}",
                    medias={k: v["media"] for k, v in nac.items() if k in ("diesel", "g95", "g98", "glp")},
                    n_estaciones=c["n"], slug=slug, tema=f"Precio de la gasolina en {nombre}", orden=orden,
                    imagen_filas=[{"nombre": "Diésel", "valor": d["min"], "nota": "la más barata"},
                                  {"nombre": "Gasolina 95", "valor": g["min"], "nota": "la más barata"}])


def semanal(snap: dict, historico: dict, ruta_fn) -> "Articulo | None":
    """Los lunes: resumen de la semana."""
    fecha = date.fromisoformat(snap["fecha"])
    antes = historico.get(fecha - timedelta(days=7))
    if fecha.weekday() != 0 or not antes:
        return None
    actualizado = datetime.fromisoformat(snap["actualizado"])
    nac, nac0 = snap["nac"], antes["nac"]
    dd = nac["diesel"]["media"] - nac0["diesel"]["media"]
    dg = nac["g95"]["media"] - nac0["g95"]["media"]
    def sentido(d, nombre):
        return f"{nombre} {'sube' if d > UMBRAL else 'baja' if d < -UMBRAL else 'se mantiene'}"
    titulo = (f"Resumen de la semana: {sentido(dd, 'el diésel')} y {sentido(dg, 'la gasolina')}. "
              f"Así ha cambiado el precio en siete días")
    secciones = []
    s = Seccion("Precio medio, hoy y hace una semana")
    s.tabla = {"cabecera": ["Combustible", "Hace una semana", "Hoy", "Cambio"],
               "filas": [[POR_CLAVE[k].nombre, precio(nac0[k]["media"]), precio(nac[k]["media"]),
                          _cts(nac[k]["media"] - nac0[k]["media"])]
                         for k in ("diesel", "g95", "g98", "glp") if k in nac and k in nac0]}
    s.parrafos.append(escape(
        f"Llenar {DEPOSITO_L} litros de diésel cuesta hoy {precio(nac['diesel']['media'] * DEPOSITO_L, 2)}, "
        f"{precio(abs(dd) * DEPOSITO_L, 2)} {'más' if dd > 0 else 'menos'} que hace una semana."))
    secciones.append(s)
    cambios = []
    for pid, p in snap["prov"].items():
        q = antes.get("prov", {}).get(pid, {})
        if pid not in FISCALIDAD_ESPECIAL and "diesel" in p and "diesel" in q:
            cambios.append((p["diesel"][0] - q["diesel"][0], p))
    if len(cambios) >= 6:
        cambios.sort(key=lambda x: x[0])
        s = Seccion("Las provincias donde más ha cambiado el diésel")
        s.tabla = {"cabecera": ["Provincia", "Hoy", "Cambio en la semana"],
                   "filas": [[(p["nombre"], f"/gasolineras/{p['slug']}/"), precio(p["diesel"][0]), _cts(dif)]
                             for dif, p in cambios[:3] + cambios[-3:][::-1]]}
        s.parrafos.append(escape("Las tres que más bajan y las tres que más suben en la Península y Baleares."))
        secciones.append(s)
    filas_c = []
    for c in snap.get("ciudades", []):
        c0 = next((x for x in antes.get("ciudades", []) if x.get("ruta") == c["ruta"]), None)
        if c.get("diesel") and c0 and c0.get("diesel"):
            filas_c.append([(c["nombre"], c["ruta"]), precio(c["diesel"]["media"]), _cts(c["diesel"]["media"] - c0["diesel"]["media"])])
    if filas_c:
        s = Seccion("En las grandes ciudades")
        s.tabla = {"cabecera": ["Ciudad", "Diésel medio", "Cambio en la semana"], "filas": filas_c}
        secciones.append(s)
    marcas = sorted((m for m in snap.get("marcas", {}).values() if m.get("n", 0) >= 50 and "diesel" in m),
                    key=lambda m: m["diesel"])
    if len(marcas) >= 5:
        s = Seccion("Las marcas más baratas esta semana")
        s.parrafos.append(escape("Entre las cadenas con al menos 50 gasolineras, por precio medio del diésel: " +
                                 "; ".join(f"{m['nombre']}, {precio(m['diesel'])}" for m in marcas[:5]) + "."))
        secciones.append(s)
    entradilla = Markup("En los últimos siete días, el precio medio del diésel en España {d} hasta {dh} y el de la "
                        "gasolina 95 {g} hasta {gh}.").format(
        d=_var_txt(dd), dh=_b(precio(nac["diesel"]["media"])), g=_var_txt(dg), gh=_b(precio(nac["g95"]["media"])))
    return Articulo(fecha, titulo, f"Cómo ha cambiado el precio de la gasolina y el diésel en la última semana, "
                    f"por provincias, ciudades y marcas.", entradilla, secciones, actualizado,
                    titular="Resumen de la semana", gancho="Así ha cambiado el precio en la semana",
                    medias={k: v["media"] for k, v in nac.items() if k in ("diesel", "g95", "g98", "glp")},
                    n_estaciones=max(v["n"] for v in nac.values()), slug="resumen-semanal-precio-gasolina",
                    tema="Resumen semanal", orden=5,
                    imagen_filas=[{"nombre": "Diésel", "valor": nac["diesel"]["media"], "var": dd},
                                  {"nombre": "Gasolina 95", "valor": nac["g95"]["media"], "var": dg}])


def record(snap: dict, historico: dict, ruta_fn) -> "Articulo | None":
    """Cuando ocurre: el precio más alto o más bajo de las últimas semanas."""
    fecha = date.fromisoformat(snap["fecha"])
    for clave, nombre, art in (("diesel", "diésel", "El"), ("g95", "gasolina 95", "La")):
        serie = _serie_nac(historico, fecha, clave)
        if len(serie) < 14:
            continue
        hoy_v = serie[-1][1]
        resto = [v for _, v in serie[:-1]]
        alto, bajo = hoy_v > max(resto) + 0.001, hoy_v < min(resto) - 0.001
        if not (alto or bajo):
            continue
        dias = (fecha - serie[0][0]).days
        extremo = "más alto" if alto else "más bajo"
        prev = max(resto) if alto else min(resto)
        titulo = f"{art} {nombre} marca su precio {extremo} de los últimos {dias} días"
        actualizado = datetime.fromisoformat(snap["actualizado"])
        s = Seccion("Los últimos días")
        s.tabla = {"cabecera": ["Día", POR_CLAVE[clave].nombre],
                   "filas": [[_dia_mes(f), precio(v)] for f, v in reversed(serie[-10:])]}
        s2 = Seccion("Qué hacer")
        s2.parrafos.append(escape(
            (f"Con el precio en máximos, compensa más que nunca comparar: en una misma ciudad la diferencia entre "
             f"gasolineras suele superar los 10 céntimos por litro, mucho más que la subida." if alto else
             f"Es un buen momento para llenar el depósito si lo tienes a medias.")))
        s2.parrafos.append(_enlace(ruta_fn, "/", "Busca la más barata cerca de ti") + Markup("."))
        entradilla = Markup("{a} {n} cuesta hoy de media {v} en España, su precio {e} de los últimos {d} días. "
                            "El anterior {e} era de {p}.").format(a=art, n=nombre, v=_b(precio(hoy_v)), e=extremo, d=dias, p=precio(prev))
        return Articulo(fecha, titulo, f"{art} {nombre} marca hoy su precio {extremo} de los últimos {dias} días.",
                        entradilla, [s, s2], actualizado, titular=f"{art} {nombre}, en su precio {extremo} en {dias} días",
                        gancho=f"{POR_CLAVE[clave].nombre} en máximos" if alto else f"{POR_CLAVE[clave].nombre} en mínimos",
                        medias={k: v["media"] for k, v in snap["nac"].items() if k in ("diesel", "g95", "g98", "glp")},
                        n_estaciones=max(v["n"] for v in snap["nac"].values()),
                        slug=f"{'maximo' if alto else 'minimo'}-precio-{'diesel' if clave == 'diesel' else 'gasolina'}",
                        tema="Última hora", orden=4,
                        imagen_filas=[{"nombre": POR_CLAVE[clave].nombre, "valor": hoy_v, "nota": "máximo" if alto else "mínimo"}])
    return None


def escribir_dia(snap: dict, historico: dict, ruta_fn) -> list[Articulo]:
    """Todas las noticias de un día, en orden: la principal primero."""
    fecha = date.fromisoformat(snap["fecha"])
    lista = [escribir(snap, historico, ruta_fn)]
    for f in (repostar_hoy, record, semanal):
        a = f(snap, historico, ruta_fn)
        if a:
            lista.append(a)
    # Dos grandes ciudades cada día, por turnos: cada una sale una vez cada seis días.
    ciudades = snap.get("ciudades", [])
    if ciudades:
        k = (fecha.toordinal() * 2) % len(ciudades)
        for i, c in enumerate(dict.fromkeys([k, (k + 1) % len(ciudades)])):
            a = ciudad(snap, historico, ruta_fn, ciudades[c], orden=2 + i)
            if a:
                lista.append(a)
    return sorted(lista, key=lambda a: a.orden)
