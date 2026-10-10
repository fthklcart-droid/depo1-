#!/bin/bash
cd "$(dirname "$0")"
PY=$(command -v python3.13 || command -v python3.12 || command -v python3.11 || command -v python3)
[ -z "$PY" ] && { echo "Python 3.11+ bulunamadı: https://www.python.org/downloads/"; exit 1; }
exec "$PY" kurulum.py "$@"
