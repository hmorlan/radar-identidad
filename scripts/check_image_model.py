#!/usr/bin/env python3
"""Verifica el modelo de imagen configurado antes de usarlo en el pipeline.

Sin argumentos solo consulta que el modelo exista para tu key (no genera nada, sin costo).
Con --generate crea UNA imagen 21:9 a 2K con el mismo cliente que usa el pipeline
(modo native) y reporta el costo calculado (~US$0.14 por imagen).

Uso:
    GOOGLE_API_KEY=... python3 scripts/check_image_model.py
    GOOGLE_API_KEY=... python3 scripts/check_image_model.py --generate --out prueba.png
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.cost_tracker import price_image_usage  # noqa: E402
from generators.image_client import NativeGeminiClient  # noqa: E402

DEFAULT_MODEL = NativeGeminiClient.DEFAULT_MODEL


def style_prompt() -> str:
    path = ROOT / "config" / "hero_style.md"
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if not l.lstrip().startswith("#")]
    return "\n".join(lines).strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", default=os.getenv("PIPELINE_IMAGE_MODEL", DEFAULT_MODEL))
    ap.add_argument("--generate", action="store_true", help="genera una imagen de prueba (~US$0.14)")
    ap.add_argument("--out", default="prueba-imagen.png")
    args = ap.parse_args()

    key = os.getenv("GOOGLE_API_KEY")
    if not key:
        print("Falta GOOGLE_API_KEY en el entorno.")
        return 2

    from google import genai

    client = genai.Client(api_key=key)
    try:
        info = client.models.get(model=args.model)
    except Exception as e:  # noqa: BLE001
        print(f"FALLA: el modelo {args.model!r} no está disponible para esta key: {e}")
        return 1
    print(f"OK: {args.model} existe ({getattr(info, 'display_name', '') or 'sin nombre'}).")
    if not args.generate:
        print("No se generó ninguna imagen (usa --generate para una prueba con costo).")
        return 0

    prompt = (
        "A classical marble automaton with gold kintsugi seams holds a split bronze tessera "
        "whose two halves no longer match; one half glows sapphire, the other flickers out.\n\n"
        + style_prompt()
    )
    native = NativeGeminiClient(api_key=key, model=args.model)
    resp = asyncio.run(native.generate(prompt=prompt, aspect_ratio="21:9", image_size="2K"))
    Path(args.out).write_bytes(resp.image_data)
    cost = price_image_usage(resp.usage)
    print(f"Imagen guardada en {args.out} ({len(resp.image_data) // 1024} KB, {resp.mime_type}).")
    if cost:
        print(f"Tokens: entrada {cost.input_tokens}, imagen {cost.image_tokens}, "
              f"texto/pensamiento {cost.text_tokens}. Costo calculado: US${cost.total_cost:.4f}")
    else:
        print("La respuesta no trajo datos de uso; costo no disponible.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
