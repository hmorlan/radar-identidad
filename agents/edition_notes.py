"""Notas de la edición y su verificación (Radar de Identidad).

Fase 4.2 — Redacción: el modelo principal recibe los mejores candidatos de todas
las categorías y escribe entre 4 y 8 notas con el formato del radar:
Qué pasó · Por qué importa · La pregunta de fondo (opcional) · Nivel de señal.

Fase 4.3 — Verificación: una segunda pasada contrasta cada nota con el texto de
su fuente. Cada nota sale ``verificada``, ``corregida`` (con el texto corregido)
o se descarta. Si la verificación falla por completo, las notas se publican
marcadas ``sin_verificar`` y la corrida queda degradada.

Fase 4.4 — Coherencia: si la verificación corrigió o descartó alguna nota, una
pasada corta revisa el titular, el resumen ejecutivo, los resúmenes por categoría
y los temas (que se escribieron antes, a partir de los análisis sin verificar) y
devuelve reemplazos mínimos para las frases que contradicen la corrección. Así una
corrección no se queda solo en la nota (corrida del 17 nov: la nota decía que los
deepfakes fueron rechazados y el resumen, que superaban la verificación).

Las instrucciones viven en ``config/prompts.yaml`` (``orchestration.edition_notes``,
``orchestration.edition_fact_check`` y ``orchestration.edition_coherence``); aquí
solo se arma el contexto, se valida la respuesta y se aplica el resultado.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .base import AnalyzedItem, CategoryReport, extract_json_str
from .llm_client import ThinkingLevel, attempt_timeout
from generators.source_names import clean_source
from .prompt_security import build_fenced_user_message, build_hardened_system, new_fence_nonce

logger = logging.getLogger(__name__)

SIGNALS = ("baja", "media", "alta")
VERDICTS = ("verificada", "corregida", "descartar")

# Candidates per category that reach the editor. Regulators arrive inside "news".
DEFAULT_LIMITS = {"news": 14, "research": 6, "social": 4, "reddit": 0}
CONTENT_CLIP = 1800


@dataclass
class EditionNote:
    item_id: str
    category: str
    title: str
    url: str
    source: str
    published: str
    que_paso: str
    por_que_importa: str
    senal: str
    pregunta_de_fondo: Optional[str] = None
    verificacion: str = "sin_verificar"
    nota_verificacion: str = ""
    # Cuando la nota viene de un post que difunde otro texto: el post (vía de
    # descubrimiento) mientras url/source apuntan al original. {"source", "url"}.
    via: Optional[Dict[str, str]] = None
    # "publicacion" (la fecha es la de la fuente) o "anuncio" (arXiv sin fecha de
    # envío: es la del anuncio, y el sitio lo dice así).
    fecha_tipo: str = "publicacion"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Edition:
    titular: str = ""
    notas: List[EditionNote] = field(default_factory=list)
    degradations: List[str] = field(default_factory=list)
    # Notas que la verificación descartó: {"id", "titulo", "motivo"}.
    descartadas: List[Dict[str, str]] = field(default_factory=list)
    # Reemplazos de coherencia ya validados: {"campo", "antes", "despues", "motivo"}.
    # Viajan en el checkpoint para reaplicarse al reanudar.
    ajustes: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"titular": self.titular, "notas": [n.to_dict() for n in self.notas],
                "descartadas": self.descartadas, "ajustes": self.ajustes}

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "Edition":
        data = data or {}
        notes = []
        for raw in data.get("notas") or []:
            try:
                notes.append(EditionNote(**{k: raw.get(k) for k in EditionNote.__dataclass_fields__ if k in raw}))
            except TypeError:
                continue
        ajustes = [a for a in data.get("ajustes") or []
                   if isinstance(a, dict) and all(isinstance(a.get(k), str) for k in ("campo", "antes", "despues"))]
        descartadas = [d for d in data.get("descartadas") or [] if isinstance(d, dict)]
        return cls(titular=data.get("titular", ""), notas=notes,
                   descartadas=descartadas, ajustes=ajustes)


# Candidatos extra de noticias fuera del top 10: Latinoamérica y España, y lo que
# llega de reguladores y empresas o iniciativas observadas. Sin esto, en la corrida
# del 13 nov la Ley de Economía Digital (México) y Agent Name Service no llegaron al
# editor aunque sí se recolectaron.
EXTRA_REGIONAL = 4
EXTRA_MIN_SCORE = 45
_REGIONAL_COUNTRIES = {"MX", "ES", "CO", "AR", "CL", "PE", "CR", "GT", "LATAM"}
_ES_WORDS = re.compile(r"\b(?:el|la|los|las|del|para|por|con|una|que|en)\b", re.I)


def _is_regional_or_watched(a: AnalyzedItem) -> bool:
    item = a.item
    meta = item.metadata or {}
    if item.source_type in ("regulator", "empresa"):
        return True
    if str(meta.get("country", "")).upper() in _REGIONAL_COUNTRIES:
        return True
    return len(_ES_WORDS.findall(item.title or "")) >= 2  # título original en español


def collect_candidates(
    category_reports: Dict[str, CategoryReport],
    limits: Optional[Dict[str, int]] = None,
    extra_regional: int = EXTRA_REGIONAL,
) -> List[Tuple[str, AnalyzedItem]]:
    """Top items from every category, best first, without duplicates; plus a few
    regional or watched news items with a decent score from outside the top."""
    limits = {**DEFAULT_LIMITS, **(limits or {})}
    seen, out = set(), []
    for category, report in category_reports.items():
        for analyzed in (report.top_items or [])[: limits.get(category, 4)]:
            if analyzed.item.id in seen:
                continue
            seen.add(analyzed.item.id)
            out.append((category, analyzed))
    news = category_reports.get("news")
    if news and extra_regional > 0:
        extras = sorted(
            (a for a in (news.all_items or [])
             if a.item.id not in seen and (a.importance_score or 0) >= EXTRA_MIN_SCORE
             and _is_regional_or_watched(a)),
            key=lambda a: -(a.importance_score or 0),
        )[:extra_regional]
        for a in extras:
            seen.add(a.item.id)
            out.append(("news", a))
    return out


# --------------------------------------------------------------------------
# Texto completo de la fuente para el redactor y el verificador
# --------------------------------------------------------------------------
# Muchos RSS solo traen un adelanto (mediana de 305 caracteres en la corrida del
# 17 nov; Payments Dive dio 143 para la billetera de ChatGPT y la nota tuvo que
# decir "el texto disponible no detalla…" cuando el artículo sí lo detallaba).
# Antes de redactar se baja la página de las noticias con texto corto. Sin costo
# de API; si la página falla o tiene muro de pago, se queda el texto del RSS.
FULLTEXT_MIN = 1200           # por debajo de esto se intenta bajar la página
FULLTEXT_CLIP = 2000          # lo que recibe el redactor de un texto completo
# 2026-11-20: con 4500 el prompt del redactor pasó de 37 mil a 65 mil caracteres y
# Opus (esfuerzo max) no terminó en 600 s en ninguno de los tres intentos. Además,
# el redactor y el verificador tienen su propio tope por intento (EDITION_LLM_TIMEOUT_SECONDS).
EDITION_TIMEOUT_DEFAULT = 1200.0
FULLTEXT_TIMEOUT = 15.0
FULLTEXT_CONCURRENCY = 6
# Páginas que responden 200 pero dicen "no encontrada" (INCIBE lo hizo el 17 nov).
_SOFT_404 = re.compile(r"p[aá]gina no encontrada|page not found|404 not found|no se ha encontrado la p[aá]gina", re.I)
_FULLTEXT_SKIP_HOSTS = ("news.google.com", "arxiv.org", "bsky.app", "mastodon")


def _edition_timeout() -> float:
    """Tope por intento del redactor y el verificador (EDITION_LLM_TIMEOUT_SECONDS)."""
    try:
        return max(60.0, float(os.getenv("EDITION_LLM_TIMEOUT_SECONDS") or EDITION_TIMEOUT_DEFAULT))
    except ValueError:
        return EDITION_TIMEOUT_DEFAULT


def _fetch_page(url: str) -> Tuple[str, str]:
    """Texto principal y fecha de publicación (AAAA-MM-DD o "") de una página.

    Bloqueante; se llama en un hilo.
    """
    import requests
    from bs4 import BeautifulSoup
    from .gatherers.link_follower import LinkFollower

    resp = requests.get(url, timeout=FULLTEXT_TIMEOUT, allow_redirects=True, headers={
        "User-Agent": "Mozilla/5.0 (compatible; RadarDeIdentidad/1.0; +https://radar.hirammorlan.com)"})
    resp.raise_for_status()
    if "html" not in resp.headers.get("content-type", "html"):
        return "", ""
    soup = BeautifulSoup(resp.content, "html.parser")
    fecha = published_date(soup)
    return LinkFollower()._extract_content(soup), fecha


_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
_JSONLD_DATE = re.compile(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})')


def published_date(soup: Any) -> str:
    """Fecha de publicación de un artículo (metadatos estándar), o "" si no la declara."""
    for attrs in ({"property": "article:published_time"}, {"property": "og:published_time"},
                  {"name": "article:published_time"}, {"itemprop": "datePublished"},
                  {"name": "date"}, {"name": "pubdate"}):
        tag = soup.find("meta", attrs=attrs)
        m = _DATE_RE.match((tag.get("content") or "").strip()) if tag else None
        if m:
            return m.group(1)
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        m = _JSONLD_DATE.search(script.string or script.get_text() or "")
        if m:
            return m.group(1)
    tag = soup.find("time", attrs={"datetime": True})
    m = _DATE_RE.match(tag["datetime"].strip()) if tag else None
    return m.group(1) if m else ""


def _fetch_url(category: str, a: AnalyzedItem) -> str:
    """Qué página bajar: el artículo que difunde un post, o la nota misma."""
    meta = a.item.metadata if isinstance(a.item.metadata, dict) else {}
    original = meta.get("enlace_original") or ""
    if category == "social" and original.startswith(("http://", "https://")):
        return original
    return a.item.url or ""


def _wants_full_text(category: str, a: AnalyzedItem) -> bool:
    it = a.item
    url = _fetch_url(category, a).lower()
    if not url.startswith(("http://", "https://")) or any(h in url for h in _FULLTEXT_SKIP_HOSTS):
        return False
    if url != (it.url or "").lower():
        return True   # el original de un post: se baja siempre (texto y fecha)
    return category in ("news", "social") and len(it.content or "") < FULLTEXT_MIN


async def enrich_full_text(candidates: List[Tuple[str, AnalyzedItem]]) -> int:
    """Guarda en ``metadata['texto_completo']`` el texto de la página cuando el RSS es corto."""
    if os.getenv("EDITION_FULLTEXT", "1") == "0":
        return 0
    todo = [(cat, a) for cat, a in candidates if _wants_full_text(cat, a)]
    sem = asyncio.Semaphore(FULLTEXT_CONCURRENCY)

    async def one(cat: str, a: AnalyzedItem) -> bool:
        url = _fetch_url(cat, a)
        async with sem:
            try:
                text, fecha = await asyncio.wait_for(asyncio.to_thread(_fetch_page, url),
                                                     FULLTEXT_TIMEOUT + 5)
            except Exception as e:  # noqa: BLE001
                logger.info("Texto completo no disponible (%s): %s", type(e).__name__, url)
                return False
        if not isinstance(a.item.metadata, dict):
            a.item.metadata = {}
        if fecha and url != a.item.url:
            # Fecha del artículo que difunde el post (20 nov: WIRED era del 17,
            # el post de Bluesky del 19).
            a.item.metadata["fecha_original"] = fecha
        text = " ".join((text or "").split())
        if _SOFT_404.search(text[:300]):
            logger.info("Texto completo descartado (página no encontrada): %s", url)
            return False
        if len(text) <= len(a.item.content or "") + 200:
            return False
        a.item.metadata["texto_completo"] = text
        return True

    got = sum(await asyncio.gather(*(one(c, a) for c, a in todo))) if todo else 0
    logger.info("Texto completo: %d de %d candidatos con RSS corto", got, len(todo))
    return got


def source_text(it: Any, limit: int) -> str:
    """Texto de la fuente: el completo si se bajó, si no el del RSS."""
    meta = it.metadata if isinstance(getattr(it, "metadata", None), dict) else {}
    full = meta.get("texto_completo")
    if full:
        return _clip(full, max(limit, FULLTEXT_CLIP))
    return _clip(it.content, limit)


def _clip(text: Optional[str], limit: int) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def candidates_context(candidates: Iterable[Tuple[str, AnalyzedItem]]) -> str:
    records = []
    for category, a in candidates:
        it = a.item
        records.append({
            "id": it.id,
            "categoria": category,
            "fuente": it.source,
            "tipo_fuente": it.source_type,
            "titulo": it.title,
            "url": it.url,
            "publicado": it.published,
            "resumen_triage": _clip(a.summary, 600),
            "puntaje_triage": a.importance_score,
            "contenido": source_text(it, CONTENT_CLIP),
        })
    return json.dumps(records, ensure_ascii=False, indent=1)


def _parse(content: str, required: Tuple[str, ...]) -> Dict[str, Any]:
    return json.loads(extract_json_str(content, required_keys=required))


def parse_notes(content: str, by_id: Dict[str, Tuple[str, AnalyzedItem]], max_notes: int) -> Edition:
    """Validate the editor's JSON into an Edition; drop anything malformed."""
    data = _parse(content, ("notas",))
    edition = Edition(titular=_clip(str(data.get("titular") or ""), 160))
    for raw in data.get("notas") or []:
        if not isinstance(raw, dict):
            continue
        item_id = str(raw.get("id") or "")
        if item_id not in by_id or any(n.item_id == item_id for n in edition.notas):
            continue
        senal = str(raw.get("senal") or "").strip().lower()
        que_paso = _clip(raw.get("que_paso"), 900)
        por_que = _clip(raw.get("por_que_importa"), 900)
        titulo = _clip(raw.get("titulo"), 180)
        if senal not in SIGNALS or not (que_paso and por_que and titulo):
            logger.warning("Nota descartada por formato inválido: %s", item_id)
            continue
        pregunta = _clip(raw.get("pregunta_de_fondo"), 300) or None
        category, analyzed = by_id[item_id]
        it = analyzed.item
        origin = note_origin(it)
        edition.notas.append(EditionNote(
            item_id=item_id, category=category, title=titulo, que_paso=que_paso,
            por_que_importa=por_que, senal=senal, pregunta_de_fondo=pregunta, **origin,
        ))
        if len(edition.notas) >= max_notes:
            break
    return edition


