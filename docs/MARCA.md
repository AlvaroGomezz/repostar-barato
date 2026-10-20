# Marca: logo e iconos

**El logo:** una gota de combustible negra con una flecha hacia abajo recortada: el combustible que baja de
precio. Va sobre el amarillo de la web. Se dibuja con código (`generador/marca.py`), así que todos los
tamaños salen idénticos. Para regenerarlos:

```
python -m generador.marca
```

## Colores

| Uso | Color |
| --- | --- |
| Amarillo de la marca (fondo del icono, cabecera) | `#ffd43b` |
| Tinta (la gota, los textos) | `#141414` |
| Verde del ahorro y de «Cómo llegar» | `#0a7c4f` |
| Fondo claro de la web | `#f3f2ef` |

Tipografía: **Albert Sans** (Google Fonts, licencia libre), en negrita para el nombre.

## Ficheros (`generador/estatico/marca/`)

| Fichero | Para qué |
| --- | --- |
| `app-ios-1024.png` | Icono de la app en el **App Store** (1024 × 1024, sin transparencia; Apple redondea las esquinas) |
| `app-play-512.png` | Icono de la ficha de **Google Play** (512 × 512) |
| `android-adaptable-primer-plano-432.png` y `android-adaptable-fondo-432.png` | **Icono adaptable de Android**: la gota (transparente, dentro de la zona segura) y el fondo amarillo |
| `icono-192.png`, `icono-512.png`, `icono-maskable-512.png` | La web instalada en el móvil (manifiesto `manifest.webmanifest`) |
| `apple-touch-icon.png` | Icono al añadir la web a la pantalla de inicio del iPhone |
| `favicon-48.png` y `../icono.svg` | Favicon del navegador |
| `logo.svg`, `logo-fondo-blanco.svg` | Logo horizontal (icono y nombre) para documentos, prensa o la ficha de la tienda |
| `icono-oscuro.svg` | Variante sobre negro: la gota en amarillo |

## Reglas sencillas

- La gota siempre en tinta sobre amarillo, o en amarillo sobre tinta. Nunca en verde ni sobre fotos.
- Deja alrededor del icono un margen libre de al menos un cuarto de su tamaño.
- No la deformes, no la gires y no le añadas sombras.
