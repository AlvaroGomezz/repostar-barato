import gzip
import json
from datetime import date, datetime
from pathlib import Path

import pytest

from generador import articulos, historico
from generador.config import ZONA, Sitio
from generador.datos import interpretar, resumen
from generador.texto import capitalizar, centimos, nombre_bonito, precio, slug
from generador.web import Web


def fila(id_, muni, mid, prov="MADRID", pid="28", diesel="1,500", g95="1,600", lat="40,4", lon="-3,7",
         rotulo="REPSOL", tipo="P", horario="L-D: 24H", glp=""):
    return {
        "C.P.": "28001", "Dirección": "CALLE MAYOR, 1", "Horario": horario, "Latitud": lat,
        "Localidad": muni.upper(), "Longitud (WGS84)": lon, "Margen": "D", "Municipio": muni,
        "Precio Gasoleo A": diesel, "Precio Gasolina 95 E5": g95, "Precio Gasolina 98 E5": "",
        "Precio Gasoleo Premium": "", "Precio Gases licuados del petróleo": glp,
        "Precio Diésel Renovable": "", "Precio Adblue": "", "Provincia": prov, "Rótulo": rotulo,
        "Tipo Venta": tipo, "IDEESS": str(id_), "IDMunicipio": mid, "IDProvincia": pid, "IDCCAA": "13",
    }


@pytest.fixture
def bruto():
    filas = [
        fila(1, "Madrid", "100", diesel="1,450", g95="1,550"),
        fila(2, "Madrid", "100", diesel="1,600", g95="1,700", rotulo="BALLENOIL", horario="L-V: 07:00-22:00"),
        fila(3, "Alcobendas", "101", diesel="1,500", g95="", lat="40,50", lon="-3,64", glp="0,990"),
        fila(4, "Boalo (El)", "102", diesel="9,999", g95="1,650", lat="40,7", lon="-3,9"),  # diésel erróneo
        fila(5, "Socios", "103", tipo="R"),  # solo socios: se descarta
        fila(6, "Palmas de Gran Canaria (Las)", "200", prov="PALMAS (LAS)", pid="35",
             diesel="1,100", g95="1,200", lat="28,1", lon="-15,4"),
        fila(7, "Sevilla", "300", prov="SEVILLA", pid="41", diesel="1,480", g95="1,580",
             lat="37,39", lon="-5,98"),
    ]
    filas += [fila(100 + i, "Madrid", "100", rotulo="REPSOL") for i in range(20)]
    return {"Fecha": "20/10/2026 16:34:29", "ListaEESSPrecio": filas, "ResultadoConsulta": "OK"}


def test_textos():
    assert slug("Alcalá de Henares") == "alcala-de-henares"
    assert nombre_bonito("Pastoriza (A)") == "A Pastoriza"
    assert nombre_bonito("Hospitalet de Llobregat (L')") == "L'Hospitalet de Llobregat"
    assert capitalizar("AVENIDA CASTILLA LA MANCHA, 26") == "Avenida Castilla la Mancha, 26"
    assert capitalizar("CARRETERA N-IV KM 12") == "Carretera N-IV km 12"
    assert capitalizar("AUTOVIA AP-7, SALIDA 3") == "Autovia AP-7, Salida 3"
    assert precio(1.479) == "1,479 €"
    assert precio(None) == "—"
    assert centimos(-0.012) == "1,2 céntimos"
    assert centimos(0.01) == "1,0 céntimo"


def test_interpretar(bruto):
    d = interpretar(bruto)
    assert d.actualizado == datetime(2026, 10, 20, 16, 34, 29, tzinfo=ZONA)
    ids = {e.id for e in d.estaciones}
    assert "5" not in ids  # venta restringida
    boalo = next(e for e in d.estaciones if e.id == "4")
    assert "diesel" not in boalo.precios and boalo.precios["g95"] == 1.65
    assert boalo.municipio.nombre == "El Boalo"
    madrid = next(m for m in d.municipios if m.nombre == "Madrid")
    assert len(madrid.estaciones) == 22
    assert madrid.ruta == "/gasolineras/madrid/madrid/"
    assert {p.nombre for p in d.provincias} == {"Madrid", "Las Palmas", "Sevilla"}
    r = resumen(madrid.estaciones, "diesel")
    assert r.minimo == 1.45 and r.maximo == 1.6 and r.mas_barata.id == "1"
    # Alcobendas está a unos 12 km del centro de Madrid; El Boalo, más lejos.
    alcob = next(m for m in d.municipios if m.nombre == "Alcobendas")
    assert any(e.municipio.nombre == "Madrid" for e, _ in alcob.cercanas)
    assert [m.nombre for m in d.marcas] == ["REPSOL"]


def test_historico_ida_y_vuelta(bruto, tmp_path):
    d = interpretar(bruto)
    snap = historico.instantanea(d)
    assert snap["fecha"] == "2026-10-20"
    assert snap["pen"]["diesel"]["min"] == 1.45   # Canarias fuera
    assert snap["nac"]["diesel"]["min"] == 1.10   # Canarias dentro
    assert historico.guardar(snap, tmp_path, datetime(2026, 10, 20, 9, tzinfo=ZONA))
    assert not historico.guardar(snap, tmp_path, datetime(2026, 10, 20, 12, tzinfo=ZONA))
    assert historico.guardar(snap, tmp_path, datetime(2026, 10, 20, 21, tzinfo=ZONA))
    cargado = historico.cargar(tmp_path)
    assert cargado[date(2026, 10, 20)]["nac"]["diesel"]["min"] == 1.10