def note_origin(it: Any) -> Dict[str, Any]:
    """URL, fuente, fecha y vía de una nota.

    - Un post de redes que difunde un artículo enlaza al artículo y lleva la fecha
      del artículo (si se pudo leer; si no, ninguna). El post queda como vía, con
      su propia fecha: publicación y descubrimiento no se mezclan.
    - Un preprint de arXiv lleva su fecha de envío; si la API no la dio, la del
      anuncio, marcada como tal.
    - La fuente va con nombre legible (generators/source_names.py).
    """
    meta = it.metadata if isinstance(getattr(it, "metadata", None), dict) else {}
    out: Dict[str, Any] = {"url": it.url, "source": clean_source(it.source),
                           "published": it.published, "via": None, "fecha_tipo": "publicacion"}
    original = meta.get("enlace_original") or ""
    if it.source_type in ("bluesky", "mastodon") and original.startswith(("http://", "https://")):
        quien = meta.get("author_display_name") or (it.author or "").lstrip("@")
        out["via"] = {"source": f"{it.source} ({quien})" if quien else it.source,
                      "url": it.url, "published": it.published or ""}
        out["url"], out["source"] = original, _host_name(original)
        out["published"] = meta.get("fecha_original") or ""
    if it.source_type == "arxiv":
        if meta.get("enviado"):
            out["published"] = meta["enviado"]
        else:
            out["fecha_tipo"] = "anuncio"
    return out


