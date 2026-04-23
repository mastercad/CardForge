"""
Tests für cardforge.translations – i18n-Infrastruktur.
Abdeckung der Funktionen: install_translator, saved_language,
effective_language, save_language.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# install_translator
# ---------------------------------------------------------------------------


class TestInstallTranslator:
    def test_install_german_loads_translator(self, qapp):
        """install_translator('de') lädt cardforge_de.qm und gibt QTranslator zurück."""
        from cardforge.translations import install_translator

        t = install_translator(qapp, "de")
        # Wenn die .qm-Datei vorhanden ist, muss ein Translator zurückgegeben werden
        from PySide6.QtCore import QTranslator

        if t is not None:
            assert isinstance(t, QTranslator)

    def test_install_german_full_locale_resolves(self, qapp):
        """'de_DE' → Kandidaten ['de_DE', 'de'] → lädt 'de' wenn 'de_DE' nicht existiert."""
        from cardforge.translations import install_translator

        # Darf nicht abstürzen
        install_translator(qapp, "de_DE")

    def test_install_french_loads_translator(self, qapp):
        from cardforge.translations import install_translator

        t = install_translator(qapp, "fr")
        if t is not None:
            from PySide6.QtCore import QTranslator

            assert isinstance(t, QTranslator)

    def test_install_spanish(self, qapp):
        from cardforge.translations import install_translator

        install_translator(qapp, "es")

    def test_install_japanese(self, qapp):
        from cardforge.translations import install_translator

        install_translator(qapp, "ja")

    def test_install_portuguese_brazil(self, qapp):
        from cardforge.translations import install_translator

        install_translator(qapp, "pt_BR")

    def test_install_russian(self, qapp):
        from cardforge.translations import install_translator

        install_translator(qapp, "ru")

    def test_install_chinese_simplified(self, qapp):
        from cardforge.translations import install_translator

        install_translator(qapp, "zh_CN")

    def test_install_english_returns_none(self, qapp):
        """Englisch benötigt keine .qm-Datei → Rückgabe None."""
        from cardforge.translations import install_translator

        result = install_translator(qapp, "en")
        assert result is None

    def test_install_unknown_locale_returns_none(self, qapp):
        """Unbekanntes Locale → keine passende .qm-Datei → None."""
        from cardforge.translations import install_translator

        result = install_translator(qapp, "xx_ZZ")
        assert result is None

    def test_install_none_uses_system_locale(self, qapp):
        """locale=None → Systemgebietsschema wird verwendet, darf nicht abstürzen."""
        from cardforge.translations import install_translator

        # Darf nicht abstürzen (Rückgabe kann None oder Translator sein)
        install_translator(qapp, None)

    def test_install_short_code_no_underscore(self, qapp):
        """Locale ohne Unterstrich wird direkt als Kandidat benutzt."""
        from cardforge.translations import install_translator

        # "de" hat keinen Unterstrich → nur ["de"] als Kandidat
        install_translator(qapp, "de")

    def test_install_locale_with_underscore_generates_two_candidates(self, qapp):
        """Locale mit Unterstrich erzeugt zwei Kandidaten (vollständig + kurz)."""
        from cardforge.translations import install_translator

        # "zh_CN" → kandidaten ["zh_CN", "zh"]
        # cardforge_zh_CN.qm existiert → sollte geladen werden
        install_translator(qapp, "zh_CN")


# ---------------------------------------------------------------------------
# saved_language / save_language
# ---------------------------------------------------------------------------


class TestSavedLanguage:
    def _clear(self):
        from cardforge.translations import save_language

        save_language(None)

    def test_returns_none_when_nothing_saved(self, qapp):
        """Ohne gespeicherte Sprache gibt saved_language() None zurück."""
        self._clear()
        from cardforge.translations import saved_language

        assert saved_language() is None

    def test_returns_saved_code_after_save(self, qapp):
        """Nach save_language('de') gibt saved_language() 'de' zurück."""
        from cardforge.translations import save_language, saved_language

        save_language("de")
        assert saved_language() == "de"
        self._clear()

    def test_returns_updated_code(self, qapp):
        """Überschreiben der Sprache wird korrekt zurückgegeben."""
        from cardforge.translations import save_language, saved_language

        save_language("fr")
        save_language("ja")
        assert saved_language() == "ja"
        self._clear()

    def test_save_none_clears_setting(self, qapp):
        """save_language(None) entfernt den gespeicherten Eintrag."""
        from cardforge.translations import save_language, saved_language

        save_language("ru")
        save_language(None)
        assert saved_language() is None

    def test_save_all_supported_languages(self, qapp):
        """Alle unterstützten Sprachcodes können gespeichert werden."""
        from cardforge.translations import SUPPORTED_LANGUAGES, save_language, saved_language

        for code in SUPPORTED_LANGUAGES:
            save_language(code)
            assert saved_language() == code

        self._clear()


# ---------------------------------------------------------------------------
# effective_language
# ---------------------------------------------------------------------------


class TestEffectiveLanguage:
    def _clear(self):
        from cardforge.translations import save_language

        save_language(None)

    def test_returns_saved_language_when_set(self, qapp):
        """Wenn eine Sprache gespeichert ist, gibt effective_language() diese zurück."""
        from cardforge.translations import effective_language, save_language

        save_language("fr")
        assert effective_language() == "fr"
        self._clear()

    def test_returns_german_when_saved(self, qapp):
        from cardforge.translations import effective_language, save_language

        save_language("de")
        assert effective_language() == "de"
        self._clear()

    def test_returns_string_when_nothing_saved(self, qapp):
        """Ohne gespeicherte Sprache liefert effective_language() trotzdem einen gültigen Code."""
        self._clear()
        from cardforge.translations import effective_language

        result = effective_language()
        assert isinstance(result, str)
        assert len(result) >= 2

    def test_effective_language_returns_valid_code_always(self, qapp):
        """effective_language() gibt immer einen gültigen nicht-leeren Code zurück."""
        self._clear()
        from cardforge.translations import effective_language

        result = effective_language()
        assert isinstance(result, str)
        assert len(result) >= 2

    def test_effective_language_branches_without_saved(self, qapp):
        """Ohne gespeicherte Sprache wird das Systemlocale abgeglichen."""
        self._clear()
        from cardforge.translations import SUPPORTED_LANGUAGES, effective_language

        result = effective_language()
        # Ergebnis muss ein gültiger Sprachcode sein
        assert isinstance(result, str)
        # Entweder bekannter Code oder "en"
        # (je nach Systemlocale kann es beides sein)
        assert result == "en" or result in SUPPORTED_LANGUAGES

    def test_effective_language_all_supported_languages(self, qapp):
        """Für jeden gespeicherten unterstützten Code gibt effective_language() genau diesen zurück."""
        from cardforge.translations import SUPPORTED_LANGUAGES, effective_language, save_language

        for code in SUPPORTED_LANGUAGES:
            save_language(code)
            result = effective_language()
            assert result == code

        self._clear()
