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
    import yaml
    return yaml.safe_load((ROOT / "config" / "hero_prompt.yaml").read_text(encoding="utf-8"))["mosaico"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", default=os.getenv("PIPELINE_IMAGE_MODEL", DEFAULT_MODEL))
    ap.add_argument("--also", nargs="*", default=["gemini-3-pro-image-preview"],
                    help="otros nombres a consultar (solo informativo, sin costo)")
    ap.add_argument("--generate", action="store_true", help="genera una imagen de prueba (~US$0.14)")
    ap.add_argument("--out", default="prueba-imagen.png")
    args = ap.parse_args()

    key = os.getenv("GOOGLE_API_KEY")
    if not key:
        print("Falta GOOGLE_API_KEY en el entorno.")
        return 2

    from google import genai
    from google.genai import types

    print(f"google-genai {getattr(genai, '__version__', '?')} · API {NativeGeminiClient.API_VERSION}")
    client = genai.Client(api_key=key, http_options=types.HttpOptions(api_version=NativeGeminiClient.API_VERSION))
    for other in args.also:
        if other == args.model:
            continue
        try:
            client.models.get(model=other)
            print(f"info: {other} también existe.")
        except Exception as e:  # noqa: BLE001
            print(f"info: {other} no está disponible ({str(e)[:120]}).")
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
        style_prompt()
        + "\nSUBJECT: Hermes hands a sealed envelope with a microchip seal to a marble automaton."
        + "\nCOMPOSITION: two figures in dialogue.\nMOSAIC STATE: intact mosaic, gold only on the subject."
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
