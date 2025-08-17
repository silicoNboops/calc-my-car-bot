#!/usr/bin/env sh
set -e

# Simple, idempotent dev-deps installer for local envs.
# Executes only when ENVIRONMENT=local and requirements-dev.txt exists.
# Creates a marker file to avoid repeated installs on every container start.

APP_DIR=/application
MARKER_FILE="$APP_DIR/.dev_deps_installed"
REQ_DEV_FILE="$APP_DIR/requirements-dev.txt"

if [ "${ENVIRONMENT:-production}" = "local" ]; then
  echo "[entrypoint] ENVIRONMENT=local detected. Ensuring dev dependencies are installed..."
  if [ -f "$REQ_DEV_FILE" ]; then
    if [ -f "$MARKER_FILE" ]; then
      echo "[entrypoint] Dev dependencies already installed (marker present). Skipping."
    else
      echo "[entrypoint] Installing dev dependencies from $REQ_DEV_FILE ..."
      pip install -r "$REQ_DEV_FILE"
      # Mark as installed to skip next starts
      touch "$MARKER_FILE"
      echo "[entrypoint] Dev dependencies installed."
    fi
  else
    echo "[entrypoint] requirements-dev.txt not found. Skipping dev deps install."
  fi
else
  echo "[entrypoint] ENVIRONMENT is '${ENVIRONMENT:-production}'. Skipping dev dependencies install."
fi

# Execute the container's main command
exec "$@"
