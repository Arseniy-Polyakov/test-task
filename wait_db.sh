#!/bin/sh

echo "Waiting for Postgres"

until pg_isready -h db -U $POSTGRES_USER -d $POSTGRES_DB; do
  sleep 2
done

echo "Postgres is ready"

exec uvicorn app.backend.main:app --host 0.0.0.0 --port 8000