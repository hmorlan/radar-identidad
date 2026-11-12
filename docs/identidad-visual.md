# Identidad visual: dirección v3.2 "mármol, tinta y oro"

**Estado: aplicada al sitio y al pipeline de imagen (11 nov 2026).** Reemplaza la dirección anterior "oro y zafiro" (fondo casi negro, azul eléctrico, imágenes cinematográficas), que queda descartada.

Intención: revista de criterio, no dashboard. Moderna y clásica a la vez: lo antiguo roto por la tecnología, contado con oficio editorial. Lo primero que se siente es papel cálido, serif legible y un detalle dorado. Una sola idea por pantalla.

## Paleta

Claro primero; oscuro como variante. El sitio sigue la preferencia del sistema y el botón "Modo" la cambia.

| Rol | Claro | Oscuro |
|---|---|---|
| Papel (fondo) | `#F5F1E8` | Obsidiana `#0E0F12` |
| Piedra (superficies) | `#E4DDCC` | `#2A2B2F` |
| Filete | `#DCD4BF` | `#2A2B2F` |
| Caja (crédito de imagen) | `#EFE9DB` | `#17181D` |
| Tinta (texto) | `#14171C` | Marfil `#ECE6D8` |
| Tinta suave | `#5A5F66` | `#A39D8F` |
| Oro (enlaces, kickers, señal alta) | `#7A5C18` | `#D4AF5A` |
| Oro hover | mismo color, subrayado más grueso | `#E8C87E` |
| Foco de teclado | Lapislázuli `#1F3A5F` | Oro `#D4AF5A` |
| Terracota (correcciones) | `#9C4A2F` | `#C9714F` |

Contrastes AA verificados (oro claro 5.53:1, oro oscuro 9.2:1). Sin azul eléctrico ni cian en la interfaz.

## Tipografía

Autoalojada con `@fontsource` (la CSP del sitio solo permite fuentes propias):

- **Marcellus SC:** solo el nombre "Radar de Identidad", con tracking `.3em`.
- **Cormorant Garamond:** titulares (500, 36–48px; 30px en móvil) y la pregunta de fondo en cursiva.
- **Newsreader:** cuerpo, 18–19px, interlineado 1.65.
- **Inter:** interfaz y metadatos, 11–13px en mayúsculas con tracking.

## Layout y componentes

- Cabecera clara, sin barra negra: nombre centrado, menú centrado bajo un filete, accesos discretos (RSS, Buscar, Modo). El menú es sticky y siempre opaco.
- **Friso** del diario: imagen 21:9 a todo el ancho, 300px (210px en móvil), entre doble filete. Un solo paneo al cargar que termina en el punto focal; sin animación con `prefers-reduced-motion`.
- Crédito tipo museo bajo cada imagen: motivo, técnica, modelo y fecha.
- "En 60 segundos" con rombos dorados.
- Notas en una columna de ~680px, numeral romano en oro en su columna lateral, también en las notas colapsadas. Sin tarjetas ni barra lateral.
- "La pregunta de fondo" enmarcada con filete de 1px en oro.
- Señal con 1–3 puntos; solo la alta va en oro.
- Al pie de la edición: franja humana (foto o video de la semana), caja "Cada domingo", temas, suscripción (Seguir en LinkedIn + RSS).
- Domingo: sello armilar pequeño que gira lento (se detiene con `prefers-reduced-motion`) y grabado dentro de la columna.

## Imagen de cada edición

- **Diario: mosaico romano con circuitos de oro.** Bloque de prompt fijo + 3 ejes variables (escena, composición, estado del mosaico) + 2 imágenes de referencia.
- **Domingo y respaldo: grabado al buril** sepia, sin oro.
- **Banco de motivos con memoria:** 4 registros (mito, vida cotidiana, crónica, emblema). El mismo motivo no se repite en 8 semanas ni se repiten composición o registro en ediciones seguidas.
- **2 candidatas en Batch API** con control automático: oro medido, colores ajenos y revisión visual con Haiku. El oro se mide por encima de la croma mediana de cada imagen (el fondo de arena varía de 0.13 a 0.22); calibrado con las 16 imágenes aprobadas del 11 nov, que miden de 1.6% a 14%. El umbral absoluto de la especificación (0.3) contaba el fondo cálido como oro en unas imágenes y no veía el oro fino en otras. Si ninguna pasa, un mosaico más y después el grabado. Nunca se publica una imagen que no pasó.
- **Nunca sin imagen:** si tampoco pasa el grabado, o Gemini no responde (tope de gasto, caída, cuota), se usa una **imagen de archivo** ya aprobada (`config/hero_archivo.yaml`, 4 mosaicos y 2 grabados): la técnica del día, sin repetir un motivo de las últimas 8 semanas. El crédito dice "Imagen de archivo" y la corrida lo anota. Además, el workflow no publica una edición sin imagen (`scripts/check_edition_image.py`): si falta, no sube a R2 ni a Pages y la corrida queda en rojo.
- **Costo real:** se cuenta toda imagen generada, incluida la segunda candidata del batch aunque gane la primera (~US$0.14 por edición cuando pasa la primera).
- **Postproceso local, sin costo:** tono del mosaico emparejado al marfil de referencia, papel del grabado blanqueado, variante oscura derivada protegiendo el oro (nunca se le pide al modelo).

## Dónde vive cada pieza

| Pieza | Archivo |
|---|---|
| Tokens de color | `frontend/src/app.css` (variables `--papel`, `--tinta`, `--oro`…) y `frontend/tailwind.config.js` (los nombres anteriores quedan como alias) |
| Fuentes | `frontend/src/routes/+layout.svelte` |
| Modo claro/oscuro | `frontend/src/lib/stores/themeStore.ts`, `ThemeToggle.svelte` |
| Cabecera, menú y pie | `frontend/src/lib/components/layout/` |
| Edición | `frontend/src/lib/components/edition/` (`EditionView`, `HeroFriso`, `NotaEdicion`, `SelloArmilar`) |
| LinkedIn y franja humana | `frontend/src/lib/config/site.ts` |
| Archivo por semanas | `frontend/src/routes/archive/+page.svelte` |
| Prompts de imagen y umbrales de control | `config/hero_prompt.yaml` |
| Banco de motivos | `config/hero_motivos.yaml` |
| Referencias | `assets/hero-ref/ref-troya.jpg`, `assets/hero-ref/ref-cerbero.jpg` |
| Imágenes de archivo (respaldo) | `config/hero_archivo.yaml`, `assets/hero-archivo/` |
| Pipeline de imagen | `generators/hero_v32.py`, `generators/hero_postprocess.py`, `generators/image_client.py` (batch) |
| Memoria de imágenes | `data/hero_historial.json` (viaja en R2, no se publica) |
| Portada del repositorio | `docs/img/portada.jpg` (Ulises y las sirenas, prueba v3.2) |

## Pendientes

- [ ] Foto o video para la franja humana.
- [ ] Plantilla completa del domingo (firma, capitular, cifra, ilustración interior).
- [ ] Logotipo y favicon; `og:image`.
- [ ] Traducir el resto de la interfaz heredada (búsqueda, feeds, replay).
