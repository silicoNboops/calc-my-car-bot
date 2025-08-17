#!/usr/bin/env sh
set -e

# Simple, idempotent dev-deps installer for local envs.
# Executes only when ENVIRONMENT=local and requirements-dev.txt exists.
# Creates a marker file to avoid repeated installs on every container start.
# The marker stores a checksum of requirements-dev.txt and tool versions.

APP_DIR=/application
MARKER_FILE="$APP_DIR/.dev_deps_installed"
REQ_DEV_FILE="$APP_DIR/requirements-dev.txt"

if [ "${ENVIRONMENT:-production}" = "local" ]; then
  echo "[entrypoint] ENVIRONMENT=local detected. Ensuring dev dependencies are installed..."
  if [ -f "$REQ_DEV_FILE" ]; then
    # Compute checksum of requirements-dev.txt in a portable way (using Python available in image)
    REQ_HASH=$(python - <<'PY'
import hashlib, pathlib
p = pathlib.Path('/application/requirements-dev.txt')
print(hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else '')
PY
)
    PY_VER=$(python - <<'PY'
import sys
print('.'.join(map(str, sys.version_info[:3])))
PY
)
    PIP_VER=$(python -m pip --version 2>/dev/null | awk '{print $2}')

    NEED_INSTALL=1
    if [ -f "$MARKER_FILE" ]; then
      MARKER_HASH=$(grep '^hash=' "$MARKER_FILE" 2>/dev/null | cut -d'=' -f2)
      MARKER_PY=$(grep '^pyver=' "$MARKER_FILE" 2>/dev/null | cut -d'=' -f2)
      MARKER_PIP=$(grep '^pipver=' "$MARKER_FILE" 2>/dev/null | cut -d'=' -f2)

      if [ "$REQ_HASH" = "$MARKER_HASH" ] && [ "$PY_VER" = "$MARKER_PY" ] && [ "$PIP_VER" = "$MARKER_PIP" ]; then
        # Sanity check: ensure at least one dev package from requirements-dev.txt is really importable.
        # This covers cases after image rebuild when site-packages are fresh but marker remains in volume.
        if python - <<'PY'
try:
    import pytest  # sentinel dev dep
    print('OK')
except Exception:
    print('MISS')
PY
        | grep -q 'OK'; then
          NEED_INSTALL=0
          echo "[entrypoint] Dev dependencies up-to-date (marker checksum matches). Skipping."
        else
          echo "[entrypoint] Marker matches but dev packages missing in image. Reinstalling..."
        fi
      else
        echo "[entrypoint] Dev dependencies out-of-date (changes detected). Reinstalling..."
      fi
    else
      echo "[entrypoint] No marker found. Installing dev dependencies..."
    fi

    if [ "$NEED_INSTALL" -ne 0 ]; then
      echo "[entrypoint] Installing dev dependencies from $REQ_DEV_FILE ..."
      pip install -r "$REQ_DEV_FILE"
      {
        echo "hash=$REQ_HASH"
        echo "pyver=$PY_VER"
        echo "pipver=$PIP_VER"
      } > "$MARKER_FILE"
      echo "[entrypoint] Dev dependencies installed and marker updated."
    fi
  else
    echo "[entrypoint] requirements-dev.txt not found. Skipping dev deps install."
  fi
else
  echo "[entrypoint] ENVIRONMENT is '${ENVIRONMENT:-production}'. Skipping dev dependencies install."
fi

# Execute the container's main command
exec "$@"
