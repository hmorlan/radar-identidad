#!/usr/bin/env python3
"""Pistas de ransomware en México, LatAm y España (no se publican).

Lo que publican los grupos de ransomware son **reclamos sin verificar** sobre
víctimas con nombre. El radar no los publica ni los usa como fuente: esta lista es
solo una pista para el revisor editorial, que busca si la prensa independiente lo
confirmó y si tiene ángulo de identidad (credenciales, datos personales, KYC,
expedientes de empleados o clientes). Si lo tiene, lo propone en "Faltantes".

Fuente: API pública de ransomware.live (sin llave). Nunca se guarda ni se sigue la
dirección del sitio de filtraciones (.onion). Para México también se enlaza el
resumen diario de ransomware.mx.

Uso:
    python3 scripts/pistas_ransomware.py --desde 2026-11-20 --hasta 2026-11-23 --out pistas/ransomware.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

API = "https://api.ransomware.live/v2/countryvictims/{cc}"
PAISES = {"MX": "México", "CO": "Colombia", "AR": "Argentina", "CL": "Chile", "PE": "Perú",
          "EC": "Ecuador", "GT": "Guatemala", "CR": "Costa Rica", "UY": "Uruguay",
          "PY": "Paraguay", "BO": "Bolivia", "DO": "República Dominicana", "PA": "Panamá",
          "VE": "Venezuela", "ES": "España"}


def pistas(desde: date, hasta: date, get=requests.get) -> dict:
    out, fallas = [], []
    for cc, pais in PAISES.items():
        try:
            resp = get(API.format(cc=cc), timeout=30, headers={"User-Agent": "RadarDeIdentidad/1.0"})
            resp.raise_for_status()
            rows = resp.json()
        except Exception as e:  # noqa: BLE001
            fallas.append(f"{cc}: {type(e).__name__}")
            continue
        for r in rows if isinstance(rows, list) else []:
            try:
                dia = datetime.fromisoformat(str(r.get("discovered"))[:19]).date()
            except ValueError:
                continue
            if not desde <= dia <= hasta:
                continue
            out.append({
                "pais": pais,
                "descubierto": dia.isoformat(),
                "grupo": r.get("group_name") or "",
                "victima_segun_el_grupo": r.get("post_title") or "",
                "descripcion": (r.get("description") or "")[:300],
                "sitio_de_la_victima": r.get("website") or "",
                # post_url (.onion) se descarta a propósito.
            })
    out.sort(key=lambda x: (x["pais"], x["descubierto"]))
    dias = [(desde + timedelta(days=i)).isoformat() for i in range((hasta - desde).days + 1)]
    return {
        "aviso": "Reclamos de grupos criminales, sin verificar. No publicar ni citar como fuente; "
                 "solo buscar cobertura de prensa independiente con ángulo de identidad.",
        "periodo": [desde.isoformat(), hasta.isoformat()],
        "fuente": "https://www.ransomware.live (API pública)",
        "resumen_mexico": [f"https://ransomware.mx/intel/{d}/" for d in dias],
        "pistas": out,
        "fallas": fallas,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--desde", required=True)
    ap.add_argument("--hasta", required=True)
    ap.add_argument("--out", default="pistas/ransomware.json")
    a = ap.parse_args()
    data = pistas(date.fromisoformat(a.desde), date.fromisoformat(a.hasta))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(data['pistas'])} pistas ({a.desde} a {a.hasta}); fallas: {data['fallas'] or 'ninguna'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
