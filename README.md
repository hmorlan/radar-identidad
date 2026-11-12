<p align="center"><img src="docs/img/portada.jpg" alt="Mosaico romano: Ulises atado al mástil frente a tres sirenas que sostienen sensores; su canto viaja como trazos de circuito en oro" width="100%"></p>

# Radar de Identidad

> **Estado: próximamente.** El sitio está en construcción y todavía no publica ediciones.

Radar de Identidad es un radar de inteligencia **en español** sobre identidad digital y sobre las noticias de IA y ciberseguridad que cambian **cómo decidimos en quién o en qué confiar**.

Está pensado para CISOs, arquitectos de identidad, equipos de fraude y riesgo, y quienes construyen fintech y banca en Latinoamérica y España.

## Qué cubre

La regla de entrada es una sola: *¿la noticia cambia cómo decidimos en quién o en qué confiar?*

- **Sí entra:** passkeys, OAuth y OpenID; account takeover y fatiga de MFA; deepfakes que pasan la verificación de identidad; agentes de IA que actúan con nuestros accesos; regulación de identidad.
- **No entra:** malware genérico, vulnerabilidades sin ángulo de identidad o noticias de IA que no tocan la confianza.

Cada nota tiene el mismo formato:

1. **Qué pasó:** el hecho, con enlace a la fuente original.
2. **Por qué importa:** la implicación práctica.
3. **La pregunta de fondo:** solo cuando la nota lo amerita.
4. **Nivel de señal:** baja, media o alta.

## Cadencia (planeada)

- **Diario:** recolección y etiquetado de fuentes, sin publicar.
- **Lunes, miércoles y viernes:** ediciones publicadas.
- **Domingo:** "La semana en identidad", análisis de fondo.

## Identidad visual

Dirección **"mármol, tinta y oro"**: una revista de criterio, no un dashboard. Papel cálido, serif legible y un solo detalle dorado por pantalla.

- **Entre semana, mosaico romano:** cada edición abre con un friso en mosaico de teselas marfil, arena y grafito, con un elemento de tecnología contemporánea (chips, circuitos, lentes, sensores) y oro solo como acento. La escena sale de un banco de motivos grecorromanos (Jano, Cerbero, Hermes, Ulises y las sirenas, Eco, Argos…) con memoria para no repetirse.
- **Domingo, grabado al buril:** "La semana en identidad" usa grabado sepia sobre papel, más sobrio y sin oro.
- **Modo claro y oscuro:** claro por defecto o según el sistema. La versión oscura de cada imagen se deriva del original protegiendo el oro, no se le pide al modelo.
- **Tipografía:** Cormorant Garamond en titulares, Newsreader en el texto, Inter en la interfaz y Marcellus SC solo en el nombre.

Las imágenes se generan con Gemini 3 Pro Image (dos candidatas por edición, con control automático de calidad). La especificación completa está en [`docs/identidad-visual.md`](docs/identidad-visual.md).

## Cómo funciona

Un pipeline en Python recolecta fuentes públicas (RSS, arXiv, Mastodon y Bluesky), las filtra y redacta las notas con modelos de Claude, y genera un sitio estático en Svelte. El motor corre en GitHub Actions y el sitio se publica en Cloudflare Pages.

| Qué | Dónde |
|---|---|
| Fuentes de noticias | `config/rss_feeds.txt` |
| Fuentes de investigación | `config/research_feeds.txt` |
| Reguladores sin RSS | `config/regulators.txt` |
| Cuentas de Mastodon y Bluesky | `config/mastodon_accounts.txt`, `config/bluesky_accounts.txt` |
| Prompts editoriales | `config/prompts.yaml` |
| Modelos y API keys (local, no se sube) | `config/providers.yaml` (copia de `providers.yaml.example`) |
| Prompts de imagen y banco de motivos | `config/hero_prompt.yaml`, `config/hero_motivos.yaml` |
| Identidad visual del sitio | [`docs/identidad-visual.md`](docs/identidad-visual.md) |

## Correrlo en local

**Solo el sitio** (no necesita API keys):

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

Sin ediciones publicadas, la portada muestra la página de "Próximamente".

**El pipeline completo** (necesita una API key de Anthropic):

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp config/providers.yaml.example config/providers.yaml   # y agrega tus keys
python3 run_pipeline.py --config-dir ./config --data-dir ./data --web-dir ./web
```

Las API keys nunca se suben al repo: `config/providers.yaml` está en `.gitignore`, y en GitHub Actions van como *Secrets* cifrados.

## Créditos y licencia

Proyecto personal de Hiram Morlán, construido exclusivamente con fuentes públicas.

El código parte de [flyryan/ai-news-aggregator](https://github.com/flyryan/ai-news-aggregator) y se distribuye bajo la misma licencia [Apache 2.0](LICENSE). Los cambios respecto al original están descritos en [NOTICE](NOTICE). La documentación técnica del proyecto original está en [`docs/upstream/`](docs/upstream/).
