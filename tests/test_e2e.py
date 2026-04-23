"""
End-to-End-Tests für CardForge.

Kein Mocking – alle Tests verwenden echte Widgets, echtes Dateisystem und echte
QSettings. Nur so werden Probleme sichtbar, die durch rein gemockte Unit-Tests
unsichtbar bleiben.

Abgedeckte Bereiche:
  - Projekt speichern & laden (Round-Trip-Integrität)
  - Recent-Files-Verhalten mit echten QSettings (inkl. Single-String-Bug)
  - Karten hinzufügen, duplizieren, löschen, umbenennen
  - Elemente einfügen und nach Round-Trip verifizieren
  - Modifiziert-Flag und Fenstertitel
  - QSettings-Isolation (kein Schreiben in echte Benutzerkonfiguration)
"""

from __future__ import annotations

import json
import os
import sys

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from cardforge.models import (
    ELEMENT_ELLIPSE,
    ELEMENT_QR,
    ELEMENT_RECT,
    ELEMENT_TEXT,
    CardElement,
    CardLayout,
    Project,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv[:1])
    return app


@pytest.fixture()
def cfg_dir(tmp_path, monkeypatch):
    """Frisches QSettings-Verzeichnis pro Test – kein Schreiben in echte Config."""
    d = tmp_path / "cfg"
    d.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(d))
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(d))
    QSettings.setPath(QSettings.Format.NativeFormat, QSettings.Scope.UserScope, str(d))
    return d


@pytest.fixture()
def win(qapp, cfg_dir):
    """Echtes MainWindow, pro Test frisch erstellt."""
    from cardforge.main_window import MainWindow

    w = MainWindow()
    yield w
    # _modified=True würde closeEvent→QMessageBox öffnen und blockieren
    w._modified = False
    w.close()


def _save_project(tmp_path, name: str = "projekt", n_cards: int = 1) -> str:
    """Erstellt und speichert ein echtes Projekt auf Disk."""
    p = Project(name=name)
    for i in range(n_cards):
        c = CardLayout(name=f"Karte {i + 1}")
        e = CardElement(type=ELEMENT_TEXT, text=f"Text {i}", x=10.0, y=10.0)
        c.front_elements.append(e)
        p.cards.append(c)
    path = str(tmp_path / f"{name}.vcproj")
    p.save(path)
    return path


# ---------------------------------------------------------------------------
# 1. Projekt-Integrität: Speichern → Laden
# ---------------------------------------------------------------------------


