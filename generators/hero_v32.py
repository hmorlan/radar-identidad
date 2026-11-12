"""Imagen de la edición, dirección v3.2 (docs/identidad-visual.md §6).

Flujo por edición:
1. **Ejes** (§6.1, §6.5): una llamada corta al modelo ligero (Haiku) elige registro,
   motivo, escena (SUBJECT), composición y estado del mosaico a partir de la nota
   principal, el banco de motivos y la memoria. No toca los prompts de redacción.
2. **Prompt**: bloque fijo idéntico + los tres ejes; 2 imágenes de referencia.
3. **Candidatas** (§6.4): 2 mosaicos en Batch API (mitad de precio). Si el batch no
   termina a tiempo, se generan al momento.
4. **Control**: oro medido, colores ajenos y revisión visual con Haiku. Gana la
   primera que pase.
5. **Respaldo** (§6.4b): un mosaico más; si también falla, grabado al buril con el
   mismo sujeto. Si el grabado falla la revisión, no se publica imagen.
6. **Postproceso** (§6.7, §6.3): tono, variante oscura derivada, miniatura.
7. **Memoria** (§6.5): se registra en data/hero_historial.json.

Los domingos se genera directamente el grabado.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import date as Date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from agents.cost_tracker import get_tracker, price_image_usage
from generators import hero_postprocess as hp

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
PROMPT_FILE = ROOT / "config" / "hero_prompt.yaml"
MOTIVOS_FILE = ROOT / "config" / "hero_motivos.yaml"
REF_DIR = ROOT / "assets" / "hero-ref"
HISTORY_FILE = ROOT / "data" / "hero_historial.json"

MOTIVO_COOLDOWN_DAYS = 56          # 8 semanas
BATCH_WAIT_SECONDS = float(os.getenv("HERO_BATCH_WAIT_MINUTES", "30")) * 60
MODEL_DISPLAY = "Gemini 3 Pro Image"
DEFAULT_FOCUS = "50% 45%"


# --------------------------------------------------------------------------
# Configuración y memoria
# --------------------------------------------------------------------------

def load_prompt_blocks() -> Dict[str, Any]:
    return yaml.safe_load(PROMPT_FILE.read_text(encoding="utf-8"))


def load_bank() -> Dict[str, Any]:
    return yaml.safe_load(MOTIVOS_FILE.read_text(encoding="utf-8"))


def load_references() -> List[bytes]:
    if not REF_DIR.exists():
        return []
    return [p.read_bytes() for p in sorted(REF_DIR.glob("ref-*.jpg"))][:2]


def load_history(path: Path = HISTORY_FILE) -> List[Dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else data.get("imagenes", [])
    except (OSError, ValueError):
        return []


def save_history(entries: List[Dict[str, Any]], path: Path = HISTORY_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    entries = sorted(entries, key=lambda e: e.get("fecha", ""))
    path.write_text(json.dumps({"imagenes": entries}, ensure_ascii=False, indent=1), encoding="utf-8")


def memory_constraints(history: List[Dict[str, Any]], today: str) -> Dict[str, Any]:
    """Lo que la memoria prohíbe hoy (§6.5)."""
    prior = sorted((e for e in history if e.get("fecha", "") < today), key=lambda e: e["fecha"])
    try:
        cutoff = (Date.fromisoformat(today) - timedelta(days=MOTIVO_COOLDOWN_DAYS)).isoformat()
    except ValueError:
        cutoff = ""
    recent_motivos = sorted({_norm(e.get("motivo", "")) for e in prior if e.get("fecha", "") >= cutoff} - {""})
    last = prior[-1] if prior else {}
    scenes_by_motivo: Dict[str, List[str]] = {}
    for e in prior:
        scenes_by_motivo.setdefault(_norm(e.get("motivo", "")), []).append(e.get("escena", ""))
    return {
        "motivos_prohibidos": recent_motivos,
        "ultima_composicion": last.get("composicion"),
        "ultimo_registro": last.get("registro"),
        "escenas_usadas": scenes_by_motivo,
    }


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


# --------------------------------------------------------------------------
# Ejes (§6.1, §6.5)
# --------------------------------------------------------------------------

@dataclass
class Axes:
    registro: str
    motivo: str          # en español, para el crédito ("Ulises y las sirenas")
    escena: str          # SUBJECT en inglés, un momento con acción
    composicion: str     # del catálogo
    estado: str          # clave del catálogo de estados
    alt: str             # texto alternativo en español
    foco: str = DEFAULT_FOCUS

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


def suggest_motivos(bank: Dict[str, Any], text: str) -> List[str]:
    text = text.lower()
    hits: List[str] = []
    for tema in bank.get("temas", []):
        if any(c.lower() in text for c in tema.get("claves", [])):
            hits.extend(tema.get("motivos", []))
    return hits


AXES_SYSTEM = """Eres el director de arte del Radar de Identidad. Cada edición lleva una imagen: un mosaico romano con un elemento de tecnología contemporánea. Tu trabajo es elegir la escena, no dibujarla.