def _host_name(url: str) -> str:
    from urllib.parse import urlparse
    host = urlparse(url).netloc.lower().removeprefix("www.")
    return clean_source(host) if host else url


def apply_fact_check(edition: Edition, content: str) -> Edition:
    """Apply verdicts: keep verified, replace corrected text, drop the rest.

    A note the checker did not mention is kept as ``sin_verificar``.
    """
    data = _parse(content, ("revisiones",))
    verdicts = {str(r.get("id")): r for r in data.get("revisiones") or [] if isinstance(r, dict)}
    kept = []
    for note in edition.notas:
        review = verdicts.get(note.item_id)
        if not review:
            kept.append(note)
            continue
        verdict = str(review.get("veredicto") or "").strip().lower()
        note.nota_verificacion = _clip(review.get("motivo"), 400)
        if verdict == "descartar":
            logger.info("Verificación: nota descartada %s (%s)", note.item_id, note.nota_verificacion)
            edition.descartadas.append({"id": note.item_id, "titulo": note.title,
                                        "motivo": note.nota_verificacion})
            continue
        if verdict == "corregida":
            for field_name in ("que_paso", "por_que_importa", "pregunta_de_fondo", "titulo"):
                new = review.get(field_name)
                if isinstance(new, str) and new.strip():
                    target = "title" if field_name == "titulo" else field_name
                    setattr(note, target, _clip(new, 900))
            senal = str(review.get("senal") or "").strip().lower()
            if senal in SIGNALS:
                note.senal = senal
            note.verificacion = "corregida"
        elif verdict == "verificada":
            note.verificacion = "verificada"
        kept.append(note)
    edition.notas = kept
    return edition