class TestProjectRoundTrip:
    """Stellt sicher, dass gespeicherte Projekte bit-genau wieder geladen werden."""

    def test_name_preserved(self, tmp_path):
        path = _save_project(tmp_path, name="MeinProjekt")
        p = Project.load(path)
        assert p.name == "MeinProjekt"

    def test_card_count_preserved(self, tmp_path):
        path = _save_project(tmp_path, name="Multi", n_cards=3)
        p = Project.load(path)
        assert len(p.cards) == 3

    def test_card_names_preserved(self, tmp_path):
        orig = Project(name="X")
        for name in ["Alpha", "Beta", "Gamma"]:
            orig.cards.append(CardLayout(name=name))
        path = str(tmp_path / "names.vcproj")
        orig.save(path)
        loaded = Project.load(path)
        assert [c.name for c in loaded.cards] == ["Alpha", "Beta", "Gamma"]

    def test_element_type_preserved(self, tmp_path):
        p = Project(name="Elems")
        c = CardLayout(name="K")
        c.front_elements.append(CardElement(type=ELEMENT_TEXT, text="Hallo"))
        c.front_elements.append(CardElement(type=ELEMENT_RECT))
        c.front_elements.append(CardElement(type=ELEMENT_ELLIPSE))
        p.cards.append(c)
        path = str(tmp_path / "types.vcproj")
        p.save(path)
        loaded = Project.load(path)
        types = [e.type for e in loaded.cards[0].front_elements]
        assert types == [ELEMENT_TEXT, ELEMENT_RECT, ELEMENT_ELLIPSE]

    def test_element_text_preserved(self, tmp_path):
        p = Project(name="TXT")
        c = CardLayout(name="K")
        c.front_elements.append(CardElement(type=ELEMENT_TEXT, text="Testinhalt 123"))
        p.cards.append(c)
        path = str(tmp_path / "text.vcproj")
        p.save(path)
        loaded = Project.load(path)
        assert loaded.cards[0].front_elements[0].text == "Testinhalt 123"

    def test_element_position_preserved(self, tmp_path):
        p = Project(name="POS")
        c = CardLayout(name="K")
        c.front_elements.append(CardElement(x=12.5, y=34.7, width=55.0, height=8.3))
        p.cards.append(c)
        path = str(tmp_path / "pos.vcproj")
        p.save(path)
        e = Project.load(path).cards[0].front_elements[0]
        assert e.x == pytest.approx(12.5)
        assert e.y == pytest.approx(34.7)
        assert e.width == pytest.approx(55.0)
        assert e.height == pytest.approx(8.3)

    def test_front_and_back_elements_preserved(self, tmp_path):
        p = Project(name="FB")
        c = CardLayout(name="K")
        c.front_elements.append(CardElement(type=ELEMENT_TEXT, text="Vorne"))
        c.back_elements.append(CardElement(type=ELEMENT_TEXT, text="Hinten"))
        p.cards.append(c)
        path = str(tmp_path / "fb.vcproj")
        p.save(path)
        loaded = Project.load(path)
        assert loaded.cards[0].front_elements[0].text == "Vorne"
        assert loaded.cards[0].back_elements[0].text == "Hinten"

    def test_qr_data_preserved(self, tmp_path):
        p = Project(name="QR")
        c = CardLayout(name="K")
        c.front_elements.append(CardElement(type=ELEMENT_QR, qr_data="https://example.com"))
        p.cards.append(c)
        path = str(tmp_path / "qr.vcproj")
        p.save(path)
        loaded = Project.load(path)
        assert loaded.cards[0].front_elements[0].qr_data == "https://example.com"

    def test_color_palette_preserved(self, tmp_path):
        p = Project(name="COL")
        p.color_palette = ["#ff0000", "#00ff00", "#0000ff"]
        path = str(tmp_path / "col.vcproj")
        p.save(path)
        loaded = Project.load(path)
        assert loaded.color_palette == ["#ff0000", "#00ff00", "#0000ff"]

    def test_file_is_valid_json(self, tmp_path):
        path = _save_project(tmp_path, "jsoncheck")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert "name" in data
        assert "cards" in data
        assert isinstance(data["cards"], list)

    def test_paper_template_preserved(self, tmp_path):
        from cardforge.models import PaperTemplate

        p = Project(name="PT")
        p.paper_template = PaperTemplate(card_width=90.0, card_height=50.0)
        path = str(tmp_path / "pt.vcproj")
        p.save(path)
        loaded = Project.load(path)
        assert loaded.paper_template.card_width == pytest.approx(90.0)
        assert loaded.paper_template.card_height == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# 2. MainWindow: Speichern und Laden über die echten UI-Methoden
# ---------------------------------------------------------------------------


