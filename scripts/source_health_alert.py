#!/usr/bin/env python3
"""Alerta de fuentes caídas: abre o actualiza un issue en GitHub.

Corre ``check_feeds.run_checks()`` (sin LLM, sin costo) y lleva la cuenta de
cuántas revisiones seguidas lleva fallando cada fuente en un archivo de estado.
Cuando una fuente llega a ``--min-streak`` fallas seguidas (por defecto 2, para
no alertar por una caída pasajera), abre un issue con la etiqueta
``salud-fuentes``. Si la lista de fuentes caídas cambia, deja un comentario;
cuando todas se recuperan, comenta y cierra el issue.

Uso:
    python3 scripts/source_health_alert.py --state data/source_health.json --dry-run
    GH_TOKEN=... GITHUB_REPOSITORY=hmorlan/radar-identidad \\
        python3 scripts/source_health_alert.py --state data/source_health.json

Lo corre ``.github/workflows/source-health.yml`` todos los días.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_feeds  # noqa: E402

LABEL = "salud-fuentes"
TITLE = "Fuentes caídas en el Radar"
OWNER_MENTION = "@hmorlan"


def evaluate(results: List[dict], state: Dict, min_streak: int, today: str) -> Tuple[Dict, List[dict], List[dict]]:
    """Update failure streaks. Returns (new_state, alerting, informational).

    ``alerting`` holds active sources whose FALLA streak reached ``min_streak``.
    ``informational`` holds active sources that are not failing but look off
    (inactive, no dates, no results): they are listed in an open issue but never
    open one by themselves.
    """
    old = state.get("streaks", {})
    streaks: Dict[str, Dict] = {}
    alerting, info = [], []
    for r in results:
        if r.get("pending"):
            continue
        key = f"{r['group']}|{r['source']}"
        if r["verdict"] == check_feeds.FAIL:
            prev = old.get(key, {})
            streak = prev.get("count", 0) + 1
            streaks[key] = {"count": streak, "since": prev.get("since", today), "error": r.get("error", "")}
            if streak >= min_streak:
                alerting.append({**r, "streak": streak, "since": streaks[key]["since"]})
        elif r["verdict"] != check_feeds.OK:
            info.append(r)
    new_state = {
        "updated": today,
        "streaks": streaks,
        "alerted": sorted(f"{a['group']}|{a['source']}" for a in alerting),
    }
    return new_state, alerting, info


def render_issue(alerting: List[dict], info: List[dict], today: str) -> str:
    lines = [
        f"{OWNER_MENTION} la revisión diaria de fuentes ({today}) encontró fuentes que dejaron de responder.",
        "",
        "Una fuente caída no detiene la edición, pero sus noticias dejan de entrar sin aviso.",
        "",
        "| Grupo | Fuente | Fallando desde | Revisiones seguidas | Detalle |",
        "|---|---|---|---|---|",
    ]
    for a in alerting:
        detail = (a.get("error") or "").replace("|", "/")[:120]
        lines.append(f"| {a['group']} | {a['source']} | {a['since']} | {a['streak']} | {detail} |")
    if info:
        lines += ["", "Para revisar sin prisa (no fallan, pero se ven raras):", ""]
        for r in info:
            lines.append(f"- {r['verdict'].lower()}: {r['group']} · {r['source']} (última {r.get('newest') or '-'})")
    lines += [
        "",
        "Qué hacer: correr `python3 scripts/check_feeds.py` y, si el sitio cambió, ajustar la fuente "
        "en `config/` o en `agents/gatherers/regulator_sources.py`. Este issue se cierra solo cuando "
        "todas vuelven a responder.",
    ]
    return "\n".join(lines)


def render_summary(results: List[dict], alerting: List[dict], today: str) -> str:
    counts: Dict[str, int] = {}
    for r in results:
        if not r.get("pending"):
            counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    out = [f"### Salud de las fuentes · {today}", "",
           " · ".join(f"{v}: {n}" for v, n in sorted(counts.items())), ""]
    out.append(f"Alertando: {len(alerting)}" if alerting else "Sin alertas.")
    fails = [r for r in results if r["verdict"] != check_feeds.OK and not r.get("pending")]
    if fails:
        out += ["", "| Veredicto | Grupo | Fuente | Detalle |", "|---|---|---|---|"]
        for r in fails:
            out.append(f"| {r['verdict']} | {r['group']} | {r['source']} | {(r.get('error') or '').replace('|', '/')[:100]} |")
    return "\n".join(out)


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def open_issue_number(repo: str) -> Optional[int]:
    out = gh("issue", "list", "--repo", repo, "--label", LABEL, "--state", "open",
             "--json", "number", "--limit", "1")
    items = json.loads(out or "[]")
    return items[0]["number"] if items else None


def sync_issue(repo: str, alerting: List[dict], info: List[dict], prev_alerted: List[str],
               now_alerted: List[str], today: str) -> str:
    number = open_issue_number(repo)
    body = render_issue(alerting, info, today)
    if alerting:
        if number is None:
            subprocess.run(["gh", "label", "create", LABEL, "--repo", repo, "--color", "D93F0B",
                            "--description", "Alertas automáticas de fuentes caídas"],
                           capture_output=True, text=True)  # ya existe: se ignora
            gh("issue", "create", "--repo", repo, "--title", TITLE, "--label", LABEL, "--body", body)
            return "abierto"
        gh("issue", "edit", str(number), "--repo", repo, "--body", body)
        if sorted(prev_alerted) != sorted(now_alerted):
            gh("issue", "comment", str(number), "--repo", repo, "--body",
               f"Cambió la lista de fuentes caídas ({today}): {len(now_alerted)} en total. "
               "La descripción del issue está actualizada.")
            return "actualizado con comentario"
        return "actualizado"
    if number is not None:
        gh("issue", "comment", str(number), "--repo", repo, "--body",
           f"Todas las fuentes volvieron a responder ({today}). Cierro el issue.")
        gh("issue", "close", str(number), "--repo", repo)
        return "cerrado"
    return "sin cambios"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--state", default="data/source_health.json", help="archivo de estado entre corridas")
    ap.add_argument("--min-streak", type=int, default=2, help="fallas seguidas antes de alertar")
    ap.add_argument("--days", type=int, default=60, help="días sin publicar para marcar INACTIVA")
    ap.add_argument("--dry-run", action="store_true", help="no toca GitHub; imprime el issue")
    ap.add_argument("--results", help="usar resultados guardados (JSON de check_feeds --json) en vez de revisar")
    args = ap.parse_args()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if args.results:
        results = json.loads(Path(args.results).read_text(encoding="utf-8"))
    else:
        results = [asdict(r) for r in check_feeds.run_checks(days=args.days)]

    state_path = Path(args.state)
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    new_state, alerting, info = evaluate(results, state, args.min_streak, today)

    summary = render_summary(results, alerting, today)
    print(summary)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fh:
            fh.write(summary + "\n")

    if args.dry_run:
        if alerting:
            print("\n--- issue (dry run) ---\n" + render_issue(alerting, info, today))
    else:
        repo = os.environ.get("GITHUB_REPOSITORY")
        if not repo:
            print("Falta GITHUB_REPOSITORY; usa --dry-run para probar localmente.", file=sys.stderr)
            return 2
        action = sync_issue(repo, alerting, info, state.get("alerted", []), new_state["alerted"], today)
        print(f"\nIssue: {action}")

    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(new_state, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
