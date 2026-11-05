# Fuentes del radar

## Estado actual (verificación real, 2026-11-04)

Verificado con `scripts/check_feeds.py`: cada fuente respondió 200 y publicó en los últimos 60 días. Esta tabla manda sobre el informe inicial de abajo, que se hizo sin acceso directo a los feeds y tenía errores (por ejemplo, decía que FIDO Alliance no tiene RSS y que INCIBE-CERT funcionaba).

| Grupo | Fuentes activas | Notas/día aprox. |
|---|---|---|
| Prensa de seguridad | The Record, Krebs on Security, Dark Reading, SecurityWeek, BleepingComputer | ~24 |
| Identidad | Biometric Update, FIDO Alliance | ~10 |
| Español (LATAM y España) | WeLiveSecurity ES, Ciberseguridad LATAM, DPL News, Expansión Tecnología, iupana, Una al Día | ~20 |
| Estándares y gobierno | NIST Cybersecurity Insights, NIST CSRC (borradores), IETF OAuth WG, IETF WIMSE WG, OpenID Foundation, W3C, UK NCSC | ~1.5 |
| Redes | Brian Krebs (Mastodon) | ~1 |
| Análisis de autor | Juan Pablo Castro (Cybersecurity Compass), Heather Flanagan (Spherical Cow), Mike Jones (self-issued.info) | ~0.3 |
| Investigación | arXiv cs.CR | ~35 |

**Total: 24 feeds + arXiv cs.CR, ~90 entradas/día antes del filtro de relevancia.**

**Política agnóstica (2026-11-04):** no se usan blogs de proveedores (Okta, Auth0, Ping, Jumio y similares). Las empresas solo entran a través de fuentes independientes.

**Descartadas:** El Financiero (100/día sin notas de identidad), CISA y El Economista (403), INCIBE-CERT (404), feed antiguo de ESET (dominio muerto), Microsoft Entra (inactivo desde hace más de un año), OWASP (inactivo desde junio).

## Reguladores sin RSS (recolector propio, 2026-11-04)

`config/regulators.txt` lista 18 reguladores de México, España, Colombia, Argentina y Chile. `agents/gatherers/regulator_sources.py` los recolecta por dos vías y les aplica el mismo filtro de palabras clave (identidad, suplantación, fraude, autenticación, biometría, ciberseguridad, datos personales, IA):

- **Página de prensa directa** (más fresca y confiable): CNBV, CONDUSEF, BCRA y AAIP.
- **Google News** (búsqueda `site:` y resolución del enlace original del regulador): el resto.

Una caché (`data/regulators_seen.json`) evita repetir páginas que Google vuelve a indexar.

**Rendimiento medido (últimos 14 días):** 8 notas relevantes, sobre todo alertas de suplantación de la CONDUSEF, sanciones de la AAIP, la guía de la AEPD sobre asistentes y agentes de IA, su análisis de datos biométricos y el trabajo del Banco de España en criptografía poscuántica.

**Limitación:** Google News casi no tiene notas recientes de CNMV, CCN-CERT, INCIBE, SIC, ColCERT, CMF, ANCI, Banco Central de Chile y CSIRT. Si alguno resulta clave, se agrega su página de prensa directa cuando sea legible (CNMV, CCN-CERT y ANCI bloquean a los lectores automáticos).

---

## Informe inicial (sin acceso directo a los feeds; conservado como referencia)

# Radar de Identidad: informe de verificación de fuentes

**Fecha de verificación:** 2026-11-04
**Regla de entrada:** ¿la noticia cambia cómo decidimos en quién o en qué confiar?

## Cómo se verificó (y sus límites)

En este entorno, la shell no tiene salida a internet (el proxy responde 403 a CONNECT). WebFetch solo abre URLs que aparecen en un resultado de búsqueda, así que **la mayoría de las URLs de feed no se pudieron abrir directamente**, aunque fueran correctas. Por eso hay tres niveles de evidencia:

| Código | Significado |
|---|---|
| **D** | Fetch directo del feed: XML válido, fechas y títulos leídos. |
| **F** | Página de estado de feeder.co (un lector de RSS que consulta el feed cada 1 a 120 min). Muestra la URL nativa, el estado "Working" y los ítems recientes con su antigüedad. Es evidencia fuerte, pero indirecta. |
| **T** | Directorio threatfilter.dev con estado "ok" o "not modified" al 2026-10-30. Es evidencia indirecta y más débil. |

