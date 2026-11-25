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
    # 25 nov: nombres que llegaban crudos (dominio o título genérico del feed)
    "correctiv.org": "CORRECTIV", "lemonde.fr": "Le Monde", "teletica.com": "Teletica",
    "gestion.pe": "Diario Gestión", "df.cl": "Diario Financiero", "pymnts.com": "PYMNTS",
    "americanbanker.com": "American Banker", "cyberscoop.com": "CyberScoop",
    "cybersecuritydive.com": "Cybersecurity Dive", "scworld.com": "SC Media",
    "idtechwire.com": "ID Tech", "dplnews.com": "DPL News", "lanacion.com.ar": "La Nación",
    "eltiempo.com": "El Tiempo", "portafolio.co": "Portafolio", "eldiario.es": "elDiario.es",
    "elnacional.com.do": "El Nacional", "elnuevodiario.com.do": "El Nuevo Diario",
    "openid.net": "OpenID Foundation", "modelcontextprotocol.io": "Model Context Protocol",
    "ciberseguridadlatam.com": "CiberSeguridad Latam", "nist.gov": "NIST", "fidoalliance.org": "FIDO Alliance",
}
_HOST_RE = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+)+$")

_IETF = re.compile(r"^I-D list for (.+?)(?: RSS Feed)?$", re.I)
_IETF_GROUPS = {"web authorization protocol": "OAuth"}
_SUFFIX = re.compile(r"\s+[-–|]\s*(latest news|articles|all|feed|rss)$", re.I)


# Títulos de feed que no dicen qué medio es: se usa el dominio del enlace (25 nov:
# "Lo último" era El Economista; "All Feed", un feed de investigación).
GENERIC = {"lo último", "lo ultimo", "últimas noticias", "ultimas noticias", "noticias", "portada",
           "inicio", "home", "all feed", "all", "feed", "rss", "latest", "latest news", "news",
           "articles", "unknown", ""}
_PAGE_PREFIX = re.compile(r"^page\s+\d+\s*[-–|]\s*", re.I)


def display_source(name: str, url: str = "") -> str:
    """Nombre del medio para mostrar: limpia el título del feed y, si queda genérico o
    como un dominio pelón, lo saca del dominio del enlace."""
    from urllib.parse import urlparse

    cleaned = clean_source(_PAGE_PREFIX.sub("", (name or "").strip()))
    host = (urlparse(url or "").hostname or "").lower().removeprefix("www.")
    generic = cleaned.lower() in GENERIC or bool(_HOST_RE.match(cleaned.lower().removeprefix("www.")))
    if generic and host:
        for h in (host, ".".join(host.split(".")[-2:]), ".".join(host.split(".")[-3:])):
            if h in HOSTS:
                return HOSTS[h]
        if cleaned.lower() in GENERIC:
            return host
    return cleaned


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
