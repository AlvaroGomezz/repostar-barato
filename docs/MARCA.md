# Marca GASVIA

**GASVIA** = gas + vía. El isotipo es una «V» amarilla y una barra carbón que sugieren una carretera.

El kit original está en `docs/marca/kit-original/` (con su guía en PDF). Los ficheros que usa la web y las
apps se generan a partir de los mismos trazos con `generador/marca.py`:

```
python -m generador.marca
```

Ese paso corrige tres cosas del kit:

- Los iconos de app venían en lienzos no cuadrados (2048 × 1117) y el favicon salía aplastado (256 × 140).
- «GASVIA» iba como texto en DejaVu Sans, una fuente que no va incluida, así que cada ordenador lo mostraba
  distinto. Ahora va convertido a trazos con esa misma fuente y espaciado.
- El logo horizontal sobre fondo oscuro tenía el contenido descentrado.

## Colores

| Uso | Color |
| --- | --- |
| Amarillo GASVIA | `#FFCF32` |
| Carbón | `#17191B` |
| Blanco | `#FFFFFF` |
| Verde de la web (ahorro, «Cómo llegar») | `#0a7c4f` |

## Qué versión usar según el fondo

| Fondo | V | Barra | Texto |
| --- | --- | --- | --- |
| Claro o blanco | amarillo | carbón | carbón |
| Amarillo (cabecera de la web, icono de app) | blanco | carbón | carbón |
| Oscuro | amarillo | blanco | blanco |

## Ficheros (`generador/estatico/marca/`)

| Fichero | Para qué |
| --- | --- |
| `app-ios-1024.png` | Icono del **App Store** (1024 × 1024, opaco; Apple redondea las esquinas) |
| `app-play-512.png` | Icono de **Google Play** (512 × 512) |
| `android-adaptable-primer-plano-432.png`, `android-adaptable-fondo-432.png` | **Icono adaptable de Android** (isotipo en la zona segura y fondo amarillo) |
| `icono-192.png`, `icono-512.png`, `icono-maskable-512.png` | Web instalable en el móvil (`manifest.webmanifest`) |
| `apple-touch-icon.png` | Pantalla de inicio del iPhone |
| `favicon.ico`, `favicon-48.png`, `../icono.svg` | Favicon (versión oscura: se distingue mejor en pequeño) |
| `logo.svg`, `logo.png` | Logo horizontal sobre fondo claro |
| `logo-sobre-amarillo.svg` | Logo horizontal sobre amarillo |
| `logo-sobre-oscuro.svg`, `logo-sobre-oscuro.png`, `logo-fondo-oscuro.svg` | Logo horizontal sobre fondo oscuro |
| `isotipo.svg`, `isotipo-negro.svg`, `isotipo-blanco.svg` | Solo el símbolo |
| `icono-app.svg`, `icono-app-oscuro.svg` | Iconos de app en vectorial |

Antes de registrar la marca conviene revisar la tipografía y la geometría con un diseñador, como indica la
propia guía del kit.
