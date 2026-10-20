# Guía: de web publicada a web que genera ingresos

## Paso 1 · Dominio propio (necesario para AdSense) — ~10 €/año

AdSense no acepta direcciones `*.github.io`. Compra un dominio `.es` o `.com` (por ejemplo en Cloudflare, Namecheap o Dondominio).

Cuando lo tengas:
1. En GitHub: repositorio → Settings → Pages → Custom domain → escribe el dominio.
2. En tu proveedor del dominio, crea los registros DNS que indica GitHub.
3. Cambia `url` en `sitio.toml` por `https://tudominio.es`.

## Paso 2 · Google Search Console (gratis, imprescindible)

Así Google descubre las 3.300 páginas cuanto antes.
1. Entra en https://search.google.com/search-console y añade la propiedad con tu dominio.
2. Verifica con el método de «etiqueta HTML»: copia solo el valor de `content="..."` en `search_console` de `sitio.toml`.
3. En «Sitemaps», envía `sitemap.xml`.

## Paso 3 · Datos del aviso legal

En España, una web con ingresos debe identificar a su titular (LSSI). Rellena `titular`, `nif` y `email` en `sitio.toml`.
Usa un correo específico para la web, no el personal.

## Paso 4 · Google AdSense (cuando la web tenga algo de tráfico)

1. Solicita una cuenta en https://adsense.google.com con tu dominio.
2. Pon tu identificador (`ca-pub-...`) en `adsense` de `sitio.toml`. La web añade sola el código de anuncios automáticos y el fichero `ads.txt`.
3. En AdSense → Privacidad y mensajes, activa el mensaje de consentimiento del RGPD (obligatorio en Europa y gratuito).
4. Google revisa la web (de unos días a unas semanas). Si la rechaza por «contenido de poco valor», espera a tener más histórico y tráfico y vuelve a solicitarlo.

## Paso 5 · Canal de Telegram con el precio de cada mañana (gratis, opcional)

Cada día, a partir de las 8:00, la web publica en un canal de Telegram la imagen de la noticia, el precio
medio, el diésel más barato en las grandes ciudades y si conviene repostar hoy o esperar.

1. En Telegram, habla con **@BotFather**, escribe `/newbot` y sigue los pasos. Al final te da un
   **token** (algo como `123456:ABC-...`). No lo compartas.
2. Crea un **canal público** (por ejemplo, `@repostarbarato`) y añade tu bot como **administrador** con
   permiso para publicar.
3. En GitHub, en el repositorio: **Settings → Secrets and variables → Actions**.
   - Pestaña *Secrets*: **New repository secret**, nombre `TELEGRAM_TOKEN` y, como valor, el token.
   - Pestaña *Variables*: **New repository variable**, nombre `TELEGRAM_CHAT` y, como valor, el canal
     (`@repostarbarato`).
4. En `sitio.toml`, pon `telegram = "@repostarbarato"` para que la web enlace el canal.

Sin estos ajustes no se publica nada y la web funciona igual.

## Qué esperar

- Las primeras semanas Google indexa poco a poco; el tráfico llega a partir de 1–3 meses, si llega.
- Seguimiento: Search Console → Rendimiento (clics e impresiones por página).
- Ingresos orientativos de AdSense en España para este tema: 1–4 € por cada 1.000 visitas.

## Si algo falla

GitHub te avisa por correo si una ejecución falla. Lo más probable es un corte temporal de la API del Ministerio: la web sigue mostrando la última versión y se recupera sola en la siguiente ejecución.
