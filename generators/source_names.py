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
    "payments dive - latest news": "Payments Dive",
    "arxiv (cryptography and security)": "arXiv (criptografía y seguridad)",
}
# Dominios de artículos que llegan desde redes (Bluesky, Hacker News): la nota
# enlaza al original y muestra el nombre del medio, no el dominio.
HOSTS = {
    "theregister.com": "The Register", "techcrunch.com": "TechCrunch",
    "bleepingcomputer.com": "BleepingComputer", "thehackernews.com": "The Hacker News",
    "darkreading.com": "Dark Reading", "wired.com": "WIRED", "es.wired.com": "WIRED en Español",
    "therecord.media": "The Record", "krebsonsecurity.com": "Krebs on Security",
    "arstechnica.com": "Ars Technica", "theverge.com": "The Verge", "404media.co": "404 Media",
    "csoonline.com": "CSO Online", "securityweek.com": "SecurityWeek",
    "biometricupdate.com": "Biometric Update", "helpnetsecurity.com": "Help Net Security",
    "infosecurity-magazine.com": "Infosecurity Magazine", "reuters.com": "Reuters",
    "bloomberg.com": "Bloomberg", "nytimes.com": "The New York Times",
    "washingtonpost.com": "The Washington Post", "theguardian.com": "The Guardian",
    "ft.com": "Financial Times", "wsj.com": "The Wall Street Journal", "bbc.com": "BBC",
    "elpais.com": "El País", "elfinanciero.com.mx": "El Financiero",
    "eleconomista.com.mx": "El Economista", "expansion.mx": "Expansión", "milenio.com": "Milenio",
    "eff.org": "EFF", "derechosdigitales.org": "Derechos Digitales", "r3d.mx": "R3D",
    "arxiv.org": "arXiv", "github.com": "GitHub", "datatracker.ietf.org": "IETF",
}
_HOST_RE = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+)+$")

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
    host = raw.lower().removeprefix("www.")
    if _HOST_RE.match(host) and host in HOSTS:
        return HOSTS[host]
    m = _IETF.match(raw)
    if m:
        group = m.group(1).strip()
        return f"IETF ({_IETF_GROUPS.get(group.lower(), group)})"
    return _SUFFIX.sub("", raw).strip() or raw
