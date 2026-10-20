"""Genera todas las páginas estáticas de la web."""
import json
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import articulos, graficos
from .config import COMBUSTIBLES, FISCALIDAD_ESPECIAL, POR_CLAVE, RAIZ, Sitio
from .datos import Datos, Estacion, Municipio, mas_baratas, resumen
from .texto import (capitalizar, centimos, fecha_corta, fecha_larga, fecha_media, hora, numero,
                    precio)

PLANTILLAS = RAIZ / "generador" / "plantillas"
ESTATICO = RAIZ / "generador" / "estatico"
COLUMNAS = ["diesel", "g95", "g98", "glp"]   # columnas de las tablas de gasolineras
EXTRAS = ["dieselp", "hvo", "adblue"]       # se muestran debajo del nombre
DEPOSITO_L = 55


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
                                centimos=centimos, capitalizar=capitalizar)
        self.env.globals.update(
            sitio=sitio, url=self.url, abs_url=self.abs_url, C=POR_CLAVE, combustibles=COMBUSTIBLES,
            actualizado=datos.actualizado, anio=self.hoy.year, ld_migas=self.ld_migas, ld_faq=self.ld_faq,
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
        return self.nac[clave].media - self.ayer["nac"][clave]["media"]

    @staticmethod
    def filas_estaciones(estaciones: list[Estacion], orden="diesel") -> tuple[list, list[str]]:
        columnas = [c for c in COLUMNAS if any(c in e.precios for e in estaciones)]
        minimos = {c: min((e.precios[c] for e in estaciones if c in e.precios), default=None)
                   for c in columnas}
        if orden not in columnas and columnas:
            orden = columnas[0]
        ordenadas = sorted(estaciones, key=lambda e: (orden not in e.precios,
                                                       e.precios.get(orden, 9), e.rotulo))
        filas = []
        for e in ordenadas:
            celdas = [(c, e.precios.get(c), e.precios.get(c) is not None and
                       e.precios.get(c) == minimos[c] and len(estaciones) > 1) for c in columnas]
            extras = [(POR_CLAVE[c].nombre, e.precios[c]) for c in EXTRAS if c in e.precios]
            filas.append({"e": e, "celdas": celdas, "extras": extras})
        return filas, columnas

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
        pen = [p for p in self.d.provincias if p.id not in FISCALIDAD_ESPECIAL]
        provincias = []
        for p in self.d.provincias:
            r = {c: resumen(p.estaciones, c) for c in ("diesel", "g95")}
            provincias.append((p, r))
        baratas_d = sorted(((p, r) for p, r in provincias if p.id not in FISCALIDAD_ESPECIAL
                            and r["diesel"].media), key=lambda x: x[1]["diesel"].media)
        peninsula = [e for p in pen for e in p.estaciones]
        grafico = graficos.evolucion([
            ("Diésel", "s1", self.serie(lambda s: s["nac"].get("diesel", {}).get("media"),
                                         self.nac["diesel"].media)),
            ("Gasolina 95", "s2", self.serie(lambda s: s["nac"].get("g95", {}).get("media"),
                                              self.nac["g95"].media)),
        ])
        self.escribir(
            "/", "inicio.html", prioridad="1.0",
            nac=self.nac, variacion=self.variacion, provincias=provincias,
            baratas=baratas_d[:5], caras=list(reversed(baratas_d[-5:])),
            top_d=mas_baratas(peninsula, "diesel", 5), top_g=mas_baratas(peninsula, "g95", 5),
            noticias=noticias[:5], grafico=grafico, n_estaciones=len(self.d.estaciones),
            n_municipios=len(self.d.municipios), deposito=DEPOSITO_L,
        )

    def provincia(self, p):
        res = {c.clave: resumen(p.estaciones, c.clave) for c in COMBUSTIBLES}
        municipios = []
        for m in p.municipios:
            municipios.append({"m": m, "n": len(m.estaciones),
                               "diesel": resumen(m.estaciones, "diesel").minimo,
                               "g95": resumen(m.estaciones, "g95").minimo})
        grafico = graficos.evolucion([
            ("Diésel", "s1", self.serie(lambda s: (s["prov"].get(p.id, {}).get("diesel") or [None])[0],
                                         res["diesel"].media)),
            ("Gasolina 95", "s2", self.serie(lambda s: (s["prov"].get(p.id, {}).get("g95") or [None])[0],
                                              res["g95"].media)),
        ])
        r24 = sum(1 for e in p.estaciones if e.abierta_24h)
        faq = []
        if res["diesel"].mas_barata:
            e = res["diesel"].mas_barata
            faq.append((f"¿Cuál es la gasolinera con el diésel más barato de {p.nombre}?",
                        f"Ahora mismo es {e.rotulo}, en {e.direccion} ({e.municipio.nombre}), a "
                        f"{precio(e.precios['diesel'])} el litro."))
        if res["g95"].mas_barata:
            e = res["g95"].mas_barata
            faq.append((f"¿Dónde está la gasolina 95 más barata de {p.nombre}?",
                        f"En {e.rotulo}, en {e.direccion} ({e.municipio.nombre}), a "
                        f"{precio(e.precios['g95'])} el litro."))
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
        self.escribir(
            p.ruta, "provincia.html", prioridad="0.8", p=p, res=res, nac=self.nac,
            municipios=municipios, grafico=grafico, faq=faq,
            top_d=mas_baratas(p.estaciones, "diesel", 10), top_g=mas_baratas(p.estaciones, "g95", 10),
            otras=[x for x in self.d.provincias if x.id != p.id],
        )

    def municipio(self, m: Municipio):
        res = {c.clave: resumen(m.estaciones, c.clave) for c in COMBUSTIBLES}
        res_p = {c: resumen(m.provincia.estaciones, c) for c in ("diesel", "g95")}
        filas, columnas = self.filas_estaciones(m.estaciones)
        cercanas_est = [e for e, _ in m.cercanas]
        dist = {e.id: d for e, d in m.cercanas}
        cerca_d = mas_baratas(cercanas_est, "diesel", 5)
        cerca_g = mas_baratas(cercanas_est, "g95", 5)
        vecinos = []
        for e, d in m.cercanas:
            if e.municipio not in vecinos:
                vecinos.append(e.municipio)
            if len(vecinos) == 10:
                break
        grafico = graficos.evolucion([
            ("Diésel", "s1", self.serie(lambda s: s["mun"].get(m.id, {}).get("diesel"), res["diesel"].media)),
            ("Gasolina 95", "s2", self.serie(lambda s: s["mun"].get(m.id, {}).get("g95"), res["g95"].media)),
        ])
        n = len(m.estaciones)
        n24 = sum(1 for e in m.estaciones if e.abierta_24h)
        faq = []
        for clave in ("diesel", "g95"):
            r = res[clave]
            if not r.mas_barata:
                continue
            nombre = POR_CLAVE[clave].nombre_largo
            resp = (f"La gasolinera con el {nombre} más barato de {m.nombre} es {r.mas_barata.rotulo} "
                    f"({r.mas_barata.direccion}), a {precio(r.minimo)} el litro.")
            if r.n > 1 and r.maximo > r.minimo:
                resp += (f" La más cara está a {precio(r.maximo)}: llenar {DEPOSITO_L} litros en la más "
                         f"barata ahorra {precio((r.maximo - r.minimo) * DEPOSITO_L, 2)}.")
            faq.append((f"¿Cuál es la gasolinera con el {nombre} más barato de {m.nombre}?", resp))
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
            m=m, res=res, res_p=res_p, filas=filas, columnas=columnas, cerca_d=cerca_d,
            cerca_g=cerca_g, dist=dist, vecinos=vecinos, grafico=grafico, faq=faq, deposito=DEPOSITO_L,
        )

    def marcas(self):
        lista = []
        for marca in self.d.marcas:
            r = {c: resumen(marca.estaciones, c) for c in ("diesel", "g95")}
            lista.append((marca, r))
        con_diesel = [x for x in lista if x[1]["diesel"].media]
        self.escribir("/marcas/", "marcas.html", prioridad="0.6",
                      lista=sorted(con_diesel, key=lambda x: x[1]["diesel"].media), nac=self.nac)
        for marca, r in lista:
            res = {c.clave: resumen(marca.estaciones, c.clave) for c in COMBUSTIBLES}
            por_prov: dict = {}
            for e in marca.estaciones:
                por_prov.setdefault(e.municipio.provincia, []).append(e)
            provincias = sorted(((p, len(es), resumen(es, "diesel").minimo) for p, es in por_prov.items()),
                                key=lambda x: -x[1])
            self.escribir(marca.ruta, "marca.html", prioridad="0.5", marca=marca, res=res, nac=self.nac,
                          provincias=provincias,
                          top_d=mas_baratas(marca.estaciones, "diesel", 15),
                          top_g=mas_baratas(marca.estaciones, "g95", 15))

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
                       self.url(e.municipio.ruta), e.precios.get("diesel"), e.precios.get("g95"),
                       e.precios.get("g98")]
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
