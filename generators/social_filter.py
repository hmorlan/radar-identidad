"""Qué publicaciones de Redes se publican (23 nov, revisión de Instinct, P1).

El análisis de Redes puntúa todo lo que traen las cuentas, y el 23 nov se
publicaron 28 entradas aunque 7 decían de sí mismas "No guarda relación con el
radar" (águilas que cazan babuinos, GTA VI, una vacante con puntaje 1) y una era
solo una URL cortada ("papoi www.404media.co/scientists-m...").

Se deja fuera de social.json (y de summary.json) la entrada que:
- el análisis marca con un tema "ajeno" (el prompt pide "Ajeno al radar"),
- puntúa por debajo de SOCIAL_MIN_SCORE (40 por defecto desde el 25 nov: en la escala
  del prompt, 20-39 es "tema solo cercano" sin ángulo de identidad), o
- no tiene texto propio: menos de 3 palabras una vez quitadas las URL.

El análisis no cambia ni se borra: sigue en los checkpoints y en el replay.
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, Iterable, List

DEFAULT_MIN_SCORE = 40.0  # 25 nov: con 20 pasaban perfilado publicitario y vigilancia sin ángulo de identidad
_URLISH = re.compile(r"(https?://\S+|www\.\S+|\S+\.(com|org|net|co|io|ai|social|app|news)(/\S*)?)", re.I)
_WORD = re.compile(r"[^\W\d_]{2,}", re.UNICODE)


def min_score() -> float:
    try:
        return float(os.getenv("SOCIAL_MIN_SCORE") or DEFAULT_MIN_SCORE)
    except ValueError:
        return DEFAULT_MIN_SCORE


def _is_ajeno(label: Any) -> bool:
    return isinstance(label, str) and "ajen" in label.lower()


def _own_words(item: Dict[str, Any]) -> int:
    text = item.get("title_original") or item.get("title") or ""
    text = _URLISH.sub(" ", str(text)).replace("...", " ").replace("…", " ")
    return len(_WORD.findall(text))


def reason_to_drop(item: Dict[str, Any], threshold: float | None = None) -> str:
    """'' si la entrada se publica; si no, el motivo."""
    threshold = min_score() if threshold is None else threshold
    if any(_is_ajeno(t) for t in (item.get("themes") or [])):
        return "ajeno"
    score = item.get("importance_score")
    if isinstance(score, (int, float)) and score < threshold:
        return "puntaje"
    if _own_words(item) < 3:
        return "sin_texto"
    return ""


def publishable(items: Iterable[Dict[str, Any]], threshold: float | None = None) -> List[Dict[str, Any]]:
    return [it for it in items if isinstance(it, dict) and not reason_to_drop(it, threshold)]


def publishable_themes(themes: Iterable[Any]) -> List[Any]:
    return [t for t in (themes or []) if not (isinstance(t, dict) and _is_ajeno(t.get("name")))]
