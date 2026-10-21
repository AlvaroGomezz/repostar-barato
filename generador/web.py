"""Genera todas las páginas estáticas de la web."""
import json
import shutil
import statistics
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from . import articulos, graficos, imagenes, mapa_estatico, marca, tendencia
from . import historico as historico_mod
from .config import COMBUSTIBLES, FISCALIDAD_ESPECIAL, LANZAMIENTO, POR_CLAVE, RAIZ, Sitio, con_articulo
from .datos import Datos, Estacion, Municipio, Provincia, mas_baratas, resumen
from .texto import (DIAS as DIAS_SEMANA, capitalizar, centimos, fecha_corta, fecha_larga, fecha_media, hora, numero,
                    precio, slug)

PLANTILLAS = RAIZ / "generador" / "plantillas"
ESTATICO = RAIZ / "generador" / "estatico"
UI = ["diesel", "g95", "g98", "glp"]   # combustibles del selector
EXTRAS = ["dieselp", "hvo", "adblue"]  # se muestran como línea secundaria de cada gasolinera
DEPOSITO_L = 50


def cifra(valor: float | None, decimales: int = 3, unidad: str = "€/l") -> Markup:
    """Precio con la unidad como sufijo pequeño: 1,799 €/l."""
    if valor is None:
        return Markup('<span class="sin-dato">—</span>')
    texto = f"{valor:.{decimales}f}".replace(".", ",")
    return Markup('<span class="importe"><span class="cifra">{}</span><span class="unidad"> {}</span></span>').format(texto, unidad)


def cts(diferencia: float) -> str:
    """0.0123 -> '+1,2 cts'."""
    c = diferencia * 100
    if abs(c) < 0.05:
        return "0 cts"
    return f"{'+' if c > 0 else '−'}{abs(c):.1f}".replace(".", ",") + " cts"


