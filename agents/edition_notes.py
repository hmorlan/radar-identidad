"""Notas de la edición y su verificación (Radar de Identidad).

Fase 4.2 — Redacción: el modelo principal recibe los mejores candidatos de todas
las categorías y escribe entre 4 y 8 notas con el formato del radar:
Qué pasó · Por qué importa · La pregunta de fondo (opcional) · Nivel de señal.

Fase 4.3 — Verificación: una segunda pasada contrasta cada nota con el texto de
su fuente. Cada nota sale ``verificada``, ``corregida`` (con el texto corregido)
o se descarta. Si la verificación falla por completo, las notas se publican
marcadas ``sin_verificar`` y la corrida queda degradada.

Las instrucciones viven en ``config/prompts.yaml`` (``orchestration.edition_notes``
y ``orchestration.edition_fact_check``); aquí solo se arma el contexto, se valida
la respuesta y se aplica el resultado.
"""
from __future__ import annotations

import json
import re
import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .base import AnalyzedItem, CategoryReport, extract_json_str
from .llm_client import ThinkingLevel
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

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Edition:
    titular: str = ""
    notas: List[EditionNote] = field(default_factory=list)
    degradations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"titular": self.titular, "notas": [n.to_dict() for n in self.notas]}

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "Edition":
        data = data or {}
        notes = []
        for raw in data.get("notas") or []:
            try:
                notes.append(EditionNote(**{k: raw.get(k) for k in EditionNote.__dataclass_fields__ if k in raw}))
            except TypeError:
                continue
        return cls(titular=data.get("titular", ""), notas=notes)


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
            "contenido": _clip(it.content, CONTENT_CLIP),
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
        edition.notas.append(EditionNote(
            item_id=item_id, category=category, title=titulo, url=it.url, source=it.source,
            published=it.published, que_paso=que_paso, por_que_importa=por_que,
            senal=senal, pregunta_de_fondo=pregunta,
        ))
        if len(edition.notas) >= max_notes:
            break
    return edition


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
                "publicado": it.published, "texto": _clip(it.content, CONTENT_CLIP * 2),
            },
        })
    return json.dumps(records, ensure_ascii=False, indent=1)


async def build_edition(
    async_client: Any,
    prompt_accessor: Any,
    category_reports: Dict[str, CategoryReport],
    target_date: str,
    grounding: Optional[str] = None,
    max_notes: int = 8,
) -> Edition:
    """Write the edition's notes, then verify them. Never raises; degrades instead."""
    candidates = collect_candidates(category_reports)
    if not candidates:
        return Edition(degradations=["notas: no hubo candidatos"])
    by_id = {a.item.id: (cat, a) for cat, a in candidates}

    notes_prompt = _prompt(prompt_accessor, "edition_notes", target_date, max_notes)
    if not notes_prompt:
        return Edition(degradations=["notas: falta orchestration.edition_notes en prompts.yaml"])

    nonce = new_fence_nonce()
    try:
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