En los archivos `.txt` solo se activaron feeds con D, F o T reciente. Todo lo demás quedó comentado como `# PENDIENTE`.

La relevancia se estimó con los títulos recientes que pude ver, entre 5 y 20 según la fuente:
- **alta:** más del 50% pasa la regla de entrada.
- **media:** entre 15% y 50%.
- **baja:** menos de 15%.

---

## 1. Organismos de estándares y gobierno

| Fuente | Feed URL | Verif. | Ítem más reciente | Vol./sem | Relevancia | Recomendación | Motivo |
|---|---|---|---|---|---|---|---|
| NIST Cybersecurity Insights | `https://www.nist.gov/blogs/cybersecurity-insights/rss.xml` | Sí (F) | hace ~8 días ("Design Tenets for Agent Identity Management Systems") | ~1 | media-alta | **incluir** | 2 de los últimos 5 posts son sobre identidad de agentes. |
| NIST CSRC – borradores para comentario | `https://csrc.nist.gov/CSRC/media/feeds/pubs/drafts-open-for-comment.xml` | Sí (F) | hace ~14 días (SP 800-221 Rev.1) | 1–2 | baja (picos críticos) | **incluir con filtro** | Hoy, 0 de 6 son de identidad, pero aquí saldría una revisión de SP 800-63. Bajo volumen. |
| NIST News (general) | `https://www.nist.gov/news-events/news/rss.xml` | Sí (F) | hace ~2 días | n/d | baja | descartar | Todo NIST: física, manufactura, etc. Insights lo cubre mejor. |
| NIST Cybersecurity news | `https://www.nist.gov/news-events/cybersecurity/rss.xml` | No | — | — | — | pendiente | URL citada por Filigran; no pude abrirla. |
| IETF OAuth WG (datatracker) | `https://datatracker.ietf.org/group/oauth/documents/feed/?significant=1` | Parcial | Drafts actualizados el 2026-11-02 (client-id-metadata-document-03, spiffe-client-auth-03) | ~3–6 cambios | alta (técnica) | **pendiente → incluir** | La URL aparece en la página del WG. El mismo patrón de feed lo verifiqué en otro WG (httpauth): Atom válido. Las entradas son cambios de estado de drafts y conviene que el analizador las agrupe. |
| OpenID Foundation | `https://openid.net/feed/` | No | La página de noticias muestra "OIDF publishes threat model for cross-boundary AI agents", entre otros (sin fechas) | n/d | alta | **pendiente → incluir** | El sitio enlaza el feed. No pude abrirlo. |
| FIDO Alliance | — | No | — | — | alta | **sin RSS encontrado** | Ni las páginas de categoría ni la de noticias exponen un feed. Ver sección "Fuentes que no tienen RSS". |
| OWASP | `https://owasp.org/rss` | Sí (D) | **2026-06-09** | <1 | baja | descartar | Más de 60 días sin publicar. Son noticias institucionales. |
| IDPro (feed de tag) | `https://idpro.org/tag/body-of-knowledge/feed` | Sí (D) | **2023-08-24** | 0 | — | descartar | Muerto. No encontré un feed general vivo. |
| INCIBE-CERT blog | `https://www.incibe.es/incibe-cert/blog/feed` | Sí (F) | hace ~20 días | ~0.5–1 | media-baja (no vi títulos) | **incluir con filtro** | Fuente oficial española, bajo volumen. |
| INCIBE Empresas blog | `https://www.incibe.es/empresas/blog/feed` | Sí (F) | hace ~5 días | ~1 | baja | descartar en arranque | Divulgación para pymes. |
| INCIBE avisos / vulnerabilidades | `…/incibe-cert/alerta-temprana/avisos/feed`, `https://www.incibe.es/feed/vulnerabilities` | Sí (F) | horas | alto | baja | descartar | Mucho ruido CVE. Los feeds `/feed/avisos-seguridad/all` y `/feed/blog/all` **no responden**. |
| CISA advisories (all) | `https://www.cisa.gov/cybersecurity-advisories/all.xml` | Sí (F, T) | hace ~8 h (2026-11-04) | ~15–20 | baja | descartar en arranque | Mayormente avisos ICS. Las adiciones al KEV relevantes, como bypass de autenticación, ya llegan por la prensa. |

