#!/usr/bin/env python3
"""Reparar a mano el texto de una edición ya publicada, sin volver a correr el pipeline.

Aplica un parche JSON (``config/reparaciones/AAAA-MM-DD.json``) sobre
``web/data/<fecha>/*.json``:

- ``reemplazos``: pares ``antes``/``despues`` exactos que se aplican en cualquier
  texto de los JSON de la fecha (resúmenes, temas, notas, razonamiento). Cada
  reemplazo tiene que encontrar su texto al menos una vez, salvo que el mismo
  parche ya esté registrado en ``reparaciones`` (el script es idempotente).
- ``notas``: campos de una nota de la edición, por ``item_id``, que se reemplazan
  completos (``titulo``, ``que_paso``, ``por_que_importa``, ``pregunta_de_fondo``,
  ``senal``, ``verificacion``).

Después vuelve a generar los campos ``*_html`` que cambiaron, los feeds Atom y el
corpus de búsqueda (si no, el feed y el buscador seguirían con el texto viejo), y
deja constancia en ``summary.json`` → ``reparaciones``.

No llama a ninguna API ni tiene costo. Publicar el resultado (R2 y Cloudflare
Pages) lo hace el workflow manual "Reparar edición".

Uso:
    python3 scripts/repair_edition.py config/reparaciones/2026-11-17.json --web-dir ./web
    python3 scripts/repair_edition.py ... --dry-run     # solo informa
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

NOTE_FIELDS = {"titulo": "title", "title": "title", "que_paso": "que_paso",
               "por_que_importa": "por_que_importa", "pregunta_de_fondo": "pregunta_de_fondo",
               "senal": "senal", "verificacion": "verificacion",
               # 20 nov: enlace faltante (IETF), original en vez del post (Bluesky) y
               # fecha de envío del preprint (arXiv).
               "url": "url", "source": "source", "published": "published", "via": "via",
               "fecha_tipo": "fecha_tipo"}
SIGNALS = {"baja", "media", "alta"}
_MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


class RepairError(Exception):
    pass


def _walk_replace(node: Any, antes: str, despues: str, changed: List[Tuple[dict, str]]) -> Tuple[Any, int]:
    """Replace ``antes`` in every string leaf; record which (dict, key) changed."""
    count = 0
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, str) and antes in v:
                count += v.count(antes)
                node[k] = v.replace(antes, despues)
                changed.append((node, k))
            elif isinstance(v, (dict, list)):
                _, c = _walk_replace(v, antes, despues, changed)
                count += c
    elif isinstance(node, list):
        for i, v in enumerate(node):
            if isinstance(v, str) and antes in v:
                count += v.count(antes)
                node[i] = v.replace(antes, despues)
            elif isinstance(v, (dict, list)):
                _, c = _walk_replace(v, antes, despues, changed)
                count += c
    return node, count


def _contains(node: Any, text: str) -> bool:
    return text in json.dumps(node, ensure_ascii=False)


def _rerender(changed: List[Tuple[dict, str]]) -> int:
    """Rebuild ``<campo>_html`` from ``<campo>`` for every markdown field that changed."""
    from generators.json_generator import JSONGenerator

    gen = JSONGenerator.__new__(JSONGenerator)  # solo usamos los conversores, sin E/S
    n = 0
    seen = set()
    for d, key in changed:
        if (id(d), key) in seen or key.endswith("_html") or f"{key}_html" not in d:
            continue
        seen.add((id(d), key))
        if key == "description":
            # Igual que orchestrator._markdown_links_to_html + la limpieza de json_generator.
            html = _MD_LINK.sub(r'<a href="\2" target="_blank">\1</a>', d[key])
            d[f"{key}_html"] = gen._sanitize_html(html)
        else:
            d[f"{key}_html"] = gen._markdown_to_html(d[key])
        n += 1
    return n


def apply_patch(patch: Dict[str, Any], day_dir: Path, dry_run: bool = False) -> Dict[str, Any]:
    files = {p.name: json.loads(p.read_text(encoding="utf-8")) for p in sorted(day_dir.glob("*.json"))}
    if "summary.json" not in files:
        raise RepairError(f"no existe {day_dir / 'summary.json'}")
    report: Dict[str, Any] = {"reemplazos": [], "notas": [], "html": 0}
    changed: List[Tuple[dict, str]] = []
    # Un parche ya aplicado puede volver a correr sin error, también cuando se amplía
    # (20 nov: segunda revisión del mismo día): si la edición ya tiene reparaciones,
    # un reemplazo cuyo texto nuevo ya está se da por aplicado.
    already = any(isinstance(r, dict) for r in files["summary.json"].get("reparaciones") or [])

    for r in patch.get("reemplazos") or []:
        antes, despues = r.get("antes", ""), r.get("despues", "")
        if not antes or antes == despues:
            raise RepairError(f"reemplazo inválido: {r!r}")
        targets = r.get("archivos") or list(files)
        total = 0
        for name in targets:
            if name not in files:
                raise RepairError(f"{name} no existe en {day_dir}")
            _, c = _walk_replace(files[name], antes, despues, changed)
            total += c
        if total == 0:
            if already and any(_contains(files[n], despues) for n in targets):
                report["reemplazos"].append({"antes": antes[:60], "estado": "ya aplicado"})
                continue
            raise RepairError(f"no se encontró el texto a reemplazar: {antes[:80]!r}")
        report["reemplazos"].append({"antes": antes[:60], "veces": total})

    notas = ((files["summary.json"].get("edition") or {}).get("notas")) or []
    by_id = {n.get("item_id"): n for n in notas if isinstance(n, dict)}
    for item_id, fields in (patch.get("notas") or {}).items():
        note = by_id.get(item_id)
        if note is None:
            raise RepairError(f"la edición no tiene la nota {item_id}")
        for k, v in fields.items():
            target = NOTE_FIELDS.get(k)
            if target is None:
                raise RepairError(f"campo de nota no permitido: {k}")
            if target == "senal" and v not in SIGNALS:
                raise RepairError(f"señal inválida: {v}")
            if target == "url" and not str(v).startswith(("https://", "http://")):
                raise RepairError(f"url inválida: {v}")
            if target == "via" and v is not None and not (
                    isinstance(v, dict) and str(v.get("url", "")).startswith(("https://", "http://"))):
                raise RepairError(f"vía inválida: {v}")
            if note.get(target) != v:
                note[target] = v
                report["notas"].append(f"{item_id}.{target}")

    report["html"] = _rerender(changed)

    if not report["notas"] and not any("veces" in r for r in report["reemplazos"]):
        report["sin_cambios"] = True
        return report

    summary = files["summary.json"]
    summary.setdefault("reparaciones", []).append({
        "fecha": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "motivo": patch.get("motivo", ""),
    })
    if not dry_run:
        for name, data in files.items():
            (day_dir / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8")
    return report


def rebuild_indexes(web_dir: Path, base_url: str) -> None:
    from generators.feed_generator import FeedGenerator
    from generators.search_indexer import SearchIndexer

    FeedGenerator(str(web_dir), rolling_window_days=7, base_url=base_url).generate_feeds()
    SearchIndexer(str(web_dir), rolling_window_days=30).update_index()


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("patch", type=Path)
    ap.add_argument("--web-dir", type=Path, default=ROOT / "web")
    ap.add_argument("--base-url", default="https://radar.hirammorlan.com")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-indexes", action="store_true", help="no regenerar feeds ni búsqueda")
    args = ap.parse_args(argv)

    patch = json.loads(args.patch.read_text(encoding="utf-8"))
    date = patch.get("date", "")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        print(f"fecha inválida en el parche: {date!r}", file=sys.stderr)
        return 2
    day_dir = args.web_dir / "data" / date
    try:
        report = apply_patch(patch, day_dir, dry_run=args.dry_run)
    except RepairError as e:
        print(f"Reparación cancelada: {e}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=1))
    if not args.dry_run and not args.no_indexes and not report.get("sin_cambios"):
        rebuild_indexes(args.web_dir, args.base_url)
        print("Feeds y corpus de búsqueda regenerados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