def fact_check_context(edition: Edition, by_id: Dict[str, Tuple[str, AnalyzedItem]]) -> str:
    records = []
    for note in edition.notas:
        it = by_id[note.item_id][1].item
        records.append({
            "id": note.item_id,
            "nota": {
                "titulo": note.title, "que_paso": note.que_paso,
                "por_que_importa": note.por_que_importa,
                "pregunta_de_fondo": note.pregunta_de_fondo, "senal": note.senal,
            },
            "fuente": {
                "nombre": it.source, "titulo": it.title, "url": it.url,
                "publicado": it.published, "texto": source_text(it, CONTENT_CLIP * 2),
            },
        })
    return json.dumps(records, ensure_ascii=False, indent=1)


# --------------------------------------------------------------------------
# Fase 4.4: coherencia de los textos derivados con las correcciones
# --------------------------------------------------------------------------

TITULAR_FIELD = "titular"
_MD_LINK = re.compile(r"\]\(([^)\s]+)\)")


def needs_coherence(edition: Edition) -> bool:
    return bool(edition.descartadas) or any(n.verificacion == "corregida" for n in edition.notas)


def coherence_context(edition: Edition, by_id: Dict[str, Tuple[str, AnalyzedItem]],
                      derived: Dict[str, str]) -> str:
    corrections = []
    for note in edition.notas:
        if note.verificacion != "corregida":
            continue
        it = by_id[note.item_id][1].item if note.item_id in by_id else None
        corrections.append({
            "id": note.item_id, "veredicto": "corregida", "motivo": note.nota_verificacion,
            "nota_corregida": {"titulo": note.title, "que_paso": note.que_paso,
                               "por_que_importa": note.por_que_importa},
            "fuente": source_text(it, CONTENT_CLIP * 2) if it else "",
        })
    for d in edition.descartadas:
        it = by_id[d.get("id", "")][1].item if d.get("id") in by_id else None
        corrections.append({
            "id": d.get("id"), "veredicto": "descartada", "motivo": d.get("motivo", ""),
            "titulo_descartado": d.get("titulo", ""),
            "fuente": source_text(it, CONTENT_CLIP * 2) if it else "",
        })
    textos = {TITULAR_FIELD: edition.titular, **derived}
    return json.dumps({"correcciones": corrections,
                       "textos": {k: v for k, v in textos.items() if v}},
                      ensure_ascii=False, indent=1)


