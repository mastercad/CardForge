"""
End-to-End-Tests für Recent Files.

Kein Mocking von QSettings – alle Tests schreiben echte INI-Dateien auf dem
Dateisystem und lesen sie mit echter QSettings-Instanz wieder ein. Damit werden
Probleme aufgedeckt, die durch rein gemockte Unit-Tests unsichtbar bleiben
(z. B. Qt gibt einen einzelnen INI-Listeneintrag als str zurück, nicht als list).
"""

from __future__ import annotations

import os
import sys

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from cardforge.models import CardLayout, Project

# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def _make_project_file(tmp_path, name: str = "testprojekt") -> str:
    """Erstellt eine echte .vcproj-Datei auf dem Dateisystem."""
    p = Project(name=name)
    p.cards.append(CardLayout(name="Karte 1"))
    f = tmp_path / f"{name}.vcproj"
    p.save(str(f))
    return str(f)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def qapp_instance():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv[:1])
    return app


@pytest.fixture()
def isolated_settings(tmp_path, monkeypatch):
    """Echte QSettings-Isolation pro Test: eigenes XDG_CONFIG_HOME-Verzeichnis.

    Jeder Test bekommt ein frisches, leeres Konfig-Verzeichnis.  So akkumulieren
    sich keine Einträge zwischen Tests und die echten Benutzer-Settings werden
    nie berührt.
    """
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(cfg_dir))
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(cfg_dir))
    QSettings.setPath(QSettings.Format.NativeFormat, QSettings.Scope.UserScope, str(cfg_dir))
    return cfg_dir


@pytest.fixture()
def main_window(qapp_instance, isolated_settings):
    """Echtes MainWindow, kein Mocking."""
    from cardforge.main_window import MainWindow

    win = MainWindow()
    yield win
    win.close()


# ---------------------------------------------------------------------------
# Tests: Schreiben und Lesen über echte QSettings
# ---------------------------------------------------------------------------


class TestRecentFilesE2E:
    """Vollständige Round-Trip-Tests ohne jegliches Mocking."""

    def test_single_entry_survives_roundtrip(self, main_window, tmp_path, isolated_settings):
        """Kern-Regression: Ein einzelner Eintrag wird von Qt als str gespeichert.
        _recent_paths() muss ihn trotzdem als list[str] zurückgeben."""
        proj_file = _make_project_file(tmp_path, "einzel")

        # Direkt in echte QSettings schreiben (wie Qt es intern tut: als str, nicht list)
        s = QSettings("CardForge", "CardForge")
        s.setValue("recentFiles", proj_file)  # explizit str, nicht list
        s.sync()

        # Jetzt _recent_paths() aufrufen – muss trotzdem list zurückgeben
        result = main_window._recent_paths()
        assert isinstance(result, list), "_recent_paths() muss immer eine list zurückgeben"
        assert result == [proj_file]

    def test_add_then_read_single_entry(self, main_window, tmp_path, isolated_settings):
        """Nach _add_recent_path() mit einem Pfad muss der Pfad wieder lesbar sein."""
        proj_file = _make_project_file(tmp_path, "einzelpfad")

        main_window._add_recent_path(proj_file)

        # Neues QSettings-Objekt – simuliert Neustart der Anwendung
        s = QSettings("CardForge", "CardForge")
        s.value("recentFiles", [])  # echten Wert einlesen zur Verifikation
        result = main_window._recent_paths()
        assert isinstance(result, list)
        assert os.path.abspath(proj_file) in result

    def test_add_then_read_multiple_entries(self, main_window, tmp_path, isolated_settings):
        """Mehrere Einträge bleiben als list erhalten und werden in richtiger Reihenfolge zurückgegeben."""
        f1 = _make_project_file(tmp_path, "alpha")
        f2 = _make_project_file(tmp_path, "beta")
        f3 = _make_project_file(tmp_path, "gamma")

        main_window._add_recent_path(f1)
        main_window._add_recent_path(f2)
        main_window._add_recent_path(f3)

        result = main_window._recent_paths()
        assert isinstance(result, list)
        # Neueste zuerst
        assert result[0] == os.path.abspath(f3)
        assert result[1] == os.path.abspath(f2)
        assert result[2] == os.path.abspath(f1)

    def test_menu_shows_entry_after_add(self, main_window, tmp_path, isolated_settings):
        """Das Recent-Files-Menü enthält nach _add_recent_path() einen echten Eintrag."""
        proj_file = _make_project_file(tmp_path, "menutest")

        main_window._add_recent_path(proj_file)

        actions = [a for a in main_window._recent_menu.actions() if a.isEnabled()]
        labels = [a.text() for a in actions]
        assert "menutest.vcproj" in labels, f"Dateiname nicht im Menü. Gefunden: {labels}"

    def test_no_pollution_of_real_config(self, main_window, tmp_path, isolated_settings):
        """Tests dürfen die echte Benutzerkonfiguration niemals verändern."""
        real_config = os.path.expanduser("~/.config/CardForge/CardForge.conf")
        mtime_before = os.path.getmtime(real_config) if os.path.exists(real_config) else None

        proj_file = _make_project_file(tmp_path, "pollution_check")
        main_window._add_recent_path(proj_file)

        mtime_after = os.path.getmtime(real_config) if os.path.exists(real_config) else None
        assert mtime_before == mtime_after, (
            "FEHLER: Test hat die echte Benutzerkonfiguration verändert! "
            f"mtime vorher={mtime_before}, nachher={mtime_after}"
        )

    def test_empty_string_in_settings_returns_empty_list(self, main_window, isolated_settings):
        """Leerer String in QSettings darf nicht als Eintrag interpretiert werden."""
        s = QSettings("CardForge", "CardForge")
        s.setValue("recentFiles", "")
        s.sync()

        result = main_window._recent_paths()
        assert result == [], f"Leerer String darf nicht als Pfad gelten, aber got: {result}"

    def test_open_project_adds_to_recent(self, main_window, tmp_path, isolated_settings):
        """Nach dem Öffnen eines Projekts steht es in der Recent-Files-Liste."""
        proj_file = _make_project_file(tmp_path, "geöffnet")

        main_window._open_recent(proj_file)

        result = main_window._recent_paths()
        assert os.path.abspath(proj_file) in result, (
            f"Geöffnetes Projekt fehlt in Recent Files. recent_paths={result}"
        )

    def test_nonexistent_file_filtered_from_menu(self, main_window, isolated_settings):
        """Nicht mehr vorhandene Dateien dürfen nicht im Menü erscheinen."""
        s = QSettings("CardForge", "CardForge")
        s.setValue("recentFiles", "/nicht/vorhanden.vcproj")
        s.sync()

        main_window._update_recent_menu()

        enabled_actions = [a for a in main_window._recent_menu.actions() if a.isEnabled()]
        assert enabled_actions == [], (
            f"Nicht vorhandene Datei erscheint im Menü: {[a.text() for a in enabled_actions]}"
        )
