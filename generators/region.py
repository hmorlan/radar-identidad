"""Notas de México, Latinoamérica y España: la audiencia del radar.

23, 25 y 27 nov: el resumen ejecutivo dejó fuera una nota de la región en las tres
ediciones (la revisión mecánica solo pedía una). Aquí vive la regla para reconocerlas
(la usan scripts/lint_edicion.py y el orquestador, que agrega al resumen la que falte).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List
from urllib.parse import urlparse

LATAM_TLD = {"mx", "es", "co", "ar", "cl", "pe", "cr", "gt", "do", "ec", "ve", "uy", "py", "bo",
             "pa", "hn", "sv", "ni", "cu", "pr", "br"}
LATAM_MEDIOS = {"ciberseguridad latam", "el economista", "diario gestión", "la nación", "dpl news",
                "el financiero", "expansión", "milenio", "el tiempo", "portafolio", "eldiario.es",
                "el país", "r3d", "derechos digitales", "teletica", "diario financiero", "iupana",
                "bloomberg línea"}
LATAM_PAISES = re.compile(r"\b(méxico|mexic|latinoam|españa|colombia|argentina|chile|perú|peru|costa rica|"
                          r"guatemala|ecuador|uruguay|paraguay|bolivia|venezuela|panamá|reniec|banxico|"
                          r"condusef|cnbv|inai|aepd|incibe|indecopi)\w*", re.I)


def is_latam(nota: Dict[str, Any]) -> bool:
    host = (urlparse(str(nota.get("url") or "")).hostname or "").lower()
    tld = host.rsplit(".", 1)[-1] if "." in host else ""
    text = " ".join(str(nota.get(k) or "") for k in ("title", "que_paso"))
    return (tld in LATAM_TLD or str(nota.get("source") or "").lower() in LATAM_MEDIOS
            or bool(LATAM_PAISES.search(text)))


_SECCION = re.compile(r"^#{2,4}\s*[^\n]*latinoam[^\n]*$", re.I | re.M)


def ensure_latam_in_summary(summary: str, notas: List[Dict[str, Any]], date: str) -> str:
    """Agrega al resumen una viñeta por cada nota de la región que no enlace. La viñeta
    usa solo el título y la fuente de la nota (ya verificada): no agrega hechos."""
    faltan = [n for n in notas if is_latam(n) and f"#item-{n.get('item_id')}" not in (summary or "")]
    if not faltan:
        return summary
    bullets = "\n".join(
        f"- Según {n.get('source') or 'la fuente'}: [{str(n.get('title') or '').strip()}]"
        f"(/?date={date}&category={n.get('category') or 'news'}#item-{n.get('item_id')})."
        for n in faltan)
    m = _SECCION.search(summary or "")
    if m:
        nxt = re.search(r"^#{2,4}\s", summary[m.end():], re.M)
        pos = m.end() + (nxt.start() if nxt else len(summary) - m.end())
        before = summary[:pos].rstrip("\n")
        return before + "\n" + bullets + "\n\n" + summary[pos:].lstrip("\n") if summary[pos:].strip() else before + "\n" + bullets + "\n"
    return (summary or "").rstrip("\n") + "\n\n#### Latinoamérica y España\n" + bullets + "\n"
