"""Genera todas las páginas estáticas de la web."""
import json
import shutil
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from . import articulos, graficos
from .config import COMBUSTIBLES, FISCALIDAD_ESPECIAL, POR_CLAVE, RAIZ, Sitio, con_articulo
from .datos import Datos, Estacion, Municipio, Provincia, mas_baratas, resumen
from .texto import (capitalizar, centimos, fecha_corta, fecha_larga, fecha_media, hora, numero,
                    precio)

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
                                centimos=centimos, capitalizar=capitalizar, cifra=cifra, cts=cts)
        self.env.globals.update(
            sitio=sitio, url=self.url, abs_url=self.abs_url, C=POR_CLAVE, combustibles=COMBUSTIBLES,
            UI=UI, actualizado=datos.actualizado, anio=self.hoy.year, ld_migas=self.ld_migas,
            ld_faq=self.ld_faq, deposito=DEPOSITO_L,
        )
        self.nac = {c.clave: resumen(datos.estaciones, c.clave) for c in COMBUSTIBLES}
        self.ayer = historico.get(self.hoy - timedelta(days=1))

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

    def serie(self, extraer, hoy_valor: float | None) -> list[tuple[date, float]]:
        """Serie de los últimos 30 días a partir del histórico, con el valor actual para hoy."""
        puntos = {}
        desde = self.hoy - timedelta(days=30)
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
        noticias = [articulos.escribir(s, historico_completo, self.url)
                    for f, s in sorted(historico_completo.items(), reverse=True)]

        self.inicio(noticias)
        for p in self.d.provincias:
            self.provincia(p)
        for m in self.d.municipios:
            self.municipio(m)
        self.marcas()
        self.noticias(noticias)
        self.legales()
        self.datos_json()
        self.ficheros_tecnicos()

    def inicio(self, noticias):
        peninsula = [e for e in self.d.estaciones if e.provincia_id not in FISCALIDAD_ESPECIAL]
        provincias = []
        for p in self.d.provincias:
            medias = {c: resumen(p.estaciones, c).media for c in UI}
            provincias.append({"p": p, "medias": medias, "n": len(p.estaciones)})

        def serie(c, hoy):
            return self.serie(lambda s: s["nac"].get(c, {}).get("media"), hoy)

        info = self.info_combustibles(peninsula, serie_fn=serie)
        for c in UI:
            info[c]["top"] = mas_baratas(peninsula, c, 5)
            info[c]["nac"] = self.nac[c]
            info[c]["var"] = self.variacion(c)
            pen = sorted((x for x in provincias if x["p"].id not in FISCALIDAD_ESPECIAL and x["medias"][c]),
                         key=lambda x: x["medias"][c])
            info[c]["prov_barata"] = pen[0] if pen else None
            info[c]["prov_cara"] = pen[-1] if pen else None
        self.escribir(
            "/", "inicio.html", prioridad="1.0", info=info, provincias=provincias,
            noticias=noticias[:4], n_estaciones=len(self.d.estaciones), n_municipios=len(self.d.municipios),
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
                      municipios=municipios, faq=faq,
                      otras=[x for x in self.d.provincias if x.id != p.id])

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
            vecinos=vecinos, faq=faq, n24=n24,
            presentes=[c for c in COMBUSTIBLES if any(c.clave in e.precios for e in m.estaciones)],
        )

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
        self.escribir("/noticias/", "noticias.html", prioridad="0.7", noticias=noticias)
        for i, a in enumerate(noticias):
            self.escribir(a.ruta, "articulo.html", prioridad="0.6", a=a,
                          anterior=noticias[i + 1] if i + 1 < len(noticias) else None,
                          siguiente=noticias[i - 1] if i > 0 else None)

    def legales(self):
        self.escribir("/sobre/", "sobre.html", prioridad="0.3")
        self.escribir("/aviso-legal/", "aviso_legal.html", prioridad="0.1")
        self.escribir("/privacidad/", "privacidad.html", prioridad="0.1")
        self.escribir("/cookies/", "cookies.html", prioridad="0.1")
        self.escribir("/404.html", "404.html", indexar=False)

    def datos_json(self):
        buscar = [[m.nombre, m.provincia.nombre, self.url(m.ruta), len(m.estaciones)]
                  for m in self.d.municipios]
        self.fichero("buscar.json", json.dumps(buscar, ensure_ascii=False, separators=(",", ":")))
        estaciones = [[round(e.lat, 5), round(e.lon, 5), e.rotulo, e.direccion, e.municipio.nombre,
                       self.url(e.municipio.ruta)] + [e.precios.get(c) for c in UI]
                      for e in self.d.estaciones if e.lat is not None]
        self.fichero("estaciones.json", json.dumps(estaciones, ensure_ascii=False, separators=(",", ":")))

    def ficheros_tecnicos(self):
        urls = "".join(
            f"<url><loc>{xml_escape(self.abs_url(r))}</loc><lastmod>{f}</lastmod>"
            f"<priority>{p}</priority></url>" for r, f, p in self.paginas)
        self.fichero("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>'
                     '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + urls + "</urlset>")
        self.fichero("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {self.abs_url('/sitemap.xml')}\n")
        if self.sitio.adsense:
            pub = self.sitio.adsense.replace("ca-", "")
            self.fichero("ads.txt", f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n")
        self.fichero(".nojekyll", "")
