#!/usr/bin/env bash
# Compile all .ts translation files into binary .qm files
set -euo pipefail
cd "$(dirname "$0")/.."

for ts in src/cardforge/i18n/cardforge_*.ts; do
    .venv/bin/pyside6-lrelease "$ts"
done

echo "Done. .qm files written to src/cardforge/i18n/"
