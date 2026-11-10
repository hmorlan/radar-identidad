#!/usr/bin/env python3
"""Archivo de ediciones en Cloudflare R2 (web/data entre corridas).

Las ediciones no se guardan en el repo público. Su archivo vive en un bucket
privado de R2 con esta forma:

    archivo/raiz.tar.gz          archivos de nivel superior de web/data (índice,
                                 feeds, búsqueda...) + .archivo.json (lista de días)
    archivo/dias/AAAA-MM-DD.tar.gz   una carpeta de edición por objeto

``pull`` reconstruye web/data completo; ``push`` sube la raíz y solo los días que
cambiaron desde el último ``pull``. Usa wrangler (CLOUDFLARE_API_TOKEN con
permiso Workers R2 Storage: Edit, y CLOUDFLARE_ACCOUNT_ID).

Uso:
    python3 scripts/archive_r2.py ensure            # crea el bucket si no existe
    python3 scripts/archive_r2.py pull web/data     # código 3 si el archivo está vacío
    python3 scripts/archive_r2.py push web/data
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path
from typing import Callable, List, Optional

BUCKET = os.getenv("R2_ARCHIVE_BUCKET", "radar-identidad-archivo")
WRANGLER = os.getenv("WRANGLER_PKG", "wrangler@4.151.2")
PREFIX = "archivo"
ROOT_KEY = f"{PREFIX}/raiz.tar.gz"
MANIFEST = ".archivo.json"
MARKER = ".archivo-descargado"
DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
EMPTY = 3  # exit code: nothing archived yet


class Missing(Exception):
    """The object does not exist in the bucket."""


def wrangler(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["npx", "--yes", WRANGLER, *args], capture_output=True, text=True)


def r2_get(key: str, dest: Path, run: Callable = wrangler) -> None:
    proc = run("r2", "object", "get", f"{BUCKET}/{key}", "--file", str(dest), "--remote")
    if proc.returncode != 0:
        msg = (proc.stderr or "") + (proc.stdout or "")
        if re.search(r"not found|does not exist|NoSuchKey|10007", msg, re.I):
            raise Missing(key)
        raise RuntimeError(f"no se pudo bajar {key}: {msg.strip()[-300:]}")
    if not dest.exists() or dest.stat().st_size == 0:
        raise Missing(key)


def r2_put(key: str, src: Path, run: Callable = wrangler) -> None:
    proc = run("r2", "object", "put", f"{BUCKET}/{key}", "--file", str(src),
               "--content-type", "application/gzip", "--remote")
    if proc.returncode != 0:
        raise RuntimeError(f"no se pudo subir {key}: {((proc.stderr or '') + (proc.stdout or '')).strip()[-300:]}")


def day_key(day: str) -> str:
    return f"{PREFIX}/dias/{day}.tar.gz"


def _extract(archive: Path, dest: Path) -> None:
    with tarfile.open(archive, "r:gz") as tar:
        tar.extractall(dest, filter="data")


def root_entries(data: Path) -> List[Path]:
    return [p for p in sorted(data.iterdir())
            if not DAY_RE.match(p.name) and p.name not in (MARKER,)]


def day_dirs(data: Path) -> List[str]:
    return sorted(p.name for p in data.iterdir() if p.is_dir() and DAY_RE.match(p.name))


def changed_days(data: Path, since: Optional[float]) -> List[str]:
    out = []
    for day in day_dirs(data):
        if since is None:
            out.append(day)
            continue
        newest = max((f.stat().st_mtime for f in (data / day).rglob("*") if f.is_file()), default=0)
        if newest > since:
            out.append(day)
    return out


def pull(data: Path, run: Callable = wrangler) -> int:
    data.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "raiz.tar.gz"
        try:
            r2_get(ROOT_KEY, root, run)
        except Missing:
            print("El archivo en R2 está vacío (primera corrida).")
            return EMPTY
        _extract(root, data)
        manifest = json.loads((data / MANIFEST).read_text(encoding="utf-8")) if (data / MANIFEST).exists() else {}
        days = manifest.get("dias", [])
        fetched = 0
        for day in days:
            target = Path(tmp) / f"{day}.tar.gz"
            try:
                r2_get(day_key(day), target, run)
            except Missing:
                print(f"::warning::Falta el día {day} en R2.")
                continue
            _extract(target, data)
            fetched += 1
    (data / MARKER).write_text(str(time.time()), encoding="utf-8")
    print(f"Archivo restaurado desde R2: {fetched} de {len(days)} ediciones.")
    return 0


def push(data: Path, run: Callable = wrangler) -> int:
    marker = data / MARKER
    since = float(marker.read_text(encoding="utf-8")) if marker.exists() else None
    days = changed_days(data, since)
    with tempfile.TemporaryDirectory() as tmp:
        for day in days:
            target = Path(tmp) / f"{day}.tar.gz"
            with tarfile.open(target, "w:gz") as tar:
                tar.add(data / day, arcname=day)
            r2_put(day_key(day), target, run)
        manifest_path = data / MANIFEST
        old = json.loads(manifest_path.read_text(encoding="utf-8")).get("dias", []) if manifest_path.exists() else []
        all_days = sorted(set(old) | set(day_dirs(data)))
        manifest_path.write_text(json.dumps({"dias": all_days, "actualizado": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
                                            ensure_ascii=False, indent=1), encoding="utf-8")
        root = Path(tmp) / "raiz.tar.gz"
        with tarfile.open(root, "w:gz") as tar:
            for entry in root_entries(data):
                tar.add(entry, arcname=entry.name)
        r2_put(ROOT_KEY, root, run)
    print(f"Archivo subido a R2: {len(days)} edición(es) nuevas o cambiadas; {len(all_days)} en total.")
    return 0


def ensure(run: Callable = wrangler) -> int:
    proc = run("r2", "bucket", "create", BUCKET)
    msg = (proc.stderr or "") + (proc.stdout or "")
    if proc.returncode == 0:
        print(f"Bucket {BUCKET} creado.")
    elif re.search(r"already exists|10004", msg, re.I):
        print(f"Bucket {BUCKET} ya existe.")
    else:
        print(f"No se pudo crear el bucket {BUCKET}: {msg.strip()[-300:]}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("action", choices=["ensure", "pull", "push"])
    ap.add_argument("data", nargs="?", default="web/data")
    args = ap.parse_args()
    if args.action == "ensure":
        return ensure()
    data = Path(args.data)
    try:
        return pull(data) if args.action == "pull" else push(data)
    except RuntimeError as e:
        print(f"::error::{e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
