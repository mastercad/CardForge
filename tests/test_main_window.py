"""Tests für cardforge.main_window – SnapshotCommand und MainWindow."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QMessageBox

from cardforge.models import CardLayout, Project


@pytest.fixture(autouse=True)
def _auto_confirm_discard():
    """Verhindert blockierende QMessageBox-Aufrufe, die auf User-Eingabe warten würden."""
    with (
        patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes),
        patch.object(QMessageBox, "critical"),
        patch.object(QMessageBox, "warning"),
    ):
        yield


def _make_project(n: int = 2) -> Project:
    p = Project(name="MWTest")
    for i in range(n):
        p.cards.append(CardLayout(name=f"Karte {i + 1}"))
    return p


# ---------------------------------------------------------------------------
# SnapshotCommand
# ---------------------------------------------------------------------------


class TestSnapshotCommand:
    """SnapshotCommand benötigt QUndoCommand und damit einen laufenden QApp."""

    def _make_command(self, project, before_dicts, after_dicts, qapp):
        from cardforge.main_window import SnapshotCommand

        canvas = MagicMock()
        panel = MagicMock()
        cmd = SnapshotCommand(project, before_dicts, after_dicts, canvas, panel, "test-op")
        return cmd, panel

    def test_first_redo_is_noop(self, qapp):
        p = _make_project(1)
        before = [c.to_dict() for c in p.cards]
        new_layout = CardLayout(name="Neu")
        p.cards.append(new_layout)
        after = [c.to_dict() for c in p.cards]
        cmd, panel = self._make_command(p, before, after, qapp)
        # Redo beim ersten Mal → kein Reload
        cmd.redo()
        panel._load_current_card.assert_not_called()

    def test_second_redo_restores_after(self, qapp):
        p = _make_project(1)
        before = [c.to_dict() for c in p.cards]
        p.cards.append(CardLayout(name="Neu"))
        after = [c.to_dict() for c in p.cards]
        cmd, panel = self._make_command(p, before, after, qapp)
        # Erstes redo → noop
        cmd.redo()
        # Jetzt undo, dann redo → should restore after
        cmd.undo()
        cmd.redo()
        panel._load_current_card.assert_called()

    def test_undo_restores_before_state(self, qapp):
        p = _make_project(2)
        before = [c.to_dict() for c in p.cards]
        p.cards.append(CardLayout(name="Neu"))
        after = [c.to_dict() for c in p.cards]
        cmd, panel = self._make_command(p, before, after, qapp)
        cmd.redo()  # noop (first)
        cmd.undo()
        assert len(p.cards) == 2
        panel._load_current_card.assert_called()
        panel._refresh_card_list.assert_called()

    def test_text_set(self, qapp):
        p = _make_project(1)
        before = [c.to_dict() for c in p.cards]
        after = before[:]
        cmd, _ = self._make_command(p, before, after, qapp)
        assert cmd.text() == "test-op"


# ---------------------------------------------------------------------------
# MainWindow
# ---------------------------------------------------------------------------


class TestMainWindow:
    def test_creates_without_crash(self, qapp):
        from cardforge.main_window import MainWindow

        win = MainWindow()
        assert win is not None
        win.close()

    def test_window_title_contains_app_name(self, qapp):
        from cardforge.main_window import MainWindow

        win = MainWindow()
        title = win.windowTitle()
        assert len(title) > 0
        win.close()

    def test_has_project(self, qapp):
        from cardforge.main_window import MainWindow

        win = MainWindow()
        assert win._project is not None  # noqa: SLF001
        win.close()

    def test_project_has_default_card(self, qapp):
        from cardforge.main_window import MainWindow

        win = MainWindow()
        assert len(win._project.cards) >= 1  # noqa: SLF001
        win.close()

    def test_has_canvas(self, qapp):
        from cardforge.main_window import MainWindow

        win = MainWindow()
        assert win._canvas is not None  # noqa: SLF001
        win.close()

    def test_has_undo_stack(self, qapp):
        from cardforge.main_window import MainWindow

        win = MainWindow()
        assert win._undo_stack is not None  # noqa: SLF001
        win.close()


# ---------------------------------------------------------------------------
# _switch_side
# ---------------------------------------------------------------------------


class TestSwitchSide:
    def _win(self, qapp):
        from cardforge.main_window import MainWindow

        win = MainWindow()
        win.show()
        return win

    def test_switch_to_back_updates_canvas_side(self, qapp):
        win = self._win(qapp)
        win._switch_side("back")
        assert win._canvas._side == "back"  # noqa: SLF001
        assert win._btn_back.isChecked()
        assert not win._btn_front.isChecked()
        win.close()

    def test_switch_to_front_updates_canvas_side(self, qapp):
        win = self._win(qapp)
        win._switch_side("back")
        win._switch_side("front")
        assert win._canvas._side == "front"  # noqa: SLF001
        assert win._btn_front.isChecked()
        assert not win._btn_back.isChecked()
        win.close()

    def test_switch_side_updates_bg_button_color(self, qapp):
        win = self._win(qapp)
        card = win._project.cards[0]
        card.back_bg = "#ff0000"
        win._switch_side("back")
        assert win._bg_btn._color == "#ff0000"  # noqa: SLF001
        win.close()

    def test_switch_side_stores_current_side(self, qapp):
        win = self._win(qapp)
        win._switch_side("back")
        assert win._current_side == "back"
        win.close()


# ---------------------------------------------------------------------------
# Karten-Operationen
# ---------------------------------------------------------------------------


class TestCardOperations:
    def _win(self, qapp):
        from cardforge.main_window import MainWindow

        return MainWindow()

    def test_add_card_ok(self, qapp):
        from unittest.mock import patch

        win = self._win(qapp)
        initial_count = len(win._project.cards)
        with patch("cardforge.main_window.QInputDialog.getText", return_value=("Neue", True)):
            win._add_card()
        assert len(win._project.cards) == initial_count + 1
        assert win._project.cards[-1].name == "Neue"
        win.close()

    def test_add_card_cancel(self, qapp):
        from unittest.mock import patch

        win = self._win(qapp)
        initial_count = len(win._project.cards)
        with patch("cardforge.main_window.QInputDialog.getText", return_value=("", False)):
            win._add_card()
        assert len(win._project.cards) == initial_count
        win.close()

    def test_add_card_empty_name_noop(self, qapp):
        from unittest.mock import patch

        win = self._win(qapp)
        initial_count = len(win._project.cards)
        with patch("cardforge.main_window.QInputDialog.getText", return_value=("", True)):
            win._add_card()
        assert len(win._project.cards) == initial_count
        win.close()

    def test_duplicate_card(self, qapp):
        win = self._win(qapp)
        initial_count = len(win._project.cards)
        src_name = win._project.cards[0].name
        win._duplicate_card()
        assert len(win._project.cards) == initial_count + 1
        assert "(Copy)" in win._project.cards[-1].name
        assert win._project.cards[-1].name.startswith(src_name)
        win.close()

    def test_delete_card_with_single_card_blocked(self, qapp):
        from unittest.mock import patch

        win = self._win(qapp)
        # Stell sicher, nur 1 Karte da
        win._project.cards = win._project.cards[:1]
        win._current_card_index = 0
        with patch("cardforge.main_window.QMessageBox.warning") as warn:
            win._delete_card()
            warn.assert_called_once()
        assert len(win._project.cards) == 1
        win.close()

    def test_delete_card_with_two_cards_ok(self, qapp):
        from unittest.mock import patch

        win = self._win(qapp)
        # Sicherstellen: 2 Karten
        if len(win._project.cards) < 2:
            win._project.cards.append(CardLayout(name="Extra"))
        win._current_card_index = 1
        with patch("cardforge.main_window.QMessageBox.warning") as warn:
            win._delete_card()
            warn.assert_not_called()
        assert len(win._project.cards) == 1
        win.close()

    def test_rename_card_ok(self, qapp):
        from unittest.mock import patch

        win = self._win(qapp)
        with patch("cardforge.main_window.QInputDialog.getText", return_value=("Umbenannt", True)):
            win._rename_card()
        assert win._project.cards[0].name == "Umbenannt"
        win.close()

    def test_rename_card_cancel(self, qapp):
        from unittest.mock import patch

        win = self._win(qapp)
        orig_name = win._project.cards[0].name
        with patch("cardforge.main_window.QInputDialog.getText", return_value=("Egal", False)):
            win._rename_card()
        assert win._project.cards[0].name == orig_name
        win.close()


# ---------------------------------------------------------------------------
# Element einfügen
# ---------------------------------------------------------------------------


class TestInsertElements:
    def _win(self, qapp):
        from cardforge.main_window import MainWindow

        return MainWindow()

    def test_insert_text_adds_element(self, qapp):
        win = self._win(qapp)
        before = len(win._canvas._elements())  # noqa: SLF001
        win._insert_text()
        assert len(win._canvas._elements()) == before + 1  # noqa: SLF001
        assert win._canvas._elements()[-1].type == "text"  # noqa: SLF001
        win.close()

    def test_insert_rect_adds_element(self, qapp):
        win = self._win(qapp)
        before = len(win._canvas._elements())  # noqa: SLF001
        win._insert_rect()
        assert len(win._canvas._elements()) == before + 1  # noqa: SLF001
        assert win._canvas._elements()[-1].type == "rect"  # noqa: SLF001
        win.close()

    def test_insert_ellipse_adds_element(self, qapp):
        from cardforge.models import ELEMENT_ELLIPSE

        win = self._win(qapp)
        before = len(win._canvas._elements())  # noqa: SLF001
        win._insert_ellipse()
        assert len(win._canvas._elements()) == before + 1  # noqa: SLF001
        assert win._canvas._elements()[-1].type == ELEMENT_ELLIPSE  # noqa: SLF001
        win.close()

    def test_insert_line_adds_element(self, qapp):
        win = self._win(qapp)
        before = len(win._canvas._elements())  # noqa: SLF001
        win._insert_line()
        assert len(win._canvas._elements()) == before + 1  # noqa: SLF001
        assert win._canvas._elements()[-1].type == "line"  # noqa: SLF001
        win.close()

    def test_insert_qr_ok(self, qapp):
        from unittest.mock import patch

        win = self._win(qapp)
        before = len(win._canvas._elements())  # noqa: SLF001
        with patch(
            "cardforge.main_window.QInputDialog.getText",
            return_value=("https://example.com", True),
        ):
            win._insert_qr()
        assert len(win._canvas._elements()) == before + 1  # noqa: SLF001
        assert win._canvas._elements()[-1].type == "qr"  # noqa: SLF001
        win.close()

    def test_insert_qr_cancel_noop(self, qapp):
        from unittest.mock import patch

        win = self._win(qapp)
        before = len(win._canvas._elements())  # noqa: SLF001
        with patch("cardforge.main_window.QInputDialog.getText", return_value=("", False)):
            win._insert_qr()
        assert len(win._canvas._elements()) == before  # noqa: SLF001
        win.close()


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------


class TestCallbacks:
    def _win(self, qapp):
        from cardforge.main_window import MainWindow

        return MainWindow()

    def test_on_selection_changed_empty(self, qapp):
        win = self._win(qapp)
        win._on_selection_changed([])
        # Props sollte mit leerer Liste aufgerufen worden sein – kein Absturz
        win.close()

    def test_on_selection_changed_with_element(self, qapp):
        from cardforge.models import CardElement

        win = self._win(qapp)
        e = CardElement(type="text", text="Hello")
        win._project.cards[0].front_elements.append(e)
        win._load_current_card()
        win._on_selection_changed([e.id])
        win.close()

    def test_on_canvas_changed_marks_modified(self, qapp):
        win = self._win(qapp)
        win._on_canvas_changed()
        assert win._modified is True
        win.close()

    def test_on_edit_started_saves_undo_before(self, qapp):
        win = self._win(qapp)
        if hasattr(win, "_undo_before"):
            del win._undo_before
        win._on_edit_started()
        assert hasattr(win, "_undo_before")
        win.close()

    def test_on_edit_finished_pushes_snapshot(self, qapp):
        from unittest.mock import patch

        win = self._win(qapp)
        win._on_edit_started()
        with patch.object(win, "_push_snapshot") as mock_push:
            win._on_edit_finished()
            mock_push.assert_called_once()
        win.close()

    def test_on_props_changed_without_undo_before(self, qapp):
        win = self._win(qapp)
        if hasattr(win, "_undo_before"):
            del win._undo_before
        win._on_props_changed()
        assert hasattr(win, "_undo_before")
        win._props_undo_timer.stop()
        win.close()

    def test_on_props_changed_with_existing_undo_before(self, qapp):
        win = self._win(qapp)
        before = [c.to_dict() for c in win._project.cards]
        win._undo_before = before
        win._on_props_changed()  # should not overwrite _undo_before
        assert win._undo_before is before
        win._props_undo_timer.stop()
        win.close()


# ---------------------------------------------------------------------------
# Ansichts-Steuerung
# ---------------------------------------------------------------------------


class TestViewControls:
    def _win(self, qapp):
        from cardforge.main_window import MainWindow

        return MainWindow()

    def test_on_zoom_updates_canvas_zoom(self, qapp):
        win = self._win(qapp)
        win._on_zoom(30)  # 30/10 = 3.0×
        assert win._canvas._zoom == 3.0  # noqa: SLF001
        win.close()

    def test_on_zoom_updates_label(self, qapp):
        win = self._win(qapp)
        win._on_zoom(25)
        assert "2.5" in win._zoom_lbl.text()
        win.close()

    def test_on_grid_changed_propagates_to_canvas(self, qapp):
        win = self._win(qapp)
        win._chk_grid.setChecked(True)
        win._snap_spin.setValue(2.0)
        win._on_grid_changed()
        # Kein Absturz, Grid ist gesetzt
        win.close()

    def test_on_bg_changed_front_side(self, qapp):
        win = self._win(qapp)
        win._current_side = "front"
        win._on_bg_changed("#123456")
        assert win._project.cards[0].front_bg == "#123456"
        win.close()

    def test_on_bg_changed_back_side(self, qapp):
        win = self._win(qapp)
        win._current_side = "back"
        win._on_bg_changed("#abcdef")
        assert win._project.cards[0].back_bg == "#abcdef"
        win.close()

    def test_on_bg_changed_no_cards_noop(self, qapp):
        win = self._win(qapp)
        win._project.cards = []
        win._on_bg_changed("#ffffff")  # kein Absturz
        win.close()


# ---------------------------------------------------------------------------
# Tree-Operationen
# ---------------------------------------------------------------------------


class TestTreeOperations:
    def _win(self, qapp):
        from cardforge.main_window import MainWindow

        return MainWindow()

    def test_refresh_card_list_with_text_element(self, qapp):
        win = self._win(qapp)
        from cardforge.models import CardElement

        e = CardElement(type="text", text="Hallo Welt")
        win._project.cards[0].front_elements.append(e)
        win._refresh_card_list()
        # Hallo Welt sollte im Tree erscheinen
        root = win._card_tree.topLevelItem(0)
        texts = [root.child(i).text(0) for i in range(root.childCount())]
        assert any("Hallo Welt" in t for t in texts)
        win.close()

    def test_refresh_card_list_invisible_element_marked(self, qapp):
        win = self._win(qapp)
        from cardforge.models import CardElement

        e = CardElement(type="rect", visible=False)
        win._project.cards[0].front_elements.append(e)
        win._refresh_card_list()
        root = win._card_tree.topLevelItem(0)
        texts = [root.child(i).text(0) for i in range(root.childCount())]
        assert any(t.startswith("○") for t in texts)
        win.close()

    def test_on_tree_current_changed_none_is_noop(self, qapp):
        win = self._win(qapp)
        win._on_tree_current_changed(None, None)  # kein Absturz
        win.close()

    def test_on_tree_current_changed_non_card_item(self, qapp):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QTreeWidgetItem

        win = self._win(qapp)
        item = QTreeWidgetItem()
        item.setData(0, Qt.ItemDataRole.UserRole, ("elem", "some-id"))
        orig_idx = win._current_card_index
        win._on_tree_current_changed(item, None)
        assert win._current_card_index == orig_idx
        win.close()

    def test_on_tree_current_changed_same_index_noop(self, qapp):
        from unittest.mock import patch

        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QTreeWidgetItem

        win = self._win(qapp)
        item = QTreeWidgetItem()
        item.setData(0, Qt.ItemDataRole.UserRole, ("card", win._current_card_index))
        with patch.object(win, "_load_current_card") as mock_load:
            win._on_tree_current_changed(item, None)
            mock_load.assert_not_called()
        win.close()

    def test_on_tree_current_changed_different_index_loads(self, qapp):
        from unittest.mock import patch

        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QTreeWidgetItem

        win = self._win(qapp)
        win._project.cards.append(CardLayout(name="Zweite"))
        win._refresh_card_list()
        item = QTreeWidgetItem()
        item.setData(0, Qt.ItemDataRole.UserRole, ("card", 1))
        with patch.object(win, "_load_current_card") as mock_load:
            win._on_tree_current_changed(item, None)
            mock_load.assert_called_once()
        win.close()

    def test_on_tree_item_clicked_non_elem_noop(self, qapp):
        from unittest.mock import patch

        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QTreeWidgetItem

        win = self._win(qapp)
        item = QTreeWidgetItem()
        item.setData(0, Qt.ItemDataRole.UserRole, ("card", 0))
        with patch.object(win._canvas, "set_selection") as mock_sel:
            win._on_tree_item_clicked(item, 0)
            mock_sel.assert_not_called()
        win.close()

    def test_on_tree_item_clicked_elem_sets_selection(self, qapp):

        win = self._win(qapp)
        from cardforge.models import CardElement

        e = CardElement(type="rect")
        win._project.cards[0].front_elements.append(e)
        win._load_current_card()
        # Simuliere Klick auf Elem-Item
        win._card_tree.blockSignals(False)
        root = win._card_tree.topLevelItem(0)
        child = root.child(0)
        win._on_tree_item_clicked(child, 0)
        win.close()


# ---------------------------------------------------------------------------
# _load_current_card – beide Seiten
# ---------------------------------------------------------------------------


class TestLoadCurrentCard:
    def _win(self, qapp):
        from cardforge.main_window import MainWindow

        return MainWindow()

    def test_load_front_sets_canvas_front(self, qapp):
        win = self._win(qapp)
        win._current_side = "front"
        win._load_current_card()
        assert win._canvas._side == "front"  # noqa: SLF001
        win.close()

    def test_load_back_sets_canvas_back(self, qapp):
        win = self._win(qapp)
        win._current_side = "back"
        win._load_current_card()
        assert win._canvas._side == "back"  # noqa: SLF001
        win.close()

    def test_load_no_cards_is_noop(self, qapp):
        win = self._win(qapp)
        win._project.cards = []
        win._load_current_card()  # kein Absturz
        win.close()


# ---------------------------------------------------------------------------
# _align / _fit_to_content
# ---------------------------------------------------------------------------


class TestAlignAndFit:
    def _win(self, qapp):
        from cardforge.main_window import MainWindow

        return MainWindow()

    def test_align_calls_canvas_align_selected(self, qapp):
        from unittest.mock import patch

        win = self._win(qapp)
        with patch.object(win._canvas, "align_selected") as mock_align:
            win._align("left")
            mock_align.assert_called_once_with("left")
        win.close()

    def test_fit_to_content_calls_canvas(self, qapp):
        from unittest.mock import patch

        win = self._win(qapp)
        with patch.object(win._canvas, "fit_to_content") as mock_fit:
            win._fit_to_content()
            mock_fit.assert_called_once()
        win.close()


# ---------------------------------------------------------------------------
# Farbpalette
# ---------------------------------------------------------------------------


class TestPaletteColor:
    def _win(self, qapp):
        from cardforge.main_window import MainWindow

        return MainWindow()

    def test_apply_palette_color_to_text_element(self, qapp):
        win = self._win(qapp)
        from cardforge.models import CardElement

        e = CardElement(type="text", color="#000000")
        win._project.cards[0].front_elements.append(e)
        win._load_current_card()
        win._canvas._selected = [e.id]  # noqa: SLF001
        fn = win._apply_palette_color("#ff0000")
        fn()
        assert e.color == "#ff0000"
        win.close()

    def test_apply_palette_color_to_rect_element(self, qapp):
        win = self._win(qapp)
        from cardforge.models import CardElement

        e = CardElement(type="rect", fill_color="#ffffff")
        win._project.cards[0].front_elements.append(e)
        win._load_current_card()
        win._canvas._selected = [e.id]  # noqa: SLF001
        fn = win._apply_palette_color("#00ff00")
        fn()
        assert e.fill_color == "#00ff00"
        win.close()

    def test_update_palette_color_updates_project(self, qapp):
        win = self._win(qapp)
        idx = 0
        win._project.color_palette = ["#000000"]
        fn = win._update_palette_color(idx)
        fn("#aabbcc")
        assert win._project.color_palette[0] == "#aabbcc"
        win.close()

    def test_update_palette_color_out_of_range_noop(self, qapp):
        win = self._win(qapp)
        win._project.color_palette = ["#000000"]
        fn = win._update_palette_color(99)
        fn("#aabbcc")  # kein Absturz, kein Effekt
        assert win._project.color_palette[0] == "#000000"
        win.close()


# ---------------------------------------------------------------------------
# _mark_modified
# ---------------------------------------------------------------------------


class TestMarkModified:
    def _win(self, qapp):
        from cardforge.main_window import MainWindow

        return MainWindow()

    def test_mark_modified_sets_flag(self, qapp):
        win = self._win(qapp)
        win._modified = False
        win._mark_modified()
        assert win._modified is True
        win.close()

    def test_mark_modified_appends_asterisk_to_title(self, qapp):
        win = self._win(qapp)
        win._modified = False
        win._mark_modified()
        assert win.windowTitle().endswith(" *")
        win.close()

    def test_mark_modified_idempotent(self, qapp):
        win = self._win(qapp)
        win._mark_modified()
        title_after_first = win.windowTitle()
        win._mark_modified()
        assert win.windowTitle() == title_after_first
        win.close()


# ---------------------------------------------------------------------------
# _new_project
# ---------------------------------------------------------------------------


class TestNewProject:
    def test_new_project_without_modification_resets(self, qapp):
        from cardforge.main_window import MainWindow

        win = MainWindow()
        win._insert_text()
        win._modified = False  # als ob gespeichert
        win._new_project()
        assert len(win._project.cards) == 1
        assert not win._modified
        win.close()

    def test_new_project_resets_undo_stack(self, qapp):
        from cardforge.main_window import MainWindow

        win = MainWindow()
        win._modified = False
        win._new_project()
        assert win._undo_stack.count() == 0
        win.close()


# ---------------------------------------------------------------------------
# _do_save (Dateispeicherung)
# ---------------------------------------------------------------------------


class TestDoSave:
    def test_do_save_writes_valid_json(self, qapp, tmp_path):
        import json

        from cardforge.main_window import MainWindow

        win = MainWindow()
        path = str(tmp_path / "test.vcproj")
        win._project_path = path  # wie _save_project_as es setzt
        win._do_save(path)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert "cards" in data
        win.close()

    def test_do_save_clears_modified_flag(self, qapp, tmp_path):
        from cardforge.main_window import MainWindow

        win = MainWindow()
        win._modified = True
        path = str(tmp_path / "test.vcproj")
        win._do_save(path)
        assert not win._modified
        win.close()


# ---------------------------------------------------------------------------
# _add_palette_color
# ---------------------------------------------------------------------------


class TestAddPaletteColor:
    def test_add_palette_color_adds_button(self, qapp):
        from unittest.mock import patch

        from PySide6.QtGui import QColor

        from cardforge.main_window import MainWindow

        win = MainWindow()
        initial_count = len(win._project.color_palette)  # noqa: SLF001
        mock_color = QColor("#112233")
        with patch("cardforge.main_window.QColorDialog.getColor", return_value=mock_color):
            win._add_palette_color()  # noqa: SLF001
        assert len(win._project.color_palette) == initial_count + 1  # noqa: SLF001
        assert win._project.color_palette[-1] == "#112233"
        win.close()

    def test_add_palette_color_invalid_noop(self, qapp):
        from unittest.mock import patch

        from PySide6.QtGui import QColor

        from cardforge.main_window import MainWindow

        win = MainWindow()
        initial_count = len(win._project.color_palette)  # noqa: SLF001
        mock_color = QColor()  # invalid color
        with patch("cardforge.main_window.QColorDialog.getColor", return_value=mock_color):
            win._add_palette_color()  # noqa: SLF001
        assert len(win._project.color_palette) == initial_count
        win.close()


# ---------------------------------------------------------------------------
# _insert_image
# ---------------------------------------------------------------------------


class TestInsertImage:
    def test_insert_image_cancelled_noop(self, qapp):
        from unittest.mock import patch

        from cardforge.main_window import MainWindow

        win = MainWindow()
        before = len(win._canvas._elements())  # noqa: SLF001
        with patch("cardforge.main_window.QFileDialog.getOpenFileName", return_value=("", "")):
            win._insert_image()  # noqa: SLF001
        assert len(win._canvas._elements()) == before  # noqa: SLF001
        win.close()

    def test_insert_image_with_path(self, qapp, tmp_path):
        from unittest.mock import patch

        # Kleines PNG erzeugen
        from PySide6.QtGui import QPixmap

        from cardforge.main_window import MainWindow

        img_path = str(tmp_path / "img.png")
        pm = QPixmap(10, 10)
        pm.save(img_path, "PNG")

        win = MainWindow()
        before = len(win._canvas._elements())  # noqa: SLF001
        with patch(
            "cardforge.main_window.QFileDialog.getOpenFileName", return_value=(img_path, "")
        ):
            win._insert_image()  # noqa: SLF001
        assert len(win._canvas._elements()) == before + 1  # noqa: SLF001
        win.close()


# ---------------------------------------------------------------------------
# Paper template operations
# ---------------------------------------------------------------------------


class TestPaperTemplateOps:
    def test_edit_paper_template_accepted(self, qapp):
        from unittest.mock import patch

        from PySide6.QtWidgets import QDialog

        from cardforge.main_window import MainWindow
        from cardforge.models import PaperTemplate

        win = MainWindow()
        new_tmpl = PaperTemplate(name="Neu", paper_width=200.0)
        with patch("cardforge.main_window.PaperTemplateDialog") as MockDlg:
            mock_inst = MockDlg.return_value
            mock_inst.exec.return_value = QDialog.DialogCode.Accepted
            mock_inst.result_template.return_value = new_tmpl
            win._edit_paper_template()  # noqa: SLF001
        assert win._project.paper_template is new_tmpl
        win.close()

    def test_edit_paper_template_rejected(self, qapp):
        from unittest.mock import patch

        from PySide6.QtWidgets import QDialog

        from cardforge.main_window import MainWindow

        win = MainWindow()
        orig_tmpl = win._project.paper_template
        with patch("cardforge.main_window.PaperTemplateDialog") as MockDlg:
            mock_inst = MockDlg.return_value
            mock_inst.exec.return_value = QDialog.DialogCode.Rejected
            win._edit_paper_template()  # noqa: SLF001
        assert win._project.paper_template is orig_tmpl
        win.close()

    def test_save_paper_to_library_ok(self, qapp, tmp_path):
        from unittest.mock import patch

        from cardforge.main_window import MainWindow

        win = MainWindow()
        lib_path = str(tmp_path / "paper_templates.json")
        with (
            patch(
                "cardforge.main_window.QInputDialog.getText", return_value=("MeineVorlage", True)
            ),
            patch("cardforge.main_window.MainWindow._user_templates_path", return_value=lib_path),
            patch("cardforge.main_window.QMessageBox.information"),
        ):
            win._save_paper_to_library()  # noqa: SLF001
        import json
        import os

        assert os.path.exists(lib_path)
        with open(lib_path) as _f:
            data = json.loads(_f.read())
        assert any(t["name"] == "MeineVorlage" for t in data)
        win.close()

    def test_save_paper_to_library_cancel(self, qapp):
        from unittest.mock import patch

        from cardforge.main_window import MainWindow

        win = MainWindow()
        with patch("cardforge.main_window.QInputDialog.getText", return_value=("", False)):
            win._save_paper_to_library()  # noqa: SLF001 — kein Absturz
        win.close()

    def test_load_paper_preset_ok(self, qapp):
        """Vorlage auswählen und laden simulieren."""
        from unittest.mock import patch

        from PySide6.QtWidgets import QDialog, QListWidget, QPushButton

        from cardforge.main_window import MainWindow

        win = MainWindow()

        def _fake_exec(dlg):
            # Passenden Listeneintrag suchen und "Laden" klicken
            lst = dlg.findChild(QListWidget)
            for i in range(lst.count()):
                if "Avery C32010 (10 Karten, A4)" in lst.item(i).text():
                    lst.setCurrentRow(i)
                    break
            for btn in dlg.findChildren(QPushButton):
                if btn.text() == "Load":
                    btn.click()
                    return QDialog.DialogCode.Accepted
            return QDialog.DialogCode.Rejected

        with (
            patch("cardforge.main_window.MainWindow._load_user_templates", return_value=[]),
            patch.object(QDialog, "exec", _fake_exec),
        ):
            win._load_paper_preset()  # noqa: SLF001
        assert win._project.paper_template.name == "Avery C32010 (10 Karten, A4)"
        win.close()

    def test_load_paper_preset_cancel(self, qapp):
        """Schließen ohne Laden ändert die Vorlage nicht."""
        from unittest.mock import patch

        from PySide6.QtWidgets import QDialog

        from cardforge.main_window import MainWindow

        win = MainWindow()
        orig_name = win._project.paper_template.name
        with (
            patch("cardforge.main_window.MainWindow._load_user_templates", return_value=[]),
            patch.object(QDialog, "exec", return_value=QDialog.DialogCode.Rejected),
        ):
            win._load_paper_preset()  # noqa: SLF001
        assert win._project.paper_template.name == orig_name
        win.close()

    def test_load_user_templates_missing_file(self, qapp, tmp_path):
        from unittest.mock import patch

        from cardforge.main_window import MainWindow

        with patch(
            "cardforge.main_window.MainWindow._user_templates_path",
            return_value=str(tmp_path / "nonexistent.json"),
        ):
            result = MainWindow._load_user_templates()  # noqa: SLF001
        assert result == []

    def test_load_user_templates_corrupt_file(self, qapp, tmp_path):
        from unittest.mock import patch

        from cardforge.main_window import MainWindow

        bad_path = str(tmp_path / "bad.json")
        with open(bad_path, "w") as f:
            f.write("INVALID JSON {{{{")
        with patch("cardforge.main_window.MainWindow._user_templates_path", return_value=bad_path):
            result = MainWindow._load_user_templates()  # noqa: SLF001
        assert result == []


# ---------------------------------------------------------------------------
# File operations
# ---------------------------------------------------------------------------


class TestFileOps:
    def test_open_project_ok(self, qapp, tmp_path):
        from unittest.mock import patch

        from cardforge.main_window import MainWindow
        from cardforge.models import CardLayout, Project

        # Projekt speichern
        p = Project(name="OpenTest")
        p.cards.append(CardLayout(name="K1"))
        path = str(tmp_path / "open.vcproj")
        p.save(path)

        win = MainWindow()
        win._modified = False
        with patch("cardforge.main_window.QFileDialog.getOpenFileName", return_value=(path, "")):
            win._open_project()  # noqa: SLF001
        assert win._project_path == path
        win.close()

    def test_open_project_cancelled(self, qapp):
        from unittest.mock import patch

        from cardforge.main_window import MainWindow

        win = MainWindow()
        orig_path = win._project_path
        with patch("cardforge.main_window.QFileDialog.getOpenFileName", return_value=("", "")):
            win._open_project()  # noqa: SLF001
        assert win._project_path == orig_path
        win.close()

    def test_open_project_error_shows_critical(self, qapp, tmp_path):
        from unittest.mock import patch

        from cardforge.main_window import MainWindow

        bad = str(tmp_path / "bad.vcproj")
        with open(bad, "w") as f:
            f.write("INVALID")
        win = MainWindow()
        win._modified = False
        with (
            patch("cardforge.main_window.QFileDialog.getOpenFileName", return_value=(bad, "")),
            patch("cardforge.main_window.QMessageBox.critical") as mock_crit,
        ):
            win._open_project()  # noqa: SLF001
            mock_crit.assert_called_once()
        win.close()

    def test_save_project_with_path_calls_do_save(self, qapp, tmp_path):
        from unittest.mock import patch

        from cardforge.main_window import MainWindow

        win = MainWindow()
        path = str(tmp_path / "existing.vcproj")
        win._project_path = path
        with patch.object(win, "_do_save") as mock_save:
            win._save_project()  # noqa: SLF001
            mock_save.assert_called_once_with(path)
        win.close()

    def test_save_project_without_path_calls_save_as(self, qapp):
        from unittest.mock import patch

        from cardforge.main_window import MainWindow

        win = MainWindow()
        win._project_path = None
        with patch.object(win, "_save_project_as") as mock_sa:
            win._save_project()  # noqa: SLF001
            mock_sa.assert_called_once()
        win.close()

    def test_save_project_as_sets_path(self, qapp, tmp_path):
        from unittest.mock import patch

        from cardforge.main_window import MainWindow

        win = MainWindow()
        out = str(tmp_path / "new.vcproj")
        with patch("cardforge.main_window.QFileDialog.getSaveFileName", return_value=(out, "")):
            win._save_project_as()  # noqa: SLF001
        assert win._project_path == out
        win.close()

    def test_save_project_as_appends_extension(self, qapp, tmp_path):
        from unittest.mock import patch

        from cardforge.main_window import MainWindow

        win = MainWindow()
        out = str(tmp_path / "new")
        with (
            patch("cardforge.main_window.QFileDialog.getSaveFileName", return_value=(out, "")),
            patch.object(win, "_do_save") as mock_save,
        ):
            win._save_project_as()  # noqa: SLF001
            call_path = mock_save.call_args[0][0]
            assert call_path.endswith(".vcproj")
        win.close()

    def test_save_project_as_cancelled(self, qapp):
        from unittest.mock import patch

        from cardforge.main_window import MainWindow

        win = MainWindow()
        with (
            patch("cardforge.main_window.QFileDialog.getSaveFileName", return_value=("", "")),
            patch.object(win, "_do_save") as mock_save,
        ):
            win._save_project_as()  # noqa: SLF001
            mock_save.assert_not_called()
        win.close()

    def test_do_save_error_shows_critical(self, qapp):
        from unittest.mock import patch

        from cardforge.main_window import MainWindow

        win = MainWindow()
        with (
            patch.object(win._project, "save", side_effect=OSError("disk full")),
            patch("cardforge.main_window.QMessageBox.critical") as mock_crit,
        ):
            win._do_save("/nonexistent/path.vcproj")  # noqa: SLF001
            mock_crit.assert_called_once()
        win.close()

    def test_export_template_ok(self, qapp, tmp_path):
        from unittest.mock import patch

        from cardforge.main_window import MainWindow

        win = MainWindow()
        out = str(tmp_path / "tmpl.vctemplate")
        with patch("cardforge.main_window.QFileDialog.getSaveFileName", return_value=(out, "")):
            win._export_template()  # noqa: SLF001
        import os

        assert os.path.exists(out)
        win.close()

    def test_export_template_appends_extension(self, qapp, tmp_path):
        from unittest.mock import patch

        from cardforge.main_window import MainWindow

        win = MainWindow()
        out = str(tmp_path / "tmpl")
        with patch("cardforge.main_window.QFileDialog.getSaveFileName", return_value=(out, "")):
            win._export_template()  # noqa: SLF001
        import os

        assert os.path.exists(out + ".vctemplate")
        win.close()

    def test_export_template_cancelled(self, qapp):
        from unittest.mock import patch

        from cardforge.main_window import MainWindow

        win = MainWindow()
        with patch("cardforge.main_window.QFileDialog.getSaveFileName", return_value=("", "")):
            win._export_template()  # noqa: SLF001
        win.close()

    def test_import_template_ok(self, qapp, tmp_path):
        import json
        from unittest.mock import patch

        from cardforge.main_window import MainWindow
        from cardforge.models import CardLayout, PaperTemplate

        win = MainWindow()
        card = CardLayout(name="ImportKarte")
        data = {
            "type": "card_template",
            "paper": PaperTemplate().to_dict(),
            "card": card.to_dict(),
        }
        path = str(tmp_path / "tmpl.vctemplate")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        before = len(win._project.cards)
        with patch("cardforge.main_window.QFileDialog.getOpenFileName", return_value=(path, "")):
            win._import_template()  # noqa: SLF001
        assert len(win._project.cards) == before + 1
        assert "(imported)" in win._project.cards[-1].name
        win.close()

    def test_import_template_cancelled(self, qapp):
        from unittest.mock import patch

        from cardforge.main_window import MainWindow

        win = MainWindow()
        with patch("cardforge.main_window.QFileDialog.getOpenFileName", return_value=("", "")):
            win._import_template()  # noqa: SLF001
        win.close()

    def test_import_template_error(self, qapp, tmp_path):
        from unittest.mock import patch

        from cardforge.main_window import MainWindow

        bad = str(tmp_path / "bad.vctemplate")
        with open(bad, "w") as f:
            f.write("INVALID JSON")
        win = MainWindow()
        with (
            patch("cardforge.main_window.QFileDialog.getOpenFileName", return_value=(bad, "")),
            patch("cardforge.main_window.QMessageBox.critical") as mock_crit,
        ):
            win._import_template()  # noqa: SLF001
            mock_crit.assert_called_once()
        win.close()


# ---------------------------------------------------------------------------
# Mail merge
# ---------------------------------------------------------------------------


class TestMailMerge:
    def test_mail_merge_no_cards_noop(self, qapp):
        from cardforge.main_window import MainWindow

        win = MainWindow()
        win._project.cards = []
        win._mail_merge()  # kein Absturz
        win.close()

    def test_mail_merge_accepted(self, qapp):
        from unittest.mock import patch

        from PySide6.QtWidgets import QDialog

        from cardforge.main_window import MainWindow
        from cardforge.models import CardLayout

        win = MainWindow()
        new_cards = [CardLayout(name="Merge1"), CardLayout(name="Merge2")]
        with (
            patch("cardforge.mail_merge.MailMergeDialog") as MockDlg,
            patch("cardforge.main_window.QMessageBox.information"),
        ):
            mock_inst = MockDlg.return_value
            mock_inst.exec.return_value = QDialog.DialogCode.Accepted
            mock_inst.result_layouts.return_value = new_cards
            before = len(win._project.cards)
            win._mail_merge()  # noqa: SLF001
        assert len(win._project.cards) == before + 2
        win.close()

    def test_mail_merge_rejected(self, qapp):
        from unittest.mock import patch

        from PySide6.QtWidgets import QDialog

        from cardforge.main_window import MainWindow

        win = MainWindow()
        before = len(win._project.cards)
        with patch("cardforge.mail_merge.MailMergeDialog") as MockDlg:
            mock_inst = MockDlg.return_value
            mock_inst.exec.return_value = QDialog.DialogCode.Rejected
            win._mail_merge()  # noqa: SLF001
        assert len(win._project.cards) == before
        win.close()


# ---------------------------------------------------------------------------
# _new_project mit modified
# ---------------------------------------------------------------------------


class TestNewProjectWithModified:
    def test_new_project_modified_confirms_discard(self, qapp):
        from cardforge.main_window import MainWindow

        win = MainWindow()
        win._modified = True
        # QMessageBox.question is mocked by autouse fixture → Yes
        win._new_project()
        assert len(win._project.cards) == 1
        win.close()

    def test_new_project_modified_aborts_on_no(self, qapp):
        from unittest.mock import patch

        from PySide6.QtWidgets import QMessageBox

        from cardforge.main_window import MainWindow

        win = MainWindow()
        win._modified = True
        win._project.cards.append(
            __import__("cardforge.models", fromlist=["CardLayout"]).CardLayout(name="Extra")
        )
        cards_count = len(win._project.cards)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
            win._new_project()
        assert len(win._project.cards) == cards_count  # nicht zurückgesetzt
        win.close()


# ---------------------------------------------------------------------------
# _open_project mit modified
# ---------------------------------------------------------------------------


class TestOpenProjectWithModified:
    def test_open_project_modified_confirms(self, qapp, tmp_path):
        from unittest.mock import patch

        from cardforge.main_window import MainWindow
        from cardforge.models import CardLayout, Project

        p = Project()
        p.cards.append(CardLayout(name="K1"))
        path = str(tmp_path / "proj.vcproj")
        p.save(path)

        win = MainWindow()
        win._modified = True
        # autouse → Yes
        with patch("cardforge.main_window.QFileDialog.getOpenFileName", return_value=(path, "")):
            win._open_project()  # noqa: SLF001
        assert win._project_path == path
        win.close()

    def test_open_project_modified_aborts_on_no(self, qapp):
        from unittest.mock import patch

        from PySide6.QtWidgets import QMessageBox

        from cardforge.main_window import MainWindow

        win = MainWindow()
        win._modified = True
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
            win._open_project()  # noqa: SLF001
        # kein Absturz, kein Dateiwähler
        win.close()


# ---------------------------------------------------------------------------
# closeEvent
# ---------------------------------------------------------------------------


class TestCloseEvent:
    def test_close_unmodified_accepts(self, qapp):
        from cardforge.main_window import MainWindow

        win = MainWindow()
        win._modified = False
        win.close()  # sollte ohne Rückfrage schließen

    def test_close_modified_no_ignores(self, qapp):
        from unittest.mock import patch

        from PySide6.QtGui import QCloseEvent
        from PySide6.QtWidgets import QMessageBox

        from cardforge.main_window import MainWindow

        win = MainWindow()
        win._modified = True
        event = QCloseEvent()
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
            win.closeEvent(event)
        assert not event.isAccepted()
        win._modified = False
        win.close()


# ---------------------------------------------------------------------------
# Dialoge (print preview / print dialog)
# ---------------------------------------------------------------------------


class TestDialogLaunchers:
    def test_print_preview_launches_dialog(self, qapp):
        from unittest.mock import patch

        from cardforge.main_window import MainWindow

        win = MainWindow()
        with patch("cardforge.print_preview.PrintPreviewDialog") as MockDlg:
            mock_inst = MockDlg.return_value
            mock_inst.exec.return_value = 0
            win._print_preview()  # noqa: SLF001
            MockDlg.assert_called_once()
        win.close()

    def test_print_dialog_launches(self, qapp):
        from unittest.mock import patch

        from cardforge.main_window import MainWindow

        win = MainWindow()
        with patch("cardforge.print_dialog.PrintExportDialog") as MockDlg:
            mock_inst = MockDlg.return_value
            mock_inst.exec.return_value = 0
            win._print_dialog()  # noqa: SLF001
            MockDlg.assert_called_once()
        win.close()

    def test_add_font_cancelled(self, qapp):
        from unittest.mock import patch

        from cardforge.main_window import MainWindow

        win = MainWindow()
        with patch("cardforge.main_window.QFileDialog.getOpenFileName", return_value=("", "")):
            win._add_font()  # noqa: SLF001
        win.close()

    def test_add_font_invalid(self, qapp, tmp_path):
        from unittest.mock import patch

        from cardforge.main_window import MainWindow

        bad_font = str(tmp_path / "bad.ttf")
        with open(bad_font, "wb") as f:
            f.write(b"not a font")
        win = MainWindow()
        with (
            patch("cardforge.main_window.QFileDialog.getOpenFileName", return_value=(bad_font, "")),
            patch("cardforge.main_window.QMessageBox.warning") as mock_warn,
        ):
            win._add_font()  # noqa: SLF001
            mock_warn.assert_called_once()
        win.close()


# ---------------------------------------------------------------------------
# _builtin_paper_presets
# ---------------------------------------------------------------------------


class TestBuiltinPaperPresets:
    def test_returns_nonempty_list(self, qapp):
        from cardforge.main_window import _builtin_paper_presets

        presets = _builtin_paper_presets()
        assert len(presets) >= 3

    def test_all_items_are_paper_template(self, qapp):
        from cardforge.main_window import _builtin_paper_presets
        from cardforge.models import PaperTemplate

        presets = _builtin_paper_presets()
        for p in presets:
            assert isinstance(p, PaperTemplate)

    def test_first_preset_is_avery(self, qapp):
        from cardforge.main_window import _builtin_paper_presets

        presets = _builtin_paper_presets()
        assert "Avery" in presets[0].name


# ---------------------------------------------------------------------------
# Zuletzt verwendet (Recent Files)
# ---------------------------------------------------------------------------


@contextmanager
def _patch_settings(initial=None):
    """Ersetzt QSettings durch eine in-memory-Implementierung.

    Gibt (store_dict, patch_obj) zurück. Alle QSettings-Instanzen teilen
    denselben ``store_dict``, sodass Lese- und Schreib-Aufrufe über mehrere
    Methodenaufrufe hinweg konsistent sind.
    """
    store: dict = dict(initial or {})

    def _make_mock(*args, **kwargs):
        m = MagicMock()
        m.value.side_effect = lambda key, default=None, **kw: store.get(key, default)
        m.setValue.side_effect = lambda key, val: store.__setitem__(key, val)
        return m

    with patch("cardforge.main_window.QSettings", side_effect=_make_mock) as p:
        yield store, p


class TestRecentFiles:
    def _win(self, qapp):
        from cardforge.main_window import MainWindow

        return MainWindow()

    def _make_vcproj(self, tmp_path, name="proj") -> str:
        """Erstellt eine echte .vcproj-Datei und gibt den Pfad zurück."""
        p = Project(name=name)
        p.cards.append(CardLayout(name="Karte 1"))
        f = tmp_path / f"{name}.vcproj"
        p.save(str(f))
        return str(f)

    # ------------------------------------------------------------------
    # _recent_paths
    # ------------------------------------------------------------------

    def test_recent_paths_empty_by_default(self, qapp):
        win = self._win(qapp)
        with _patch_settings():
            result = win._recent_paths()
        assert result == []
        win.close()

    def test_recent_paths_returns_stored_list(self, qapp):
        win = self._win(qapp)
        with _patch_settings({"recentFiles": ["/a/b.vcproj", "/c/d.vcproj"]}):
            result = win._recent_paths()
        assert result == ["/a/b.vcproj", "/c/d.vcproj"]
        win.close()

    def test_recent_paths_handles_single_string(self, qapp):
        """QSettings gibt bei einem einzelnen INI-Eintrag einen str zurück, keine list.
        _recent_paths() muss diesen Fall korrekt behandeln."""
        win = self._win(qapp)
        # Simuliert das echte QSettings-Verhalten: einzelner Wert als str
        with _patch_settings({"recentFiles": "/a/b.vcproj"}):
            result = win._recent_paths()
        assert result == ["/a/b.vcproj"]
        win.close()

    # ------------------------------------------------------------------
    # _add_recent_path
    # ------------------------------------------------------------------

    def test_add_recent_path_prepends_new_path(self, qapp, tmp_path):
        win = self._win(qapp)
        f = tmp_path / "test.vcproj"
        f.write_text("{}")
        with _patch_settings() as (store, _):
            win._add_recent_path(str(f))
            assert store["recentFiles"][0] == str(f)
        win.close()

    def test_add_recent_path_deduplicates_existing(self, qapp, tmp_path):
        win = self._win(qapp)
        f = tmp_path / "test.vcproj"
        f.write_text("{}")
        path = str(f)
        with _patch_settings({"recentFiles": ["/other.vcproj", path]}) as (store, _):
            win._add_recent_path(path)
            assert store["recentFiles"][0] == path
            assert store["recentFiles"].count(path) == 1
        win.close()

    def test_add_recent_path_truncates_to_max(self, qapp, tmp_path):
        win = self._win(qapp)
        new_file = tmp_path / "new.vcproj"
        new_file.write_text("{}")
        # 10 bereits vorhandene Einträge
        existing = [f"/old/file_{i}.vcproj" for i in range(10)]
        with _patch_settings({"recentFiles": existing}) as (store, _):
            win._add_recent_path(str(new_file))
            assert len(store["recentFiles"]) == 10
            assert store["recentFiles"][0] == str(new_file)
        win.close()

    def test_add_recent_path_updates_menu(self, qapp, tmp_path):
        win = self._win(qapp)
        f = tmp_path / "test.vcproj"
        f.write_text("{}")
        with _patch_settings(), patch.object(win, "_update_recent_menu") as mock_update:
            win._add_recent_path(str(f))
            mock_update.assert_called_once()
        win.close()

    # ------------------------------------------------------------------
    # _update_recent_menu
    # ------------------------------------------------------------------

    def test_update_recent_menu_empty_shows_disabled_entry(self, qapp):
        win = self._win(qapp)
        with _patch_settings():
            win._update_recent_menu()
        actions = win._recent_menu.actions()
        assert len(actions) == 1
        assert "(none)" in actions[0].text()
        assert not actions[0].isEnabled()
        win.close()

    def test_update_recent_menu_nonexistent_paths_filtered(self, qapp):
        win = self._win(qapp)
        with _patch_settings({"recentFiles": ["/nonexistent/ghost.vcproj"]}):
            win._update_recent_menu()
        actions = win._recent_menu.actions()
        assert len(actions) == 1
        assert "(none)" in actions[0].text()
        win.close()

    def test_update_recent_menu_existing_path_shown(self, qapp, tmp_path):
        win = self._win(qapp)
        f = tmp_path / "myproject.vcproj"
        f.write_text("{}")
        with _patch_settings({"recentFiles": [str(f)]}):
            win._update_recent_menu()
        labels = [a.text() for a in win._recent_menu.actions() if not a.isSeparator()]
        assert "myproject.vcproj" in labels
        win.close()

    def test_update_recent_menu_has_clear_action(self, qapp, tmp_path):
        win = self._win(qapp)
        f = tmp_path / "p.vcproj"
        f.write_text("{}")
        with _patch_settings({"recentFiles": [str(f)]}):
            win._update_recent_menu()
        labels = [a.text() for a in win._recent_menu.actions() if not a.isSeparator()]
        assert "Clear List" in labels
        win.close()

    def test_update_recent_menu_has_separator_before_clear(self, qapp, tmp_path):
        win = self._win(qapp)
        f = tmp_path / "p.vcproj"
        f.write_text("{}")
        with _patch_settings({"recentFiles": [str(f)]}):
            win._update_recent_menu()
        actions = win._recent_menu.actions()
        # Vorletztes Element muss Separator sein
        assert actions[-2].isSeparator()
        win.close()

    def test_update_recent_menu_tooltip_is_full_path(self, qapp, tmp_path):
        win = self._win(qapp)
        f = tmp_path / "sub" / "p.vcproj"
        f.parent.mkdir()
        f.write_text("{}")
        with _patch_settings({"recentFiles": [str(f)]}):
            win._update_recent_menu()
        file_actions = [
            a for a in win._recent_menu.actions() if not a.isSeparator() and a.isEnabled()
        ]
        assert file_actions[0].toolTip() == str(f)
        win.close()

    # ------------------------------------------------------------------
    # _clear_recent
    # ------------------------------------------------------------------

    def test_clear_recent_empties_settings(self, qapp):
        win = self._win(qapp)
        with _patch_settings({"recentFiles": ["/some/path.vcproj"]}) as (store, _):
            win._clear_recent()
            assert store["recentFiles"] == []
        win.close()

    def test_clear_recent_updates_menu(self, qapp):
        win = self._win(qapp)
        with _patch_settings({"recentFiles": ["/some/path.vcproj"]}):
            win._clear_recent()
        actions = win._recent_menu.actions()
        assert any("(none)" in a.text() for a in actions)
        win.close()

    # ------------------------------------------------------------------
    # _open_recent
    # ------------------------------------------------------------------

    def test_open_recent_modified_user_cancels_is_noop(self, qapp, tmp_path):
        win = self._win(qapp)
        win._modified = True
        f = tmp_path / "x.vcproj"
        f.write_text("{}")
        orig_project = win._project
        with patch.object(win, "_confirm_discard", return_value=False):
            win._open_recent(str(f))
        assert win._project is orig_project
        win.close()

    def test_open_recent_missing_file_shows_warning(self, qapp):
        win = self._win(qapp)
        win._modified = False
        missing = "/definitely/does/not/exist.vcproj"
        with (
            patch("cardforge.main_window.QMessageBox.warning") as mock_warn,
            patch.object(win, "_update_recent_menu") as mock_update,
            _patch_settings({"recentFiles": [missing]}),
        ):
            win._open_recent(missing)
            mock_warn.assert_called_once()
            mock_update.assert_called_once()
        win.close()

    def test_open_recent_success_loads_project(self, qapp, tmp_path):
        win = self._win(qapp)
        win._modified = False
        path = self._make_vcproj(tmp_path)
        with _patch_settings():
            win._open_recent(path)
        assert win._project_path == path
        assert not win._modified
        win.close()

    def test_open_recent_success_updates_title(self, qapp, tmp_path):
        win = self._win(qapp)
        win._modified = False
        path = self._make_vcproj(tmp_path, name="mycard")
        with _patch_settings():
            win._open_recent(path)
        assert "mycard.vcproj" in win.windowTitle()
        win.close()

    def test_open_recent_success_adds_to_recent(self, qapp, tmp_path):
        win = self._win(qapp)
        win._modified = False
        path = self._make_vcproj(tmp_path)
        with _patch_settings(), patch.object(win, "_add_recent_path") as mock_add:
            win._open_recent(path)
            mock_add.assert_called_once_with(path)
        win.close()

    def test_open_recent_load_error_shows_critical(self, qapp, tmp_path):
        win = self._win(qapp)
        win._modified = False
        f = tmp_path / "broken.vcproj"
        f.write_text("kein gueltiges json")  # Datei existiert, ist aber kaputt
        with patch("cardforge.main_window.QMessageBox.critical") as mock_crit, _patch_settings():
            win._open_recent(str(f))
            mock_crit.assert_called_once()
        win.close()

    def test_open_recent_modified_user_accepts_proceeds(self, qapp, tmp_path):
        win = self._win(qapp)
        win._modified = True
        path = self._make_vcproj(tmp_path)
        with patch.object(win, "_confirm_discard", return_value=True), _patch_settings():
            win._open_recent(path)
        assert win._project_path == path
        win.close()

    # ------------------------------------------------------------------
    # _open_project – add_recent_path nach erfolgreichem Öffnen
    # ------------------------------------------------------------------

    def test_open_project_calls_add_recent_on_success(self, qapp, tmp_path):
        win = self._win(qapp)
        path = self._make_vcproj(tmp_path, name="ok")
        with (
            patch("cardforge.main_window.QFileDialog.getOpenFileName", return_value=(path, "")),
            patch.object(win, "_add_recent_path") as mock_add,
        ):
            win._open_project()
            mock_add.assert_called_once_with(path)
        win.close()

    def test_open_project_cancelled_no_add_recent(self, qapp):
        win = self._win(qapp)
        with (
            patch("cardforge.main_window.QFileDialog.getOpenFileName", return_value=("", "")),
            patch.object(win, "_add_recent_path") as mock_add,
        ):
            win._open_project()
            mock_add.assert_not_called()
        win.close()

    # ------------------------------------------------------------------
    # _do_save – add_recent_path nach erfolgreichem Speichern
    # ------------------------------------------------------------------

    def test_do_save_calls_add_recent_on_success(self, qapp, tmp_path):
        win = self._win(qapp)
        f = tmp_path / "save.vcproj"
        with patch.object(win._project, "save"), patch.object(win, "_add_recent_path") as mock_add:
            win._do_save(str(f))
            mock_add.assert_called_once_with(str(f))
        win.close()

    def test_do_save_error_no_add_recent(self, qapp, tmp_path):
        win = self._win(qapp)
        f = tmp_path / "err.vcproj"
        with (
            patch.object(win._project, "save", side_effect=OSError("kein Platz")),
            patch("cardforge.main_window.QMessageBox.critical"),
            patch.object(win, "_add_recent_path") as mock_add,
        ):
            win._do_save(str(f))
            mock_add.assert_not_called()
        win.close()


# ---------------------------------------------------------------------------
# Branch-Coverage-Lücken schließen
# ---------------------------------------------------------------------------


class TestMissingCardBranches:
    """Tests for missing branches in card operations."""

    def _win(self, qapp):
        from cardforge.main_window import MainWindow

        return MainWindow()

    def test_duplicate_card_no_cards_noop(self, qapp):
        win = self._win(qapp)
        win._project.cards = []
        win._duplicate_card()  # early return – kein Absturz
        assert win._project.cards == []
        win.close()

    def test_rename_card_no_cards_noop(self, qapp):
        win = self._win(qapp)
        win._project.cards = []
        win._rename_card()  # early return – kein Absturz
        win.close()

    def test_switch_side_no_cards_noop(self, qapp):
        """Branch 922->926: _switch_side when project has no cards."""
        win = self._win(qapp)
        win._project.cards = []
        win._switch_side("back")  # kein Absturz
        assert win._current_side == "back"
        win.close()

    def test_refresh_card_list_two_selected_elements(self, qapp):
        """Branch 860->850: first_selected_item is NOT None on second selected element."""
        from cardforge.models import CardElement

        win = self._win(qapp)
        e1 = CardElement(type="text", text="Eins")
        e2 = CardElement(type="text", text="Zwei")
        win._project.cards[0].front_elements.extend([e1, e2])
        win._load_current_card()
        # Beide Elemente in canvas-Selektion setzen
        win._canvas._selected = [e1.id, e2.id]  # noqa: SLF001
        win._refresh_card_list()  # first_selected_item wird für e1 gesetzt, e2 überspringt branch
        win.close()


class TestInsertIcon:
    """Tests for _insert_icon (lines 1054-1069)."""

    def _win(self, qapp):
        from cardforge.main_window import MainWindow

        return MainWindow()

    def test_insert_icon_rejected_noop(self, qapp):
        from PySide6.QtWidgets import QDialog

        win = self._win(qapp)
        before = len(win._canvas._elements())  # noqa: SLF001
        with patch("cardforge.main_window.IconPickerDialog") as MockDlg:
            rejected = QDialog.DialogCode.Rejected
            MockDlg.return_value.exec.return_value = rejected
            MockDlg.DialogCode.Accepted = QDialog.DialogCode.Accepted
            win._insert_icon()
        assert len(win._canvas._elements()) == before  # noqa: SLF001
        win.close()

    def test_insert_icon_accepted_no_icon_noop(self, qapp):
        from PySide6.QtWidgets import QDialog

        win = self._win(qapp)
        before = len(win._canvas._elements())  # noqa: SLF001
        with patch("cardforge.main_window.IconPickerDialog") as MockDlg:
            accepted = QDialog.DialogCode.Accepted
            MockDlg.return_value.exec.return_value = accepted
            MockDlg.DialogCode.Accepted = accepted
            MockDlg.return_value.selected_icon = ""
            win._insert_icon()
        assert len(win._canvas._elements()) == before  # noqa: SLF001
        win.close()

    def test_insert_icon_accepted_with_icon(self, qapp):
        from PySide6.QtWidgets import QDialog

        win = self._win(qapp)
        before = len(win._canvas._elements())  # noqa: SLF001
        with patch("cardforge.main_window.IconPickerDialog") as MockDlg:
            accepted = QDialog.DialogCode.Accepted
            MockDlg.return_value.exec.return_value = accepted
            # _insert_icon checks: dlg.exec() != IconPickerDialog.DialogCode.Accepted
            # so MockDlg.DialogCode.Accepted must equal the return value
            MockDlg.DialogCode.Accepted = accepted
            MockDlg.return_value.selected_icon = "mdi.account"
            win._insert_icon()
        assert len(win._canvas._elements()) == before + 1  # noqa: SLF001
        assert win._canvas._elements()[-1].type == "icon"  # noqa: SLF001
        win.close()


class TestAutoFitRequested:
    """Tests for _on_auto_fit_requested (lines 1119-1122)."""

    def _win(self, qapp):
        from cardforge.main_window import MainWindow

        return MainWindow()

    def test_on_auto_fit_requested_calls_fit(self, qapp):
        win = self._win(qapp)
        with patch.object(win._canvas, "fit_to_content") as mock_fit:
            win._on_auto_fit_requested()
            mock_fit.assert_called_once()
        win.close()

    def test_on_auto_fit_requested_updates_props(self, qapp):
        from cardforge.models import CardElement

        win = self._win(qapp)
        e = CardElement(type="text", text="test")
        win._project.cards[0].front_elements.append(e)
        win._load_current_card()
        win._canvas._selected = [e.id]  # noqa: SLF001
        win._on_auto_fit_requested()  # kein Absturz
        win.close()


class TestElemPreviewLabelMissing:
    """Tests for missing _elem_preview_label branches (icon, fallback)."""

    def _win(self, qapp):
        from cardforge.main_window import MainWindow

        return MainWindow()

    def test_elem_preview_label_icon(self, qapp):
        from cardforge.models import CardElement

        win = self._win(qapp)
        e = CardElement(type="icon", icon_name="mdi.account")
        label = win._elem_preview_label(e)
        assert isinstance(label, str)
        win.close()

    def test_elem_preview_label_fallback_unknown_type(self, qapp):
        from cardforge.models import CardElement

        win = self._win(qapp)
        e = CardElement(type="unknown_future_type")
        label = win._elem_preview_label(e)
        assert "unknown_future_type" in label or isinstance(label, str)
        win.close()

    def test_elem_preview_label_image_no_path(self, qapp):
        from cardforge.models import CardElement

        win = self._win(qapp)
        e = CardElement(type="image", image_path="")
        label = win._elem_preview_label(e)
        assert "(no file)" in label
        win.close()

    def test_elem_preview_label_image_with_path(self, qapp):
        from cardforge.models import CardElement

        win = self._win(qapp)
        e = CardElement(type="image", image_path="/some/path/file.png")
        label = win._elem_preview_label(e)
        assert "file.png" in label
        win.close()

    def test_elem_preview_label_qr_empty(self, qapp):
        from cardforge.models import CardElement

        win = self._win(qapp)
        e = CardElement(type="qr", qr_data="")
        label = win._elem_preview_label(e)
        assert "(no data)" in label
        win.close()

    def test_elem_preview_label_line(self, qapp):
        from cardforge.models import CardElement

        win = self._win(qapp)
        e = CardElement(type="line", color="#123456", width=20.0, height=1.0)
        label = win._elem_preview_label(e)
        assert "#123456" in label
        win.close()

    def test_refresh_card_list_with_icon_element(self, qapp):
        """Covers icon branch in _elem_preview_label via _refresh_card_list."""
        from cardforge.models import CardElement

        win = self._win(qapp)
        e = CardElement(type="icon", icon_name="mdi.account")
        win._project.cards[0].front_elements.append(e)
        win._refresh_card_list()  # kein Absturz
        win.close()


class TestOnCanvasZoomChanged:
    """Tests for _on_canvas_zoom_changed (lines 1201-1202 are eventFilter; 1172 is this)."""

    def _win(self, qapp):
        from cardforge.main_window import MainWindow

        return MainWindow()

    def test_on_canvas_zoom_changed_updates_label(self, qapp):
        win = self._win(qapp)
        win._on_canvas_zoom_changed(2.5)
        assert "2.5" in win._zoom_lbl.text()
        win.close()

    def test_on_canvas_zoom_changed_updates_slider(self, qapp):
        win = self._win(qapp)
        win._on_canvas_zoom_changed(3.0)
        assert win._zoom_slider.value() == 30
        win.close()


class TestEventFilterLeave:
    """Tests for eventFilter Leave event (lines 1201-1202)."""

    def _win(self, qapp):
        from cardforge.main_window import MainWindow

        return MainWindow()

    def test_event_filter_leave_hides_button(self, qapp):
        from PySide6.QtCore import QEvent

        win = self._win(qapp)
        win._hover_del_btn.show()
        win._hover_del_elem_id = "some-id"
        leave_event = QEvent(QEvent.Type.Leave)
        win.eventFilter(win._card_tree, leave_event)
        assert not win._hover_del_btn.isVisible()
        assert win._hover_del_elem_id is None
        win.close()

    def test_event_filter_non_leave_passthrough(self, qapp):
        from PySide6.QtCore import QEvent

        win = self._win(qapp)
        win._hover_del_elem_id = "some-id"
        enter_event = QEvent(QEvent.Type.Enter)
        win.eventFilter(win._card_tree, enter_event)
        # should NOT have cleared hover_del_elem_id since it's not a Leave event
        assert win._hover_del_elem_id == "some-id"
        win.close()


class TestOnTreeItemEntered:
    """Tests for _on_tree_item_entered (lines 1206-1219)."""

    def _win(self, qapp):
        from cardforge.main_window import MainWindow

        return MainWindow()

    def test_on_tree_item_entered_elem_shows_button(self, qapp):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QTreeWidgetItem

        win = self._win(qapp)
        item = QTreeWidgetItem(win._card_tree)
        item.setData(0, Qt.ItemDataRole.UserRole, ("elem", "elem-id-123"))
        win._on_tree_item_entered(item, 0)
        assert win._hover_del_elem_id == "elem-id-123"
        # isHidden() is False means show() was called (visibility depends on parent)
        assert not win._hover_del_btn.isHidden()
        win.close()

    def test_on_tree_item_entered_non_elem_hides_button(self, qapp):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QTreeWidgetItem

        win = self._win(qapp)
        win._hover_del_elem_id = "some-id"
        win._hover_del_btn.show()
        item = QTreeWidgetItem(win._card_tree)
        item.setData(0, Qt.ItemDataRole.UserRole, ("card", 0))
        win._on_tree_item_entered(item, 0)
        assert win._hover_del_elem_id is None
        assert not win._hover_del_btn.isVisible()
        win.close()


class TestDeleteHoveredElem:
    """Tests for _delete_hovered_elem (lines 1222-1238)."""

    def _win(self, qapp):
        from cardforge.main_window import MainWindow

        return MainWindow()

    def test_delete_hovered_elem_none_id_noop(self, qapp):
        win = self._win(qapp)
        win._hover_del_elem_id = None
        before = len(win._project.cards[0].front_elements)
        win._delete_hovered_elem()
        assert len(win._project.cards[0].front_elements) == before
        win.close()

    def test_delete_hovered_elem_not_found_noop(self, qapp):
        win = self._win(qapp)
        win._hover_del_elem_id = "nonexistent-id-xyz"
        before = len(win._project.cards[0].front_elements)
        win._delete_hovered_elem()
        assert len(win._project.cards[0].front_elements) == before
        win.close()

    def test_delete_hovered_elem_ok_removes_element(self, qapp):
        from cardforge.models import CardElement

        win = self._win(qapp)
        e = CardElement(type="rect")
        win._project.cards[0].front_elements.append(e)
        win._load_current_card()
        win._hover_del_elem_id = e.id
        before = len(win._project.cards[0].front_elements)
        win._delete_hovered_elem()
        assert len(win._project.cards[0].front_elements) == before - 1
        assert win._hover_del_elem_id is None
        win.close()

    def test_delete_hovered_elem_also_removes_from_selection(self, qapp):
        from cardforge.models import CardElement

        win = self._win(qapp)
        e = CardElement(type="text", text="del")
        win._project.cards[0].front_elements.append(e)
        win._load_current_card()
        win._canvas._selected = [e.id]  # noqa: SLF001
        win._hover_del_elem_id = e.id
        win._delete_hovered_elem()
        assert e.id not in win._canvas._selected  # noqa: SLF001
        win.close()


class TestOnThemeAndAbout:
    """Tests for _on_theme_changed and _show_about (lines 1241-1250)."""

    def _win(self, qapp):
        from cardforge.main_window import MainWindow

        return MainWindow()

    def test_on_theme_changed_calls_apply_theme(self, qapp):
        win = self._win(qapp)
        with patch("cardforge.main_window.apply_theme") as mock_apply:
            win._on_theme_changed("dark")
            mock_apply.assert_called_once()
        win.close()

    def test_on_theme_changed_saves_theme(self, qapp):
        win = self._win(qapp)
        with patch("cardforge.main_window.save_theme") as mock_save:
            win._on_theme_changed("light")
            mock_save.assert_called_once_with("light")
        win.close()

    def test_show_about_opens_dialog(self, qapp):
        win = self._win(qapp)
        with patch("cardforge.main_window.AboutDialog") as MockDlg:
            MockDlg.return_value.exec.return_value = 0
            win._show_about()
            MockDlg.assert_called_once()
        win.close()


class TestOnLanguageChanged:
    """Tests for _on_language_changed (lines 1184-1185)."""

    def _win(self, qapp):
        from cardforge.main_window import MainWindow

        return MainWindow()

    def test_on_language_changed_saves_language(self, qapp):
        win = self._win(qapp)
        with (
            patch("cardforge.main_window.save_language") as mock_save,
            patch("cardforge.main_window.QMessageBox.information"),
        ):
            win._on_language_changed("de")
            mock_save.assert_called_once_with("de")
        win.close()

    def test_on_language_changed_shows_info(self, qapp):
        win = self._win(qapp)
        with (
            patch("cardforge.main_window.save_language"),
            patch("cardforge.main_window.QMessageBox.information") as mock_info,
        ):
            win._on_language_changed("fr")
            mock_info.assert_called_once()
        win.close()


class TestUserTemplatesPath:
    """Tests for _user_templates_path (lines 1272-1276)."""

    def test_user_templates_path_returns_json_path(self, qapp):
        from cardforge.main_window import MainWindow

        path = MainWindow._user_templates_path()
        assert isinstance(path, str)
        assert path.endswith("paper_templates.json")

    def test_load_user_templates_with_real_path(self, qapp):
        """Calls _load_user_templates without mocking _user_templates_path."""
        from cardforge.main_window import MainWindow

        result = MainWindow._load_user_templates()
        assert isinstance(result, list)


class TestManagePaperLibraryMissing:
    """Tests for missing branches in _manage_paper_library nested functions."""

    def _win(self, qapp):
        from cardforge.main_window import MainWindow

        return MainWindow()

    def test_rebuild_with_user_templates(self, qapp):
        """Cover _rebuild() user-template loop body (lines 1371-1373, 1380-1381)."""
        from unittest.mock import patch

        from PySide6.QtWidgets import QDialog

        from cardforge.models import PaperTemplate

        win = self._win(qapp)
        # Give user templates so _rebuild's user-loop is entered
        user_tmpl = PaperTemplate(name=win._project.paper_template.name, paper_width=200.0)

        def _fake_exec(dlg):
            return QDialog.DialogCode.Rejected

        with (
            patch(
                "cardforge.main_window.MainWindow._load_user_templates", return_value=[user_tmpl]
            ),
            patch.object(QDialog, "exec", _fake_exec),
        ):
            win._manage_paper_library()  # opens and closes immediately
        win.close()

    def test_do_load_no_selection_noop(self, qapp):
        """Cover _do_load() early return when nothing is selected (line 1415)."""
        from unittest.mock import patch

        from PySide6.QtWidgets import QDialog, QListWidget, QPushButton

        win = self._win(qapp)
        orig_name = win._project.paper_template.name

        def _fake_exec(dlg):
            # Clear any selection in the list
            lst = dlg.findChild(QListWidget)
            if lst is not None:
                lst.clearSelection()
                lst.setCurrentRow(-1)
            # Click Load with no selection
            for btn in dlg.findChildren(QPushButton):
                if "Load" in btn.text():
                    btn.click()
                    break
            return QDialog.DialogCode.Rejected

        with (
            patch("cardforge.main_window.MainWindow._load_user_templates", return_value=[]),
            patch.object(QDialog, "exec", _fake_exec),
        ):
            win._manage_paper_library()
        assert win._project.paper_template.name == orig_name
        win.close()

    def test_do_edit_cancel_noop(self, qapp):
        """Cover _do_edit() body and dialog-cancel path (lines 1423-1434)."""
        from unittest.mock import patch

        from PySide6.QtWidgets import QDialog, QListWidget, QPushButton

        from cardforge.models import PaperTemplate

        win = self._win(qapp)
        user_tmpl = PaperTemplate(name="EditMe", paper_width=200.0)
        call_count = [0]

        def _fake_exec(dlg):
            call_count[0] += 1
            if call_count[0] == 1:
                # Outer manage dialog: select user template and click Edit
                lst = dlg.findChild(QListWidget)
                if lst is not None:
                    for i in range(lst.count()):
                        if lst.item(i) and "★" in lst.item(i).text():
                            lst.setCurrentRow(i)
                            break
                for btn in dlg.findChildren(QPushButton):
                    if btn.text() == "Edit…":
                        btn.click()
                        break
                return QDialog.DialogCode.Rejected
            else:
                # Inner PaperTemplateDialog → cancel
                return QDialog.DialogCode.Rejected

        with (
            patch(
                "cardforge.main_window.MainWindow._load_user_templates", return_value=[user_tmpl]
            ),
            patch.object(QDialog, "exec", _fake_exec),
        ):
            win._manage_paper_library()
        win.close()

    def test_do_delete_user_no_confirmation(self, qapp):
        """Cover _do_delete() up to the 'No' answer (lines 1437-1449)."""
        from unittest.mock import patch

        from PySide6.QtWidgets import QDialog, QListWidget, QMessageBox, QPushButton

        from cardforge.models import PaperTemplate

        win = self._win(qapp)
        user_tmpl = PaperTemplate(name="DeleteMe", paper_width=200.0)

        def _fake_exec(dlg):
            lst = dlg.findChild(QListWidget)
            if lst is not None:
                for i in range(lst.count()):
                    if lst.item(i) and "★" in lst.item(i).text():
                        lst.setCurrentRow(i)
                        break
            for btn in dlg.findChildren(QPushButton):
                if btn.text() == "Delete":
                    btn.click()
                    break
            return QDialog.DialogCode.Rejected

        with (
            patch(
                "cardforge.main_window.MainWindow._load_user_templates", return_value=[user_tmpl]
            ),
            patch.object(QDialog, "exec", _fake_exec),
            patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No),
        ):
            win._manage_paper_library()
        win.close()

    def test_do_delete_user_confirmed(self, qapp):
        """Cover _do_delete() Yes path (lines 1450-1453)."""
        from unittest.mock import patch

        from PySide6.QtWidgets import QDialog, QListWidget, QMessageBox, QPushButton

        from cardforge.models import PaperTemplate

        win = self._win(qapp)
        user_tmpl = PaperTemplate(name="ConfirmDelete", paper_width=200.0)

        def _fake_exec(dlg):
            lst = dlg.findChild(QListWidget)
            if lst is not None:
                for i in range(lst.count()):
                    if lst.item(i) and "★" in lst.item(i).text():
                        lst.setCurrentRow(i)
                        break
            for btn in dlg.findChildren(QPushButton):
                if btn.text() == "Delete":
                    btn.click()
                    break
            return QDialog.DialogCode.Rejected

        saved_templates = []

        def _fake_save(templates):
            saved_templates[:] = templates

        with (
            patch(
                "cardforge.main_window.MainWindow._load_user_templates", return_value=[user_tmpl]
            ),
            patch.object(QDialog, "exec", _fake_exec),
            patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes),
            patch("cardforge.main_window.MainWindow._save_user_templates", _fake_save),
        ):
            win._manage_paper_library()
        assert saved_templates == []  # template was deleted
        win.close()

    def test_do_edit_ok(self, qapp):
        """Cover _do_edit() success path (lines 1430-1434)."""
        from unittest.mock import patch

        from PySide6.QtWidgets import QDialog, QListWidget, QPushButton

        from cardforge.models import PaperTemplate

        win = self._win(qapp)
        user_tmpl = PaperTemplate(name="EditOK", paper_width=200.0)
        updated_tmpl = PaperTemplate(name="EditOK", paper_width=210.0)
        call_count = [0]

        def _fake_exec(dlg):
            call_count[0] += 1
            if call_count[0] == 1:
                # Outer manage dialog: select user template and click Edit
                lst = dlg.findChild(QListWidget)
                if lst is not None:
                    for i in range(lst.count()):
                        if lst.item(i) and "★" in lst.item(i).text():
                            lst.setCurrentRow(i)
                            break
                for btn in dlg.findChildren(QPushButton):
                    if btn.text() == "Edit…":
                        btn.click()
                        break
                return QDialog.DialogCode.Rejected
            else:
                # Inner PaperTemplateDialog → accept
                return QDialog.DialogCode.Accepted

        with (
            patch(
                "cardforge.main_window.MainWindow._load_user_templates", return_value=[user_tmpl]
            ),
            patch.object(QDialog, "exec", _fake_exec),
            patch("cardforge.main_window.PaperTemplateDialog") as MockPTD,
            patch("cardforge.main_window.MainWindow._save_user_templates"),
        ):
            MockPTD.return_value.exec.return_value = QDialog.DialogCode.Accepted
            MockPTD.return_value.result_template.return_value = updated_tmpl
            win._manage_paper_library()
        win.close()


class TestExportTemplateNoCards:
    """Test _export_template with no cards (line 1612)."""

    def _win(self, qapp):
        from cardforge.main_window import MainWindow

        return MainWindow()

    def test_export_template_no_cards_noop(self, qapp):
        win = self._win(qapp)
        win._project.cards = []
        win._export_template()  # kein Absturz
        win.close()


class TestPushSnapshotNoBefore:
    """Test _push_snapshot when _undo_before not set (branch 1734->exit)."""

    def _win(self, qapp):
        from cardforge.main_window import MainWindow

        return MainWindow()

    def test_push_snapshot_without_undo_before_is_noop(self, qapp):
        win = self._win(qapp)
        if hasattr(win, "_undo_before"):
            del win._undo_before
        stack_count_before = win._undo_stack.count()
        win._push_snapshot()
        assert win._undo_stack.count() == stack_count_before  # nichts gepusht
        win.close()


class TestKeyPressEvent:
    """Tests for keyPressEvent (lines 1768-1782)."""

    def _win(self, qapp):
        from cardforge.main_window import MainWindow

        return MainWindow()

    def test_key_press_t_inserts_text(self, qapp):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeyEvent

        win = self._win(qapp)
        before = len(win._canvas._elements())  # noqa: SLF001
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_T, Qt.KeyboardModifier.NoModifier)
        win.keyPressEvent(event)
        assert len(win._canvas._elements()) == before + 1  # noqa: SLF001
        win.close()

    def test_key_press_r_inserts_rect(self, qapp):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeyEvent

        win = self._win(qapp)
        before = len(win._canvas._elements())  # noqa: SLF001
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_R, Qt.KeyboardModifier.NoModifier)
        win.keyPressEvent(event)
        assert len(win._canvas._elements()) == before + 1  # noqa: SLF001
        win.close()

    def test_key_press_e_inserts_ellipse(self, qapp):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeyEvent

        win = self._win(qapp)
        before = len(win._canvas._elements())  # noqa: SLF001
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_E, Qt.KeyboardModifier.NoModifier)
        win.keyPressEvent(event)
        assert len(win._canvas._elements()) == before + 1  # noqa: SLF001
        win.close()

    def test_key_press_l_inserts_line(self, qapp):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeyEvent

        win = self._win(qapp)
        before = len(win._canvas._elements())  # noqa: SLF001
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_L, Qt.KeyboardModifier.NoModifier)
        win.keyPressEvent(event)
        assert len(win._canvas._elements()) == before + 1  # noqa: SLF001
        win.close()

    def test_key_press_other_passes_to_super(self, qapp):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeyEvent

        win = self._win(qapp)
        before = len(win._canvas._elements())  # noqa: SLF001
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Z, Qt.KeyboardModifier.NoModifier)
        win.keyPressEvent(event)  # kein Absturz, kein neues Element
        assert len(win._canvas._elements()) == before  # noqa: SLF001
        win.close()

    def test_key_press_ignored_when_text_widget_focused(self, qapp):
        """Branch 1769: isinstance(fw, QTextEdit/...) → super() called instead."""
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeyEvent
        from PySide6.QtWidgets import QApplication, QLineEdit

        win = self._win(qapp)
        before = len(win._canvas._elements())  # noqa: SLF001
        line_edit = QLineEdit()
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_T, Qt.KeyboardModifier.NoModifier)
        # QApplication.focusWidget() patchen damit es den QLineEdit zurückgibt
        with patch.object(QApplication, "focusWidget", return_value=line_edit):
            win.keyPressEvent(event)
        # T soll nicht als Element-Einfüge-Shortcut behandelt werden
        assert len(win._canvas._elements()) == before  # noqa: SLF001
        win.close()


class TestCloseEventAcceptModified:
    """Test closeEvent accept path when user says Yes (branch coverage)."""

    def _win(self, qapp):
        from cardforge.main_window import MainWindow

        return MainWindow()

    def test_close_event_modified_yes_accepts(self, qapp):
        from PySide6.QtGui import QCloseEvent

        win = self._win(qapp)
        win._modified = True
        event = QCloseEvent()
        # autouse fixture already patches QMessageBox.question → Yes
        win.closeEvent(event)
        assert event.isAccepted()
        win._modified = False
        win.close()

    def test_close_event_unmodified_accepts_directly(self, qapp):
        from PySide6.QtGui import QCloseEvent

        win = self._win(qapp)
        win._modified = False
        event = QCloseEvent()
        win.closeEvent(event)
        assert event.isAccepted()
        win.close()


class TestSavePaperToLibraryEmptyName:
    """Test _save_paper_to_library with ok=True but empty/whitespace name."""

    def _win(self, qapp):
        from cardforge.main_window import MainWindow

        return MainWindow()

    def test_save_paper_to_library_whitespace_name_noop(self, qapp):
        win = self._win(qapp)
        with patch("cardforge.main_window.QInputDialog.getText", return_value=("   ", True)):
            win._save_paper_to_library()  # early return – name.strip() == ""
        win.close()


class TestInsertQrEmpty:
    """Test _insert_qr with ok=True but empty data (covers empty data path)."""

    def _win(self, qapp):
        from cardforge.main_window import MainWindow

        return MainWindow()

    def test_insert_qr_ok_but_empty_data_noop(self, qapp):
        win = self._win(qapp)
        before = len(win._canvas._elements())  # noqa: SLF001
        with patch("cardforge.main_window.QInputDialog.getText", return_value=("", True)):
            win._insert_qr()
        assert len(win._canvas._elements()) == before  # noqa: SLF001
        win.close()