def parse_coherence(content: str, texts: Dict[str, str]) -> List[Dict[str, str]]:
    """Keep only edits that are safe to apply verbatim.

    ``antes`` must appear exactly once in its field, and ``despues`` must keep
    every internal link that ``antes`` had (the summaries are full of links).
    """
    data = _parse(content, ("ajustes",))
    edits: List[Dict[str, str]] = []
    for raw in data.get("ajustes") or []:
        if not isinstance(raw, dict):
            continue
        campo, antes, despues = (str(raw.get(k) or "") for k in ("campo", "antes", "despues"))
        text = texts.get(campo, "")
        if not antes.strip() or not despues.strip() or antes == despues:
            continue
        if text.count(antes) != 1:
            logger.warning("Coherencia: ajuste ignorado en %s (el texto original no aparece una vez)", campo)
            continue
        if not set(_MD_LINK.findall(antes)) <= set(_MD_LINK.findall(despues)):
            logger.warning("Coherencia: ajuste ignorado en %s (perdía enlaces)", campo)
            continue
        if len(despues) > max(2 * len(antes), len(antes) + 300):
            logger.warning("Coherencia: ajuste ignorado en %s (reescribía de más)", campo)
            continue
        edits.append({"campo": campo, "antes": antes, "despues": despues,
                      "motivo": _clip(raw.get("motivo"), 200)})
    return edits