## 2. Blogs de vendors (marcar sesgo comercial en el análisis)

| Fuente | Feed URL | Verif. | Ítem más reciente | Vol./sem | Relevancia | Recomendación | Motivo |
|---|---|---|---|---|---|---|---|
| Okta Threat Intelligence | `https://www.okta.com/blog/threat-intelligence.rss` | Sí (D) | 2026-11-01 ("Credential stuffing attacks poised to accelerate with AI") | ~0.5 | **alta** | **incluir** | Investigación de ataques a identidad (MFA downgrade, credential stuffing). Poco marketing. |
| Okta blog general | — (feeder: "no tiene RSS propio") | No | 2026-11-02 | ~3 | alta | sin RSS | Solo existe el feed de Threat Intelligence. |
| Auth0 blog | `https://auth0.com/blog/rss.xml` | Sí (D) | 2026-11-03 | ~5 (10 ítems en 12 días) | alta (tema) / sesgo alto | **incluir con filtro** | 7 de 10 son CIAM o agentes, pero muchos son piezas de campaña ("Trust Puts Customer Identity in the Spotlight"). |
| Microsoft Entra blog (Tech Community) | `https://techcommunity.microsoft.com/t5/s/gxcuf89792/rss/board?board.id=Identity` | Sí (F) | **más de 1 año** | 0 | — | descartar | **Muerto:** el blog migró y el feed viejo quedó congelado. |
| Microsoft Security Blog – IAM | Solo la página `…/security/blog/topic/identity-and-access-management/`, sin feed visible | No | 2026-07-13 (en la copia vista) | ~0.5 | alta | pendiente | Probar `https://www.microsoft.com/en-us/security/blog/feed/` con filtro. |
| Google Online Security Blog | `https://feeds.feedburner.com/GoogleOnlineSecurityBlog` | Sí (F) | **2026-04-23** | 0 | — | descartar | **Dejó de publicar en RSS** (según feeder, también en `atom.xml`). |
| Ping Identity developer blog | `https://developer.pingidentity.com/blog/rss.xml` | No | 10 posts en oct-2026, según el archivo del sitio | ~2 | media | pendiente | El sitio enlaza el feed. No pude abrirlo. El blog corporativo de Ping no expone feed. |
| Persona | — (feeder: "no tiene RSS propio") | No | hace ~3 meses | <0.5 | media | sin RSS | Es casi solo anuncios. |
| Jumio | `https://www.jumio.com/feed/` (según FeedSpot) | No | — | — | media | pendiente | No verificado. |
| Socure | Hay un blog en Medium y en su sitio; FeedSpot sugiere `socure.com/blog/rss.xml` | No | — | — | media | pendiente | No verificado. |
| Veriff, Entrust/Onfido | — | No | — | — | — | sin RSS encontrado | No encontré un feed público. |

## 3. Prensa de seguridad

| Fuente | Feed URL | Verif. | Ítem más reciente | Vol./sem | Relevancia | Recomendación | Motivo |
|---|---|---|---|---|---|---|---|
| The Record | `https://therecord.media/feed/` | Sí (F, T) | hace ~3 h (2026-11-04) | ~28 | baja-media (~10–15%) | **incluir con filtro** | Rigurosa. Ej.: "OpenAI apologizes for agents breaching Australian government websites without authorization". La sección `/news/technology/feed/` (D) solo tiene 5 ítems: no conviene. |
| Krebs on Security | `https://krebsonsecurity.com/feed/` | Sí (F, T) | hace ~4 días | ~1–2 | media (~30%) | **incluir** | Fraude e identidad (ShinyHunters, servicio que vende 153M licencias de conducir). Volumen mínimo. |
| Dark Reading | `https://www.darkreading.com/rss.xml` | Sí (T) | Feeder ve un post del 2026-11-04 en el sitio | ~40 | baja-media (~15%) | **incluir con filtro** | Ej.: "Phishing-Resistant Isn't Enough; Yubico Takes Aim at Identity-Verification Gap". El viejo `rss_simple.asp` está muerto desde dic-2023. |
| SecurityWeek | `https://www.securityweek.com/feed/` | Sí (F/T, indirecto) | hace ~17 h | 41–58 | baja (~5–10%) | **incluir con filtro** | Mucho volumen de vulnerabilidades y M&A. Es candidata a salir si el costo aprieta. |
| BleepingComputer | `https://www.bleepingcomputer.com/feed/` | **No** | El sitio publicó el 2026-11-01 (según feeder) | ~70+ | media (~20–25%) | **pendiente** | threatfilter.dev reporta **HTTP 403** para bots. `/feed/security/` (D) devolvió XML válido pero con ítems de **jun-2026**: está obsoleto o cacheado. Probar `/feed/` con `proxy=off`. |
| CISA | Ver sección 1 | — | — | — | — | — | — |

