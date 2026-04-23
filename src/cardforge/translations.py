"""
i18n-Infrastruktur für CardForge.

Unterstützte Sprachen (ISO-639-1 / IETF-Tag):
    de      – Deutsch
    en      – English  (Quellsprache, kein .qm nötig)
    es      – Español
    fr      – Français
    ja      – 日本語
    pt_BR   – Português (Brasil)
    ru      – Русский
    zh_CN   – 中文 (简体)

Workflow für Entwickler::

    # Strings aus Python-Quellen extrahieren / .ts-Dateien aktualisieren:
    pyside6-lupdate src/cardforge/*.py -ts src/cardforge/i18n/cardforge_de.ts ...

    # .qm-Binaries kompilieren:
    pyside6-lrelease src/cardforge/i18n/cardforge_de.ts ...

    # Bequem per Skript:
    scripts/update_translations.sh
    scripts/compile_translations.sh
"""

from __future__ import annotations

import os

from PySide6.QtCore import QLocale, QSettings, QTranslator
from PySide6.QtWidgets import QApplication

# Alle unterstützten Sprachen: Code → Anzeigename (in der jeweiligen Sprache)
SUPPORTED_LANGUAGES: dict[str, str] = {
    "en": "English",
    "de": "Deutsch",
    "es": "Español",
    "fr": "Français",
    "ja": "日本語",
    "pt_BR": "Português (Brasil)",
    "ru": "Русский",
    "zh_CN": "中文 (简体)",
}

_I18N_DIR = os.path.join(os.path.dirname(__file__), "i18n")
_SETTINGS_KEY = "language"


# ---------------------------------------------------------------------------
# Öffentliche API
# ---------------------------------------------------------------------------


def install_translator(app: QApplication, locale: str | None = None) -> QTranslator | None:
    """Lädt und installiert die beste passende .qm-Datei für *locale*.

    *locale* kann ein vollständiger Locale-String (``"de_DE"``) oder ein
    kurzer Sprachcode (``"de"``) sein.  Bei ``None`` wird das Systemgebietsschema
    verwendet.  Englisch (``"en"*``) benötigt keine .qm-Datei – die Quellstrings
    dienen als Fallback.

    Gibt den installierten QTranslator zurück oder ``None`` falls kein passende
    .qm-Datei gefunden wurde (App zeigt dann englische Quellstrings).
    """
    if locale is None:
        locale = QLocale.system().name()  # z. B. "de_DE"

    # Kandidaten: vollständiger Locale zuerst, dann nur Sprachcode
    candidates: list[str] = [locale]
    if "_" in locale:
        candidates.append(locale.split("_")[0])

    translator = QTranslator(app)
    for name in candidates:
        qm_path = os.path.join(_I18N_DIR, f"cardforge_{name}.qm")
        if translator.load(qm_path):
            app.installTranslator(translator)
            return translator

    return None


def saved_language() -> str | None:
    """Gibt den in QSettings gespeicherten Sprachcode zurück, oder ``None``
    (→ Systemgebietsschema wird verwendet)."""
    s = QSettings("CardForge", "CardForge")
    return s.value(_SETTINGS_KEY, None)  # type: ignore[return-value]


def effective_language() -> str:
    """Gibt den tatsächlich aktiven Sprachcode zurück.

    Falls kein Code gespeichert ist, wird das System-Locale gegen
    ``SUPPORTED_LANGUAGES`` abgeglichen (Fallback: ``"en"``).  Das Ergebnis
    entspricht dem, was ``install_translator`` tatsächlich lädt.
    """
    saved = saved_language()
    if saved:
        return saved
    locale = QLocale.system().name()  # z. B. "de_DE"
    if locale in SUPPORTED_LANGUAGES:
        return locale
    lang = locale.split("_")[0]
    if lang in SUPPORTED_LANGUAGES:
        return lang
    return "en"


def save_language(lang_code: str | None) -> None:
    """Speichert die Sprachauswahl in QSettings."""
    s = QSettings("CardForge", "CardForge")
    if lang_code is None:
        s.remove(_SETTINGS_KEY)
    else:
        s.setValue(_SETTINGS_KEY, lang_code)
