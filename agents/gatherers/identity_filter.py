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
    r"data breach", r"fuite de donn",
    # Verificación, regulación e identidad digital
    r"\bkyc\b", r"biometr", r"reconocimiento facial", r"facial recogn", r"reconnaissance faciale",
    r"verificaci[oó]n de (?:identidad|edad)", r"identity verification", r"age verification",
    r"v[ée]rification d.(?:identit|[aâ]ge)", r"eidas", r"digital wallet", r"identity wallet",
    r"cartera digital", r"\bcurp\b", r"firma electr", r"signature [ée]lectronique",
    r"protecci[oó]n de datos", r"datos personales", r"privacy", r"\bgdpr\b", r"\brgpd\b",
    # Agentes de IA que actúan en nuestro nombre
    r"agentes? de (?:ia|inteligencia artificial)", r"\bagentes?\b.{0,60}\b(?:ia|inteligencia artificial)\b", r"\bai agents?\b", r"\bagentic", r"\bmcp\b",
    r"agent d.ia", r"agents? ia\b",
]
_RE = re.compile("|".join(_TERMS), re.IGNORECASE)

FILTERS = {"identidad"}


def matches(text: str) -> bool:
    """True si el texto toca algo de identidad (criterio amplio)."""
    return bool(text) and bool(_RE.search(text))