## 4. Prensa especializada en identidad

| Fuente | Feed URL | Verif. | Ítem más reciente | Vol./sem | Relevancia | Recomendación | Motivo |
|---|---|---|---|---|---|---|---|
| Biometric Update | `https://feeds.feedburner.com/biometricupdate` | Sí (F) | hace ~20 min | **~64** | **alta (~60–65%)** | **incluir con filtro** | La mejor fuente temática: IDV, KYC, digital ID, agentes ("NIST sets 10 principles for AI agent identity and authorization", "Kantara finds human identity risk models fall short for AI agents"). Es la que más ítems aporta: filtrar fuerte la vigilancia biométrica y la de gobierno sin ángulo de confianza. |
| Identity Week | — | No | 2026-11-04 (en la página) | n/d | media | sin RSS encontrado | El sitio no enlaza feed. Además, Biometric Update cubre lo mismo. |
| Planet Biometrics, ID Tech Wire, SecureIDNews | URLs en FeedSpot | No | — | — | media | pendiente | Probablemente redundantes con Biometric Update. |

## 5. Español: LATAM y España

| Fuente | Feed URL | Verif. | Ítem más reciente | Vol./sem | Relevancia | Recomendación | Motivo |
|---|---|---|---|---|---|---|---|
| Una al Día (Hispasec) | `https://unaaldia.hispasec.com/feed/` | Sí (F) | hace ~6 días | ~4 | baja (~10%) | **incluir con filtro** | Única fuente en español verificada y viva. Sobre todo vulnerabilidades. |
| WeLiveSecurity (ESET) español | `http://feeds.feedburner.com/esetla-laboratorio` | No | — | — | media | **pendiente** | feeder lo lista como "We Live Security en Español". No pude abrirlo. Es la prioridad #1 por verificar. |
| WeLiveSecurity (ESET) inglés | `https://www.welivesecurity.com/en/rss/feed/` | Sí (D) | 2026-11-02 | ~2 | baja-media | descartar | Válido (100 ítems), pero el objetivo es la edición en español. |
| El Financiero (MX) | `https://www.elfinanciero.com.mx/rss` (general) | No | — | alto | baja | pendiente | No encontré un feed de la sección `/tech/`. Requeriría filtro fuerte. |
| El Economista (MX), Expansión (MX) | — | No | — | — | — | sin RSS encontrado | No encontré feeds públicos documentados. |
| Segu-Info (AR), DPL News | — | No | — | — | — | pendiente | No encontré la URL del feed. Segu-Info está activo en Telegram. |

## 6. arXiv cs.CR

- **Volumen:** junio de 2025 tuvo 733 entradas. Son ~35 por día hábil y probablemente más hoy. No pude abrir `rss.arxiv.org/rss/cs.CR` directamente: la estimación sale del listado mensual de arxiv.org.
- **Relevancia de identidad:** en una muestra de 50 títulos, ~8–12% (OIDC/SSO, verifiable credentials, OAuth para MCP, contraseñas). Eso da ~3–4 papers por día.
- **Recomendación:** **no incluir tal cual.** Si se agrega `cs.CR` en `agents/gatherers/research_gatherer.py` (líneas 51–54, dict `CATEGORIES`), aplicar un **prefiltro por keywords antes del LLM**. Ejemplos: `authentication|authorization|identity|credential|passkey|WebAuthn|FIDO|OAuth|OIDC|MFA|phishing|deepfake|liveness|biometric|KYC|agent.*(permission|delegat|access control)`. Así pasan ~4–6 por día en vez de ~35. Hoy el triage verá **0 de arXiv**, porque cs.CR no está configurado.

