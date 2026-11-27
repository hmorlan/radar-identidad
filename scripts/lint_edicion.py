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
from generators.region import is_latam as _is_latam  # noqa: E402

NOMBRES_OK = {v.lower() for v in HOSTS.values()} | {"pymnts.com", "eldiario.es"}

CATEGORIAS = ("news", "research", "social")
INGLES = re.compile(r"\b(yesterday|as first reported|also flagged|following yesterday|building on yesterday|"
                    r"continuing our coverage|according to)\b", re.I)
INTERNOS = re.compile(r"(la etiqueta (de la fuente|del origen)|conviene verificar la jurisdicci|este ciclo|"
                      r"solo tiene \*{0,2}\w+\*{0,2} candidatos|se descartaron|indicada en el t[ií]tulo|queda detr[aá]s de|"
                      r"el texto disponible solo contiene|empresa observada;|no guarda relaci[oó]n con el radar|"
                      r"\bnota sobre [A-ZÁÉÍÓÚ][^:]{2,60} \(empresa)", re.I)
TITULO_SUFIJO = re.compile(r"(\s[-–|•]\s[A-ZÁÉÍÓÚ][\w .-]{1,30}$|\(\d{1,2}:\d{2}\s*h\)\s*$)")
ENLACE = re.compile(r"/\?date=([0-9-]{10})&(?:amp;)?category=(\w+)#item-([0-9a-fA-F]+)")
FUENTE_CRUDA = re.compile(r"(^page \d+\s*[-–|]|\s-\s*articles$|^www\.|^[a-z0-9-]+(\.[a-z0-9-]+)+$|\.(mx|com|org|net)$|[.:;,]$)", re.I)
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
                    or ".freshness" in path \
                    or path.startswith("reparaciones"):
                continue  # el original en inglés y el registro de correcciones son legítimos
            if path.endswith(".source") or path == "source":
                low = value.strip().lower()
                if low not in NOMBRES_OK and (low in GENERIC or FUENTE_CRUDA.search(value.strip())):
                    add("fuente_cruda", f"{name}:{path}", value)
                continue
            if path.endswith(".author"):
                v = value.strip().lower()
                if v in ("unknown", "desconocido", "newsletter", "admin", "staff", "editor", "redacción") or (re.search(r"\S+@\S+\.\w+", v) and not v.startswith("@")):
                    add("autor_generico", f"{name}:{path}", value)
                continue
            if path.endswith(".title") and TITULO_SUFIJO.search(value):
                add("titulo_con_medio", f"{name}:{path}", value)
            if INGLES.search(value) and not path.endswith(("summary_en", "quote")):
                add("ingles", f"{name}:{path}", INGLES.search(value).group(0) + " … " + value[:120])
            m_int = INTERNOS.search(value)
            if m_int:
                add("comentario_interno", f"{name}:{path}", f"«{m_int.group(0)}» … {value[:120]}")

    notas = (summary.get("edition") or {}).get("notas") or []
    resumen = summary.get("executive_summary") or ""
    # 27 nov: cada nota de la región debe estar en el resumen (antes bastaba una).
    for n in notas:
        if _is_latam(n) and f"#item-{n.get('item_id')}" not in resumen:
            add("latam_fuera_del_resumen", "summary.json:executive_summary", str(n.get("title") or "")[:120])
    # 27 nov: enlaces internos a entradas que no se publicaron.
    ids = {cat: {str(it.get("id")) for it in (docs.get(f"{cat}.json") or {}).get("items") or []}
           for cat in CATEGORIAS if f"{cat}.json" in docs}
    fecha = day_dir.name
    for path, value in _texts(summary):
        for m in ENLACE.finditer(value):
            if m.group(1) == fecha and m.group(2) in ids and m.group(3) not in ids[m.group(2)]:
                add("enlace_roto", f"summary.json:{path}", m.group(0))
    for m in re.finditer(r"^#+\s*([^\n]*latinoam[^\n]*)$", resumen, re.I | re.M):
        start = m.end()
        nxt = re.search(r"^#+\s", resumen[start:], re.M)
        seccion = resumen[start:start + (nxt.start() if nxt else len(resumen))]
        if not LATAM_PAISES.search(seccion):
            add("seccion_latam_vacia", "summary.json:executive_summary", m.group(1))
    return found


# 27 nov (decisión de Hiram): estos tipos ya los corrige el código antes de
# publicar; si aparece uno es un bug y la edición no se publica hasta repararla.
# fuente_cruda no bloquea: un dominio sin nombre conocido (p. ej. ncsc.gov.uk) se
# muestra como dominio, que es legible aunque no ideal.
BLOQUEANTES = ("enlace_roto", "autor_generico")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--web-dir", default="web")
    ap.add_argument("--date", required=True)
    ap.add_argument("--out", default="")
    ap.add_argument("--github-output", default="", help="archivo $GITHUB_OUTPUT para escribir bloquea=true|false")
    args = ap.parse_args()
    day_dir = Path(args.web_dir) / "data" / args.date
    if not (day_dir / "summary.json").exists():
        print(f"No existe {day_dir}/summary.json", file=sys.stderr)
        return 1
    found = lint(day_dir)
    by_type: Dict[str, int] = {}
    for f in found:
        by_type[f["tipo"]] = by_type.get(f["tipo"], 0) + 1
    bloqueantes = {t: n for t, n in by_type.items() if t in BLOQUEANTES}
    report = {"date": args.date, "total": len(found), "por_tipo": by_type,
              "bloqueantes": bloqueantes, "hallazgos": found}
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Revisión mecánica {args.date}: {len(found)} hallazgos {by_type}")
    if bloqueantes:
        print(f"BLOQUEA la publicación: {bloqueantes}")
    if args.github_output:
        with open(args.github_output, "a", encoding="utf-8") as fh:
            fh.write(f"bloquea={'true' if bloqueantes else 'false'}\n")
    for f in found[:60]:
        print(f"  [{f['tipo']}] {f['donde']}: {f['texto']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
