# Diseño y experiencia de uso

## Para quién y para qué

Quien entra suele llegar desde Google («gasolinera más barata en …»), con el móvil y a punto de repostar.
Cada pantalla responde primero a una pregunta:

- **Municipio:** ¿dónde lleno más barato *mi* combustible aquí, y cómo llego?
- **Provincia:** ¿qué municipio y qué gasolinera tienen el precio más bajo?
- **Portada:** ¿cuánto cuesta hoy y dónde está lo más barato cerca de mí?

## Decisiones

- **Respuesta primero:** el precio más barato, grande y en azul, con su gasolinera y un botón «Cómo llegar».
- **Selector de combustible** (Diésel, 95, 98, GLP) en todas las páginas. Se recuerda entre visitas y queda
  en la dirección (`?c=g95`), así que se puede compartir y funciona sin JavaScript.
- **Ahorro calculado:** «Llenar 50 l aquí cuesta X €; en la más cara, Y €: ahorras Z €». Los litros
  se pueden cambiar (30–70 l).
- **Escalera de precios:** una marca por gasolinera entre el precio mínimo y el máximo. Dice de un
  vistazo si en ese municipio importa dónde repostar.
- **Listas en vez de tablas anchas:** cada gasolinera en dos líneas, con el precio a la derecha, la diferencia
  con la más barata y un botón «Ir». Se puede ordenar por cercanía (con la ubicación del móvil) y filtrar
  las abiertas 24 horas.
- **Estilo «achromatic ledger»:** interfaz en tinta y un solo tono (#1d5fbf) para el dato principal. Fondo gris
  azulado (#f2f4f7), tipografía Geist con cifras tabulares, bordes de 1 px y sin sombras en reposo.
- **Móvil:** menú plegado, buscador en la barra y zonas táctiles de 44 px como mínimo.

## Herramientas usadas

Instaladas en local (no están en el repositorio):

- **Taste Skill** (`Leonxlnx/taste-skill`): guía de pantallas prácticas (`app-screens.md`), estilo elegido
  con `draw.mjs --app` e inspector (`inspect.mjs --app`) a 1440, 768 y 390 px. Resultado: 0 fallos en las
  páginas principales.
- **Web Design Guidelines** (Vercel): auditoría de accesibilidad, foco, formularios, movimiento y textos.
- **Awesome Design** (`VoltAgent/awesome-design-md`): referencias de Uber, NerdWallet y Revolut para la
  navegación en el móvil, las filas de comparación y las zonas táctiles.
- **Playwright CLI** (`@playwright/cli`): pruebas de uso reales (cambiar combustible, litros, búsqueda,
  filtros, menú móvil).
- **Image-to-Code** (`Leonxlnx/imagegen-skills`): no se aplicó, porque necesita una herramienta que
  genere imágenes y esta sesión no tiene ninguna.

Para reinstalarlas:

```
npx skills add https://github.com/Leonxlnx/taste-skill
npx skills add https://github.com/vercel-labs/agent-skills --skill web-design-guidelines
npm install -g @playwright/cli@latest
```

## Avisos del inspector que se aceptan

`ragged-row` en municipio y provincia: la lista de gasolineras es larga por naturaleza y va junto a un
resumen más corto. Se acepta porque la lista es el contenido principal.
