#!/usr/bin/env python3
"""Revisión mecánica de la edición antes de publicar (sin IA, sin costo).

25 nov: 16 de las 34 correcciones de la edición fueron mecánicas (nombres de fuente
crudos, autor "Unknown", frases en inglés, comentarios internos, país mal
etiquetado). Ese tipo de error no debería llegar al revisor editorial. Este script
recorre lo que se va a publicar y lista cada caso; la corrida lo sube como artefacto
`lint` y la revisión técnica lo cuenta. No modifica nada ni bloquea la publicación:
el arreglo va en el código que lo produjo.

Uso:
    python3 scripts/lint_edicion.py --web-dir web --date 2026-11-27 [--out lint/lint.json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from generators.source_names import GENERIC, HOSTS  # noqa: E402

NOMBRES_OK = {v.lower() for v in HOSTS.values()} | {"pymnts.com", "eldiario.es"}

CATEGORIAS = ("news", "research", "social")
INGLES = re.compile(r"\b(yesterday|as first reported|also flagged|following yesterday|building on yesterday|"
                    r"continuing our coverage|according to)\b", re.I)
INTERNOS = re.compile(r"(la etiqueta (de la fuente|del origen)|conviene verificar la jurisdicci|"
                      r"el texto disponible solo contiene|empresa observada;|no guarda relaci[oó]n con el radar|"
                      r"\bnota sobre [A-ZÁÉÍÓÚ][^:]{2,60} \(empresa)", re.I)
FUENTE_CRUDA = re.compile(r"(^page \d+\s*[-–|]|\s-\s*articles$|^www\.|^[a-z0-9-]+(\.[a-z0-9-]+)+$)", re.I)
LATAM_TLD = {"mx", "es", "co", "ar", "cl", "pe", "cr", "gt", "do", "ec", "ve", "uy", "py", "bo",
             "pa", "hn", "sv", "ni", "cu", "pr", "br"}
LATAM_MEDIOS = {"ciberseguridad latam", "el economista", "diario gestión", "la nación", "dpl news",
                "el financiero", "expansión", "milenio", "el tiempo", "portafolio", "eldiario.es",
                "el país", "r3d", "derechos digitales", "teletica", "diario financiero", "iupana"}
LATAM_PAISES = re.compile(r"\b(méxico|mexic|latinoam|españa|colombia|argentina|chile|perú|peru|costa rica|"
                          r"guatemala|ecuador|uruguay|paraguay|bolivia|venezuela|panamá|reniec|banxico|"
                          r"condusef|cnbv|inai|aepd|incibe)\w*", re.I)


def _texts(obj: Any, path: str = "") -> Iterable[Tuple[str, str]]:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.endswith("_html") or k in ("url", "id", "item_id", "link", "image", "hero"):
                continue
            yield from _texts(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _texts(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, obj


def _is_latam(nota: Dict[str, Any]) -> bool:
    host = (urlparse(nota.get("url") or "").hostname or "").lower()
    tld = host.rsplit(".", 1)[-1] if "." in host else ""
    text = " ".join(str(nota.get(k) or "") for k in ("title", "que_paso"))
    return tld in LATAM_TLD or str(nota.get("source") or "").lower() in LATAM_MEDIOS or bool(LATAM_PAISES.search(text))


def lint(day_dir: Path) -> List[Dict[str, str]]:
    found: List[Dict[str, str]] = []

    def add(tipo: str, donde: str, texto: str) -> None:
        found.append({"tipo": tipo, "donde": donde, "texto": texto[:200]})

    summary = json.loads((day_dir / "summary.json").read_text(encoding="utf-8"))
    docs = {"summary.json": summary}
    for cat in CATEGORIAS:
        f = day_dir / f"{cat}.json"
        if f.exists():
            docs[f"{cat}.json"] = json.loads(f.read_text(encoding="utf-8"))

    for name, doc in docs.items():
        for path, value in _texts(doc):
            if path.endswith(("title_original", "content", "original_title", "reference_text")) \
                    or ".reparaciones" in path \
                    or path.startswith("reparaciones"):
                continue  # el original en inglés y el registro de correcciones son legítimos
            if path.endswith(".source") or path == "source":
                low = value.strip().lower()
                if low not in NOMBRES_OK and (low in GENERIC or FUENTE_CRUDA.search(value.strip())):
                    add("fuente_cruda", f"{name}:{path}", value)
                continue
            if path.endswith(".author"):
                if value.strip().lower() in ("unknown", "desconocido"):
                    add("autor_generico", f"{name}:{path}", value)
                continue
            if INGLES.search(value) and not path.endswith(("summary_en", "quote")):
                add("ingles", f"{name}:{path}", INGLES.search(value).group(0) + " … " + value[:120])
            if INTERNOS.search(value):
                add("comentario_interno", f"{name}:{path}", value[:160])

    notas = (summary.get("edition") or {}).get("notas") or []
    resumen = summary.get("executive_summary") or ""
    latam = [n for n in notas if _is_latam(n)]
    if latam and not any((f"#item-{n.get('item_id')}" in resumen) or (str(n.get("title") or "")[:40] and
                         str(n.get("title"))[:40] in resumen) for n in latam):
        add("latam_fuera_del_resumen", "summary.json:executive_summary",
            "; ".join(str(n.get("title") or "")[:80] for n in latam))
    for m in re.finditer(r"^#+\s*([^\n]*latinoam[^\n]*)$", resumen, re.I | re.M):
        start = m.end()
        nxt = re.search(r"^#+\s", resumen[start:], re.M)
        seccion = resumen[start:start + (nxt.start() if nxt else len(resumen))]
        if not LATAM_PAISES.search(seccion):
            add("seccion_latam_vacia", "summary.json:executive_summary", m.group(1))
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--web-dir", default="web")
    ap.add_argument("--date", required=True)
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    day_dir = Path(args.web_dir) / "data" / args.date
    if not (day_dir / "summary.json").exists():
        print(f"No existe {day_dir}/summary.json", file=sys.stderr)
        return 1
    found = lint(day_dir)
    by_type: Dict[str, int] = {}
    for f in found:
        by_type[f["tipo"]] = by_type.get(f["tipo"], 0) + 1
    report = {"date": args.date, "total": len(found), "por_tipo": by_type, "hallazgos": found}
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Revisión mecánica {args.date}: {len(found)} hallazgos {by_type}")
    for f in found[:60]:
        print(f"  [{f['tipo']}] {f['donde']}: {f['texto']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