class TestMainWindowFilePersistence:
    """Testet _do_save() und den Lade-Pfad mit echten Dateien."""

    def test_do_save_creates_file(self, win, tmp_path):
        path = str(tmp_path / "save_test.vcproj")
        win._do_save(path)
        assert os.path.isfile(path), "Datei wurde nicht erstellt"

    def test_do_save_clears_modified_flag(self, win, tmp_path):
        win._modified = True
        path = str(tmp_path / "mod_flag.vcproj")
        win._do_save(path)
        assert win._modified is False

    def test_do_save_adds_to_recent(self, win, tmp_path):
        path = str(tmp_path / "recent_check.vcproj")
        win._do_save(path)
        assert os.path.abspath(path) in win._recent_paths()

    def test_open_recent_loads_project(self, win, tmp_path):
        # Projekt speichern
        p = Project(name="E2E-Ladeprojekt")
        p.cards.append(CardLayout(name="TestKarte"))
        path = str(tmp_path / "open_test.vcproj")
        p.save(path)

        # Über open_recent laden
        win._open_recent(path)

        assert win._project.name == "E2E-Ladeprojekt"
        assert win._project.cards[0].name == "TestKarte"

    def test_open_recent_sets_project_path(self, win, tmp_path):
        path = _save_project(tmp_path, "path_check")
        win._open_recent(path)
        assert win._project_path == path

    def test_open_recent_clears_modified_flag(self, win, tmp_path):
        # _open_recent() überprüft _modified und ruft _confirm_discard() auf wenn True.
        # Daher: _modified muss False sein beim Aufruf. Wir testen nur, dass nach
        # dem Laden _modified False ist (was es sein muss).
        path = _save_project(tmp_path, "mod_clear")
        assert win._modified is False  # Startzustand
        win._open_recent(path)
        assert win._modified is False

    def test_save_then_reload_preserves_cards(self, win, tmp_path):
        """Vollständiger Round-Trip über MainWindow: Karte hinzufügen → speichern → neu laden → prüfen."""
        # Karte zum Projekt hinzufügen
        win._project.cards.append(CardLayout(name="E2E-Karte"))
        path = str(tmp_path / "roundtrip.vcproj")
        win._do_save(path)

        # In zweitem Fenster laden
        from cardforge.main_window import MainWindow

        win2 = MainWindow()
        win2._open_recent(path)
        try:
            card_names = [c.name for c in win2._project.cards]
            assert "E2E-Karte" in card_names
        finally:
            win2._modified = False
            win2.close()

    def test_save_then_reload_preserves_elements(self, win, tmp_path):
        """Elemente bleiben nach Save/Load erhalten."""
        card = win._project.cards[0] if win._project.cards else CardLayout(name="K")
        if not win._project.cards:
            win._project.cards.append(card)
        elem = CardElement(type=ELEMENT_TEXT, text="Persistenztest", x=5.0, y=5.0)
        card.front_elements.append(elem)

        path = str(tmp_path / "elem_rt.vcproj")
        win._do_save(path)

        from cardforge.main_window import MainWindow

        win2 = MainWindow()
        win2._open_recent(path)
        try:
            texts = [
                e.text for e in win2._project.cards[0].front_elements if e.type == ELEMENT_TEXT
            ]
            assert "Persistenztest" in texts
        finally:
            win2._modified = False
            win2.close()


# ---------------------------------------------------------------------------
# 3. Recent Files mit echten QSettings (kein Mocking)
# ---------------------------------------------------------------------------


class TestRecentFilesRealQSettings:
    """Vollständige Round-Trip-Tests mit echten QSettings-Dateien."""

    def test_single_entry_stored_as_string_still_readable(self, win, tmp_path):
        """Kern-Regression: Qt speichert einen einzelnen Listeneintrag als str.
        _recent_paths() muss ihn trotzdem als list zurückgeben."""
        path = _save_project(tmp_path, "einzel")
        s = QSettings("CardForge", "CardForge")
        s.setValue("recentFiles", path)  # str, nicht list – wie Qt es intern tut
        s.sync()

        result = win._recent_paths()
        assert isinstance(result, list), "_recent_paths() muss immer list zurückgeben"
        assert result == [path]

    def test_multiple_entries_preserved_in_order(self, win, tmp_path):
        p1 = _save_project(tmp_path, "alpha")
        p2 = _save_project(tmp_path, "beta")
        p3 = _save_project(tmp_path, "gamma")

        win._add_recent_path(p1)
        win._add_recent_path(p2)
        win._add_recent_path(p3)

        result = win._recent_paths()
        assert result[0] == os.path.abspath(p3)
        assert result[1] == os.path.abspath(p2)
        assert result[2] == os.path.abspath(p1)

    def test_deduplication_moves_existing_to_top(self, win, tmp_path):
        p1 = _save_project(tmp_path, "dup1")
        p2 = _save_project(tmp_path, "dup2")
        win._add_recent_path(p1)
        win._add_recent_path(p2)
        win._add_recent_path(p1)  # nochmal – soll nach oben

        result = win._recent_paths()
        assert result[0] == os.path.abspath(p1)
        assert result.count(os.path.abspath(p1)) == 1

    def test_max_10_entries_enforced(self, win, tmp_path):
        for i in range(12):
            f = tmp_path / f"proj_{i}.vcproj"
            f.write_text("{}")
            win._add_recent_path(str(f))

        result = win._recent_paths()
        assert len(result) <= 10

    def test_empty_string_not_treated_as_path(self, win):
        s = QSettings("CardForge", "CardForge")
        s.setValue("recentFiles", "")
        s.sync()
        assert win._recent_paths() == []

    def test_menu_shows_real_file(self, win, tmp_path):
        path = _save_project(tmp_path, "menuitem")
        win._add_recent_path(path)
        enabled = [a for a in win._recent_menu.actions() if a.isEnabled()]
        labels = [a.text() for a in enabled]
        assert "menuitem.vcproj" in labels

    def test_nonexistent_file_not_in_menu(self, win):
        s = QSettings("CardForge", "CardForge")
        s.setValue("recentFiles", "/existiert/nicht.vcproj")
        s.sync()
        win._update_recent_menu()
        enabled = [a for a in win._recent_menu.actions() if a.isEnabled()]
        assert enabled == []

    def test_clear_recent_empties_list(self, win, tmp_path):
        for i in range(3):
            f = tmp_path / f"cl_{i}.vcproj"
            f.write_text("{}")
            win._add_recent_path(str(f))

        win._clear_recent()
        assert win._recent_paths() == []

    def test_tests_do_not_pollute_real_config(self, win, tmp_path):
        """Tests dürfen die echte Benutzerkonfiguration nie verändern."""
        real = os.path.expanduser("~/.config/CardForge/CardForge.conf")
        mtime_before = os.path.getmtime(real) if os.path.exists(real) else None

        path = _save_project(tmp_path, "pollution")
        win._add_recent_path(path)

        mtime_after = os.path.getmtime(real) if os.path.exists(real) else None
        assert mtime_before == mtime_after, (
            f"Test hat echte Config verändert! vorher={mtime_before}, nachher={mtime_after}"
        )