Devuelve SOLO un objeto JSON con estas claves:
- "registro": uno de {registros}.
- "motivo": nombre corto en español del motivo, para el crédito (p. ej. "Ulises y las sirenas").
- "escena": en inglés, UNA oración: un momento con acción (no un retrato posando con un aparato) que traduzca la tensión de la nota principal, con un elemento claro de tecnología contemporánea hecho de teselas (microchips, trazos de circuito, lentes, sensores o fibra óptica). Sin teléfonos, teclados ni pantallas. Sin texto.
- "composicion": exactamente una de {composiciones}.
- "estado": exactamente una de {estados}.
- "alt": texto alternativo en español, una oración que describa la imagen.

Reglas de memoria:
- No uses estos motivos (salieron en las últimas 8 semanas): {prohibidos}.
- No repitas la composición anterior ({ultima_composicion}) ni el registro anterior ({ultimo_registro}).
- Si eliges un motivo que ya salió antes, usa otro momento del mito; escenas ya usadas: {escenas}.

Banco de motivos por tema (semilla, puedes proponer otro del mismo espíritu): {banco}
Sugerencias para esta nota: {sugeridos}"""


def _fallback_axes(bank: Dict[str, Any], constraints: Dict[str, Any], suggestions: List[str], titulo: str) -> Axes:
    """Ejes deterministas si el modelo falla: primer motivo sugerido permitido."""
    banned = set(constraints["motivos_prohibidos"])
    pool = suggestions + [m for t in bank.get("temas", []) for m in t.get("motivos", [])]
    motivo = next((m for m in pool if _norm(m) not in banned), pool[0] if pool else "Jano con llave y sensor")
    comps = [c for c in bank["composiciones"] if c != constraints["ultima_composicion"]]
    registro = "mito" if constraints["ultimo_registro"] != "mito" else "emblema"
    return Axes(
        registro=registro,
        motivo=motivo,
        escena=f"{motivo}, rendered as a Roman scene of action that echoes: {titulo}",
        composicion=comps[0],
        estado="grietas",
        alt=f"{motivo} en mosaico romano con circuitos de oro.",
    )


def validate_axes(raw: Dict[str, Any], bank: Dict[str, Any], constraints: Dict[str, Any]) -> Optional[Axes]:
    regs = list(bank["registros"].keys())
    comps = list(bank["composiciones"].keys())
    estados = list(bank["estados"].keys())
    try:
        registro = str(raw["registro"]).strip().lower()
        composicion = str(raw["composicion"]).strip().lower()
        estado = str(raw["estado"]).strip().lower()
        motivo = str(raw["motivo"]).strip()
        escena = str(raw["escena"]).strip()
        alt = str(raw.get("alt") or motivo).strip()
    except (KeyError, TypeError):
        return None
    if registro not in regs or composicion not in comps or estado not in estados or not motivo or not escena:
        return None
    # La memoria se hace cumplir aquí, no solo en el prompt.
    if _norm(motivo) in constraints["motivos_prohibidos"]:
        return None
    if registro == constraints["ultimo_registro"]:
        return None
    if composicion == constraints["ultima_composicion"]:
        alt_comps = [c for c in comps if c != composicion]
        composicion = alt_comps[0]
    return Axes(registro, motivo[:80], escena[:500], composicion, estado, alt[:300],
                bank["composiciones"].get(composicion, DEFAULT_FOCUS))


async def choose_axes(llm_client: Any, edition: Dict[str, Any], topics: List[Any],
                      history: List[Dict[str, Any]], today: str) -> Tuple[Axes, Optional[str]]:
    """Devuelve (ejes, aviso). El aviso no es None si se usaron ejes de respaldo."""
    bank = load_bank()
    constraints = memory_constraints(history, today)
    notes = (edition or {}).get("notas") or []
    lead = notes[0] if notes else {}
    titulo = lead.get("title") or (getattr(topics[0], "name", None) if topics else "") or ""
    context = " ".join(str(x) for x in (titulo, lead.get("que_paso", ""), lead.get("por_que_importa", "")))
    topic_names = [getattr(t, "name", None) or (t.get("name") if isinstance(t, dict) else str(t)) for t in topics or []]
    suggestions = suggest_motivos(bank, context + " " + " ".join(map(str, topic_names)))

    if llm_client is None:
        return _fallback_axes(bank, constraints, suggestions, titulo), "ejes: sin cliente LLM, se usó el banco"

    from agents.llm_client import ThinkingLevel
    from agents.base import extract_json_str

    system = AXES_SYSTEM.format(
        registros=list(bank["registros"].keys()),
        composiciones=list(bank["composiciones"].keys()),
        estados=list(bank["estados"].keys()),
        prohibidos=constraints["motivos_prohibidos"] or "ninguno",
        ultima_composicion=constraints["ultima_composicion"] or "ninguna",
        ultimo_registro=constraints["ultimo_registro"] or "ninguno",
        escenas=json.dumps(constraints["escenas_usadas"], ensure_ascii=False)[:1500],
        banco=json.dumps([{"tema": t["tema"], "motivos": t["motivos"]} for t in bank["temas"]], ensure_ascii=False),
        sugeridos=suggestions or "ninguna",
    )
    user = json.dumps({
        "nota_principal": {k: lead.get(k) for k in ("title", "que_paso", "por_que_importa")},
        "temas_del_dia": topic_names[:6],
    }, ensure_ascii=False)
    for attempt in range(2):
        try:
            response = await llm_client.call_with_thinking(
                messages=[{"role": "user", "content": user}],
                system=system,
                profile=ThinkingLevel.QUICK,
                caller="hero.axes",
            )
            raw = json.loads(extract_json_str(response.content, required_keys=("registro", "escena")))
            axes = validate_axes(raw, bank, constraints)
            if axes:
                return axes, None
            logger.warning(f"Ejes de imagen inválidos o contra la memoria (intento {attempt + 1}): {raw}")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Ejes de imagen fallaron (intento {attempt + 1}): {e}")
    return _fallback_axes(bank, constraints, suggestions, titulo), "ejes: el modelo no dio ejes válidos, se usó el banco"


# --------------------------------------------------------------------------
# Prompts
# --------------------------------------------------------------------------

def mosaic_prompt(blocks: Dict[str, Any], axes: Axes, with_refs: bool) -> str:
    bank = load_bank()
    parts = []
    if with_refs:
        parts.append(blocks["referencias"].strip())
    parts.append(blocks["mosaico"].strip())
    parts.append(f"SUBJECT: {axes.escena}")
    parts.append(f"COMPOSITION: {_composition_en(axes.composicion)}.")
    parts.append(f"MOSAIC STATE: {bank['estados'][axes.estado]}.")
    return "\n".join(parts)


def engraving_prompt(blocks: Dict[str, Any], axes: Axes) -> str:
    return blocks["grabado"].strip().replace("[SUJETO]", axes.escena.rstrip("."))


_COMP_EN = {
    "primer plano recortado": "cropped close-up",
    "vista cenital": "top-down view",
    "figura centrada": "centered figure",
    "sujeto a la izquierda": "subject on the left, open field on the right",
    "sujeto a la derecha": "subject on the right, open field on the left",
    "dos figuras en diálogo": "two figures in dialogue",
    "friso horizontal": "horizontal frieze",
    "diagonal": "diagonal composition",
}


def _composition_en(c: str) -> str:
    return _COMP_EN.get(c, c)


# --------------------------------------------------------------------------
# Revisión visual con Haiku (§6.4.3)
# --------------------------------------------------------------------------

REVIEW_PROMPT = {
    "mosaico": (
        "You review a generated image that must look like an ancient Roman floor mosaic. "
        "Answer with JSON only: {\"ok\": true|false, \"motivo\": \"short reason in Spanish\", "
        "\"foco_x\": number 0-100}. Set ok=false if ANY of these is visible: a frame, border or "
        "stone edge around the image; any text, letters or numerals; a mobile phone, keypad or "
        "screen; a cut-out halo around figures (background tesserae not touching the contours); "
        "figures painted smoothly instead of built from tesserae. Reject only clear, obvious "
        "violations: chip grids, circuit traces, sensor rings and other abstract geometric "
        "patterns made of tesserae are intended and are NOT text, keypads or screens. "
        "foco_x is the horizontal position (percent from the left) of the main subject."
    ),
    "grabado": (
        "You review a generated image that must look like a sepia copperplate engraving. "
        "Answer with JSON only: {\"ok\": true|false, \"motivo\": \"short reason in Spanish\", "
        "\"foco_x\": number 0-100}. Set ok=false if ANY of these is visible: a frame, border or "
        "dotted outline; text, letters or blocks of ruled lines that imitate text; color other "
        "than sepia ink; accidental shapes such as heart-shaped fingerprints. Reject only clear, "
        "obvious violations; cross-hatching, cables and circuit traces are intended. foco_x is "
        "the horizontal position (percent from the left) of the main subject."
    ),
}


def _parse_review(text: str) -> Optional[Dict[str, Any]]:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except ValueError:
        return None
    return data if isinstance(data, dict) and "ok" in data else None


async def review_image(image_jpeg: bytes, tecnica: str) -> Tuple[bool, str, Optional[float]]:
    """Revisión sí/no con el modelo ligero.

    Solo una respuesta legible con ok=false bloquea una candidata. Sin key, con
    error de la API o con una respuesta que no se puede leer (dos intentos), la
    revisión no bloquea: el control de color ya se aplicó y el motivo queda en
    el registro de intentos. Así un fallo del revisor no deja la edición sin imagen.
    """
    model = os.getenv("PIPELINE_LIGHT_MODEL", "claude-haiku-5-5")
    if not os.getenv("ANTHROPIC_API_KEY"):
        return True, "revisión visual omitida (sin ANTHROPIC_API_KEY)", None
    try:
        import anthropic
        client = anthropic.AsyncAnthropic()
        small = hp.resize_width(hp.to_image(hp.load_rgb(image_jpeg)), 1200)
        b64 = base64.b64encode(hp.jpeg_bytes(small, 85)).decode()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Revisión visual no disponible ({e}); no bloquea la imagen")
        return True, f"revisión visual no disponible ({type(e).__name__})", None

    last_text = ""
    for attempt in range(2):
        try:
            resp = await client.messages.create(
                model=model,
                # Holgado: si el modelo piensa antes de responder, el pensamiento
                # cuenta contra este tope y una respuesta corta se quedaba vacía.
                max_tokens=4000,
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                    {"type": "text", "text": REVIEW_PROMPT[tecnica]},
                ]}],
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Revisión visual falló ({e}); no bloquea la imagen")
            return True, f"revisión visual no disponible ({type(e).__name__})", None
        usage = {"input_tokens": resp.usage.input_tokens, "output_tokens": resp.usage.output_tokens}
        get_tracker().record_call(caller="hero.review", usage=usage, model=model, thinking_level="NONE")
        last_text = "".join(getattr(b, "text", "") or "" for b in resp.content
                            if getattr(b, "type", "") == "text")
        data = _parse_review(last_text)
        if data is not None:
            foco = data.get("foco_x")
            foco = float(foco) if isinstance(foco, (int, float)) and 0 <= foco <= 100 else None
            ok = data.get("ok")
            ok = ok if isinstance(ok, bool) else str(ok).strip().lower() in ("true", "sí", "si", "yes")
            reason = str(data.get("motivo") or ("sin observaciones" if ok else "rechazada sin motivo"))[:200]
            logger.info(f"Revisión visual ({tecnica}): {'ok' if ok else 'rechazada'} · {reason}")
            return ok, reason, foco
        logger.warning(f"Revisión visual ilegible (intento {attempt + 1}, stop={resp.stop_reason}): "
                       f"{last_text[:300]!r}")
    return True, "revisión visual ilegible; no bloquea", None


# --------------------------------------------------------------------------
# Generación con candidatas y respaldo
# --------------------------------------------------------------------------

@dataclass
class Attempt:
    tecnica: str
    via: str                     # "batch" o "directo"
    passed: bool
    reason: str
    cost_usd: Optional[float] = None


@dataclass
class HeroOutcome:
    image: bytes
    tecnica: str
    axes: Axes
    foco: str
    prompt: str
    attempts: List[Attempt] = field(default_factory=list)
    cost_usd: float = 0.0


def _cost(response: Any) -> Optional[float]:
    cost = price_image_usage(getattr(response, "usage", None))
    if not cost:
        return None
    factor = 0.5 if (response.usage or {}).get("batch") else 1.0
    return round(cost.total_cost * factor, 6)


async def _evaluate(response: Any, tecnica: str) -> Tuple[bool, str, Optional[float]]:
    a = hp.load_rgb(response.image_data)
    if tecnica == "mosaico":
        check = hp.color_check(a)
        if not check.ok:
            return False, check.reason(), None
    ok, reason, foco = await review_image(response.image_data, tecnica)
    return ok, reason or ("ok" if ok else "revisión visual"), foco


def _focus_from(axes: Axes, foco_x: Optional[float]) -> str:
    if foco_x is not None and axes.composicion not in ("sujeto a la izquierda", "sujeto a la derecha"):
        return f"{round(foco_x)}% 45%"
    return axes.foco


async def produce(client: Any, axes: Axes, sunday: bool,
                  keep_dir: Optional[Path] = None) -> Optional[HeroOutcome]:
    """Candidatas → control → respaldo. Nunca devuelve una imagen que no pasó.

    ``keep_dir``: carpeta donde se guarda cada candidata y el motivo de su
    resultado (va en el artefacto de diagnóstico, no se publica).
    """
    blocks = load_prompt_blocks()
    hp.configure(blocks.get("control"))
    refs = load_references()
    attempts: List[Attempt] = []
    total = 0.0

    async def accept(resp, tecnica, via, prompt) -> Optional[HeroOutcome]:
        nonlocal total
        cost = _cost(resp)
        total += cost or 0.0
        ok, reason, foco_x = await _evaluate(resp, tecnica)
        attempts.append(Attempt(tecnica, via, ok, reason, cost))
        if keep_dir is not None:
            try:
                keep_dir.mkdir(parents=True, exist_ok=True)
                n = len(attempts)
                name = f"candidata-{n}-{tecnica}-{'ok' if ok else 'rechazada'}.jpg"
                (keep_dir / name).write_bytes(hp.jpeg_bytes(hp.to_image(hp.load_rgb(resp.image_data)), 90))
                (keep_dir / "intentos.json").write_text(json.dumps(
                    {"ejes": axes.to_dict(), "intentos": [a.__dict__ for a in attempts]},
                    ensure_ascii=False, indent=1), encoding="utf-8")
            except Exception as e:  # noqa: BLE001
                logger.warning(f"No se pudo guardar la candidata: {e}")
        if ok:
            return HeroOutcome(resp.image_data, tecnica, axes, _focus_from(axes, foco_x), prompt, attempts, total)
        logger.info(f"Candidata descartada ({tecnica}, {via}): {reason}")
        return None

    if not sunday:
        prompt = mosaic_prompt(blocks, axes, with_refs=bool(refs))
        # 1) Dos candidatas en batch; si el batch falla o tarda, al momento.
        candidates: List[Tuple[Any, str]] = []
        if hasattr(client, "generate_batch"):
            try:
                results = await client.generate_batch([prompt, prompt], reference_images=refs,
                                                      max_wait_seconds=BATCH_WAIT_SECONDS)
                candidates = [(r, "batch") for r in results if r is not None]
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Batch de imágenes no disponible ({e}); se generan al momento")
        if not candidates:
            for _ in range(2):
                try:
                    candidates.append((await client.generate(prompt=prompt, reference_images=refs), "directo"))
                except Exception as e:  # noqa: BLE001
                    logger.warning(f"Candidata directa falló: {e}")
        for resp, via in candidates:
            outcome = await accept(resp, "mosaico", via, prompt)
            if outcome:
                return outcome
        # 2) Respaldo: un mosaico más (§6.4b).
        try:
            outcome = await accept(await client.generate(prompt=prompt, reference_images=refs),
                                   "mosaico", "directo", prompt)
            if outcome:
                return outcome
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Reintento de mosaico falló: {e}")

    # 3) Grabado con el mismo sujeto (domingo, o respaldo final).
    prompt = engraving_prompt(blocks, axes)
    try:
        outcome = await accept(await client.generate(prompt=prompt), "grabado", "directo", prompt)
        if outcome:
            return outcome
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Grabado falló: {e}")
    logger.error("Ninguna imagen pasó el control; la edición se publica sin imagen")
    return None


def publish(outcome: HeroOutcome, web_dir: Path, date: str) -> Dict[str, Any]:
    """Escribe las variantes y devuelve el bloque hero_image del summary."""
    light, dark, thumb = hp.build_variants(outcome.image, outcome.tecnica)
    out = web_dir / "data" / date
    out.mkdir(parents=True, exist_ok=True)
    (out / "hero-light.jpg").write_bytes(light)
    (out / "hero-dark.jpg").write_bytes(dark)
    (out / "hero-thumb.jpg").write_bytes(thumb)
    for legacy in ("hero.webp", "hero.png"):
        try:
            (out / legacy).unlink()
        except FileNotFoundError:
            pass
    return {
        "light_url": f"/data/{date}/hero-light.jpg",
        "dark_url": f"/data/{date}/hero-dark.jpg",
        "thumb_url": f"/data/{date}/hero-thumb.jpg",
        "focus": outcome.foco,
        "tecnica": outcome.tecnica,
        "motivo": outcome.axes.motivo,
        "alt": outcome.axes.alt,
        "modelo": MODEL_DISPLAY,
    }


def remember(date: str, outcome: HeroOutcome, path: Path = HISTORY_FILE) -> None:
    entries = [e for e in load_history(path) if e.get("fecha") != date]
    entries.append({
        "fecha": date,
        "registro": outcome.axes.registro,
        "motivo": outcome.axes.motivo,
        "escena": outcome.axes.escena,
        "composicion": outcome.axes.composicion,
        "estado": outcome.axes.estado,
        "tecnica": outcome.tecnica,
        "foco": outcome.foco,
    })
    save_history(entries, path)


async def generate_v32(client: Any, llm_client: Any, edition: Dict[str, Any], topics: List[Any],
                       date: str, web_dir: Path) -> Optional[Dict[str, Any]]:
    """Punto de entrada de la fase 4.7. Devuelve el resultado para el orquestador."""
    sunday = Date.fromisoformat(date).weekday() == 6
    history = load_history()
    axes, notice = await choose_axes(llm_client, edition, topics, history, date)
    logger.info(f"Imagen v3.2: {axes.registro} · {axes.motivo} · {axes.composicion} · {axes.estado}")
    keep_dir = ROOT / "data" / "checkpoints" / date / "hero"
    outcome = await produce(client, axes, sunday, keep_dir=keep_dir)
    if outcome is None:
        return None
    hero = publish(outcome, web_dir, date)
    remember(date, outcome)
    usage = {
        "cost_usd": round(outcome.cost_usd, 6),
        "model": getattr(client, "model", None),
        "intentos": [a.__dict__ for a in outcome.attempts],
    }
    return {
        "path": hero["light_url"],
        "prompt": outcome.prompt,
        "usage": usage,
        "hero_image": hero,
        "notice": notice,
    }
