"""Tests für cardforge.theme – Dark-/Light-/System-Mode."""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Hilfsfunktion: _SYSTEM_DARK zurücksetzen zwischen Tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_system_dark():
    """Setzt das Modul-Global _SYSTEM_DARK vor jedem Test zurück."""
    import cardforge.theme as _t

    _t._SYSTEM_DARK = None  # noqa: SLF001
    yield
    _t._SYSTEM_DARK = None  # noqa: SLF001


# ---------------------------------------------------------------------------
# detect_system_theme
# ---------------------------------------------------------------------------


class TestDetectSystemTheme:
    def test_with_running_qapp_sets_system_dark(self, qapp):
        import cardforge.theme as _t

        assert _t._SYSTEM_DARK is None  # noqa: SLF001
        _t.detect_system_theme()
        # nach dem Aufruf muss _SYSTEM_DARK ein bool sein
        assert isinstance(_t._SYSTEM_DARK, bool)  # noqa: SLF001

    def test_without_qapp_does_nothing(self, monkeypatch):
        """Ohne laufende QApplication darf die Funktion keinen Fehler werfen und _SYSTEM_DARK bleibt None."""
        from PySide6.QtWidgets import QApplication

        import cardforge.theme as _t

        monkeypatch.setattr(QApplication, "instance", staticmethod(lambda: None))
        _t.detect_system_theme()
        assert _t._SYSTEM_DARK is None  # noqa: SLF001

    def test_fallback_via_attribute_error(self, qapp, monkeypatch):
        """Wenn colorScheme() nicht verfügbar ist (AttributeError), wird die Palette-Helligkeit genutzt."""

        import cardforge.theme as _t

        # style_hints-Objekt ohne colorScheme-Attribut simulieren
        class _FakeHints:
            pass

        monkeypatch.setattr(qapp, "styleHints", lambda: _FakeHints())
        _t.detect_system_theme()
        assert isinstance(_t._SYSTEM_DARK, bool)  # noqa: SLF001


# ---------------------------------------------------------------------------
# is_system_dark
# ---------------------------------------------------------------------------


class TestIsSystemDark:
    def test_returns_bool(self, qapp):
        from cardforge.theme import is_system_dark

        result = is_system_dark()
        assert isinstance(result, bool)

    def test_calls_detect_when_none(self, qapp):
        """Wenn _SYSTEM_DARK noch None ist, ruft is_system_dark() detect_system_theme() auf."""
        import cardforge.theme as _t

        _t._SYSTEM_DARK = None  # noqa: SLF001
        result = _t.is_system_dark()
        assert isinstance(result, bool)

    def test_returns_true_when_system_dark_is_true(self):
        import cardforge.theme as _t

        _t._SYSTEM_DARK = True  # noqa: SLF001
        assert _t.is_system_dark() is True

    def test_returns_false_when_system_dark_is_false(self):
        import cardforge.theme as _t

        _t._SYSTEM_DARK = False  # noqa: SLF001
        assert _t.is_system_dark() is False

    def test_default_true_when_detect_yields_none(self, monkeypatch):
        """Falls detect_system_theme() _SYSTEM_DARK nicht setzt, gibt is_system_dark() True zurück."""
        import cardforge.theme as _t

        # detect_system_theme wird aufgerufen aber setzt _SYSTEM_DARK nicht
        monkeypatch.setattr(_t, "detect_system_theme", lambda: None)
        _t._SYSTEM_DARK = None  # noqa: SLF001
        result = _t.is_system_dark()
        assert result is True


# ---------------------------------------------------------------------------
# resolve_theme
# ---------------------------------------------------------------------------


class TestResolveTheme:
    def test_dark_resolves_to_dark(self):
        from cardforge.theme import resolve_theme

        assert resolve_theme("dark") == "dark"

    def test_light_resolves_to_light(self):
        from cardforge.theme import resolve_theme

        assert resolve_theme("light") == "light"

    def test_unknown_resolves_to_dark(self):
        from cardforge.theme import resolve_theme

        assert resolve_theme("foobar") == "dark"

    def test_system_dark_resolves_to_dark(self):
        import cardforge.theme as _t

        _t._SYSTEM_DARK = True  # noqa: SLF001
        assert _t.resolve_theme("system") == "dark"

    def test_system_light_resolves_to_light(self):
        import cardforge.theme as _t

        _t._SYSTEM_DARK = False  # noqa: SLF001
        assert _t.resolve_theme("system") == "light"


# ---------------------------------------------------------------------------
# get_saved_theme / save_theme
# ---------------------------------------------------------------------------


class TestSaveAndGetTheme:
    def test_default_is_system(self, qapp):
        from PySide6.QtCore import QSettings

        # Eintrag löschen, damit Defaultwert greift
        s = QSettings("CardForge", "CardForge")
        s.remove("theme")
        s.sync()

        from cardforge.theme import get_saved_theme

        assert get_saved_theme() == "system"

    def test_save_dark_and_retrieve(self, qapp):
        from cardforge.theme import get_saved_theme, save_theme

        save_theme("dark")
        assert get_saved_theme() == "dark"

    def test_save_light_and_retrieve(self, qapp):
        from cardforge.theme import get_saved_theme, save_theme

        save_theme("light")
        assert get_saved_theme() == "light"

    def test_save_system_and_retrieve(self, qapp):
        from cardforge.theme import get_saved_theme, save_theme

        save_theme("system")
        assert get_saved_theme() == "system"


