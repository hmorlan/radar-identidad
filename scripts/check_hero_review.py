#!/usr/bin/env python3
"""Prueba la revisión visual de la imagen (Haiku) con las referencias aprobadas.

Las dos referencias de assets/hero-ref/ deberían pasar. Imprime la respuesta del
modelo para ver qué contesta. Costo: menos de US$0.01.

Uso:
    ANTHROPIC_API_KEY=... python3 scripts/check_hero_review.py
"""
import asyncio
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from generators import hero_v32 as hv  # noqa: E402


async def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    refs = sorted((ROOT / "assets" / "hero-ref").glob("ref-*.jpg"))
    bad = 0
    for ref in refs:
        ok, reason, foco = await hv.review_image(ref.read_bytes(), "mosaico")
        print(f"{'OK   ' if ok else 'FALLA'} {ref.name}: {reason} (foco_x={foco})")
        bad += not ok
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
