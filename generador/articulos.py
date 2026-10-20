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

    @property
    def ruta(self) -> str:
        return f"/noticias/{self.fecha.isoformat()}-precio-gasolina-diesel-hoy/"

    @property
    def imagen(self) -> str:
        return f"/imagenes/noticias/{self.fecha.isoformat()}.jpg"


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
        gancho = f"diésel a {precio(d_hoy)} y gasolina a {precio(g_hoy)}"
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
    descripcion = (f"Precio medio hoy {fecha.day} de {MESES[fecha.month - 1]}: diésel {precio(d_hoy)}/l "
                   f"y gasolina 95 {precio(g_hoy)}/l. Provincias y gasolineras más baratas de España.")

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
