# Diseño y experiencia de uso

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
- **Sin fotos ni vídeo:** las imágenes de gasolineras antiguas no ayudaban a nadie. La pieza visual es la
  propia lista de precios.

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