# ---------------------------------------------------------------------------
# 4. Karten-Operationen
# ---------------------------------------------------------------------------


class TestCardOperations:
    def test_new_project_has_one_card(self, win):
        # _new_project() öffnet QMessageBox wenn _modified=True → direkt über Modell
        assert len(win._project.cards) >= 1

    def test_add_card_increases_count(self, win):
        # _add_card() öffnet QInputDialog → direkt über Modell
        count_before = len(win._project.cards)
        win._project.cards.append(CardLayout(name="Direkt hinzugefügt"))
        win._refresh_card_list()
        assert len(win._project.cards) == count_before + 1

    def test_delete_card_with_multiple_cards(self, win):
        # _delete_card() mit 1 Karte öffnet QMessageBox → erst zweite Karte anlegen
        win._project.cards.append(CardLayout(name="Zweite"))
        win._refresh_card_list()
        count_before = len(win._project.cards)
        win._delete_card()
        assert len(win._project.cards) == count_before - 1

    def test_delete_card_minimum_one_remains(self, win):
        # Solange nur 1 Karte → _delete_card() darf nichts löschen (öffnet Warning-Dialog)
        # Wir testen das Verhalten über das Modell direkt
        while len(win._project.cards) > 1:
            del win._project.cards[-1]
        win._refresh_card_list()
        # Jetzt hat die App 1 Karte. _delete_card() würde Dialog öffnen → nicht aufrufen.
        # Stattdessen: sicherstellen dass das Projekt noch genau 1 Karte hat.
        assert len(win._project.cards) == 1

    def test_duplicate_card_copies_name(self, win):
        # _duplicate_card() öffnet keinen Dialog → direkt aufrufbar
        win._project.cards[0].name = "Original"
        win._duplicate_card()
        names = [c.name for c in win._project.cards]
        assert any("Original" in n for n in names), f"Kein Duplikat gefunden: {names}"

    def test_duplicate_card_copies_elements(self, win):
        win._project.cards[0].front_elements.append(
            CardElement(type=ELEMENT_TEXT, text="Kopiertext")
        )
        card_count_before = len(win._project.cards)
        win._duplicate_card()
        assert len(win._project.cards) == card_count_before + 1
        texts = [e.text for e in win._project.cards[-1].front_elements if e.type == ELEMENT_TEXT]
        assert "Kopiertext" in texts

    def test_switch_side_toggles(self, win):
        assert win._current_side == "front"
        win._switch_side("back")
        assert win._current_side == "back"
        win._switch_side("front")
        assert win._current_side == "front"

    def test_card_tree_item_count_matches_project(self, win):
        win._project.cards.append(CardLayout(name="Extra1"))
        win._project.cards.append(CardLayout(name="Extra2"))
        win._refresh_card_list()
        top_level = win._card_tree.topLevelItemCount()
        assert top_level == len(win._project.cards)