def test_articulo_con_y_sin_historico(bruto):
    d = interpretar(bruto)
    snap = historico.instantanea(d)
    a = articulos.escribir(snap, {}, lambda r: r)
    assert a.titulo.startswith("Precio de la gasolina y el diésel hoy, martes 20 de octubre")
    assert "respecto a ayer" not in a.entradilla
    ayer = json.loads(json.dumps(snap))
    ayer["fecha"] = "2026-10-19"
    ayer["nac"]["diesel"]["media"] += 0.02
    a2 = articulos.escribir(snap, {date(2026, 10, 19): ayer}, lambda r: r)
    assert "2,0 céntimos respecto a ayer" in a2.entradilla
    assert "el diésel baja" in a2.titulo
    textos = " ".join(str(p) for s in a2.secciones for p in s.parrafos)
    assert "Sevilla" in textos and "Las Palmas" in textos


def test_web_completa(bruto, tmp_path):
    d = interpretar(bruto)
    snap = historico.instantanea(d)
    sitio = Sitio("Prueba", "lema", "https://ejemplo.es/sub", "/sub", "ca-pub-123", "", "", "", "",
                  adsense_bloque="999")
    salida = tmp_path / "publico"
    web = Web(d, {}, sitio, salida)
    web.construir(snap)
    madrid = (salida / "gasolineras/madrid/madrid/index.html").read_text(encoding="utf-8")
    assert "<title>Gasolineras baratas en Madrid hoy · Diésel 1,450 €</title>" in madrid
    assert "1,450 €" in madrid and 'href="/sub/gasolineras/madrid/"' in madrid
    assert "FAQPage" in madrid and "BreadcrumbList" in madrid
    assert "adsbygoogle" in madrid
    # El bloque de anuncios fijo sale en municipio, provincia y portada.
    for pagina in ("gasolineras/madrid/madrid", "gasolineras/madrid", ""):
        html = (salida / pagina / "index.html").read_text(encoding="utf-8")
        assert html.count('data-ad-slot="999"') == 1, pagina
    for ruta in salida.rglob("*.html"):
        html = ruta.read_text(encoding="utf-8")
        assert "None" not in html and "undefined" not in html, ruta
    sitemap = (salida / "sitemap.xml").read_text(encoding="utf-8")
    assert "https://ejemplo.es/sub/gasolineras/madrid/madrid/" in sitemap
    assert "404" not in sitemap
    assert (salida / "ads.txt").read_text().startswith("google.com, pub-123, DIRECT")
    assert (salida / "noticias/2026-10-20-precio-gasolina-diesel-hoy/index.html").exists()
    buscar = json.loads((salida / "buscar.json").read_text(encoding="utf-8"))
    assert ["Madrid", "Madrid", "/sub/gasolineras/madrid/madrid/", 22] in [x[:4] for x in buscar]
    # Vídeo del día: la página privada no va al sitemap y cada escena se dibuja sin errores.
    assert "/video/" not in sitemap and 'content="noindex' in (salida / "video/index.html").read_text(encoding="utf-8")
    from generador import video
    datos_video = json.loads((tmp_path / "aviso" / "video.json").read_text(encoding="utf-8"))
    assert datos_video["ciudades"] and datos_video["medias"]
    lista = video.escenas(datos_video)
    inicio = 0.0
    for _, dur in lista:
        for t in (inicio + 0.05, inicio + dur / 2, inicio + dur - 0.05):
            assert video.fotograma(datos_video, t, lista).size == (video.ANCHO, video.ALTO)
        inicio += dur


def test_interfaz_por_combustible(bruto, tmp_path):
    """Cada página trae los 4 combustibles y el ahorro calculado; el selector funciona sin JavaScript."""
    d = interpretar(bruto)
    sitio = Sitio("Prueba", "lema", "https://ejemplo.es", "", "", "", "", "", "")
    salida = tmp_path / "publico"
    Web(d, {}, sitio, salida).construir(historico.instantanea(d))
    html = (salida / "gasolineras/madrid/madrid/index.html").read_text(encoding="utf-8")
    for c in ("diesel", "g95", "g98", "glp"):
        assert f'data-elegir="{c}"' in html and f'href="?c={c}"' in html
        assert f'class="respuesta" data-c="{c}"' in html
    # Diésel: 1,450 la más barata y 1,600 la más cara -> 50 l ahorran 7,50 €.
    assert 'data-min="1.45" data-max="1.6"' in html
    assert "7,50 €" in html
    assert 'class="escalera"' in html
    # Madrid no tiene GLP: lo dice en vez de dejar un hueco.
    assert "Ninguna gasolinera en Madrid vende GLP" in html
    assert html.count('class="estacion"') == 22


def test_horario_semanal():
    from generador.horario import semana
    assert semana("L-D: 24H") == "24"
    assert semana("L-D: 06:00-22:00") == "360-1320"
    assert semana("L-V: 06:00-22:00; S-D: 07:00-22:00").split("|")[5] == "420-1320"
    assert semana("L-S: 07:00-14:00 y 16:00-21:00").split("|")[6] == ""  # el domingo, cerrada
    assert semana("L-D: 22:00-06:00") == "1320-1800"  # cruza la medianoche
    assert semana("texto raro") is None


def test_tendencia():
    from datetime import date, timedelta
    from generador.tendencia import calcular
    hoy = date(2026, 10, 20)
    sube = calcular([(hoy - timedelta(days=i), 1.80 + 0.003 * (10 - i)) for i in range(10, -1, -1)], "diésel")
    assert sube["estado"] == "sube" and "no esperes" in sube["texto"]
    baja = calcular([(hoy - timedelta(days=i), 1.80 - 0.003 * (10 - i)) for i in range(10, -1, -1)], "diésel")
    assert baja["estado"] == "baja"
    assert calcular([(hoy, 1.8)], "diésel")["estado"] == "pocos"
