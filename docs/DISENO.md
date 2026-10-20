# Diseño y experiencia de uso

## La idea

**El poste de precios de la gasolinera es el buscador.** La portada pone a funcionar el producto en lugar de
describirlo: un poste como los que hay junto a la carretera, con los precios en grande. Escribes tu pueblo
o usas tu ubicación y el poste muestra los precios de tu gasolinera más barata, con las cifras rodando.

Ningún comparador de la competencia (tablas y mapas) lo hace así.

## Quién entra y qué busca

Llega desde Google («gasolinera más barata en …»), casi siempre con el móvil y a punto de repostar.
Cada pantalla responde primero a una pregunta:

- **Portada:** ¿dónde está lo más barato para mí? → el poste.
- **Municipio:** ¿dónde lleno más barato aquí, y cómo llego? → panel negro con el precio en grande y «Cómo llegar».
- **Provincia:** ¿qué municipio y qué gasolinera tienen el precio más bajo?

## La portada, sección a sección

1. **Poste** (héroe en dos tonos, el poste a la derecha): buscador, ubicación, toque en un combustible.
2. **Hoy, en España, un litro cuesta:** las cuatro medias, enormes y alineadas en la coma, con la
   variación desde ayer. Foto de una antigua gasolinera de CAMPSA.
3. **Elegir bien, cada vez:** vídeo de la M-23 de Madrid y un dato real calculado cada día (la diferencia
   media entre la más cara y la más barata de una misma ciudad).
4. **Así se ve [pueblo] hoy:** cinco piezas reales del producto con los datos de un pueblo (lista,
   escalera de precios, ahorro, cercanía, combustible). En pantallas anchas la fila avanza de lado con el
   scroll y se ilumina la del centro.
5. **Las más baratas de la Península hoy:** pestañas por combustible y bandas.
6. **Tu provincia:** las 52 agrupadas por comunidad, con las cinco más baratas marcadas. Foto de una
   CAMPSA en Portillo (Valladolid).
7. **Cómo funciona:** la misma tarjeta de precio en cuatro momentos, del surtidor a esta web.
8. **Pie en teselas:** la Gasolinera Gesa (Madrid, 1927), la noticia del día y los créditos de las fotos.

## Sistema

- **Dirección:** «The product performs» (Taste Skill, semilla 1604849307).
- **Tipografía:** Albert Sans.
- **Paleta:** masilla y negro (#dedad3, #0a0a0a). Azul petróleo (#256f82) para la acción y el precio más
  barato; #1b5462 cuando va como texto sobre fondo claro.
- **Forma:** esquinas rectas en la página. Las piezas del producto (`data-ui`) llevan sus propios bordes.
- **Seis tamaños de letra:** 15, 16, 17–19, 20–26, 32–52 y las cifras grandes.
- **Movimiento:**
  - el titular sube línea a línea;
  - las cifras ruedan;
  - la foto se abre;
  - la fila de piezas se desplaza;
  - respuesta al pulsar.

  Todo se desactiva con «reducir movimiento».
- **Comportamiento:** el combustible elegido se recuerda y va en la dirección (`?c=g95`). Funciona sin
  JavaScript, mostrando el diésel.

## Fotos y vídeo

Proceden de Wikimedia Commons, con licencias CC BY-SA y CC0. Los créditos aparecen en el pie de todas las
páginas y están en `generador/estatico/fotos/credits.json`. Se buscaron con `assets.mjs` del Taste Skill.

## Herramientas

Están instaladas en local y no se suben al repositorio.

- **Taste Skill** (`Leonxlnx/taste-skill`): dirección de arte, inspector a 1440, 768 y 390 px, y crítica
  por rondas. La portada y las páginas interiores pasan con 0 fallos.
- **Web Design Guidelines** (Vercel): accesibilidad, foco, formularios, movimiento.
- **Awesome Design** (`VoltAgent/awesome-design-md`): referencias de Uber y NerdWallet.
- **Playwright CLI:** pruebas de uso (poste, combustible, litros, búsqueda, filtros, menú).
- **Image-to-Code:** no se aplicó, porque necesita una herramienta para generar imágenes.

## Avisos del inspector que se aceptan

- `side-scroll` y `empty-middle` en móvil y tableta: la fila de piezas es un carrusel con imán y con la
  pieza siguiente asomando a propósito.
- `card-rows`: la misma tarjeta repetida en «Cómo funciona» es la idea de esa sección.
- `ragged-row` en municipio y noticia: lista o artículo largo junto a un resumen corto.
- `app-title-size` y `kpi-size` en las páginas interiores: el título y el precio grandes son la identidad
  de la web.
