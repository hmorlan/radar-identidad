#!/usr/bin/env python3
"""Candado de publicación: una edición no se publica sin imagen.

Revisa que web/data/<fecha>/summary.json traiga ``hero_image`` y que existan sus
archivos (clara, oscura y miniatura). Si falta algo, termina con código 1 y el
workflow no sube la edición a R2 ni a Cloudflare Pages; la corrida queda en rojo
(GitHub manda correo) y la edición sigue en el artefacto para reanudar con
``--resume-from 4.7``.

Uso:
    python3 scripts/check_edition_image.py 2026-11-13 [--web-dir web]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List


def problems(date: str, web_dir: Path) -> List[str]:
    summary_path = web_dir / "data" / date / "summary.json"
    if not summary_path.is_file():
        return [f"no existe {summary_path}"]
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return [f"summary.json ilegible: {e}"]
    hero = summary.get("hero_image")
    if not isinstance(hero, dict) or not hero.get("light_url"):
        return ["la edición no tiene imagen (falta hero_image en summary.json)"]
    out = []
    for key in ("light_url", "dark_url", "thumb_url"):
        url = str(hero.get(key) or "")
        if not url:
            out.append(f"falta {key}")
            continue
        path = web_dir / url.split("?", 1)[0].lstrip("/")
        if not path.is_file() or path.stat().st_size == 0:
            out.append(f"{key} apunta a un archivo que no existe: {path}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("date")
    ap.add_argument("--web-dir", default="web")
    args = ap.parse_args()
    found = problems(args.date, Path(args.web_dir))
    if found:
        print(f"La edición {args.date} no se publica:")
        for p in found:
            print(f"  - {p}")
        print("Reanuda con --resume-from 4.7 cuando Gemini vuelva a responder.")
        return 1
    print(f"Imagen de la edición {args.date}: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
