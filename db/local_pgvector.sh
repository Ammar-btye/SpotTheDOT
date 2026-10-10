#!/usr/bin/env bash
# Start a local Postgres 17 + pgvector in Docker for testing (stand-in for Neon).
#   ./db/local_pgvector.sh          start (or reuse) the container and print DATABASE_URL
#   ./db/local_pgvector.sh stop     stop and remove it (data is kept in the spot-pgvector-data volume)
#   ./db/local_pgvector.sh wipe     stop, remove, and delete the data volume
set -euo pipefail

NAME=spot-pgvector
IMAGE=pgvector/pgvector:pg17
PORT=${PGVECTOR_PORT:-5433}
VOLUME=spot-pgvector-data
URL="postgresql://postgres:postgres@localhost:${PORT}/spot"

case "${1:-start}" in
  stop) docker rm -f "$NAME" >/dev/null 2>&1 || true; echo "stopped $NAME"; exit 0 ;;
  wipe) docker rm -f "$NAME" >/dev/null 2>&1 || true; docker volume rm "$VOLUME" >/dev/null 2>&1 || true
        echo "removed $NAME and volume $VOLUME"; exit 0 ;;
  start) ;;
  *) echo "usage: $0 [start|stop|wipe]" >&2; exit 2 ;;
esac

if [ -n "$(docker ps -q -f name="^${NAME}$")" ]; then
  echo "$NAME already running"
elif [ -n "$(docker ps -aq -f name="^${NAME}$")" ]; then
  docker start "$NAME" >/dev/null
else
  docker run -d --name "$NAME" -p "${PORT}:5432" \
    -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=spot \
    -v "${VOLUME}:/var/lib/postgresql/data" "$IMAGE" >/dev/null
fi

for _ in $(seq 1 60); do
  if docker exec "$NAME" pg_isready -U postgres -d spot >/dev/null 2>&1; then break; fi
  sleep 1
done
docker exec "$NAME" pg_isready -U postgres -d spot >/dev/null || { echo "postgres did not become ready" >&2; exit 1; }
docker exec "$NAME" psql -U postgres -d spot -qtAc "CREATE EXTENSION IF NOT EXISTS vector" >/dev/null

echo "pgvector $(docker exec "$NAME" psql -U postgres -d spot -qtAc "SELECT extversion FROM pg_extension WHERE extname='vector'") on $(docker exec "$NAME" psql -U postgres -d spot -qtAc 'SHOW server_version')"
echo "export DATABASE_URL=${URL}"
echo "# from another container (e.g. the db tooling image): postgresql://postgres:postgres@host.docker.internal:${PORT}/spot"
