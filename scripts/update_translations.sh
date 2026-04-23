#!/usr/bin/env bash
# Extract/update translatable strings from all source files into .ts files
set -euo pipefail
cd "$(dirname "$0")/.."

.venv/bin/pyside6-lupdate \
    main.py \
    src/cardforge/about_dialog.py \
    src/cardforge/canvas.py \
    src/cardforge/icon_picker_dialog.py \
    src/cardforge/icons.py \
    src/cardforge/mail_merge.py \
    src/cardforge/main_window.py \
    src/cardforge/models.py \
    src/cardforge/paper_template_dialog.py \
    src/cardforge/pdf_export.py \
    src/cardforge/print_dialog.py \
    src/cardforge/print_preview.py \
    src/cardforge/properties_panel.py \
    src/cardforge/renderer.py \
    src/cardforge/theme.py \
    src/cardforge/translations.py \
    -ts \
    src/cardforge/i18n/cardforge_de.ts \
    src/cardforge/i18n/cardforge_es.ts \
    src/cardforge/i18n/cardforge_fr.ts \
    src/cardforge/i18n/cardforge_ja.ts \
    src/cardforge/i18n/cardforge_pt_BR.ts \
    src/cardforge/i18n/cardforge_ru.ts \
    src/cardforge/i18n/cardforge_zh_CN.ts

echo "Done. Fill new strings with: .venv/bin/python scripts/fill_translations.py"
