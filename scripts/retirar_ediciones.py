#!/usr/bin/env python3
"""Retira del sitio las ediciones de config/ediciones_retiradas.txt (sin costo).

Quita cada fecha de ``web/data``: su carpeta, su entrada en ``index.json`` y en el
manifiesto del archivo (``.archivo.json``, para que ``archive_r2.py`` no la vuelva
a restaurar), y regenera feeds y búsqueda. El objeto en R2 se conserva como
respaldo privado. Idempotente: una fecha ya retirada no cambia nada.

Uso:
    python3 scripts/retirar_ediciones.py --web-dir ./web [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
LISTA = ROOT / "config" / "ediciones_retiradas.txt"
DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def retiradas(path: Path = LISTA) -> list[str]:
    if not path.exists():
        return []
    return [l.strip() for l in path.read_text(encoding="utf-8").splitlines()
            if DAY_RE.match(l.strip())]


def retirar(data: Path, fechas: list[str], dry_run: bool = False) -> list[str]:
    hechos = []
    index_path, manifest_path = data / "index.json", data / ".archivo.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None
    for fecha in fechas:
        if (data / fecha).is_dir():
            hechos.append(f"{fecha}: carpeta")
            if not dry_run:
                shutil.rmtree(data / fecha)
        if index and any(d.get("date") == fecha for d in index.get("dates", [])):
            index["dates"] = [d for d in index["dates"] if d.get("date") != fecha]
            hechos.append(f"{fecha}: índice")
        if manifest and fecha in manifest.get("dias", []):
            manifest["dias"] = [d for d in manifest["dias"] if d != fecha]
            hechos.append(f"{fecha}: manifiesto de R2")
    if index is not None:
        index["latestDate"] = index["dates"][0]["date"] if index.get("dates") else None
        index["totalDates"] = len(index.get("dates", []))
    if hechos and not dry_run:
        if index is not None:
            index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if manifest is not None:
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return hechos


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--web-dir", type=Path, default=ROOT / "web")
    ap.add_argument("--base-url", default="https://radar.hirammorlan.com")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    fechas = retiradas()
    hechos = retirar(args.web_dir / "data", fechas, args.dry_run)
    for h in hechos:
        print("Retirada", h)
    if not hechos:
        print(f"Nada que retirar ({', '.join(fechas) or 'lista vacía'}).")
    elif not args.dry_run:
        from scripts.repair_edition import rebuild_indexes
        rebuild_indexes(args.web_dir, args.base_url)
        print("Feeds y corpus de búsqueda regenerados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