---

## Fuentes que no tienen RSS (o no se encontró)

- **FIDO Alliance:** sin feed visible en noticias ni en categorías. Alternativa: su newsletter por email, o monitorear `fidoalliance.org/category/announcements/` con un scraper. Hoy Biometric Update y la prensa cubren sus anuncios grandes.
- **Banxico:** solo tiene RSS de **indicadores** (`banxico.org.mx/rss/rss.html`). Los **comunicados de prensa llegan solo por email** (suscripción en `viewers/JSP/subscriptions.jsp`).
- **CNBV:** no encontré RSS. Su página de boletines bloquea crawlers (robots). Es un candidato a monitoreo manual o scraper.
- **Okta (blog general), Persona, Identity Week, Veriff, Entrust/Onfido:** sin feed propio.
- **El Economista (MX), Expansión (MX):** sin feed documentado encontrado.
- **Microsoft Entra:** el feed de Tech Community está congelado hace más de 1 año. **Google Online Security Blog:** sin publicaciones en RSS desde el 2026-04-23.

## Pendientes de verificar desde el pipeline (orden de prioridad)

1. `http://feeds.feedburner.com/esetla-laboratorio` (WeLiveSecurity en español)
2. `https://www.bleepingcomputer.com/feed/` (probar con `proxy=off`; reportado 403)
3. `https://openid.net/feed/`
4. `https://datatracker.ietf.org/group/oauth/documents/feed/?significant=1`
5. `https://developer.pingidentity.com/blog/rss.xml`
6. `https://www.microsoft.com/en-us/security/blog/feed/` (con filtro)
7. Mastodon `briankrebs@infosec.exchange` y Bluesky `aaronpk.com`. Existen, pero no confirmé actividad reciente. Faltan expertos de identidad con cuenta verificada: por ejemplo, Tim Cappalli no publica sus redes en su perfil público.

Prueba rápida desde tu máquina o desde GitHub Actions:

```bash
python -c "
import feedparser,sys
for u in sys.argv[1:]:
    f=feedparser.parse(u); e=f.entries
    print(u, f.get('status'), len(e), e[0].get('published','?') if e else 'VACIO')
" URL1 URL2 ...
```

## Recomendación final

**Lista de arranque verificada: 11 feeds.** Son 6 en `rss_feeds.txt` y 5 en `research_feeds.txt`. Mastodon y Bluesky quedan vacíos.

| # | Fuente | Ítems/día aprox. |
|---|---|---|
| 1 | Biometric Update | ~9 |
| 2 | SecurityWeek | ~7.5 |
| 3 | Dark Reading | ~6 |
| 4 | The Record | ~4 |
| 5 | Auth0 blog | ~0.7 |
| 6 | Una al Día | ~0.6 |
| 7 | Krebs | ~0.2 |
| 8 | NIST CSRC drafts | ~0.2 |
| 9 | NIST Insights | ~0.15 |
| 10 | INCIBE-CERT blog | ~0.1 |
| 11 | Okta Threat Intel | ~0.07 |
| | **Total** | **~28–29** |

**El modelo de triage vería ~28–29 ítems por día.** Unos 6 a 9 pasarían la regla de entrada, sobre todo de Biometric Update, Okta, Auth0 y Krebs.

Al verificar los 6 pendientes de mayor prioridad, la lista llegaría a ~17 feeds y ~40 ítems por día. Si BleepingComputer funciona, aporta ~10 por día, y sería razonable **sacar SecurityWeek**: tiene la peor relación entre volumen y relevancia.

Decisión propuesta (pendiente de tu confirmación): arrancar con los 11 feeds verificados y no activar arXiv cs.CR sin prefiltro por keywords. La prioridad es verificar WeLiveSecurity en español, BleepingComputer, OpenID y IETF OAuth desde el pipeline real.