class Web:
    def __init__(self, datos: Datos, historico: dict, sitio: Sitio, salida: Path):
        self.d = datos
        self.sitio = sitio
        self.salida = salida
        self.hoy = datos.actualizado.date()
        self.historico = historico
        self.paginas: list[tuple[str, str, str]] = []  # (ruta, lastmod, prioridad)
        self.env = Environment(loader=FileSystemLoader(PLANTILLAS),
                               autoescape=select_autoescape(["html", "xml"]),
                               trim_blocks=True, lstrip_blocks=True)
        self.env.filters.update(precio=precio, numero=numero, fecha_larga=fecha_larga,
                                fecha_media=fecha_media, fecha_corta=fecha_corta, hora=hora,
                                centimos=centimos, capitalizar=capitalizar, cifra=cifra, cts=cts,
                                fila_tabla=lambda e, presentes: [e.rotulo, e.direccion,
                                                                 [precio(e.precios.get(c.clave)) for c in presentes]])
        self.env.globals.update(
            sitio=sitio, url=self.url, abs_url=self.abs_url, C=POR_CLAVE, combustibles=COMBUSTIBLES,
            UI=UI, actualizado=datos.actualizado, anio=self.hoy.year, ld_migas=self.ld_migas,
            ld_faq=self.ld_faq, deposito=DEPOSITO_L, n_total=len(datos.estaciones),
            logo_amarillo=Markup(marca.logo_svg(**marca.SOBRE_AMARILLO, atributos=' class="logo" aria-hidden="true" focusable="false"')),
            logo_claro=Markup(marca.logo_svg(**marca.SOBRE_CLARO, atributos=' class="logo" aria-hidden="true" focusable="false"')),
        )
        self.nac = {c.clave: resumen(datos.estaciones, c.clave) for c in COMBUSTIBLES}
        self.ayer = historico.get(self.hoy - timedelta(days=1))
        self.series_graficos: dict[str, list] = {}  # datos del cursor de los gráficos nacionales (datos/graficos.json)
        # ¿Repostar hoy o esperar? Tendencia del precio medio en España de cada combustible.
        nombres = {"diesel": ("diésel", "el"), "g95": ("gasolina 95", "la"), "g98": ("gasolina 98", "la"), "glp": ("GLP", "el")}
        self.tendencias = {
            c: tendencia.calcular(self.serie(lambda s, c=c: s["nac"].get(c, {}).get("media"), self.nac[c].media), *nombres[c])
            for c in UI}
        self.env.globals["tendencias"] = self.tendencias

    # ---------- utilidades ----------

    def url(self, ruta: str) -> str:
        return self.sitio.base + ruta

    def abs_url(self, ruta: str) -> str:
        return self.sitio.url + ruta

    def ld_migas(self, items) -> dict:
        lista = [("Inicio", "/")] + [(n, r) for n, r in items if r]
        return {"@context": "https://schema.org", "@type": "BreadcrumbList",
                "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n,
                                     "item": self.abs_url(r)} for i, (n, r) in enumerate(lista)]}

    @staticmethod
    def ld_gasolineras(nombre: str, estaciones: list[Estacion], n: int = 20) -> dict:
        """ItemList de gasolineras (GasStation), de la más barata a la más cara en diésel, para que Google
        entienda que la página es una lista de gasolineras con su dirección, ubicación y precios."""
        def clave(e):
            return (e.precios.get("diesel", e.precios.get("g95", 9)), e.id)

        def gasolinera(e: Estacion) -> dict:
            g = {"@type": "GasStation", "name": e.rotulo,
                 "address": {"@type": "PostalAddress", "streetAddress": e.direccion, "postalCode": e.cp,
                             "addressLocality": e.municipio.nombre if e.municipio else "",
                             "addressRegion": e.municipio.provincia.nombre if e.municipio else "",
                             "addressCountry": "ES"}}
            if e.lat is not None:
                g["geo"] = {"@type": "GeoCoordinates", "latitude": e.lat, "longitude": e.lon}
            ofertas = [{"@type": "Offer", "name": POR_CLAVE[c].nombre, "priceCurrency": "EUR",
                        "priceSpecification": {"@type": "UnitPriceSpecification", "price": e.precios[c],
                                               "priceCurrency": "EUR", "unitCode": "LTR"}}
                       for c in ("diesel", "g95") if c in e.precios]
            if ofertas:
                g["makesOffer"] = ofertas
            return g

        lista = sorted(estaciones, key=clave)[:n]
        return {"@context": "https://schema.org", "@type": "ItemList", "name": nombre,
                "numberOfItems": len(lista),
                "itemListElement": [{"@type": "ListItem", "position": i + 1, "item": gasolinera(e)}
                                    for i, e in enumerate(lista)]}

    @staticmethod
    def ld_faq(preguntas) -> dict:
        return {"@context": "https://schema.org", "@type": "FAQPage",
                "mainEntity": [{"@type": "Question", "name": p,
                                "acceptedAnswer": {"@type": "Answer", "text": r}} for p, r in preguntas]}

    def escribir(self, ruta: str, plantilla: str, prioridad="0.5", indexar=True, **ctx):
        html = self.env.get_template(plantilla).render(ruta=ruta, **ctx)
        destino = self.salida / ruta.lstrip("/")
        if ruta.endswith("/"):
            destino = destino / "index.html"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(html, encoding="utf-8")
        if indexar:
            self.paginas.append((ruta, self.hoy.isoformat(), prioridad))

    def fichero(self, nombre: str, contenido: str):
        destino = self.salida / nombre
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(contenido, encoding="utf-8")

    def serie(self, extraer, hoy_valor: float | None, dias: int = 30) -> list[tuple[date, float]]:
        """Serie de los últimos días a partir del histórico, con el valor actual para hoy."""
        puntos = {}
        desde = self.hoy - timedelta(days=dias)
        for f, snap in self.historico.items():
            if f >= desde:
                v = extraer(snap)
                if v is not None:
                    puntos[f] = v
        if hoy_valor is not None:
            puntos[self.hoy] = hoy_valor
        return sorted(puntos.items())

    def variacion(self, clave: str) -> float | None:
        if not self.ayer or clave not in self.ayer["nac"] or self.nac[clave].media is None:
            return None
        return round(self.nac[clave].media - self.ayer["nac"][clave]["media"], 3)

    @staticmethod
    def filas(estaciones: list[Estacion]) -> list[dict]:
        """Una fila por gasolinera con sus precios del selector y la diferencia con la más barata."""
        minimos = {c: min((e.precios[c] for e in estaciones if c in e.precios), default=None) for c in UI}
        filas = []
        for e in sorted(estaciones, key=lambda e: ("diesel" not in e.precios, e.precios.get("diesel", 9), e.rotulo)):
            filas.append({
                "e": e,
                "precios": {c: e.precios.get(c) for c in UI},
                "dif": {c: (e.precios[c] - minimos[c]) if c in e.precios else None for c in UI},
                "barata": {c: c in e.precios and e.precios[c] == minimos[c] and len(estaciones) > 1 for c in UI},
                "tiene": " ".join(c for c in UI if c in e.precios),
                "extras": [(POR_CLAVE[c].nombre, e.precios[c]) for c in EXTRAS if c in e.precios],
            })
        return filas

    def info_combustibles(self, estaciones, serie_fn=None, cercanas=None) -> dict:
        """Para cada combustible del selector: resumen, escalera de precios, cercanas y evolución."""
        info = {}
        for c in UI:
            r = resumen(estaciones, c)
            precios = [e.precios[c] for e in estaciones if c in e.precios]
            info[c] = {
                "r": r,
                "escalera": graficos.escalera(precios, r.media) if r.n > 2 else Markup(""),
                "cerca": mas_baratas(cercanas, c, 5) if cercanas is not None else [],
                "grafico": graficos.evolucion(serie_fn(c, r.media)) if serie_fn else Markup(""),
            }
        return info

    # ---------- páginas ----------

    def construir(self, articulo_hoy_snap: dict):
        if self.salida.exists():
            shutil.rmtree(self.salida)
        self.salida.mkdir(parents=True)
        shutil.copytree(ESTATICO, self.salida / "estatico")

        historico_completo = dict(self.historico)
        historico_completo[self.hoy] = articulo_hoy_snap
        noticias = [a for f, s in sorted(historico_completo.items(), reverse=True) if f >= LANZAMIENTO
                    for a in articulos.escribir_dia(s, historico_completo, self.url)]
        self.env.globals["noticia_hoy"] = noticias[0] if noticias else None
        try:
            lista = json.loads((imagenes.FOTOS / "credits.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            lista = []
        self.creditos_fotos = {Path(c["file"]).name: c for c in lista}
        self.env.globals["creditos_fotos"] = [c for c in lista if Path(c["file"]).name in imagenes.ENCUADRE]

        self.imagenes(noticias)
        self.inicio(noticias)
        self.calculadora()
        self.ruta()
        self.paginas_tema()
        for p in self.d.provincias:
            self.provincia(p)
        for m in self.d.municipios:
            self.municipio(m)
        self.widgets()
        self.marcas()
        self.noticias(noticias)
        self.legales()
        self.datos_json()
        self.ficheros_tecnicos()
        self.aviso_telegram(noticias[0] if noticias else None)
        self.datos_video()

    # ---------- imágenes para compartir y para Google ----------

    def imagenes(self, noticias):
        destino = self.salida / "imagenes"
        etiqueta = lambda f: f"{f.day} {fecha_corta(f).split()[1].upper()} {f.year}"  # noqa: E731
        hora_txt = hora(self.d.actualizado)
        n = len(self.d.estaciones)

        def fila(nombre, valor, nota="", sentido=0):
            return {"nombre": nombre, "valor": f"{valor:.3f}".replace(".", ","), "unidad": "€/l",
                    "nota": nota, "sentido": sentido}

        def fila_var(clave, nombre, valor, var):
            if var is None:
                return fila(nombre, valor)
            if abs(var) < 0.0005:
                return fila(nombre, valor, "igual que ayer")
            return fila(nombre, valor, cts(var), 1 if var > 0 else -1)

        # Una foto real de surtidores o gasolineras, distinta cada día, con el titular y los precios encima.
        usadas_por_dia: dict = {}
        for a in noticias:
            usadas = usadas_por_dia.setdefault(a.fecha, set())
            clave = a.fecha.toordinal() + a.orden * 3
            if a.slug != "precio-gasolina-diesel-hoy":
                # Las demás noticias llevan solo la foto, sin texto encima.
                grupo = ("deposito" if a.slug.startswith("merece") else
                         "gasolinera" if a.slug.startswith("gasolineras-mas-baratas") else "todas")
                foto = imagenes.elegir(grupo, clave, usadas)
                a.foto = self.creditos_fotos.get(foto)
                imagenes.solo_foto(self.salida / a.imagen.lstrip("/"), foto)
                continue
            if a.imagen_filas:
                filas = [fila(x["nombre"], x["valor"], x["nota"]) if x.get("nota") else
                         fila_var(None, x["nombre"], x["valor"], x.get("var")) for x in a.imagen_filas]
            else:
                filas = [fila_var(c, POR_CLAVE[c].nombre, a.medias[c], a.cambios.get(c))
                         for c in ("diesel", "g95") if a.medias.get(c)]
            foto = imagenes.elegir("todas", clave, usadas)
            a.foto = self.creditos_fotos.get(foto)
            imagenes.portada_con_foto(self.salida / a.imagen.lstrip("/"), a.tema,
                                      a.titular, filas, foto, etiqueta=etiqueta(a.fecha))
        medias = [fila_var(c, POR_CLAVE[c].nombre, self.nac[c].media, self.variacion(c))
                  for c in ("diesel", "g95") if self.nac[c].media]
        imagenes.portada_con_foto(destino / "portada.jpg", "Precios oficiales de hoy", "Gasolineras baratas cerca de ti",
                                  medias, "gas-pump-in-lannion.jpg", etiqueta=etiqueta(self.hoy))
        imagenes.portada_con_foto(destino / "ruta.jpg", "Gasolineras en tu ruta",
                                  "¿Dónde repostar más barato en tu viaje?", medias, "gasolinera-en-ceutaa-1.jpg",
                                  etiqueta=etiqueta(self.hoy))
        imagenes.portada_con_foto(destino / "calculadora.jpg", "Calculadora de gasolina",
                                  "¿Cuánto cuesta tu viaje en coche?", medias, "red-gas-pump-handle-in-car-gas.jpg",
                                  etiqueta=etiqueta(self.hoy))
        for p in self.d.provincias:
            filas = []
            for c in ("diesel", "g95"):
                barata = mas_baratas(p.estaciones, c, 1)
                if barata:
                    filas.append(fila(f"{POR_CLAVE[c].nombre}, la más barata", barata[0].precios[c],
                                      f"media {precio(resumen(p.estaciones, c).media).replace(' €', '')}"))
            imagenes.portada_con_foto(destino / "provincias" / f"{p.slug}.jpg", f"Precio de la gasolina en {p.nombre}",
                                      f"Gasolineras más baratas en {p.nombre} hoy", filas,
                                      imagenes.foto_para(int(p.id)), etiqueta=etiqueta(self.hoy))

    # ---------- páginas fijas para las búsquedas grandes ----------

    RANGOS = [(30, "1 mes"), (90, "3 meses"), (180, "6 meses"), (365, "1 año")]

    def serie_nac(self, c: str, dias: int = 365) -> list[tuple]:
        """[(fecha, media, p25, p75)] de España, del histórico y de hoy."""
        pts = {}
        desde = self.hoy - timedelta(days=dias)
        for f, s in self.historico.items():
            n = s.get("nac", {}).get(c)
            if f >= desde and n and n.get("media"):
                pts[f] = (f, n["media"], n.get("p25"), n.get("p75"))
        if self.nac[c].media:
            p25, p75 = historico_mod._cuartiles(self.d.estaciones, c)
            pts[self.hoy] = (self.hoy, self.nac[c].media, p25, p75)
        return [pts[k] for k in sorted(pts)]

    @staticmethod
    def _hace(serie: list[tuple], hoy: date, dias: int):
        """El valor más reciente de hace al menos `dias` días (si el histórico llega)."""
        objetivo = hoy - timedelta(days=dias)
        previos = [p for p in serie if p[0] <= objetivo]
        if not previos or (objetivo - previos[-1][0]).days > 3:
            return None
        return previos[-1]

    def graficos_rango(self, serie: list[tuple], nombre: str, clave: str = "") -> list[dict]:
        salida = []
        for dias, etiqueta in self.RANGOS:
            sub = [p for p in serie if p[0] >= self.hoy - timedelta(days=dias)]
            if len(sub) < 2 or (dias > 30 and (sub[-1][0] - sub[0][0]).days < dias * 0.6):
                continue
            svg = graficos.evolucion_banda(sub, nombre, ref=f"{clave}-{dias}" if clave else "",
                                           almacen=self.series_graficos)
            salida.append({"dias": dias, "etiqueta": etiqueta, "svg": svg})
        return salida

    def ficha_combustible(self, c: str) -> dict:
        serie = self.serie_nac(c)
        hoy = serie[-1] if serie else None
        cambios = []
        for dias, texto in ((1, "desde ayer"), (7, "en una semana"), (30, "en un mes"), (365, "en un año")):
            p = self._hace(serie, self.hoy, dias)
            if hoy and p:
                cambios.append({"texto": texto, "dif": hoy[1] - p[1], "antes": p[1], "fecha": p[0]})
        valores = [p[1] for p in serie]
        extremos = None
        if len(serie) >= 30:
            alto = max(serie, key=lambda p: p[1])
            bajo = min(serie, key=lambda p: p[1])
            extremos = {"alto": alto, "bajo": bajo, "dias": (serie[-1][0] - serie[0][0]).days}
        return {"c": c, "nombre": POR_CLAVE[c].nombre, "largo": POR_CLAVE[c].nombre_largo, "r": self.nac[c],
                "hoy": hoy, "cambios": cambios, "graficos": self.graficos_rango(serie, POR_CLAVE[c].nombre, clave=c),
                "extremos": extremos, "n_dias": len(valores)}

    def provincias_tabla(self, c: str) -> list[dict]:
        antes = self.historico.get(self.hoy - timedelta(days=7)) or {}
        filas = []
        for p in self.d.provincias:
            r = resumen(p.estaciones, c)
            if not r.media:
                continue
            q = antes.get("prov", {}).get(p.id, {}).get(c)
            barata = (mas_baratas(p.estaciones, c, 1) or [None])[0]
            filas.append({"p": p, "media": r.media, "dif7": (r.media - q[0]) if q else None, "barata": barata,
                          "especial": p.id in FISCALIDAD_ESPECIAL})
        return sorted(filas, key=lambda x: x["media"])

    def datos_video(self):
        """Prepara los datos del vídeo vertical del día (lo dibuja generador/video.py) y la página
        privada /video/ desde la que se descarga para subirlo a Instagram o TikTok."""
        from .texto import DIAS, MESES
        hoy = self.d.actualizado
        fecha = f"{DIAS[hoy.weekday()]} {hoy.day} de {MESES[hoy.month - 1]}"

        medias = []
        for c in ("diesel", "g95"):
            m, var = self.nac[c].media, self.variacion(c)
            if m is None:
                continue
            if var is None:
                nota, sentido = "", 0
            elif abs(var) < 0.0005:
                nota, sentido = "Igual que ayer", 0
            else:
                nota, sentido = f"{centimos(var)} {'más' if var > 0 else 'menos'} que ayer", 1 if var > 0 else -1
            medias.append({"nombre": POR_CLAVE[c].nombre, "valor": m, "nota": nota, "sentido": sentido})

        # La ciudad más grande de cada provincia (sin Canarias, Ceuta ni Melilla, con otros impuestos).
        ciudades, grandes = [], []
        for m in sorted(self.d.municipios, key=lambda m: -len(m.estaciones)):
            if m.provincia.id in FISCALIDAD_ESPECIAL or any(x.provincia.id == m.provincia.id for x in grandes):
                continue
            grandes.append(m)
            e = (mas_baratas(m.estaciones, "diesel", 1) or [None])[0]
            if e:
                ciudades.append({"nombre": m.nombre, "precio": e.precios["diesel"], "rotulo": e.rotulo})
            if len(ciudades) == 6:
                break
        ciudades.sort(key=lambda x: x["precio"])  # de más barata a más cara: la primera sale en verde

        # Lo que se ahorra en un depósito eligiendo bien la gasolinera en la ciudad más grande.
        ahorro = None
        if grandes:
            m = grandes[0]
            barata = (mas_baratas(m.estaciones, "diesel", 1) or [None])[0]
            r = resumen(m.estaciones, "diesel")
            if barata and r.maximo and r.maximo > barata.precios["diesel"]:
                ahorro = {"ciudad": m.nombre, "euros": round((r.maximo - barata.precios["diesel"]) * DEPOSITO_L, 2),
                          "litros": DEPOSITO_L}

        t = self.tendencias.get("diesel")
        # Solo cuando el precio se mueve: "estable" no aporta nada en un vídeo.
        tend = {"titulo": t["titulo"], "texto": t["texto"], "estado": t["estado"]} if t and t["estado"] in ("sube", "baja") else None

        lineas = [f"⛽ Precio de la gasolina hoy, {fecha}", ""]
        lineas += [f"{x['nombre']}: {precio(x['valor'])}/l" + (f" ({x['nota'].lower()})" if x["nota"] else "") for x in medias]
        if ciudades:
            lineas += ["", "El diésel más barato hoy en…"]
            lineas += [f"📍 {x['nombre']}: {precio(x['precio'])} ({x['rotulo']})" for x in ciudades]
        if ahorro:
            lineas += ["", f"💸 En {ahorro['ciudad']}, elegir bien la gasolinera ahorra hasta "
                           f"{numero(ahorro['euros'])} € en un depósito de {ahorro['litros']} litros."]
        if tend:
            lineas += ["", f"📈 ¿Repostar hoy o esperar? {tend['titulo']}. {tend['texto']}"]
        lineas += ["", "👉 Busca la gasolinera más barata de tu pueblo en gasvia.es (enlace en el perfil)", "",
                   "#gasolina #diesel #preciogasolina #gasolinerasbaratas #ahorro #coches #españa"]
        texto = "\n".join(lineas)

        nombre = f"gasvia-{hoy:%Y-%m-%d}.mp4"
        carpeta = self.salida.parent / "aviso"
        carpeta.mkdir(exist_ok=True)
        (carpeta / "video.json").write_text(json.dumps({
            "fecha": hoy.date().isoformat(), "fecha_texto": fecha, "medias": medias, "ciudades": ciudades,
            "ahorro": ahorro, "tendencia": tend, "texto": texto,
            "destino": str((self.salida / "video" / "gasvia-hoy.mp4").resolve()),
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        self.escribir("/video/", "video.html", indexar=False, texto=texto, nombre=nombre, fecha=fecha)

    def grandes_ciudades(self, n: int = 12) -> list:
        ciudades, vistas = [], set()
        for m in sorted(self.d.municipios, key=lambda m: -len(m.estaciones)):
            if m.provincia.id in vistas:
                continue
            vistas.add(m.provincia.id)
            ciudades.append(m)
            if len(ciudades) == n:
                break
        return ciudades

    def ranking_provincias(self) -> dict:
        """Las provincias de la más barata a la más cara para cada combustible, con su barra y su diferencia."""
        salida = {}
        for c in UI:
            nac = self.nac[c].media
            filas = []
            for p in self.d.provincias:
                r = resumen(p.estaciones, c)
                if r.media:
                    filas.append({"p": p, "media": r.media, "dif": (r.media - nac) if nac else None,
                                  "comunidad": p.comunidad, "especial": p.id in FISCALIDAD_ESPECIAL})
            if not filas:
                salida[c] = []
                continue
            filas.sort(key=lambda x: x["media"])
            # La barra se escala con la Península (Canarias, Ceuta y Melilla aplastarían el resto).
            pen = [x["media"] for x in filas if not x["especial"]] or [x["media"] for x in filas]
            lo, hi = min(pen), max(pen)
            for x in filas:
                q = 0 if hi == lo else (x["media"] - lo) / (hi - lo)
                x["pct"] = round(12 + 88 * max(0, min(1, q)))
                x["tono"] = "barata" if q < 0.34 else "media" if q < 0.67 else "cara"
            salida[c] = filas
        return salida

    def paginas_tema(self):
        peninsula = [e for e in self.d.estaciones if e.provincia_id not in FISCALIDAD_ESPECIAL]
        ciudades = self.grandes_ciudades()
        # Precio de la gasolina y precio del diésel.
        for c, otro, ruta in (("g95", "g98", "/precio-gasolina/"), ("diesel", "dieselp", "/precio-diesel/")):
            ficha = self.ficha_combustible(c)
            filas_c = [{"m": m, "r": resumen(m.estaciones, c), "barata": (mas_baratas(m.estaciones, c, 1) or [None])[0]}
                       for m in ciudades]
            self.escribir(ruta, "precio.html", prioridad="0.9", f=ficha, otro=self.nac.get(otro), otro_c=otro,
                          provincias=self.provincias_tabla(c), top=mas_baratas(peninsula, c, 10),
                          ciudades=[x for x in filas_c if x["r"].media], og_imagen="/imagenes/portada.jpg")
        # Gasolineras baratas: las más baratas de España y de cada provincia, por combustible.
        por_prov = {c: [x for x in self.provincias_tabla(c) if x["barata"]] for c in UI}
        marcas = {}
        for c in UI:
            filas = []
            for marca in self.d.marcas:
                r = resumen([e for e in marca.estaciones if e.provincia_id not in FISCALIDAD_ESPECIAL], c)
                if r.n >= 30:
                    filas.append({"marca": marca, "media": r.media})
            marcas[c] = sorted(filas, key=lambda x: x["media"])[:8]
        self.escribir("/gasolineras-baratas/", "baratas.html", prioridad="0.9",
                      top={c: mas_baratas(peninsula, c, 20) for c in UI}, por_prov=por_prov, marcas=marcas,
                      og_imagen="/imagenes/portada.jpg")
        # Estadísticas: todos los combustibles, meses, días de la semana y provincias que más cambian.
        fichas = {c: self.ficha_combustible(c) for c in UI}
        meses = {}
        for c in ("diesel", "g95"):
            for f, v, _, _ in self.serie_nac(c):
                meses.setdefault((f.year, f.month), {}).setdefault(c, []).append(v)
        tabla_meses = [{"anio": a, "mes": m, "diesel": statistics.fmean(d["diesel"]) if d.get("diesel") else None,
                        "g95": statistics.fmean(d["g95"]) if d.get("g95") else None}
                       for (a, m), d in sorted(meses.items(), reverse=True)]
        dias_semana = None
        serie_d = self.serie_nac("diesel")
        if len(serie_d) >= 56:
            valores = {p[0]: p[1] for p in serie_d}
            desv: dict[int, list[float]] = {}
            for f, v in valores.items():
                vecinos = [valores[f + timedelta(days=k)] for k in range(-3, 4) if f + timedelta(days=k) in valores]
                if len(vecinos) == 7:
                    desv.setdefault(f.weekday(), []).append(v - statistics.fmean(vecinos))
            if len(desv) == 7:
                dias_semana = [{"dia": DIAS_SEMANA[d], "dif": statistics.fmean(x)} for d, x in sorted(desv.items())]
        anio = self.historico.get(self.hoy - timedelta(days=365)) or {}
        cambio_prov = []
        for p in self.d.provincias:
            r = resumen(p.estaciones, "diesel")
            q = anio.get("prov", {}).get(p.id, {}).get("diesel")
            if r.media and q and p.id not in FISCALIDAD_ESPECIAL:
                cambio_prov.append({"p": p, "media": r.media, "dif": r.media - q[0]})
        cambio_prov.sort(key=lambda x: x["dif"])
        self.escribir("/estadisticas/", "estadisticas.html", prioridad="0.8", fichas=fichas, meses=tabla_meses,
                      dias_semana=dias_semana, cambio_prov=cambio_prov, og_imagen="/imagenes/portada.jpg")

    def ruta(self):
        self.escribir("/ruta/", "ruta.html", prioridad="0.8", og_imagen="/imagenes/ruta.jpg")

    def calculadora(self):
        precios = {c: self.nac[c].media for c in UI if self.nac[c].media}
        self.escribir("/calculadora/", "calculadora.html", prioridad="0.8", precios=precios,
                      og_imagen="/imagenes/calculadora.jpg")

    def inicio(self, noticias):
        peninsula = [e for e in self.d.estaciones if e.provincia_id not in FISCALIDAD_ESPECIAL]
        cifras = [{"c": c, "media": self.nac[c].media, "var": self.variacion(c), "n": self.nac[c].n}
                  for c in UI if self.nac[c].media]
        # La más barata de la Península: solo como dato, no como protagonista.
        mejor = {c: (mas_baratas(peninsula, c, 1) or [None])[0] for c in UI}

        # Grandes ciudades (una por provincia): su gasolinera más barata de hoy para cada combustible.
        ciudades, vistas = [], set()
        for m in sorted(self.d.municipios, key=lambda m: -len(m.estaciones)):
            if m.provincia.id in vistas:
                continue
            vistas.add(m.provincia.id)
            ciudades.append({
                "m": m, "n": len(m.estaciones),
                "min": {c: (mas_baratas(m.estaciones, c, 1) or [None])[0] for c in UI},
                "media": {c: resumen(m.estaciones, c).media for c in UI},
            })
            if len(ciudades) == 16:
                break

        # Lo que se ahorra comparando dentro de una misma ciudad.
        difs = []
        for m in self.d.municipios:
            r = resumen(m.estaciones, "diesel")
            if r.n >= 5:
                difs.append(r.maximo - r.minimo)
        media_dif = statistics.fmean(difs) if difs else 0
        hallazgo = {"cts": media_dif * 100, "n": len(difs), "euros": media_dif * DEPOSITO_L}

        # Marcas con la media más baja (con al menos 30 gasolineras en la Península).
        marcas = {}
        for c in UI:
            filas = []
            for marca in self.d.marcas:
                es = [e for e in marca.estaciones if e.provincia_id not in FISCALIDAD_ESPECIAL]
                r = resumen(es, c)
                if r.n >= 30:
                    filas.append({"marca": marca, "media": r.media, "n": r.n})
            filas.sort(key=lambda x: x["media"])
            marcas[c] = {"baratas": filas[:5], "cara": filas[-1] if len(filas) > 5 else None}
        media_pen = {c: resumen(peninsula, c).media for c in UI}

        grupos: dict[str, list] = {}
        for p in self.d.provincias:
            medias = {c: resumen(p.estaciones, c).media for c in UI}
            grupos.setdefault(p.comunidad or p.nombre, []).append({"p": p, "medias": medias, "n": len(p.estaciones)})
        prov_baratas, baratas = {}, {}
        for c in UI:
            filas = [x for g in grupos.values() for x in g if x["p"].id not in FISCALIDAD_ESPECIAL and x["medias"][c]]
            filas.sort(key=lambda x: x["medias"][c])
            prov_baratas[c] = filas[:5]
            baratas[c] = {x["p"].id for x in filas[:5]}
        grupos_ordenados = sorted(grupos.items(), key=lambda kv: slug(kv[0]))

        self.escribir(
            "/", "inicio.html", prioridad="1.0", cifras=cifras, mejor=mejor, ciudades=ciudades,
            fichas={c: self.ficha_combustible(c) for c in UI}, rank_prov=(rank := self.ranking_provincias()),
            # Los otros combustibles de la clasificación de provincias: el JS reordena la lista con esto.
            rank_json={c: [[x["p"].id, f'{x["media"]:.3f}'.replace(".", ","),
                            cts(x["dif"]) if x["dif"] is not None else "",
                            ("baja" if x["dif"] < -0.0005 else "sube" if x["dif"] > 0.0005 else "") if x["dif"] is not None else "",
                            x["pct"], x["tono"]] for x in rank[c]] for c in UI},
            ciudades_mapa=[[round(x["m"].lat, 4), round(x["m"].lon, 4), x["m"].nombre, f'{x["n"]} gasolineras', "",
                            self.url(x["m"].ruta)] + [x["min"][c].precios[c] if x["min"][c] else None for c in UI] + [0, None]
                           for x in ciudades if x["m"].lat is not None and x["m"].provincia.id not in FISCALIDAD_ESPECIAL],
            pines_mapa=mapa_estatico.pines(
                [{"nombre": x["m"].nombre, "url": self.url(x["m"].ruta), "lat": x["m"].lat, "lon": x["m"].lon,
                  "precios": {c: x["min"][c].precios[c] for c in UI if x["min"][c]}}
                 for x in ciudades if x["m"].lat is not None and x["m"].provincia.id not in FISCALIDAD_ESPECIAL], UI),
            hallazgo=hallazgo, marcas=marcas, media_pen=media_pen, prov_baratas=prov_baratas,
            grupos=grupos_ordenados, baratas=baratas, noticias=noticias[:6],
            n_estaciones=len(self.d.estaciones), n_municipios=len(self.d.municipios),
        )

    def provincia(self, p: Provincia):
        def serie(c, hoy):
            return self.serie(lambda s: (s["prov"].get(p.id, {}).get(c) or [None])[0], hoy)

        info = self.info_combustibles(p.estaciones, serie_fn=serie)
        for c in UI:
            info[c]["top"] = mas_baratas(p.estaciones, c, 6)
        municipios = []
        for m in p.municipios:
            minimos = {c: resumen(m.estaciones, c).minimo for c in UI}
            municipios.append({"m": m, "n": len(m.estaciones), "min": minimos})
        res = {c: info[c]["r"] for c in UI}
        r24 = sum(1 for e in p.estaciones if e.abierta_24h)
        faq = []
        for c in ("diesel", "g95"):
            e = res[c].mas_barata
            if e:
                faq.append((f"¿Dónde está {con_articulo(c, 'barat')} de {p.nombre}?",
                            f"Ahora mismo en {e.rotulo}, {e.direccion} ({e.municipio.nombre}), a "
                            f"{precio(e.precios[c])} el litro."))
        if res["diesel"].media and self.nac["diesel"].media:
            dif = res["diesel"].media - self.nac["diesel"].media
            comp = "igual que" if abs(dif) < 0.0005 else (
                f"{centimos(dif)} {'más caro' if dif > 0 else 'más barato'} que")
            faq.append((f"¿Cuánto cuesta el diésel en {p.nombre}?",
                        f"El precio medio del diésel en {p.nombre} es {precio(res['diesel'].media)} el "
                        f"litro, {comp} la media de España ({precio(self.nac['diesel'].media)})."))
        faq.append((f"¿Cuántas gasolineras hay en {p.nombre}?",
                    f"Hay {numero(len(p.estaciones), 0)} gasolineras de venta al público en "
                    f"{len(p.municipios)} municipios; {r24} abren las 24 horas."))
        self.escribir(p.ruta, "provincia.html", prioridad="0.8", p=p, info=info, nac=self.nac,
                      og_imagen=f"/imagenes/provincias/{p.slug}.jpg",
                      municipios=municipios, faq=faq,
                      ld_lista=self.ld_gasolineras(f"Gasolineras más baratas de {p.nombre}", p.estaciones),
                      otras=[x for x in self.d.provincias if x.id != p.id])

    def puesto_en_provincia(self, m: Municipio, c: str = "diesel") -> tuple[int, int] | None:
        """Puesto del municipio en su provincia por el precio más bajo de c (1 = el más barato)."""
        cache = self.__dict__.setdefault("_puestos", {})
        clave = (m.provincia.id, c)
        if clave not in cache:
            lista = sorted((min(e.precios[c] for e in x.estaciones if c in e.precios), x.id)
                           for x in self.d.municipios
                           if x.provincia.id == m.provincia.id and any(c in e.precios for e in x.estaciones))
            cache[clave] = {mid: i + 1 for i, (_, mid) in enumerate(lista)}, len(lista)
        puestos, total = cache[clave]
        return (puestos[m.id], total) if m.id in puestos else None

    def resumen_municipio(self, m: Municipio, res: dict, res_p: dict, serie_diesel: list) -> list[str]:
        """Un párrafo propio de cada pueblo, calculado con sus datos de hoy: frente a su provincia,
        su puesto, si compensa ir al pueblo de al lado, cuánto cambia dentro del pueblo y la semana."""
        frases = []
        r, rp = res["diesel"], res_p["diesel"]
        if r.minimo is not None:
            base = r.media if r.n > 1 else r.minimo
            que = "El precio medio del diésel" if r.n > 1 else "El diésel"
            if rp.media:
                dif = base - rp.media
                comp = ("igual que la media" if abs(dif) < 0.0005 else
                        f"{centimos(dif)} {'por encima' if dif > 0 else 'por debajo'} de la media")
                frases.append(f"{que} en {m.nombre} hoy es de {precio(base)}, {comp} de la provincia de "
                              f"{m.provincia.nombre} ({precio(rp.media)}).")
            puesto = self.puesto_en_provincia(m)
            if puesto and puesto[1] > 2:
                pos, total = puesto
                if pos == 1:
                    frases.append(f"Es el municipio con el diésel más barato de los {total} de {m.provincia.nombre} con gasolinera.")
                else:
                    frases.append(f"Por su gasolinera más barata, ocupa el puesto {pos} de {total} municipios de "
                                  f"{m.provincia.nombre} con gasolinera (el 1 es el más barato).")
            # ¿Compensa ir al pueblo de al lado?
            mejor = None
            for e, d in m.cercanas:
                v = e.precios.get("diesel")
                if v is not None and v < r.minimo - 0.005 and (mejor is None or v < mejor[0].precios["diesel"]):
                    mejor = (e, d)
            ahorro = (r.minimo - mejor[0].precios["diesel"]) * DEPOSITO_L if mejor else 0
            if mejor and ahorro < 1:
                frases.append(f"A menos de 15 km no hay grandes diferencias: como mucho ahorrarías "
                              f"{precio(ahorro, 2)} en un depósito de {DEPOSITO_L} litros.")
            elif mejor:
                e, d = mejor
                frases.append(f"Si te pilla de paso, en {e.municipio.nombre} (a {numero(d, 0)} km) hay diésel a "
                              f"{precio(e.precios['diesel'])} en {e.rotulo}: en un depósito de {DEPOSITO_L} litros "
                              f"ahorras {precio(ahorro, 2)} frente a la más barata de {m.nombre}.")
            elif m.cercanas:
                frases.append(f"Ninguna gasolinera a menos de 15 km tiene el diésel más barato que la mejor de "
                              f"{m.nombre}, así que no compensa desviarse.")
            if r.n > 1 and r.maximo - r.minimo >= 0.005:
                frases.append(f"Dentro de {m.nombre}, entre la gasolinera más barata y la más cara hay "
                              f"{centimos(r.maximo - r.minimo)}: {precio((r.maximo - r.minimo) * DEPOSITO_L, 2)} "
                              f"de diferencia al llenar {DEPOSITO_L} litros.")
        # La semana: con el histórico propio del municipio.
        semana = [(f, v) for f, v in serie_diesel if f >= self.hoy - timedelta(days=7)]
        if len(semana) >= 3:
            cambio = semana[-1][1] - semana[0][1]
            dias = (semana[-1][0] - semana[0][0]).days
            if abs(cambio) >= 0.0005:
                frases.append(f"En los últimos {dias} días, el diésel ha {'subido' if cambio > 0 else 'bajado'} "
                              f"{centimos(cambio)} en {m.nombre}.")
            else:
                frases.append(f"En los últimos {dias} días, el precio del diésel en {m.nombre} no se ha movido.")
        g = res["g95"]
        if g.mas_barata:
            frases.append(f"La gasolina 95 más barata está a {precio(g.minimo)} en {g.mas_barata.rotulo}.")
        return frases

    def municipio(self, m: Municipio):
        def serie(c, hoy):
            if c not in ("diesel", "g95"):
                return []
            return self.serie(lambda s: s["mun"].get(m.id, {}).get(c), hoy)

        cercanas = [e for e, _ in m.cercanas]
        info = self.info_combustibles(m.estaciones, serie_fn=serie, cercanas=cercanas)
        res_p = {c: resumen(m.provincia.estaciones, c) for c in UI}
        dist = {e.id: d for e, d in m.cercanas}
        vecinos = []
        for e, d in m.cercanas:
            if e.municipio not in vecinos:
                vecinos.append(e.municipio)
            if len(vecinos) == 10:
                break
        n = len(m.estaciones)
        n24 = sum(1 for e in m.estaciones if e.abierta_24h)
        res = {c: info[c]["r"] for c in UI}
        faq = []
        for c in ("diesel", "g95"):
            r = res[c]
            if not r.mas_barata:
                continue
            frase = con_articulo(c, "barat")
            resp = (f"La gasolinera con {frase} de {m.nombre} es {r.mas_barata.rotulo} "
                    f"({r.mas_barata.direccion}), a {precio(r.minimo)} el litro.")
            if r.n > 1 and r.maximo > r.minimo:
                resp += (f" La más cara está a {precio(r.maximo)}: llenar {DEPOSITO_L} litros en la más "
                         f"barata ahorra {precio((r.maximo - r.minimo) * DEPOSITO_L, 2)}.")
            faq.append((f"¿Cuál es la gasolinera con {frase} de {m.nombre}?", resp))
        if res["diesel"].media and res_p["diesel"].media:
            dif = res["diesel"].media - res_p["diesel"].media
            comp = "el mismo que" if abs(dif) < 0.0005 else (
                f"{centimos(dif)} {'por encima' if dif > 0 else 'por debajo'} de")
            faq.append((f"¿Cuál es el precio medio del diésel en {m.nombre}?",
                        f"{precio(res['diesel'].media)} el litro, {comp} la media de la provincia de "
                        f"{m.provincia.nombre} ({precio(res_p['diesel'].media)})."))
        faq.append((f"¿Cuántas gasolineras hay en {m.nombre}?",
                    f"Hay {n} gasolinera{'s' if n != 1 else ''} de venta al público"
                    + (f", de las que {n24} abre{'n' if n24 != 1 else ''} las 24 horas." if n24 else
                       ". Ninguna figura como abierta las 24 horas.")))
        if res["glp"].n:
            faq.append((f"¿Dónde repostar GLP (autogás) en {m.nombre}?",
                        f"{res['glp'].n} gasolinera{'s' if res['glp'].n != 1 else ''} vende"
                        f"{'n' if res['glp'].n != 1 else ''} GLP; la más barata es {res['glp'].mas_barata.rotulo} "
                        f"a {precio(res['glp'].minimo)}."))
        self.escribir(
            m.ruta, "municipio.html", prioridad="0.7" if n > 1 else "0.5",
            m=m, info=info, res=res, res_p=res_p, filas=self.filas(m.estaciones), dist=dist,
            og_imagen=f"/imagenes/provincias/{m.provincia.slug}.jpg",
            puntos_mapa=[[round(e.lat, 5), round(e.lon, 5), e.rotulo, e.direccion, m.nombre, ""]
                         + [e.precios.get(c) for c in UI] + [1 if e.abierta_24h else 0, e.semana]
                         for e in m.estaciones if e.lat is not None],
            vecinos=vecinos, faq=faq, n24=n24,
            resumen_texto=self.resumen_municipio(m, res, res_p, serie("diesel", res["diesel"].media)),
            ld_lista=self.ld_gasolineras(f"Gasolineras baratas en {m.nombre} ({m.provincia.nombre})", m.estaciones),
            presentes=[c for c in COMBUSTIBLES if any(c.clave in e.precios for e in m.estaciones)],
        )

    def widgets(self):
        """Widget para otras webs: una página mínima por municipio (/widget/<provincia>/<municipio>/, sin
        indexar) y la página /widget/ donde se elige el municipio y se copia el código."""
        self.escribir("/widget/", "widget.html", prioridad="0.5")
        for m in self.d.municipios:
            filas = []
            for c in ("diesel", "g95"):
                r = resumen(m.estaciones, c)
                if r.mas_barata:
                    filas.append({"nombre": POR_CLAVE[c].nombre, "precio": r.minimo, "rotulo": r.mas_barata.rotulo,
                                  "media": r.media, "n": r.n})
            cerca = None
            minimo = filas[0]["precio"] if filas and filas[0]["nombre"] == POR_CLAVE["diesel"].nombre else None
            for e, d in m.cercanas:
                v = e.precios.get("diesel")
                if v is not None and (minimo is None or v < minimo - 0.005) and (cerca is None or v < cerca["precio"]):
                    cerca = {"municipio": e.municipio.nombre, "km": numero(d, 0), "precio": v}
            self.escribir(m.ruta.replace("/gasolineras/", "/widget/", 1), "widget_municipio.html", indexar=False,
                          m=m, n=len(m.estaciones), filas=filas, cerca=cerca)

    def marcas(self):
        lista = []
        for marca in self.d.marcas:
            medias = {c: resumen(marca.estaciones, c).media for c in UI}
            lista.append({"marca": marca, "medias": medias, "n": len(marca.estaciones)})
        self.escribir("/marcas/", "marcas.html", prioridad="0.6",
                      lista=sorted(lista, key=lambda x: x["medias"]["diesel"] or 9), nac=self.nac)
        for marca in self.d.marcas:
            info = self.info_combustibles(marca.estaciones)
            for c in UI:
                info[c]["top"] = mas_baratas(marca.estaciones, c, 10)
            por_prov: dict = {}
            for e in marca.estaciones:
                por_prov.setdefault(e.municipio.provincia, []).append(e)
            provincias = sorted(({"p": p, "n": len(es), "min": {c: resumen(es, c).minimo for c in UI}}
                                 for p, es in por_prov.items()), key=lambda x: -x["n"])
            self.escribir(marca.ruta, "marca.html", prioridad="0.5", marca=marca, info=info, nac=self.nac,
                          provincias=provincias)

    def noticias(self, noticias):
        self.escribir("/noticias/", "noticias.html", prioridad="0.7", noticias=noticias,
                      og_imagen=noticias[0].imagen if noticias else None)
        for i, a in enumerate(noticias):
            self.escribir(a.ruta, "articulo.html", prioridad="0.6", a=a, og_imagen=a.imagen,
                          otras=[x for x in noticias if x is not a][:4],
                          anterior=noticias[i + 1] if i + 1 < len(noticias) else None,
                          siguiente=noticias[i - 1] if i > 0 else None)

    def legales(self):
        self.escribir("/sobre/", "sobre.html", prioridad="0.3")
        self.escribir("/aviso-legal/", "aviso_legal.html", prioridad="0.1")
        self.escribir("/privacidad/", "privacidad.html", prioridad="0.1")
        self.escribir("/cookies/", "cookies.html", prioridad="0.1")
        self.escribir("/404.html", "404.html", indexar=False)

    def datos_json(self):
        # [nombre, provincia, url, gasolineras, lat, lon]
        buscar = [[m.nombre, m.provincia.nombre, self.url(m.ruta), len(m.estaciones),
                   round(m.lat, 4) if m.lat is not None else None, round(m.lon, 4) if m.lon is not None else None]
                  for m in self.d.municipios]
        self.fichero("buscar.json", json.dumps(buscar, ensure_ascii=False, separators=(",", ":")))
        # [lat, lon, rótulo, dirección, municipio, url, diésel, 95, 98, GLP, abierta 24 h, semana]
        estaciones = [[round(e.lat, 5), round(e.lon, 5), e.rotulo, e.direccion, e.municipio.nombre,
                       self.url(e.municipio.ruta)] + [e.precios.get(c) for c in UI] + [1 if e.abierta_24h else 0, e.semana]
                      for e in self.d.estaciones if e.lat is not None]
        self.fichero("estaciones.json", json.dumps(estaciones, ensure_ascii=False, separators=(",", ":")))

    def aviso_telegram(self, a):
        """Prepara el mensaje del día para Telegram (lo publica generador/telegram.py)."""
        if not a:
            return
        from html import escape as h

        def linea_media(c):
            m, var = self.nac[c].media, self.variacion(c)
            if var is None or abs(var) < 0.0005:
                cambio = "igual que ayer" if var is not None else ""
            else:
                cambio = f"{'▲' if var > 0 else '▼'} {cts(var)}"
            return f"{POR_CLAVE[c].nombre}: <b>{precio(m)}/l</b>" + (f" ({cambio})" if cambio else "")

        partes = [f"⛽ <b>{h(a.titulo)}</b>", "", linea_media("diesel"), linea_media("g95"), "",
                  "<b>El diésel más barato hoy en…</b>"]
        ciudades, vistas = [], set()
        for m in sorted(self.d.municipios, key=lambda m: -len(m.estaciones)):
            if m.provincia.id in vistas or m.provincia.id in FISCALIDAD_ESPECIAL:
                continue
            vistas.add(m.provincia.id)
            e = (mas_baratas(m.estaciones, "diesel", 1) or [None])[0]
            if e:
                ciudades.append(f'<a href="{self.abs_url(m.ruta)}">{h(m.nombre)}</a>: {precio(e.precios["diesel"])} · {h(e.rotulo)}')
            if len(ciudades) == 8:
                break
        partes += ciudades
        t = self.tendencias.get("diesel")
        if t and t["estado"] != "pocos":
            partes += ["", f"📈 <b>¿Repostar hoy o esperar?</b> {h(t['titulo'])}. {h(t['texto'])}"]
        partes += ["", f'👉 <a href="{self.abs_url("/")}">Las más baratas cerca de ti</a> · <a href="{self.abs_url(a.ruta)}">Noticia completa</a>']
        texto = "\n".join(partes)
        while len(texto) > 1000 and ciudades:  # límite de Telegram para el pie de una foto
            partes.remove(ciudades.pop())
            texto = "\n".join(partes)
        carpeta = self.salida.parent / "aviso"
        carpeta.mkdir(exist_ok=True)
        (carpeta / "telegram.json").write_text(json.dumps({
            "fecha": a.fecha.isoformat(), "texto": texto,
            "imagen": str((self.salida / a.imagen.lstrip("/")).resolve()),
        }, ensure_ascii=False), encoding="utf-8")

    def ficheros_tecnicos(self):
        urls = "".join(
            f"<url><loc>{xml_escape(self.abs_url(r))}</loc><lastmod>{f}</lastmod>"
            f"<priority>{p}</priority></url>" for r, f, p in self.paginas)
        self.fichero("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>'
                     '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + urls + "</urlset>")
        if self.series_graficos:
            self.fichero("datos/graficos.json", json.dumps(self.series_graficos, ensure_ascii=False, separators=(",", ":")))
        self.fichero("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {self.abs_url('/sitemap.xml')}\n")
        if self.sitio.adsense:
            pub = self.sitio.adsense.replace("ca-", "")
            self.fichero("ads.txt", f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n")
        self.fichero(".nojekyll", "")
        # Algunos buscadores y lectores piden /favicon.ico aunque la página indique otro icono.
        shutil.copyfile(ESTATICO / "marca" / "favicon.ico", self.salida / "favicon.ico")
        if self.sitio.indexnow:  # Bing comprueba esta clave antes de aceptar los avisos de IndexNow
            self.fichero(f"{self.sitio.indexnow}.txt", self.sitio.indexnow)
        # La web se puede añadir a la pantalla de inicio del móvil como una app.
        icono = lambda n, t, extra=None: dict({"src": self.url(f"/estatico/marca/{n}"), "sizes": t, "type": "image/png"}, **(extra or {}))  # noqa: E731
        self.fichero("manifest.webmanifest", json.dumps({
            "name": self.sitio.nombre, "short_name": self.sitio.nombre, "lang": "es",
            "description": "Las gasolineras más baratas cerca de ti, con los precios oficiales de hoy.",
            "start_url": self.url("/"), "scope": self.url("/"), "display": "standalone",
            "background_color": "#f3f2ef", "theme_color": "#ffe27a",
            "icons": [icono("icono-192.png", "192x192"), icono("icono-512.png", "512x512"),
                      icono("icono-maskable-512.png", "512x512", {"purpose": "maskable"})],
        }, ensure_ascii=False, indent=1))
