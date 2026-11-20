"""Nombres de fuente legibles para el sitio.

Muchos feeds traen títulos de canal como "Security News | TechCrunch",
"www.theregister.com - Articles" o "I-D list for Web Authorization Protocol RSS
Feed" (revisión de Hiram, 20 nov). Aquí se limpian para mostrarlos.
"""
from __future__ import annotations

import re

EXACT = {
    "security news | techcrunch": "TechCrunch",
    "www.theregister.com - articles": "The Register",
    "darkreading": "Dark Reading",
    "ai | the verge": "The Verge",
    "security latest": "WIRED",
    "es.wired.com": "WIRED en Español",
    "infosecurity-magazine.com": "Infosecurity Magazine",
    "scm feed for latest": "SC Media",
    "all cisa advisories": "CISA",
    "el tiempo.com -tecnología": "El Tiempo",
    "la nacion - tecnología": "La Nación",
    "portafolio.co -tecnología": "Portafolio",
    "eldiario.es - tecnología": "elDiario.es",
    "expansión - tecnología": "Expansión",
    "linux foundation - press releases": "Linux Foundation",
    "the record from recorded future news": "The Record",
}
_IETF = re.compile(r"^I-D list for (.+?)(?: RSS Feed)?$", re.I)
_IETF_GROUPS = {"web authorization protocol": "OAuth"}
_SUFFIX = re.compile(r"\s+[-–|]\s*(latest news|articles|all|feed|rss)$", re.I)


def clean_source(name: str) -> str:
    raw = (name or "").strip()
    if not raw:
        return raw
    hit = EXACT.get(raw.lower())
    if hit:
        return hit
    m = _IETF.match(raw)
    if m:
        group = m.group(1).strip()
        return f"IETF ({_IETF_GROUPS.get(group.lower(), group)})"
    return _SUFFIX.sub("", raw).strip() or raw