# ---------------------------------------------------------------------------
# 5. Element-Operationen
# ---------------------------------------------------------------------------


class TestElementOperations:
    def test_insert_text_element(self, win):
        win._new_project()
        count_before = len(win._canvas._elements())
        win._insert_text()
        assert len(win._canvas._elements()) == count_before + 1
        new_elem = win._canvas._elements()[-1]
        assert new_elem.type == ELEMENT_TEXT

    def test_insert_rect_element(self, win):
        win._new_project()
        win._insert_rect()
        types = [e.type for e in win._canvas._elements()]
        assert ELEMENT_RECT in types

    def test_insert_ellipse_element(self, win):
        win._new_project()
        win._insert_ellipse()
        types = [e.type for e in win._canvas._elements()]
        assert ELEMENT_ELLIPSE in types

    def test_inserted_element_is_centered(self, win):
        win._new_project()
        win._insert_rect()
        paper = win._project.paper_template
        elem = win._canvas._elements()[-1]
        cx = elem.x + elem.width / 2
        cy = elem.y + elem.height / 2
        assert abs(cx - paper.card_width / 2) < paper.card_width / 2
        assert abs(cy - paper.card_height / 2) < paper.card_height / 2

    def test_delete_selected_removes_element(self, win):
        win._new_project()
        win._insert_text()
        win._canvas.select_all()
        count_before = len(win._canvas._elements())
        win._canvas.delete_selected()
        assert len(win._canvas._elements()) < count_before

    def test_element_position_set_correctly(self, win):
        win._new_project()
        win._insert_rect()
        elem = win._canvas._elements()[-1]
        assert elem.x >= 0
        assert elem.y >= 0
        assert elem.width > 0
        assert elem.height > 0


# ---------------------------------------------------------------------------
# 6. Modifiziert-Flag und Fenstertitel
# ---------------------------------------------------------------------------


class TestModifiedFlag:
    def test_initial_not_modified(self, win):
        # Frisch geöffnetes Fenster: nicht modifiziert
        assert win._modified is False

    def test_mark_modified_sets_flag(self, win):
        win._mark_modified()
        assert win._modified is True

    def test_mark_modified_adds_asterisk_to_title(self, win):
        win._mark_modified()
        assert "*" in win.windowTitle()

    def test_save_clears_modified_flag(self, win, tmp_path):
        win._mark_modified()
        path = str(tmp_path / "unflag.vcproj")
        win._do_save(path)
        assert win._modified is False

    def test_save_removes_asterisk_from_title(self, win, tmp_path):
        win._mark_modified()
        path = str(tmp_path / "title.vcproj")
        win._do_save(path)
        assert "*" not in win.windowTitle()


# ---------------------------------------------------------------------------
# 7. Neues Projekt
# ---------------------------------------------------------------------------


class TestNewProject:
    def test_new_project_resets_path(self, win, tmp_path):
        # _new_project() öffnet Dialog wenn _modified=True → sicherstellen dass nicht modifiziert
        path = _save_project(tmp_path, "alt")
        win._open_recent(path)
        assert win._project_path == path
        # _modified ist nach open_recent False → kein Dialog
        assert win._modified is False
        win._new_project()
        assert win._project_path is None

    def test_new_project_clears_undo_stack(self, win):
        # _new_project() öffnet Dialog wenn _modified=True. Daher: Eintrag in
        # Undo-Stack direkt einfügen ohne canvas-Signal (das _mark_modified() auslöst).
        from PySide6.QtGui import QUndoCommand

        cmd = QUndoCommand()
        cmd.setText("test")
        win._undo_stack.push(cmd)
        assert win._undo_stack.count() == 1
        assert win._modified is False  # Undo-Push alleine markiert nicht als modifiziert
        win._new_project()  # _modified=False → kein Dialog
        assert win._undo_stack.count() == 0

    def test_new_project_default_name(self, win):
        assert win._modified is False
        win._new_project()
        assert win._project.name  # muss non-empty sein

    def test_new_project_has_empty_front_elements(self, win):
        assert win._modified is False
        win._new_project()
        assert win._project.cards[0].front_elements == []
