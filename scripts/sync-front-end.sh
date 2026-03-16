#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUBMODULE_PATH="heating-ui"
SUBMODULE_DIR="${ROOT_DIR}/${SUBMODULE_PATH}"
DIST_DIR="${SUBMODULE_DIR}/dist"
TARGET_DIR="${ROOT_DIR}/application/front-end"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Error: required command '$1' is not available in PATH." >&2
    exit 1
  fi
}

require_cmd git
require_cmd npm
require_cmd rsync

if ! git -C "$ROOT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Error: '$ROOT_DIR' is not a git repository." >&2
  exit 1
fi

if ! grep -q "path = ${SUBMODULE_PATH}" "${ROOT_DIR}/.gitmodules" 2>/dev/null; then
  echo "Error: '${SUBMODULE_PATH}' is not configured as a git submodule." >&2
  exit 1
fi

submodule_status="$(git -C "$ROOT_DIR" submodule status -- "${SUBMODULE_PATH}" || true)"
if [ -z "$submodule_status" ]; then
  echo "Error: could not resolve submodule status for '${SUBMODULE_PATH}'." >&2
  exit 1
fi

status_prefix="${submodule_status:0:1}"
if [ "$status_prefix" = "-" ]; then
  echo "Error: submodule '${SUBMODULE_PATH}' is not initialized." >&2
  echo "Run: git submodule update --init --recursive ${SUBMODULE_PATH}" >&2
  exit 1
fi
if [ "$status_prefix" = "U" ]; then
  echo "Error: submodule '${SUBMODULE_PATH}' has merge conflicts." >&2
  exit 1
fi

if [ ! -f "${SUBMODULE_DIR}/package.json" ]; then
  echo "Error: '${SUBMODULE_PATH}' working tree is unavailable." >&2
  exit 1
fi

echo "Building ${SUBMODULE_PATH}..."
(
  cd "$SUBMODULE_DIR"
  npm run build
)

if [ ! -d "$DIST_DIR" ]; then
  echo "Error: build output not found at '${DIST_DIR}'." >&2
  exit 1
fi

mkdir -p "$TARGET_DIR"
echo "Syncing '${DIST_DIR}/' -> '${TARGET_DIR}/'..."
rsync -a --delete "${DIST_DIR}/" "${TARGET_DIR}/"
echo "Frontend sync complete."
