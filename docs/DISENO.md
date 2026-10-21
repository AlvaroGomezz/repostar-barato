# Diseño y experiencia de uso (GASVIA)

## La idea

**Lo primero, tus gasolineras.** La portada se abre con tu zona: usas tu ubicación o escribes tu pueblo y
ves al momento las más baratas, con la distancia, lo que ahorras y un botón para ir. La web recuerda tu
zona, tu combustible y tus litros, así que en la siguiente visita lo ves nada más entrar.

Los datos de España (medias, la más barata de la Península) quedan como referencia, más abajo.

## Quién entra y qué busca

Llega desde Google («gasolinera más barata en …») o vuelve desde el móvil, casi siempre a punto de
repostar. Cada pantalla responde primero a una pregunta:

- **Portada:** ¿dónde está la más barata cerca de mí? → tu zona.
- **Municipio:** ¿dónde lleno más barato aquí, y cómo llego? → cartel amarillo con el precio en grande y
  «Cómo llegar».
- **Provincia:** ¿qué municipio y qué gasolinera tienen el precio más bajo?

## La portada, sección a sección

1. **Cabecera amarilla.** A la izquierda: buscador, «Usar mi ubicación», combustible y litros. A la
   derecha, la tarjeta de tu zona:
   - **Sin zona elegida:** las 12 grandes ciudades con su gasolinera más barata de hoy. Un toque abre la
     lista de esa ciudad sin cambiar de página.
   - **Con ubicación:** «Cerca de ti», con radio de 3, 5, 10 o 25 km (se elige solo el menor con al menos
     seis gasolineras), orden por precio o por cercanía y filtro de abiertas 24 h.
   - **Con municipio:** todas sus gasolineras, de la más barata a la más cara.
   - **Siempre:** la más barata en grande, lo que cuesta llenar y lo que ahorras frente a la media, y
     las siguientes con su botón «Ir».
2. **Hoy en España:** las cuatro medias con la variación desde ayer (al tocarlas se elige el
   combustible) y la más barata de la Península como dato.
3. **Para pagar menos:** el ahorro medio por depósito al comparar dentro de una ciudad, las marcas más
   baratas y las provincias más baratas.
4. **Busca por provincia:** las 52, agrupadas por comunidad.
5. **Pie en teselas:** la noticia del día, las páginas y el nombre de la web.

En el móvil, la tarjeta de tu zona va justo después del combustible, y los litros, después de la tarjeta.

## Estilo periódico

- **Barra de temas** en todas las páginas, como la de un diario: «HOY · Precio de la gasolina, 20 de
  octubre», gasolineras cerca de mí, calculadora, provincias, marcas y noticias.
- **Lo último** en la portada: la noticia del día en grande, con su imagen, y al lado los días anteriores y
  las herramientas.
- **La noticia** se maqueta como en un diario: antetítulo, titular largo, sumario, imagen, firma y fecha,
  botones para compartir y el precio en las 12 grandes ciudades («El precio de la gasolina hoy en Madrid»).
- **Imágenes para Google y redes** (`generador/imagenes.py`, con Pillow): 1200 × 675, dibujadas con los
  precios del día. Hay una por noticia, una para la portada, otra para la calculadora y una por provincia
  (los municipios usan la de su provincia). Se declaran en `og:image`, en el `NewsArticle` y con
  `max-image-preview:large`, que es lo que Google necesita para enseñarlas en los resultados.

## Herramientas prácticas

- **Abierta ahora** (`generador/horario.py`): el horario del Ministerio se convierte en una semana compacta
  y el navegador dice si cada gasolinera está abierta, a qué hora cierra o cuándo abre. Hay un filtro
  «Abiertas ahora» en la portada, en la ruta y en cada municipio. Si la más barata está cerrada, se avisa de
  la más barata abierta.
- **Mapa de precios** (MapLibre con los mapas gratuitos de OpenFreeMap, se carga al llegar a él): siempre
  visible en tu zona, en la ruta y en cada municipio. Burbujas con el precio: más barata (verde lleno), barata,
  media y cara; leyenda, «Mi ubicación» y zoom con dos dedos o Ctrl + rueda.
- **Gráficos interactivos:** al pasar el ratón o el dedo se ve la fecha, el precio y la franja del 50 % central.
- **Cabecera con menú:** enlaces principales y un botón «Menú» con todas las secciones agrupadas.
- **Ruta** (`/ruta/`): origen y destino, con el camino por carretera del servicio público de OSRM. Muestra
  las gasolineras a 1, 3 o 5 km del camino, la más barata, dónde parar tramo a tramo (cada 100 km) y lo que
  cuesta la gasolina del viaje.
