#!/bin/bash

# Exit immediately if any command fails
set -e

echo "Running Alembic migrations..."
alembic upgrade head

exec "$@"