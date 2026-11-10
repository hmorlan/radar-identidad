#!/usr/bin/env bash
# Compila el sitio (frontend → web/) y lo sube a Cloudflare Pages (Direct Upload).
#
# Lo usan .github/workflows/deploy-site.yml (manual) y daily-pipeline.yml (tras
# una corrida). Las ediciones viajan en web/data aunque no se guarden en el repo.
#
# Requiere: CLOUDFLARE_API_TOKEN (permiso "Cloudflare Pages: Edit") y
# CLOUDFLARE_ACCOUNT_ID. Opcional: CF_PAGES_PROJECT (por defecto radar-identidad).
set -euo pipefail

PROJECT="${CF_PAGES_PROJECT:-radar-identidad}"
WRANGLER="wrangler@4.151.2"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

: "${CLOUDFLARE_API_TOKEN:?Falta CLOUDFLARE_API_TOKEN}"
: "${CLOUDFLARE_ACCOUNT_ID:?Falta CLOUDFLARE_ACCOUNT_ID}"

cd "$ROOT/frontend"
npm ci --no-audit --no-fund
npm run build

cd "$ROOT"
# Crea el proyecto la primera vez; si ya existe, el error se ignora.
npx --yes "$WRANGLER" pages project create "$PROJECT" --production-branch main >/dev/null 2>&1 \
  && echo "Proyecto $PROJECT creado en Cloudflare Pages." || true

npx --yes "$WRANGLER" pages deploy web --project-name "$PROJECT" --branch main --commit-dirty=true
