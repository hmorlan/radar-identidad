# Identidad visual: qué hay y dónde se cambia

**Estado: aplicado al sitio (6 nov 2026).** La fuente de verdad es el design system "Radar de Identidad" (artifact en claude.ai); este documento dice dónde vive cada pieza en el código.

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
- **Tipografía:** Marcellus SC para titulares (mayúsculas pequeñas tipo inscripción romana) e Inter para el texto, ambas de Google Fonts y autoalojadas con `@fontsource` (la CSP del sitio solo permite fuentes propias). Se descartó Trajan Sans de Adobe.
- **Portada del repositorio:** `docs/img/portada.jpg`, un observatorio con una esfera armilar que escanea la ciudad; una de las huellas del haz se fractura.

## Inventario de piezas

| Pieza | Archivo | Estado |
|---|---|---|
| Tokens de color (claro/oscuro) | `frontend/src/app.css` (variables `--ground`, `--surface`, `--line`, `--ink*`, `--electric-blue`, `--sapphire`, `--signal-gold`, `--core-glow`) y `frontend/tailwind.config.js` | Aplicados, idénticos a `tokens.json`. Los `radar-*` son alias para componentes heredados |
| Estilos de texto | `frontend/src/app.css` (`t-display-hero`, `t-display-note`, `t-question`, `t-wordmark`, `t-body`, `t-meta`, `t-kicker`, `t-label`, `t-numeral`) | Aplicados |
| Tipografía | `@fontsource/marcellus-sc`, `@fontsource/inter`, importadas en `frontend/src/routes/+layout.svelte` | Aplicada |
| Modo claro/oscuro | `frontend/src/lib/stores/themeStore.ts`, `ThemeToggle.svelte`, `app.html` (`class="dark"`) | Oscuro por defecto salvo que el sistema pida claro; botón redondo sol/luna |
| Barra superior y pie | `Header.svelte`, `Navigation.svelte`, `Footer.svelte` | Nombre en `wordmark`, sin logotipo (aún no existe) |
| Edición "Editorial" | `frontend/src/lib/components/edition/EditionView.svelte` | Hero a pantalla completa, notas numeradas, barra lateral |
| Portada "Próximamente" | `ComingSoon.svelte` | Con tokens nuevos |
| Favicon | `frontend/static/favicon.svg` y `favicon.png` | Provisional (radar); cambiar cuando exista logotipo |
| Estilo de las imágenes | `config/hero_style.md` | Prompt base vigente del design system |
| Imagen de referencia | `assets/hero-reference.jpg` | Autómata con huella fracturada; solo guía de color, luz y materiales |
| Símbolos por tema | `generators/hero_generator.py` (`VISUAL_MAPPINGS`) | Versión 1 de la tabla |
| Metadatos para redes | `frontend/src/app.html` | Falta `og:image` y `og:url` hasta publicar |

## Pendientes

- [ ] Logotipo definitivo y favicon.
- [ ] Revisar la tabla de símbolos con imágenes reales del pipeline.
- [ ] Traducir al español el resto de la interfaz heredada (búsqueda, feeds, replay).
- [ ] `og:image` y `og:url` cuando exista el subdominio.
- [ ] Vista de "La semana en identidad" (domingo).