def apply_edits(texts: Dict[str, str], edits: Iterable[Dict[str, str]]) -> Dict[str, str]:
    """Return a copy of ``texts`` with each edit applied once (if it still matches)."""
    out = dict(texts)
    for e in edits:
        text = out.get(e.get("campo", ""))
        if text is not None and text.count(e["antes"]) == 1:
            out[e["campo"]] = text.replace(e["antes"], e["despues"], 1)
    return out


async def reconcile_derived(
    async_client: Any,
    prompt_accessor: Any,
    edition: Edition,
    by_id: Dict[str, Tuple[str, AnalyzedItem]],
    derived: Dict[str, str],
    target_date: str,
    max_notes: int = 8,
) -> Edition:
    """Fase 4.4. Never raises: on failure the derived texts stay as they were."""
    if not derived or not needs_coherence(edition):
        return edition
    prompt = _prompt(prompt_accessor, "edition_coherence", target_date, max_notes)
    if not prompt:
        edition.degradations.append("coherencia: falta orchestration.edition_coherence")
        return edition
    nonce = new_fence_nonce()
    try:
        response = await async_client.call_with_thinking(
            messages=[{"role": "user", "content": build_fenced_user_message(
                coherence_context(edition, by_id, derived), nonce,
                task_line="Revisa los textos cercados contra las correcciones, según tus "
                          "instrucciones de sistema.")}],
            system=build_hardened_system(prompt, nonce),
            profile=ThinkingLevel.QUICK,
            caller="orchestrator.edition_coherence",
        )
        texts = {TITULAR_FIELD: edition.titular, **derived}
        edits = parse_coherence(response.content, texts)
    except Exception as e:  # noqa: BLE001
        logger.error("Coherencia de la edición falló: %s", e)
        edition.degradations.append(f"coherencia: falló ({type(e).__name__}); resúmenes sin ajustar")
        return edition
    for e in edits:
        logger.info("Coherencia: %s · %s", e["campo"], e.get("motivo") or "ajuste")
    edition.titular = apply_edits({TITULAR_FIELD: edition.titular},
                                  [e for e in edits if e["campo"] == TITULAR_FIELD])[TITULAR_FIELD]
    edition.ajustes = [e for e in edits if e["campo"] != TITULAR_FIELD]
    return edition


