#!/bin/bash
# findicon — shortcut for ``iconlib search``
set -euo pipefail

resolve_self() {
  local target=$1
  if command -v readlink >/dev/null 2>&1; then
    readlink -f "$target" 2>/dev/null && return
  fi
  if command -v realpath >/dev/null 2>&1; then
    realpath "$target" 2>/dev/null && return
  fi
  printf '%s\n' "$target"
}

self=$(resolve_self "$0")
bindir=$(dirname "$self")
iconlib="${bindir}/iconlib"

if [ ! -x "$iconlib" ]; then
  if ! iconlib=$(command -v iconlib); then
    echo "findicon: iconlib not found in PATH" >&2
    exit 127
  fi
fi

if [ "$#" -eq 1 ] && [ "$1" = "--version" ]; then
  exec "$iconlib" --version
fi

exec "$iconlib" search "$@"