- **¿Repostar hoy o esperar?** (`generador/tendencia.py`): la tendencia de los últimos 7 días y, con tres
  semanas de histórico, el día de la semana más barato. En la portada, en la noticia y en Telegram.
- **Telegram** (`generador/telegram.py`): aviso diario en un canal (ver docs/GUIA.md, paso 5).
- **Barra fija en el móvil**: «Cerca de mí», «Buscar», «Ruta», «Calculadora» y «Noticias».

## Noticias de cada día (`generador/articulos.py`, `escribir_dia`)

| Noticia | Cuándo | Qué aporta |
| --- | --- | --- |
| Precio de la gasolina y el diésel hoy | cada día | medias, provincias, grandes ciudades, las más baratas |
| ¿Merece la pena echar gasolina hoy o es mejor esperar? | cada día, desde que hay 3 días de histórico | tendencia, tabla de los últimos días, dónde sube y baja, recomendación |
| Gasolineras más baratas en [ciudad] hoy | cada día, 2 ciudades por turnos (cada una cada 6 días) | top 5 de diésel y gasolina 95 con dirección, ahorro, comparación con España |
| Resumen de la semana | los lunes, con el histórico de hace 7 días | cambio semanal por combustible, provincias, ciudades y marcas |
| Precio más alto o más bajo en N días | solo cuando ocurre (con 14 días de histórico o más) | la cifra, los últimos días y qué hacer |

Cada noticia sale de datos propios de ese día; si no hay datos suficientes para que aporte algo, no se
publica. No se generan decenas de páginas casi iguales: Google penaliza el contenido automático en masa.

## Imágenes de las noticias

Foto real de surtidores o gasolineras a la derecha, con el titular y los precios del día sobre el amarillo de
la marca (`imagenes.portada_con_foto`). La foto cambia cada día; las provincias tienen la suya. Fotos de
Wikimedia Commons con licencia libre, en `generador/fotos/` con sus créditos (`credits.json`), que se
muestran al pie de la foto de cada noticia y en «Sobre esta web».

## Calculadora

`/calculadora/`: lo que cuesta un viaje (kilómetros, ida y vuelta, consumo, precio y personas que pagan)
con el precio medio de hoy del combustible elegido, y lo que cuesta llenar el depósito.

## Sistema

- **Tipografía:** Albert Sans.
- **Paleta:**
  - fondo claro (#f3f2ef) y tarjetas blancas;
  - amarillo de cartel de carretera (#ffd43b) para la marca, la cabecera y la respuesta de cada municipio;
  - tinta negra (#141414);
  - verde (#0a7c4f) para el ahorro y «Cómo llegar».
- **Forma:** tarjetas con esquinas de 16 px; botones y campos de 10 px.
- **Movimiento:** el titular sube línea a línea, la tarjeta de tu zona entra desde abajo, la cifra de la
  más barata rueda y las secciones aparecen al bajar. Todo se desactiva con «reducir movimiento».
- **Comportamiento:**
  - el combustible y los litros se recuerdan, y el combustible va en la dirección (`?c=g95`);
  - la zona se guarda en el navegador (`rb-lugar`): el municipio o la ubicación redondeada a unos 100 m;
  - si el navegador ya tenía permiso de ubicación, se usa sola al entrar;
  - sin JavaScript se muestran el diésel y los enlaces a cada ciudad.
- **Fotos solo donde informan:** en las imágenes de las noticias, nunca como decoración de la portada.

## Herramientas

Están instaladas en local y no se suben al repositorio.

- **Taste Skill** (`Leonxlnx/taste-skill`): dirección de arte, inspector a 1440, 768 y 390 px, y crítica
  por rondas. La portada y las páginas interiores pasan con 0 fallos.
- **Web Design Guidelines** (Vercel): accesibilidad, foco, formularios, movimiento.
- **Awesome Design** (`VoltAgent/awesome-design-md`): referencias de Uber y NerdWallet.
- **Playwright CLI:** pruebas de uso (poste, combustible, litros, búsqueda, filtros, menú).
- **Image-to-Code:** no se aplicó, porque necesita una herramienta para generar imágenes.

## Avisos del inspector que se aceptan

- `few-pictures` y `no-footage`: sin fotos a propósito (ver arriba).
- `card-rows` y `ragged-row`: listas de gasolineras junto a resúmenes cortos.
- `app-title-size` y `kpi-size` en las páginas interiores: el título y el precio grandes son la identidad
  de la web.
- `body-size`: buena parte del texto son datos secundarios de las listas, a 15 px.
