"""Temas de categoría sin duplicados (25 nov, revisión de Instinct).

El análisis por lotes devuelve temas por lote y se juntaban tal cual: el 25 nov
Noticias tenía "Agentes de IA con accesos delegados" (10) y "Agentes de IA con
acceso delegado" (7), "Robo de credenciales y SSO" y "Robo de credenciales y
secretos", y un tema de una sola nota. Aquí se funden los que comparten la mitad
o más de sus palabras de contenido (singular y plural cuentan igual) y se quitan
los de una sola nota cuando quedan al menos tres temas.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List

_STOP = {"de", "del", "la", "las", "el", "los", "y", "e", "o", "u", "en", "con", "contra", "para",
         "por", "a", "al", "sus", "su", "un", "una", "the", "and", "of"}


def _tokens(name: str) -> set:
    t = "".join(c for c in unicodedata.normalize("NFD", (name or "").lower()) if unicodedata.category(c) != "Mn")
    out = set()
    for w in re.findall(r"[a-z0-9]+", t):
        if w in _STOP or len(w) < 2:
            continue
        if len(w) > 4 and w.endswith("es") and not w.endswith("ies"):
            w = w[:-2]
        elif len(w) > 3 and w.endswith("s"):
            w = w[:-1]
        out.add(w)
    return out


def _similar(a: set, b: set) -> bool:
    return bool(a and b) and len(a & b) / len(a | b) >= 0.5


def merge_themes(themes: List[Any]) -> List[Any]:
    merged: List[Dict[str, Any]] = []
    keys: List[set] = []
    passthrough: List[Any] = []
    for t in themes or []:
        if not isinstance(t, dict) or not t.get("name"):
            passthrough.append(t)
            continue
        tok = _tokens(t["name"])
        for i, k in enumerate(keys):
            if _similar(tok, k):
                m = merged[i]
                big = t if (t.get("item_count") or 0) > (m.get("item_count") or 0) else m
                m.update({
                    "name": big["name"],
                    "description": big.get("description", m.get("description")),
                    "item_count": (m.get("item_count") or 0) + (t.get("item_count") or 0),
                    "importance": max(m.get("importance") or 0, t.get("importance") or 0),
                    "example_items": (m.get("example_items") or []) + [
                        x for x in (t.get("example_items") or []) if x not in (m.get("example_items") or [])],
                })
                keys[i] = k | tok
                break
        else:
            merged.append(dict(t))
            keys.append(tok)
    if len([m for m in merged if (m.get("item_count") or 0) > 1]) >= 3:
        merged = [m for m in merged if (m.get("item_count") or 0) > 1]
    merged.sort(key=lambda m: (-(m.get("item_count") or 0), -(m.get("importance") or 0)))
    return merged + [p for p in passthrough if p]
