#!/usr/bin/env bash
# Run on an approved Linux host in an existing checked-out release directory.
# Publication/TLS and host provisioning are separate, explicitly approved steps.
set -euo pipefail
if [[ "${1:-}" != "--approved" ]]; then
  echo "Review release, backup, environment, migration and deployment approval first."
  echo "Usage: scripts/deploy.sh --approved"
  exit 2
fi
cd "$(dirname "$0")/.."
test -f apps/api/.env
test -f .env
if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  echo "Tracked checkout has uncommitted changes; select a clean release."
  exit 1
fi
compose=(docker compose -f compose.yml -f docker-compose.prod.yml)
"${compose[@]}" config --quiet
mkdir -p backups
chmod 700 backups
if "${compose[@]}" ps --status running --services | grep -qx db; then
  backup="backups/predeploy-$(date -u +%Y%m%dT%H%M%SZ).dump"
  (umask 077; "${compose[@]}" exec -T db pg_dump -U flowstate -d flowstate -Fc > "$backup")
  test -s "$backup"
  "${compose[@]}" exec -T db pg_restore --list < "$backup" >/dev/null
fi
"${compose[@]}" build
# Avoid old workers writing during migrations. No volumes or databases deleted.
"${compose[@]}" stop scheduler worker api web nginx
"${compose[@]}" up -d --wait db redis
"${compose[@]}" run --rm migrate
"${compose[@]}" up -d --wait --wait-timeout 180
curl --fail --silent --show-error http://127.0.0.1:8080/api/health/ready
curl --fail --silent --show-error --output /dev/null http://127.0.0.1:8080/
echo "Loopback container health verified. Public HTTPS and Google login need separate validation."
