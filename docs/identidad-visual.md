# Identidad visual: qué hay y dónde se cambia

**Estado: dirección cerrada; falta aplicarla al código.** Este documento lista todas las piezas visuales para cambiarlas en un solo pase.

## Dirección acordada

- **Imágenes de cada edición:** una civilización grecorromana con tecnología imposiblemente avanzada (mármol, bronce, túnicas y armaduras), con rostros ocultos y sin texto. Cada imagen tiene tensión: algo está mal o en juego.
  - La tecnología se ve como luz, no como pantallas: hologramas que flotan, geometría luminosa, grecas del piso y los muros por las que corre luz como datos, naves monolíticas de piedra al fondo y autómatas de mármol con vetas de oro tipo kintsugi.
  - Sin cyberpunk, sin neón y sin pantallas ni tabletas con hologramas.
- **Símbolos:** symbolon y tessera hospitalis (tokens de autenticación), Jano (accesos y umbrales), Hermes (agentes de IA y delegación), Argos Panoptes (monitoreo), máscaras y sombras (deepfakes).
- **Paleta de las imágenes ("Oro y zafiro"):** el mundo físico se queda en mármol, bronce envejecido y ámbar; solo la tecnología que emite luz brilla en oro eléctrico (casi blanco en el núcleo) y zafiro o azul eléctrico.

  | Rol | Color | HEX |
  |---|---|---|
  | Base (sombras) | Obsidiana | `#0E0B08` |
  | Base (metal) | Bronce antiguo | `#7A4E26` |
  | Base (luz ambiente) | Ámbar | `#C98A3A` |
  | Base (arquitectura) | Mármol | `#E9E2D4` |
  | Acento principal | Oro eléctrico | `#FFD23F` |
  | Centro de la luz | Núcleo incandescente | `#FFF6C8` |
  | Acento secundario | Zafiro | `#1E5BFF` |
  | Chispas y bordes | Azul eléctrico | `#4FC3FF` |

  Los HEX sirven para el sitio y para revisar las imágenes; no se le pasan al modelo, que recibe la descripción en palabras.
- **Generación:** Gemini 3 Pro Image, 21:9 nativo a 2K (3168×1344). Costo medido en pruebas locales: ~US$0.141 por imagen, incluido el pensamiento del modelo. Con una imagen de referencia, el prompt debe decir que solo tome el color, la luz y los materiales; si no, copia la composición.
- **Sitio (maqueta "Editorial"):** imagen de la edición a pantalla completa con el titular encima, notas numeradas y barra lateral con el análisis semanal. Fondo casi negro (`#050608`) con azul eléctrico y zafiro como acentos; el oro solo marca la señal alta. Modo claro y oscuro con un botón de sol/luna (oscuro por defecto si el sistema no indica otra cosa); el hero se queda oscuro en ambos.
- **Tipografía:** Trajan Sans (Adobe Fonts, con el código de inserción de un web project) para titulares e Inter para el texto.
- **Portada del repositorio:** `docs/img/portada.jpg`, un observatorio con una esfera armilar que escanea la ciudad; una de las huellas del haz se fractura.

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

- [ ] Aplicar la paleta y la tipografía de la maqueta "Editorial" a `tailwind.config.js` y `app.css`.
- [ ] Pasar el prompt de imagen final a `config/hero_style.md` y decidir si se agrega `assets/hero-reference.png`.
- [ ] Tabla de mapeo de símbolos según el tema de la nota principal.
- [ ] Logotipo definitivo.
- [ ] Mockup de nota individual.
- [ ] Traducir al español el resto de la interfaz (calendario, búsqueda, categorías, feeds, replay).
- [ ] `og:image` y `og:url` cuando exista el subdominio.
- [ ] Ajustar las categorías heredadas (news, research, social, reddit) a las del radar.
