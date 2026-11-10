#!/usr/bin/env python3
"""Comprueba los modelos de Claude del pipeline antes de la primera corrida real.

Hace una llamada mínima a cada combinación que usa el pipeline, con la misma
forma de petición que ``agents/llm_client.py`` (pensamiento adaptativo +
``output_config.effort``), y reporta si la API la acepta, los tokens y el costo.

- Opus 5.5 (redacción y verificación): effort high, xhigh y max.
- Haiku 5.5 (triage): effort high.

Costo total esperado: menos de US$0.05.

Uso:
    ANTHROPIC_API_KEY=... python3 scripts/check_claude_models.py
    python3 scripts/check_claude_models.py --dry-run     # solo muestra qué probaría
"""
from __future__ import annotations

import argparse
import os
import sys

HEAVY = os.getenv("ANTHROPIC_MODEL", "claude-opus-5-5")
LIGHT = os.getenv("PIPELINE_LIGHT_MODEL", "claude-haiku-5-5")
# USD por millón de tokens (entrada, salida); mismos valores que agents/cost_tracker.py.
PRICES = {"claude-opus-5-5": (4.0, 20.0), "claude-haiku-5-5": (0.10, 0.50)}
CASES = [(HEAVY, "high"), (HEAVY, "xhigh"), (HEAVY, "max"), (LIGHT, "high")]
PROMPT = "Responde exactamente con la palabra: listo"


def cost(model: str, usage) -> float:
    pin, pout = PRICES.get(model, (0.0, 0.0))
    return (usage.input_tokens * pin + usage.output_tokens * pout) / 1_000_000


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-tokens", type=int, default=1024,
                    help="tope por llamada (incluye pensamiento); el modelo suele usar mucho menos")
    args = ap.parse_args()

    if args.dry_run:
        for model, effort in CASES:
            print(f"probaría {model} con effort={effort}")
        return 0
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Falta ANTHROPIC_API_KEY.", file=sys.stderr)
        return 2

    import anthropic

    client = anthropic.Anthropic()
    failures, total = 0, 0.0
    for model, effort in CASES:
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=args.max_tokens,
                messages=[{"role": "user", "content": PROMPT}],
                thinking={"type": "adaptive", "display": "summarized"},
                extra_body={"output_config": {"effort": effort}},
            )
        except anthropic.APIStatusError as e:
            failures += 1
            msg = getattr(e, "message", str(e))
            print(f"FALLA  {model:<18} effort={effort:<5} HTTP {e.status_code}: {msg[:200]}")
            continue
        except anthropic.APIConnectionError as e:
            failures += 1
            print(f"FALLA  {model:<18} effort={effort:<5} sin conexión: {e}")
            continue
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
        c = cost(model, resp.usage)
        total += c
        print(f"OK     {model:<18} effort={effort:<5} entrada {resp.usage.input_tokens:>4} · "
              f"salida {resp.usage.output_tokens:>4} · US${c:.4f} · respuesta: {text[:40]!r}")

    print(f"\nCosto total de la prueba: US${total:.4f}")
    if failures:
        print(f"{failures} combinación(es) rechazadas: ajustar el mapeo de perfiles en "
              "agents/llm_client.py antes de la corrida real.", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