async def build_edition(
    async_client: Any,
    prompt_accessor: Any,
    category_reports: Dict[str, CategoryReport],
    target_date: str,
    grounding: Optional[str] = None,
    max_notes: int = 8,
    derived: Optional[Dict[str, str]] = None,
) -> Edition:
    """Write the edition's notes, verify them and reconcile the derived texts.

    ``derived`` maps field names (``executive_summary``, ``resumen:news``,
    ``tema:0``…) to the texts written before the notes; the edits for them come
    back in ``edition.ajustes``. Never raises; degrades instead.
    """
    candidates = collect_candidates(category_reports)
    if not candidates:
        return Edition(degradations=["notas: no hubo candidatos"])
    by_id = {a.item.id: (cat, a) for cat, a in candidates}
    await enrich_full_text(candidates)

    notes_prompt = _prompt(prompt_accessor, "edition_notes", target_date, max_notes)
    if not notes_prompt:
        return Edition(degradations=["notas: falta orchestration.edition_notes en prompts.yaml"])

    nonce = new_fence_nonce()
    try:
        with attempt_timeout(_edition_timeout()):
            response = await async_client.call_with_thinking(
                messages=[{"role": "user", "content": build_fenced_user_message(
                    candidates_context(candidates), nonce,
                    task_line="Escribe las notas de la edición a partir de los candidatos cercados, "
                              "según tus instrucciones de sistema.")}],
                system=build_hardened_system(notes_prompt, nonce, grounding=grounding),
                profile=ThinkingLevel.DEEP,
                caller="orchestrator.edition_notes",
                full_output_budget=True,
            )
        edition = parse_notes(response.content, by_id, max_notes)
    except Exception as e:  # noqa: BLE001
        logger.error("Notas de la edición fallaron: %s", e)
        return Edition(degradations=[f"notas: falló la redacción ({type(e).__name__})"])

    if not edition.notas:
        edition.degradations.append("notas: el editor no devolvió notas válidas")
        return edition

    check_prompt = _prompt(prompt_accessor, "edition_fact_check", target_date, max_notes)
    if not check_prompt:
        edition.degradations.append("verificación: falta orchestration.edition_fact_check")
        return edition
    nonce = new_fence_nonce()
    try:
        with attempt_timeout(_edition_timeout()):
            response = await async_client.call_with_thinking(
                messages=[{"role": "user", "content": build_fenced_user_message(
                    fact_check_context(edition, by_id), nonce,
                    task_line="Verifica cada nota contra el texto de su fuente, según tus "
                              "instrucciones de sistema.")}],
                system=build_hardened_system(check_prompt, nonce),
                profile=ThinkingLevel.DEEP,
                caller="orchestrator.edition_fact_check",
                full_output_budget=True,
            )
        edition = apply_fact_check(edition, response.content)
    except Exception as e:  # noqa: BLE001
        logger.error("Verificación de notas falló: %s", e)
        edition.degradations.append(f"verificación: falló ({type(e).__name__}); notas sin verificar")
        return edition
    return await reconcile_derived(async_client, prompt_accessor, edition, by_id,
                                   derived or {}, target_date, max_notes)


def _prompt(prompt_accessor: Any, name: str, target_date: str, max_notes: int) -> Optional[str]:
    if prompt_accessor is None:
        return None
    try:
        return prompt_accessor.get_orchestration_prompt(
            name, {"date": target_date, "max_notes": str(max_notes)}
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("Prompt %s no disponible: %s", name, e)
        return None
