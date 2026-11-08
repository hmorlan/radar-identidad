# CLAUDE.md

Instrucciones para Claude (y cualquier asistente de código) al trabajar en este repositorio.

## Qué es este proyecto

**Radar de Identidad** es un radar de inteligencia **en español** sobre identidad digital y sobre las noticias de IA y ciberseguridad que cambian **cómo decidimos en quién o en qué confiar**. Es un proyecto personal de Hiram Morlan, construido solo con fuentes públicas.

El código parte de [flyryan/ai-news-aggregator](https://github.com/flyryan/ai-news-aggregator) (Apache 2.0), pero es un **proyecto aparte**, con otro propósito, otra marca y otras fuentes. Los cambios respecto al original están en `NOTICE` y la documentación técnica original se conserva en `docs/upstream/`.

## Reglas de trabajo

- **Idioma.** Todo lo visible (sitio, documentación, prompts editoriales) va en español. Se conservan en inglés los términos de la industria: passkey, token, OAuth, OpenID Connect, MFA, SSO, CIAM, IAM, phishing, deepfake, ransomware, account takeover, KYC. Los prompts de imagen van en inglés.
- **Fuentes públicas solamente.** Nunca uses, pidas ni supongas información interna, clientes o sistemas del empleador de Hiram.
- **Verifica antes de afirmar.** No inventes cifras, fechas ni citas. Si algo no está confirmado, dilo.
- **Revisa el código real** antes de proponer cambios; si una sugerencia contradice el código, señálalo con archivo y línea.
- **Costos.** Claude: ~US$80/mes (créditos API del plan Max). Imágenes: < US$10/mes. Antes de cualquier cambio que suba el costo, estima el impacto y pide confirmación.
- **Acciones con efecto real.** No hagas push a `main`, despliegues ni corridas del pipeline (incluidas reanudaciones y backfills) sin confirmación explícita de Hiram. Correr tests no requiere permiso.
- **Commits.** Autor `hmorlan <hmorlan@users.noreply.github.com>` para no exponer correos personales en un repo público.

## Criterio editorial

- **Regla de entrada:** ¿la noticia cambia cómo decidimos en quién o en qué confiar? Si no, no entra.
- **Sí entran:** ransomware que empezó por credenciales robadas o fatiga de MFA; agentes de IA que actúan con nuestros accesos; deepfakes que pasan la verificación de identidad; estándares (passkeys, OAuth, OpenID); regulación de identidad.
- **No entran:** malware genérico, vulnerabilidades sin ángulo de identidad, noticias de IA sin relación con la confianza, y notas de mercado (rondas de inversión, adquisiciones, lanzamientos de producto) salvo que cambien cómo decidimos en quién o en qué confiar.
- **Formato de cada nota:** Qué pasó (2–3 frases, con enlace a la fuente) · Por qué importa · La pregunta de fondo (solo cuando aplica) · Nivel de señal (baja, media o alta).
- **Agnóstico de proveedores.** No se usan blogs ni comunicados de empresas del sector como fuente. Una empresa (incluidos competidores o el empleador de Hiram) solo aparece cuando la cubre una fuente independiente: prensa, organismos de estándares (FIDO, OpenID, IETF, NIST) o reguladores. Tono factual, sin comparar productos ni recomendar proveedores. Las afirmaciones de una empresa se atribuyen ("según la empresa").
- **Análisis de autor.** Los blogs personales de expertos independientes (p. ej. Cybersecurity Compass, Spherical Cow, self-issued.info) se tratan como opinión y se citan por nombre del autor, no como noticia. No se usan blogs ni cuentas de autores que trabajan en empresas de identidad, fraude, verificación o protección contra bots.

## Cadencia (planeada)

- **Diario:** recolección y etiquetado, sin publicar.
- **Lunes, miércoles y viernes:** ediciones publicadas.
- **Domingo:** "La semana en identidad", análisis de fondo y guion del video semanal.

Hoy el workflow `.github/workflows/daily-pipeline.yml` **no tiene horario**: solo se ejecuta a mano (`workflow_dispatch`).

## Modelos

| Rol | Modelo |
|---|---|
| Triage diario | Claude Haiku 5.5 |
| Redacción | Claude Opus 5.5 con pensamiento adaptativo |
| Verificación y edición | Segunda pasada de Claude Opus 5.5 |
| Imágenes | Gemini 3 Pro Image, `gemini-3-pro-image-preview` en modo `native` (API de Google; probado el 2026-11-05). `gemini-3-pro-image` era el alias del proxy del proyecto original y no aplica |

Usar Batch API donde no se necesite respuesta inmediata. **No usar Fable en el pipeline** (costo).

## Comandos

### Sitio (Svelte)

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 (sirve ../web/data)
npm run build      # genera el sitio estático en ../web
npm run check      # verificación de tipos
npm run test:titles
```

Sin ediciones en `web/data/index.json`, la portada muestra "Próximamente".

### Pipeline (Python)

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp config/providers.yaml.example config/providers.yaml   # agregar API keys (no se sube)
python3 run_pipeline.py --config-dir ./config --data-dir ./data --web-dir ./web

TARGET_DATE="2026-11-04" python3 run_pipeline.py ...     # fecha específica
python3 run_pipeline.py --resume ...                       # reanudar tras una falla
python3 run_pipeline.py --resume-from 4.7 ...              # regenerar solo la imagen
```

**Semántica de fechas:** `TARGET_DATE` es la fecha de la edición; cubre las noticias del día anterior (zona horaria de la variable `TZ`, `America/Mexico_City` en el workflow).

### Tests y verificación

```bash
python3 -m unittest discover -s tests -p '*_test.py'   # tests de Python (sin red)
python3 scripts/check_feeds.py            # estado de cada fuente, sin costo
python3 scripts/check_feeds.py --pending  # incluye candidatas comentadas
python3 scripts/source_health_alert.py --dry-run   # simula la alerta de fuentes caídas
GOOGLE_API_KEY=... python3 scripts/check_image_model.py              # confirma el modelo de imagen, sin costo
GOOGLE_API_KEY=... python3 scripts/check_image_model.py --generate   # una imagen de prueba (~US$0.14)
```

`tests/admin_auth_test.py` necesita además `pip install -r admin_service/requirements.txt`.

**Red en el entorno en la nube de Claude:** npm y pip deben pasar por el proxy, por ejemplo `NO_PROXY= no_proxy= npm ci --noproxy=localhost --proxy "$HTTPS_PROXY" --https-proxy "$HTTPS_PROXY" --cafile /root/.ccr/ca-bundle.crt`.

## Configuración

| Qué | Dónde |
|---|---|
| Fuentes de noticias | `config/rss_feeds.txt` |
| Investigación y estándares | `config/research_feeds.txt` |
| arXiv | `agents/gatherers/research_gatherer.py` (`CATEGORIES`, hoy solo `cs.CR`) |
| Reguladores sin RSS (MX, ES, CO, AR, CL) | `config/regulators.txt` → `agents/gatherers/regulator_sources.py` (página de prensa directa o Google News; vista previa: `python3 -m agents.gatherers.regulator_sources --hours 72`) |
| Mastodon y Bluesky | `config/mastodon_accounts.txt`, `config/bluesky_accounts.txt` |
| X y Reddit | Desactivados (APIs de pago) |
| Prompts editoriales | `config/prompts.yaml` (en español) |
| Modelos, keys y URL base | `config/providers.yaml` (copia de `providers.yaml.example`) |
| Estilo de imágenes | `config/hero_style.md` (las líneas `#` no se envían al modelo) |
| Identidad visual del sitio | `docs/identidad-visual.md` |
| Estado de las fuentes | `docs/fuentes.md` |

Para agregar una fuente: añadirla al `.txt` correspondiente, correr `scripts/check_feeds.py` y documentarla en `docs/fuentes.md`.

**Alerta de fuentes caídas:** `.github/workflows/source-health.yml` corre `check_feeds.py` todos los días a las 07:17 (CDMX), sin costo. Si una fuente falla dos revisiones seguidas (o la página de prensa de un regulador deja de devolver notas), la corrida termina en rojo y GitHub manda correo (con Issues activados, además abre un issue `salud-fuentes` que se cierra solo al recuperarse).

## Arquitectura

### Fases del pipeline (`run_pipeline.py` → `agents/orchestrator.py`)

| Fase | Qué hace |
|---|---|
| 0 | Contexto del ecosistema (fechas de lanzamiento de modelos, para evitar alucinaciones) |
| 1 | Recolección en paralelo: noticias (RSS), investigación (arXiv + blogs), redes (Mastodon, Bluesky) |
| 2 | Análisis por categoría |
| 3 | Temas transversales entre categorías |
| 4 | Resumen ejecutivo |
| 4.5 | Enlaces internos en los resúmenes |
| 4.6 | Detección de lanzamientos de modelos |
| 4.7 | Imagen de la edición (21:9) |
| 5–6 | Ensamblado y JSON para el sitio (`web/data/`) |
| 6.2 | Replay de la corrida (`/replay`) |
| 6.5 | Feeds Atom (`web/data/feeds/`) |
| 7 | Corpus de búsqueda |

Las fases principales guardan checkpoints en `data/checkpoints/{fecha}/`, lo que permite `--resume` y `--resume-from N`.

### Perfiles de análisis

Los perfiles internos se traducen al `effort` del pensamiento adaptativo de Claude: QUICK → high, STANDARD → xhigh, DEEP → max, ULTRATHINK → max. El tope de salida lo fija `LLM_ADAPTIVE_MAX_TOKENS` (incluye pensamiento + respuesta).

### Directorios

| Directorio | Contenido |
|---|---|
| `agents/` | Orquestador, cliente LLM, recolectores (`gatherers/`) y analizadores (`analyzers/`) |
| `generators/` | JSON del sitio, imagen, feeds, búsqueda y replay |
| `frontend/` | Sitio en SvelteKit + Tailwind (salida estática a `web/`) |
| `config/` | Fuentes, prompts, proveedores y estilo de imagen |
| `scripts/` | Utilidades (verificación de fuentes, regenerar imagen, reparaciones) |
| `tests/` | Tests de Python |
| `docs/` | Documentación del proyecto; `docs/upstream/` es la del original |

### Sitio

- `web/_app/` y los HTML compilados no se versionan: los genera `npm run build` (y Cloudflare Pages al desplegar).
- **CSP:** la política de scripts vive solo en el `<meta>` que genera SvelteKit (`frontend/svelte.config.js`, `kit.csp`). No agregues `script-src` ni `default-src` en cabeceras del servidor, porque bloquearía los scripts con hash y dejaría la página en blanco.
- Las URLs de las notas se filtran por esquema (http, https, mailto) en `generators/json_generator.py` y en `frontend/src/lib/services/sanitize.ts`.

## Despliegue (planeado)

GitHub Actions como motor y Cloudflare Pages para el sitio estático en `radar.hirammorlan.com` (subdominio provisional). Durante la beta las ediciones no se guardan en el repo público (`commit_outputs=false`).

## Infraestructura heredada que no aplica

Los directorios `admin_service/`, `deploy/`, `webhook/` y `shadow/`, y los scripts asociados (`trigger_rebuild.sh`, `deploy.sh`, `verified_sync.sh`, Mullvad, Reddit, Twitter), son del servidor del proyecto original y **no se usan aquí**. Siguen en el repo porque parte del pipeline y de los tests importan módulos de ellos (por ejemplo, `agents/jev_relevance.py` usa `shadow/`). Se retirarán con cuidado, corriendo los tests en cada paso.
