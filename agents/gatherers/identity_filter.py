"""Filtro previo de identidad para fuentes ruidosas (directiva ``filtro=identidad``).

Algunas fuentes publican mucho y casi nada de identidad: boletines de
vulnerabilidades (CERT-FR), secciones generalistas de tecnología o finanzas. Para
no gastar triage en ellas, sus entradas solo pasan si el título o el resumen
mencionan algo de identidad, credenciales, fraude o agentes. Está pensado para no
perder notas (prefiere dejar pasar de más): el triage con Haiku decide después.

Cubre español, inglés y francés.
"""
from __future__ import annotations

import re

_TERMS = [
    # Identidad y autenticación. En español, "identidad", "sesión" y "verificación"
    # solas son ambiguas en notas de política o finanzas; por eso van con contexto.
    r"identity", r"identities", r"identité", r"identidad digital", r"robo de identidad",
    r"usurpaci[oó]n de identidad", r"suplantaci[oó]n de identidad", r"identidad (?:electr|biom|oficial)",
    r"identificaci[oó]n (?:digital|oficial|biom|electr)", r"identifiant",
    r"authent", r"autentic", r"authentif",
    r"credential", r"credencial", r"password", r"contraseñ", r"mot de passe",
    r"passkey", r"\bmfa\b", r"\b2fa\b", r"multi-?fact", r"multifactor", r"doble factor",
    r"\boauth", r"openid", r"\bsso\b", r"single sign", r"inicio de sesi[oó]n", r"\blog-?in\b",
    r"session hijack", r"session token", r"secuestro de sesi", r"cookies? de sesi", r"cookies? de session",
    r"\btokens?\b", r"jeton", r"active directory", r"kerberos",
    r"privileged access", r"privilege escalation", r"escalada de privilegios",
    r"acceso privilegiado", r"élévation de privil", r"control de acceso", r"access control", r"contr[oô]le d.acc[eè]s",
    r"acceso no autorizado", r"unauthori[sz]ed access", r"acc[eè]s non autoris", r"account takeover",
    r"toma de cuentas?", r"robo de cuentas?", r"cuentas? (?:hackead|robad|comprometid)",
    # Suplantación y fraude
    r"phishing", r"smishing", r"vishing", r"hame[cç]onnage", r"suplant", r"usurpa", r"impersonat",
    r"spoof", r"deepfake", r"ultrafalso", r"voz clonada", r"clonaci[oó]n de voz", r"voice clon",
    r"fraud", r"estafa", r"arnaque", r"\bscams?\b", r"robo de datos", r"filtraci[oó]n de datos",
    r"data breach", r"\bbreach", r"fuite de donn", r"brecha de (?:datos|seguridad)",
    r"(?:datos|información) (?:filtrad|expuest|robad)", r"se filtraron", r"ciberataque", r"hackeo",
    # Verificación, regulación e identidad digital
    r"verifiable credential", r"credenciales? verificables?", r"decentrali[sz]ed identi",
    r"identificador(?:es)? descentralizado", r"\bkyc\b", r"biometr", r"reconocimiento facial", r"facial recogn", r"reconnaissance faciale",
    r"verificaci[oó]n de (?:identidad|edad)", r"identity verification", r"age verification",
    r"v[ée]rification d.(?:identit|[aâ]ge)", r"eidas", r"\beudi\b", r"digital id\b", r"\bid digital", r"digital driver.?s licen[cs]e",
    r"licencia (?:de conducir )?digital", r"digital wallet", r"identity wallet",
    r"cartera digital", r"\bcurp\b", r"firma electr", r"signature [ée]lectronique",
    r"protecci[oó]n de datos", r"datos personales", r"privacy", r"\bgdpr\b", r"\brgpd\b",
    # Agentes de IA que actúan en nuestro nombre
    r"agentes? de (?:ia|inteligencia artificial)", r"\bagentes?\b.{0,60}\b(?:ia|inteligencia artificial)\b", r"\bai agents?\b", r"\bagentic", r"\bmcp\b",
    r"agent d.ia", r"agents? ia\b", r"agent name service", r"agent identity", r"identidad de (?:los )?agentes",
]
_RE = re.compile("|".join(_TERMS), re.IGNORECASE)

FILTERS = {"identidad", "titulo"}


def matches(text: str) -> bool:
    """True si el texto toca algo de identidad (criterio amplio)."""
    return bool(text) and bool(_RE.search(text))


def matches_feed_entry(filtro: str, title: str, content: str = "") -> bool:
    """Aplica la directiva de un feed.

    - ``identidad``: título y resumen (primeros 1500 caracteres).
    - ``titulo``: solo el título. Para boletines como los de CERT-FR, cuya
      descripción siempre lista impactos genéricos ("usurpation", "élévation de
      privilèges") aunque el aviso no tenga nada de identidad.
    """
    if filtro == "titulo":
        return matches(title)
    return matches(f"{title} {(content or '')[:1500]}")


# Contenido patrocinado que algunos medios (The Hacker News, SC Media) publican en su
# feed de noticias: webinars, "expert insights" y notas pagadas. No es cobertura.
_SPONSORED_RE = re.compile(
    r"^\s*(?:\[?(?:webinar|sponsored|patrocinado|expert insights?|partner content)\]?\s*[:|\-–]|"
    r"\[?(?:webinar|sponsored)\])",
    re.IGNORECASE,
)


def is_sponsored(title: str) -> bool:
    return bool(_SPONSORED_RE.search(title or ""))


# 27 nov (política B de proveedores, config/proveedores.txt): fuera de las listas lo
# que publica un proveedor de identidad, fraude o verificación (por dominio) y las
# tribunas que firma la empresa (autor = nombre del proveedor).
_PROVEEDORES = None


def _load_proveedores():
    global _PROVEEDORES
    if _PROVEEDORES is not None:
        return _PROVEEDORES
    import os
    from pathlib import Path
    path = Path(os.getenv("PROVEEDORES_CONFIG") or Path(__file__).resolve().parents[2] / "config" / "proveedores.txt")
    dominios, nombres, seccion = set(), set(), ""
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            if line.startswith("[") and line.endswith("]"):
                seccion = line[1:-1].strip().lower()
                continue
            if seccion != "identidad" or "|" not in line:
                continue
            dom, names = (x.strip() for x in line.split("|", 1))
            dominios.add(dom.lower().removeprefix("www."))
            nombres.update(n.strip().lower() for n in names.split(",") if n.strip())
    except OSError:
        pass
    _PROVEEDORES = (dominios, nombres)
    return _PROVEEDORES


def is_identity_vendor(url: str = "", author: str = "") -> bool:
    """True si el enlace es de un proveedor de identidad/fraude/verificación o si la
    entrada la firma uno de ellos."""
    from urllib.parse import urlparse
    dominios, nombres = _load_proveedores()
    host = (urlparse(url or "").hostname or "").lower().removeprefix("www.")
    if host and any(host == d or host.endswith("." + d) for d in dominios):
        return True
    a = (author or "").strip().lower()
    return bool(a) and a in nombres
