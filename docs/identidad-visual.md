# Identidad visual: qué hay y dónde se cambia

**Estado: provisional.** La paleta y el estilo se están definiendo; este documento lista todas las piezas visuales para cambiarlas en un solo pase cuando cerremos el mockup.

## Dirección acordada

- **Imágenes de cada edición:** una civilización grecorromana con tecnología imposiblemente avanzada (mármol, bronce, túnicas y armaduras), sin pantallas ni cyberpunk, con rostros ocultos y sin texto. Cada imagen tiene tensión: algo está mal o en juego.
- **Símbolos:** symbolon y tessera hospitalis (tokens de autenticación), Jano (accesos y umbrales), Hermes (agentes de IA y delegación), Argos Panoptes (monitoreo), máscaras y sombras (deepfakes).
- **Paleta:** en revisión. La idea es salir del "todo dorado" y combinar bronce y ámbar con azules.
- **Sitio:** la propuesta es una banda superior oscura para la imagen de la edición y un cuerpo de lectura claro (pendiente de mockup).

## Inventario de piezas

| Pieza | Archivo | Estado |
|---|---|---|
| Logotipo | `frontend/static/assets/logo.svg` | Provisional: un radar (círculos azules con un barrido en bronce) |
| Favicon | `frontend/static/favicon.svg` y `favicon.png` | Copia del logotipo provisional |
| Paleta del sitio | `frontend/tailwind.config.js` (tokens `radar-*`) y `frontend/src/app.css` | Provisional: azul `#2F5F9E`, azul oscuro `#1F4373`, bronce `#B8925A`, fondo oscuro `#0F1A2A`, grises azulados |
| Tipografía | `frontend/tailwind.config.js` (`fontFamily`) | Fuentes del sistema, sin definir |
| Encabezado | `frontend/src/lib/components/layout/Header.svelte` | Nombre y lema en español |
| Pie de página | `frontend/src/lib/components/layout/Footer.svelte` | Nombre, créditos y aviso de IA |
| Portada "Próximamente" | `frontend/src/lib/components/common/ComingSoon.svelte` | Se muestra mientras `web/data/index.json` no tenga ediciones |
| Imagen de la edición (marco) | `frontend/src/lib/components/layout/HeroSection.svelte` | Formato 21:9 heredado |
| Página "Acerca de" | `frontend/src/routes/about/+page.svelte` | En español |
| Metadatos para redes (Open Graph) | `frontend/src/app.html` | Falta `og:url` y `og:image` hasta definir el subdominio |
| Estilo de las imágenes | `config/hero_style.md` | Provisional; lo que no empieza con `#` se envía al modelo |
| Imagen de referencia (opcional) | `assets/hero-reference.png` | No existe; si se agrega, se envía al modelo como guía de estilo |
| Configuración de imagen | `config/providers.yaml` (sección `image`) | Gemini 3 Pro Image, 2K, 21:9 |

## Pendientes

- [ ] Paleta final (bronce + azules) y tipografía.
- [ ] Logotipo definitivo.
- [ ] Mockup de portada de edición y de nota individual.
- [ ] Traducir al español el resto de la interfaz (calendario, búsqueda, categorías, feeds, replay).
- [ ] `og:image` y `og:url` cuando exista el subdominio.
- [ ] Ajustar las categorías heredadas (news, research, social, reddit) a las del radar.