# ---------------------------------------------------------------------------
# _build_palette
# ---------------------------------------------------------------------------


class TestBuildPalette:
    def test_dark_palette_returns_qpalette(self, qapp):
        from PySide6.QtGui import QPalette

        from cardforge.theme import DARK, _build_palette

        pal = _build_palette(DARK)
        assert isinstance(pal, QPalette)

    def test_light_palette_returns_qpalette(self, qapp):
        from PySide6.QtGui import QPalette

        from cardforge.theme import LIGHT, _build_palette

        pal = _build_palette(LIGHT)
        assert isinstance(pal, QPalette)

    def test_dark_window_color_matches_token(self, qapp):
        from PySide6.QtGui import QColor, QPalette

        from cardforge.theme import DARK, _build_palette

        pal = _build_palette(DARK)
        expected = QColor(DARK["BG_APP"])
        actual = pal.color(QPalette.ColorRole.Window)
        assert actual.name() == expected.name()

    def test_light_window_color_matches_token(self, qapp):
        from PySide6.QtGui import QColor, QPalette

        from cardforge.theme import LIGHT, _build_palette

        pal = _build_palette(LIGHT)
        expected = QColor(LIGHT["BG_APP"])
        actual = pal.color(QPalette.ColorRole.Window)
        assert actual.name() == expected.name()


# ---------------------------------------------------------------------------
# _build_stylesheet
# ---------------------------------------------------------------------------


class TestBuildStylesheet:
    def test_dark_stylesheet_is_nonempty_string(self):
        from cardforge.theme import DARK, _build_stylesheet

        ss = _build_stylesheet(DARK)
        assert isinstance(ss, str)
        assert len(ss) > 0

    def test_light_stylesheet_is_nonempty_string(self):
        from cardforge.theme import LIGHT, _build_stylesheet

        ss = _build_stylesheet(LIGHT)
        assert isinstance(ss, str)
        assert len(ss) > 0

    def test_dark_stylesheet_contains_bg_color(self):
        from cardforge.theme import DARK, _build_stylesheet

        ss = _build_stylesheet(DARK)
        assert DARK["BG_APP"] in ss

    def test_light_stylesheet_contains_bg_color(self):
        from cardforge.theme import LIGHT, _build_stylesheet

        ss = _build_stylesheet(LIGHT)
        assert LIGHT["BG_APP"] in ss


# ---------------------------------------------------------------------------
# apply_theme
# ---------------------------------------------------------------------------


class TestApplyTheme:
    def test_apply_dark(self, qapp):
        from cardforge.theme import apply_theme

        apply_theme(qapp, "dark")  # darf nicht werfen

    def test_apply_light(self, qapp):
        from cardforge.theme import apply_theme

        apply_theme(qapp, "light")

    def test_apply_system(self, qapp):
        from cardforge.theme import apply_theme

        apply_theme(qapp, "system")

    def test_apply_unknown_defaults_to_dark(self, qapp):
        """Unbekanntes Theme-Name fällt auf Dark zurück (via resolve_theme)."""
        from cardforge.theme import apply_theme

        apply_theme(qapp, "unknown_xyz")

    def test_apply_dark_sets_palette(self, qapp):
        import cardforge.theme as _t

        _t._SYSTEM_DARK = True  # noqa: SLF001
        _t.apply_theme(qapp, "dark")
        from PySide6.QtGui import QColor, QPalette

        expected_bg = QColor(_t.DARK["BG_APP"]).name()
        actual_bg = qapp.palette().color(QPalette.ColorRole.Window).name()
        assert actual_bg == expected_bg


# ---------------------------------------------------------------------------
# current_tokens
# ---------------------------------------------------------------------------


class TestCurrentTokens:
    def test_returns_dict(self, qapp):
        from cardforge.theme import current_tokens, save_theme

        save_theme("dark")
        tokens = current_tokens()
        assert isinstance(tokens, dict)

    def test_dark_tokens_contain_expected_keys(self, qapp):
        from cardforge.theme import DARK, current_tokens, save_theme

        save_theme("dark")
        tokens = current_tokens()
        for key in DARK:
            assert key in tokens

    def test_light_tokens_returned_when_saved_light(self, qapp):
        from cardforge.theme import LIGHT, current_tokens, save_theme

        save_theme("light")
        tokens = current_tokens()
        assert tokens["BG_APP"] == LIGHT["BG_APP"]

    def test_dark_tokens_returned_when_saved_dark(self, qapp):
        from cardforge.theme import DARK, current_tokens, save_theme

        save_theme("dark")
        tokens = current_tokens()
        assert tokens["BG_APP"] == DARK["BG_APP"]

    def test_system_resolves_to_either_dark_or_light(self, qapp):
        from cardforge.theme import DARK, LIGHT, current_tokens, save_theme

        save_theme("system")
        tokens = current_tokens()
        assert tokens in (DARK, LIGHT)
