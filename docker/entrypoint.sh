#!/bin/sh
set -e

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  uv run python src/manage.py migrate --noinput
fi

if [ "${COLLECT_STATIC:-1}" = "1" ]; then
  uv run python src/manage.py collectstatic --noinput
fi

exec "$@"
