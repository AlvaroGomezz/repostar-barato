# GASVIA (antes Repostar Barato)

Web automática de precios de gasolina y diésel en España. Cada 3 horas, GitHub Actions:

1. Descarga los precios oficiales de las ~11.000 gasolineras (API del Ministerio para la Transición Ecológica).
2. Genera unas 3.300 páginas: portada, 52 provincias, ~3.200 municipios, ranking de marcas y una noticia diaria.
3. Guarda un resumen diario en `historico/` (para los gráficos y las comparaciones con ayer y con hace una semana).
4. Publica la web en GitHub Pages.

No hay nada que supervisar. Si un día la API del Ministerio falla, la web sigue mostrando la última versión publicada.

## Probar en local

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m pytest -q
set SITE_URL=http://localhost:8000
.venv\Scripts\python -m generador --no-guardar-historico
.venv\Scripts\python -m http.server 8000 --directory publico
```

## Ajustes

Todo está en [sitio.toml](sitio.toml): nombre, dirección, AdSense, Search Console y datos del aviso legal.
Los pasos para monetizar están en [docs/GUIA.md](docs/GUIA.md).

## Estructura

- `generador/datos.py`: descarga e interpreta la API.
- `generador/historico.py`: resumen diario.
- `generador/articulos.py`: noticia diaria, escrita con plantillas a partir de los datos (sin IA, para que no pueda inventarse cifras).
- `generador/web.py` y `generador/plantillas/`: páginas HTML, sitemap, robots.txt y ads.txt.
