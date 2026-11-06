#!/usr/bin/env bash
# Single start command: makes the database available, initialises it, then runs the API (8000)
# and the frontend (5173). It never stops, removes, or recreates an existing container and never
# touches other databases on it. Ctrl-C stops only the processes started here.
#
# Usage: scripts/dev.sh [--check | --db-only]
#   --check    print which database branch would be taken and exit without acting
#   --db-only  make the database available, then exit
# Overrides (tests): ENV_FILE (default .env), DB_WAIT_SECONDS (default 60).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT/.env}"
WAIT_SECONDS="${DB_WAIT_SECONDS:-60}"
CONTAINER=azure-sql-edge
IMAGE=mcr.microsoft.com/azure-sql-edge
VOLUME=azure-sql-edge-data

MODE=run
case "${1:-}" in
  "") ;;
  --check) MODE=check ;;
  --db-only) MODE=db-only ;;
  *) echo "usage: scripts/dev.sh [--check | --db-only]" >&2; exit 2 ;;
esac

fail() { echo "error: $*" >&2; exit 1; }

env_value() {
  # One variable from the env file without sourcing it, so values are never evaluated or echoed.
  { grep -E "^$1=" "$ENV_FILE" 2>/dev/null || true; } | head -n1 | cut -d= -f2- \
    | sed -e "s/^[\"']//" -e "s/[\"']\$//"
}

DB_HOST="$(env_value DB_HOST)"; DB_HOST="${DB_HOST:-localhost}"
DB_PORT="$(env_value DB_PORT)"; DB_PORT="${DB_PORT:-1433}"

port_open() { bash -c 'echo > "/dev/tcp/$0/$1"' "$DB_HOST" "$DB_PORT" 2>/dev/null; }
docker_up() { docker info >/dev/null 2>&1; }
container_exists() { docker inspect "$CONTAINER" >/dev/null 2>&1; }
container_running() {
  [ "$(docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null || true)" = "true" ]
}

decide() {
  if ! docker_up; then echo start-docker-daemon
  elif container_running; then
    if port_open; then echo reuse-running; else echo wait-for-running; fi
  elif container_exists; then echo start-stopped
  elif port_open; then echo port-conflict
  else echo create
  fi
}

creation_method() {
  if docker compose version >/dev/null 2>&1; then echo "docker compose up"; else echo "docker run"; fi
}

check() {
  local branch
  branch="$(decide)"
  case "$branch" in
    create) echo "branch: create (via $(creation_method))" ;;
    port-conflict)
      echo "branch: port-conflict"
      echo "port $DB_PORT is in use by another process and $CONTAINER does not exist; no second instance would be started"
      return 1 ;;
    *) echo "branch: $branch" ;;
  esac
}

wait_for_port() {
  local waited=0
  until port_open; do
    [ "$waited" -lt "$WAIT_SECONDS" ] || fail "$DB_HOST:$DB_PORT did not accept connections within ${WAIT_SECONDS}s"
    sleep 1
    waited=$((waited + 1))
  done
}

ensure_docker() {
  docker_up && return 0
  echo "Docker daemon is not running; starting colima"
  colima start
  docker_up || fail "the Docker daemon is still not reachable after colima start"
}

create_container() {
  local password
  password="$(env_value DB_PASSWORD)"
  [ -n "$password" ] || fail "DB_PASSWORD is not set in $ENV_FILE"
  # Exported so docker reads the value from the environment; it never appears on a command line.
  export MSSQL_SA_PASSWORD="$password" DB_PASSWORD="$password" DB_PORT
  if docker compose version >/dev/null 2>&1; then
    (cd "$ROOT" && docker compose up -d)
  else
    docker run -d --name "$CONTAINER" -p "$DB_PORT:1433" -e ACCEPT_EULA=1 -e MSSQL_SA_PASSWORD \
      -v "$VOLUME:/var/opt/mssql" \
      --health-cmd "bash -c 'echo > /dev/tcp/127.0.0.1/1433'" \
      --health-interval 10s --health-timeout 5s --health-retries 12 "$IMAGE" >/dev/null
  fi
}

ensure_database() {
  ensure_docker
  case "$(decide)" in
    reuse-running) echo "database already running, reusing it" ;;
    wait-for-running)
      echo "container $CONTAINER is running; waiting up to ${WAIT_SECONDS}s for $DB_HOST:$DB_PORT"
      wait_for_port ;;
    start-stopped) docker start "$CONTAINER" >/dev/null; wait_for_port ;;
    port-conflict)
      fail "port $DB_PORT is already in use and container $CONTAINER does not exist; not starting a second instance" ;;
    create) create_container; wait_for_port ;;
  esac
}

PIDS=""
stop_children() {
  local pid
  trap - INT TERM EXIT
  for pid in $PIDS; do kill -TERM -- "-$pid" 2>/dev/null || true; done
}

serve() {
  set -m
  trap stop_children INT TERM EXIT
  (cd "$ROOT/src/backend" && exec "$ROOT/.venv/bin/uvicorn" app.main:create_app --factory --port 8000) &
  PIDS="$!"
  npm --prefix "$ROOT/src/frontend" run dev &
  PIDS="$PIDS $!"
  while for pid in $PIDS; do kill -0 "$pid" 2>/dev/null || exit 1; done; do sleep 1; done
}

if [ "$MODE" = check ]; then check; exit $?; fi
ensure_database
if [ "$MODE" = db-only ]; then exit 0; fi
"$ROOT/scripts/db-init.sh"
serve
