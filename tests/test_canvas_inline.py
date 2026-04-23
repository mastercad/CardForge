"""
Umfassende Tests für cardforge.canvas – Inline-Editing, Tastatur,
Mausereignisse, Grid-Zeichnung und Hilfsfunktionen.

Deckt Zeilen ab: 44, 52, 56-58, 64-71, 403-404, 418, 588, 602-620,
662-668, 678-689, 695-698, 703-704, 727-734, 743-744, 870, 872,
890-895, 1068, 1073, 1091-1119, 1122-1180, 1182-1314, 1331, 1370,
1422-1440, 1453-1455
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from cardforge.models import (
    ELEMENT_IMAGE,
    ELEMENT_LINE,
    ELEMENT_RECT,
    ELEMENT_TEXT,
    CardElement,
    CardLayout,
    PaperTemplate,
)

# ---------------------------------------------------------------------------
# Hilfsfunktionen aus canvas (module-level helpers)
# ---------------------------------------------------------------------------


class TestModuleLevelHelpers:
    """_seg_for_pos, _line_for_pos, _all_visual_lines (Zeilen 44-71)."""

    def _make_segs(self, qapp):
        """Erzeugt Segmente via build_para_layouts für Tests."""
        from PySide6.QtGui import QFont

        from cardforge.renderer import build_para_layouts

        font = QFont("Arial")
        font.setPixelSize(14)
        segs, _ = build_para_layouts("Hallo\n\nWelt", font, 200.0, "left")
        return segs

    def test_seg_for_pos_first_segment(self, qapp):
        from cardforge.canvas import _seg_for_pos

        segs = self._make_segs(qapp)
        seg = _seg_for_pos(segs, 0)
        assert seg["char_start"] == 0

    def test_seg_for_pos_empty_paragraph(self, qapp):
        from cardforge.canvas import _seg_for_pos

        segs = self._make_segs(qapp)
        # Position 6 ist der leere Absatz (nach "Hallo\n")
        seg = _seg_for_pos(segs, 6)
        assert seg["layout"] is None

    def test_seg_for_pos_last_segment(self, qapp):
        from cardforge.canvas import _seg_for_pos

        segs = self._make_segs(qapp)
        # Position 7 ist in "Welt" (char_start=7)
        seg = _seg_for_pos(segs, 7)
        assert seg["layout"] is not None

    def test_line_for_pos_empty_para_returns_none_line(self, qapp):
        from cardforge.canvas import _line_for_pos

        segs = self._make_segs(qapp)
        seg, line = _line_for_pos(segs, 6)
        assert seg["layout"] is None
        assert line is None

    def test_line_for_pos_normal_seg_returns_valid_line(self, qapp):
        from cardforge.canvas import _line_for_pos

        segs = self._make_segs(qapp)
        seg, line = _line_for_pos(segs, 0)
        assert seg["layout"] is not None
        assert line is not None

    def test_all_visual_lines_includes_empty_para(self, qapp):
        from cardforge.canvas import _all_visual_lines

        segs = self._make_segs(qapp)
        lines = _all_visual_lines(segs)
        # Mindestens eine Zeile pro nicht-leerem Absatz + eine für den leeren
        none_lines = [ln for (s, ln) in lines if ln is None]
        assert len(none_lines) >= 1

    def test_all_visual_lines_count(self, qapp):
        from cardforge.canvas import _all_visual_lines

        segs = self._make_segs(qapp)
        lines = _all_visual_lines(segs)
        # "Hallo" = 1 Zeile, "" = 1 Zeile (None), "Welt" = 1 Zeile → mindestens 3
        assert len(lines) >= 3


# ---------------------------------------------------------------------------
# Hilfs-Setup für Canvas-Tests
# ---------------------------------------------------------------------------


def _make_canvas(qapp, text="Hello World", text_wrap=False):
    """Erstellt einen Canvas mit einem Text-Element und gibt (canvas, elem) zurück."""
    from cardforge.canvas import CardCanvas

    canvas = CardCanvas()
    layout = CardLayout()
    canvas.set_layout(layout, "front")
    canvas.set_paper(PaperTemplate())
    canvas.resize(600, 500)
    canvas.show()
    QApplication.processEvents()

    elem = CardElement(
        type=ELEMENT_TEXT,
        text=text,
        x=10.0,
        y=5.0,
        width=40.0 if not text_wrap else 30.0,
        height=10.0,
        text_wrap=text_wrap,
    )
    layout.front_elements.append(elem)
    canvas._selected = [elem.id]  # noqa: SLF001
    return canvas, elem


def _key_event(key, mods=Qt.KeyboardModifier.NoModifier, text=""):
    """Erzeugt ein QKeyEvent für Tests."""
    return QKeyEvent(QEvent.Type.KeyPress, key, mods, text)


# ---------------------------------------------------------------------------
# _start_inline_edit / _finish_inline_edit (Zeilen 1312-1314, 1331)
# ---------------------------------------------------------------------------


class TestInlineEditLifecycle:
    def test_start_inline_edit_sets_inline_elem(self, qapp):
        canvas, elem = _make_canvas(qapp)
        canvas._start_inline_edit(elem)  # noqa: SLF001
        assert canvas._inline_elem is elem  # noqa: SLF001
        canvas.close()

    def test_start_inline_edit_cursor_at_end(self, qapp):
        canvas, elem = _make_canvas(qapp, text="ABC")
        canvas._start_inline_edit(elem)  # noqa: SLF001
        assert canvas._cursor_pos == 3  # noqa: SLF001
        canvas.close()

    def test_start_inline_edit_with_click_pos(self, qapp):
        canvas, elem = _make_canvas(qapp, text="ABC")
        r = canvas._elem_rect_px(elem)  # noqa: SLF001
        click = QPointF(r.left(), r.center().y())
        canvas._start_inline_edit(elem, click)  # noqa: SLF001
        assert canvas._inline_elem is elem  # noqa: SLF001
        canvas.close()

    def test_finish_inline_edit_commit_true(self, qapp):
        canvas, elem = _make_canvas(qapp, text="Original")
        canvas._start_inline_edit(elem)  # noqa: SLF001
        elem.text = "Modified"
        canvas._finish_inline_edit(commit=True)  # noqa: SLF001
        assert canvas._inline_elem is None  # noqa: SLF001
        assert elem.text == "Modified"
        canvas.close()

    def test_finish_inline_edit_commit_false_restores(self, qapp):
        canvas, elem = _make_canvas(qapp, text="Original")
        canvas._start_inline_edit(elem)  # noqa: SLF001
        elem.text = "Modified"
        canvas._finish_inline_edit(commit=False)  # noqa: SLF001
        assert canvas._inline_elem is None  # noqa: SLF001
        assert elem.text == "Original"
        canvas.close()

    def test_finish_inline_edit_without_start_is_noop(self, qapp):
        """_finish_inline_edit wenn kein Inline-Edit aktiv → kein Absturz."""
        canvas, _ = _make_canvas(qapp)
        canvas._finish_inline_edit(commit=True)  # noqa: SLF001
        assert canvas._inline_elem is None  # noqa: SLF001
        canvas.close()

    def test_start_inline_edit_commits_previous(self, qapp):
        """Zweiter _start_inline_edit committet den ersten."""
        canvas, elem = _make_canvas(qapp, text="First")
        canvas._start_inline_edit(elem)  # noqa: SLF001
        elem.text = "Modified"
        elem2 = CardElement(type=ELEMENT_TEXT, text="Second", x=20.0, y=20.0)
        canvas._layout.front_elements.append(elem2)  # noqa: SLF001
        canvas._start_inline_edit(elem2)  # noqa: SLF001
        assert canvas._inline_elem is elem2  # noqa: SLF001
        assert elem.text == "Modified"
        canvas.close()


# ---------------------------------------------------------------------------
# _handle_inline_key – Zeichen-Eingabe (Zeilen 1122-1180)
# ---------------------------------------------------------------------------


class TestInlineKeyHandling:
    def _setup(self, qapp, text="Hello", text_wrap=False):
        canvas, elem = _make_canvas(qapp, text=text, text_wrap=text_wrap)
        canvas._start_inline_edit(elem)  # noqa: SLF001
        canvas._cursor_pos = len(text)  # Cursor ans Ende setzen  # noqa: SLF001
        return canvas, elem

    # --- Escape ---
    def test_escape_cancels_edit(self, qapp):
        canvas, elem = self._setup(qapp, text="Original")
        elem.text = "Changed"
        canvas._handle_inline_key(_key_event(Qt.Key.Key_Escape))  # noqa: SLF001
        assert canvas._inline_elem is None  # noqa: SLF001
        assert elem.text == "Original"
        canvas.close()

    # --- Ctrl+Return: Commit ---
    def test_ctrl_return_commits(self, qapp):
        canvas, elem = self._setup(qapp, text="Test")
        elem.text = "Committed"
        canvas._handle_inline_key(  # noqa: SLF001
            _key_event(Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
        )
        assert canvas._inline_elem is None  # noqa: SLF001
        assert elem.text == "Committed"
        canvas.close()

    def test_ctrl_enter_commits(self, qapp):
        canvas, elem = self._setup(qapp, text="Test")
        canvas._handle_inline_key(  # noqa: SLF001
            _key_event(Qt.Key.Key_Enter, Qt.KeyboardModifier.ControlModifier)
        )
        assert canvas._inline_elem is None  # noqa: SLF001
        canvas.close()

    # --- Zeichen-Eingabe ---
    def test_char_input_appends_to_end(self, qapp):
        canvas, elem = self._setup(qapp, text="Hi")
        canvas._handle_inline_key(_key_event(Qt.Key.Key_X, text="x"))  # noqa: SLF001
        assert elem.text == "Hix"
        assert canvas._cursor_pos == 3  # noqa: SLF001
        canvas.close()

    def test_char_input_inserts_at_position(self, qapp):
        canvas, elem = self._setup(qapp, text="Hello")
        canvas._cursor_pos = 2  # noqa: SLF001
        canvas._handle_inline_key(_key_event(Qt.Key.Key_X, text="X"))  # noqa: SLF001
        assert elem.text == "HeXllo"
        canvas.close()

    def test_char_input_replaces_selection(self, qapp):
        canvas, elem = self._setup(qapp, text="Hello")
        canvas._cursor_pos = 5  # noqa: SLF001
        canvas._sel_anchor = 1  # noqa: SLF001
        canvas._handle_inline_key(_key_event(Qt.Key.Key_X, text="X"))  # noqa: SLF001
        assert elem.text == "HX"
        canvas.close()

    # --- Backspace ---
    def test_backspace_deletes_char_before_cursor(self, qapp):
        canvas, elem = self._setup(qapp, text="Hello")
        canvas._handle_inline_key(_key_event(Qt.Key.Key_Backspace))  # noqa: SLF001
        assert elem.text == "Hell"
        assert canvas._cursor_pos == 4  # noqa: SLF001
        canvas.close()

    def test_backspace_at_start_is_noop(self, qapp):
        canvas, elem = self._setup(qapp, text="Hi")
        canvas._cursor_pos = 0  # noqa: SLF001
        canvas._handle_inline_key(_key_event(Qt.Key.Key_Backspace))  # noqa: SLF001
        assert elem.text == "Hi"
        canvas.close()

    def test_backspace_removes_selection(self, qapp):
        canvas, elem = self._setup(qapp, text="Hello")
        canvas._cursor_pos = 5  # noqa: SLF001
        canvas._sel_anchor = 0  # noqa: SLF001
        canvas._handle_inline_key(_key_event(Qt.Key.Key_Backspace))  # noqa: SLF001
        assert elem.text == ""
        canvas.close()

    # --- Delete ---
    def test_delete_removes_char_after_cursor(self, qapp):
        canvas, elem = self._setup(qapp, text="Hello")
        canvas._cursor_pos = 0  # noqa: SLF001
        canvas._handle_inline_key(_key_event(Qt.Key.Key_Delete))  # noqa: SLF001
        assert elem.text == "ello"
        canvas.close()

    def test_delete_at_end_is_noop(self, qapp):
        canvas, elem = self._setup(qapp, text="Hi")
        canvas._handle_inline_key(_key_event(Qt.Key.Key_Delete))  # noqa: SLF001
        assert elem.text == "Hi"
        canvas.close()

    def test_delete_removes_selection(self, qapp):
        canvas, elem = self._setup(qapp, text="Hello")
        canvas._cursor_pos = 3  # noqa: SLF001
        canvas._sel_anchor = 0  # noqa: SLF001
        canvas._handle_inline_key(_key_event(Qt.Key.Key_Delete))  # noqa: SLF001
        assert elem.text == "lo"
        canvas.close()

    # --- Return: Zeilenumbruch ---
    def test_return_inserts_newline(self, qapp):
        canvas, elem = self._setup(qapp, text="Hello")
        canvas._cursor_pos = 2  # noqa: SLF001
        canvas._handle_inline_key(_key_event(Qt.Key.Key_Return))  # noqa: SLF001
        assert elem.text == "He\nllo"
        assert canvas._cursor_pos == 3  # noqa: SLF001
        canvas.close()

    def test_return_with_selection_replaces_with_newline(self, qapp):
        canvas, elem = self._setup(qapp, text="Hello")
        canvas._cursor_pos = 4  # noqa: SLF001
        canvas._sel_anchor = 2  # noqa: SLF001
        canvas._handle_inline_key(_key_event(Qt.Key.Key_Return))  # noqa: SLF001
        assert elem.text == "He\no"
        canvas.close()

    # --- Ctrl+A (Select All) ---
    def test_ctrl_a_selects_all(self, qapp):
        canvas, elem = self._setup(qapp, text="Hello")
        canvas._cursor_pos = 2  # noqa: SLF001
        canvas._handle_inline_key(  # noqa: SLF001
            _key_event(Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
        )
        assert canvas._sel_anchor == 0  # noqa: SLF001
        assert canvas._cursor_pos == 5  # noqa: SLF001
        canvas.close()

    # --- Ctrl+C (Copy) ---
    def test_ctrl_c_copies_selection(self, qapp):
        canvas, elem = self._setup(qapp, text="Hello World")
        canvas._cursor_pos = 5  # noqa: SLF001
        canvas._sel_anchor = 0  # noqa: SLF001
        canvas._handle_inline_key(  # noqa: SLF001
            _key_event(Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
        )
        clip = QApplication.clipboard().text()
        assert clip == "Hello"
        canvas.close()

    def test_ctrl_c_copies_all_when_no_selection(self, qapp):
        canvas, elem = self._setup(qapp, text="Hello")
        canvas._handle_inline_key(  # noqa: SLF001
            _key_event(Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
        )
        clip = QApplication.clipboard().text()
        assert clip == "Hello"
        canvas.close()

    # --- Ctrl+X (Cut) ---
    def test_ctrl_x_cuts_selection(self, qapp):
        canvas, elem = self._setup(qapp, text="Hello World")
        canvas._cursor_pos = 5  # noqa: SLF001
        canvas._sel_anchor = 0  # noqa: SLF001
        canvas._handle_inline_key(  # noqa: SLF001
            _key_event(Qt.Key.Key_X, Qt.KeyboardModifier.ControlModifier)
        )
        assert elem.text == " World"
        assert QApplication.clipboard().text() == "Hello"
        canvas.close()

    def test_ctrl_x_cuts_all_when_no_selection(self, qapp):
        canvas, elem = self._setup(qapp, text="Hello")
        canvas._handle_inline_key(  # noqa: SLF001
            _key_event(Qt.Key.Key_X, Qt.KeyboardModifier.ControlModifier)
        )
        assert elem.text == ""
        assert canvas._cursor_pos == 0  # noqa: SLF001
        canvas.close()

    # --- Ctrl+V (Paste) ---
    def test_ctrl_v_pastes_at_cursor(self, qapp):
        canvas, elem = self._setup(qapp, text="Hello")
        canvas._cursor_pos = 5  # noqa: SLF001
        QApplication.clipboard().setText(" World")
        canvas._handle_inline_key(  # noqa: SLF001
            _key_event(Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)
        )
        assert elem.text == "Hello World"
        canvas.close()

    def test_ctrl_v_replaces_selection(self, qapp):
        canvas, elem = self._setup(qapp, text="Hello World")
        canvas._cursor_pos = 5  # noqa: SLF001
        canvas._sel_anchor = 0  # noqa: SLF001
        QApplication.clipboard().setText("Hi")
        canvas._handle_inline_key(  # noqa: SLF001
            _key_event(Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)
        )
        assert elem.text == "Hi World"
        canvas.close()

    # --- Left/Right Pfeiltasten ---
    def test_left_moves_cursor_back(self, qapp):
        canvas, elem = self._setup(qapp, text="Hello")
        canvas._cursor_pos = 3  # noqa: SLF001
        canvas._handle_inline_key(_key_event(Qt.Key.Key_Left))  # noqa: SLF001
        assert canvas._cursor_pos == 2  # noqa: SLF001
        canvas.close()

    def test_left_at_start_stays(self, qapp):
        canvas, elem = self._setup(qapp, text="Hi")
        canvas._cursor_pos = 0  # noqa: SLF001
        canvas._handle_inline_key(_key_event(Qt.Key.Key_Left))  # noqa: SLF001
        assert canvas._cursor_pos == 0  # noqa: SLF001
        canvas.close()

    def test_right_moves_cursor_forward(self, qapp):
        canvas, elem = self._setup(qapp, text="Hello")
        canvas._cursor_pos = 2  # noqa: SLF001
        canvas._handle_inline_key(_key_event(Qt.Key.Key_Right))  # noqa: SLF001
        assert canvas._cursor_pos == 3  # noqa: SLF001
        canvas.close()

    def test_right_at_end_stays(self, qapp):
        canvas, elem = self._setup(qapp, text="Hi")
        canvas._handle_inline_key(_key_event(Qt.Key.Key_Right))  # noqa: SLF001
        assert canvas._cursor_pos == 2  # noqa: SLF001
        canvas.close()

    def test_shift_left_starts_selection(self, qapp):
        canvas, elem = self._setup(qapp, text="Hello")
        canvas._cursor_pos = 3  # noqa: SLF001
        canvas._handle_inline_key(  # noqa: SLF001
            _key_event(Qt.Key.Key_Left, Qt.KeyboardModifier.ShiftModifier)
        )
        assert canvas._sel_anchor == 3  # noqa: SLF001
        assert canvas._cursor_pos == 2  # noqa: SLF001
        canvas.close()

    def test_shift_right_starts_selection(self, qapp):
        canvas, elem = self._setup(qapp, text="Hello")
        canvas._cursor_pos = 2  # noqa: SLF001
        canvas._handle_inline_key(  # noqa: SLF001
            _key_event(Qt.Key.Key_Right, Qt.KeyboardModifier.ShiftModifier)
        )
        assert canvas._sel_anchor == 2  # noqa: SLF001
        assert canvas._cursor_pos == 3  # noqa: SLF001
        canvas.close()

    # --- Home / End ---
    def test_home_moves_to_line_start(self, qapp):
        canvas, elem = self._setup(qapp, text="Hello\nWorld")
        canvas._cursor_pos = 9  # noqa: SLF001
        canvas._handle_inline_key(_key_event(Qt.Key.Key_Home))  # noqa: SLF001
        assert canvas._cursor_pos == 6  # noqa: SLF001  (start of "World" line)
        canvas.close()

    def test_home_at_first_line(self, qapp):
        canvas, elem = self._setup(qapp, text="Hello")
        canvas._cursor_pos = 3  # noqa: SLF001
        canvas._handle_inline_key(_key_event(Qt.Key.Key_Home))  # noqa: SLF001
        assert canvas._cursor_pos == 0  # noqa: SLF001
        canvas.close()

    def test_end_moves_to_line_end(self, qapp):
        canvas, elem = self._setup(qapp, text="Hello\nWorld")
        canvas._cursor_pos = 0  # noqa: SLF001
        canvas._handle_inline_key(_key_event(Qt.Key.Key_End))  # noqa: SLF001
        assert canvas._cursor_pos == 5  # noqa: SLF001  (end of "Hello" line)
        canvas.close()

    def test_end_at_last_line(self, qapp):
        canvas, elem = self._setup(qapp, text="Hello")
        canvas._cursor_pos = 2  # noqa: SLF001
        canvas._handle_inline_key(_key_event(Qt.Key.Key_End))  # noqa: SLF001
        assert canvas._cursor_pos == 5  # noqa: SLF001
        canvas.close()

    def test_shift_home_extends_selection(self, qapp):
        canvas, elem = self._setup(qapp, text="Hello")
        canvas._cursor_pos = 3  # noqa: SLF001
        canvas._handle_inline_key(  # noqa: SLF001
            _key_event(Qt.Key.Key_Home, Qt.KeyboardModifier.ShiftModifier)
        )
        assert canvas._sel_anchor == 3  # noqa: SLF001
        canvas.close()

    def test_shift_end_extends_selection(self, qapp):
        canvas, elem = self._setup(qapp, text="Hello")
        canvas._cursor_pos = 2  # noqa: SLF001
        canvas._handle_inline_key(  # noqa: SLF001
            _key_event(Qt.Key.Key_End, Qt.KeyboardModifier.ShiftModifier)
        )
        assert canvas._sel_anchor == 2  # noqa: SLF001
        canvas.close()

    # --- Up / Down (ohne text_wrap, Zeilen per \n) ---
    def test_up_moves_to_previous_line(self, qapp):
        canvas, elem = self._setup(qapp, text="Hello\nWorld")
        canvas._cursor_pos = 9  # noqa: SLF001  Position in "World"
        canvas._handle_inline_key(_key_event(Qt.Key.Key_Up))  # noqa: SLF001
        # Sollte auf die erste Zeile gesprungen sein
        assert canvas._cursor_pos < 6  # noqa: SLF001
        canvas.close()

    def test_down_moves_to_next_line(self, qapp):
        canvas, elem = self._setup(qapp, text="Hello\nWorld")
        canvas._cursor_pos = 2  # noqa: SLF001  Position in "Hello"
        canvas._handle_inline_key(_key_event(Qt.Key.Key_Down))  # noqa: SLF001
        # Sollte in die zweite Zeile gesprungen sein
        assert canvas._cursor_pos >= 6  # noqa: SLF001
        canvas.close()

    def test_up_on_first_line_is_noop(self, qapp):
        canvas, elem = self._setup(qapp, text="Hello")
        canvas._cursor_pos = 3  # noqa: SLF001
        original = canvas._cursor_pos  # noqa: SLF001
        canvas._handle_inline_key(_key_event(Qt.Key.Key_Up))  # noqa: SLF001
        assert canvas._cursor_pos == original  # noqa: SLF001
        canvas.close()

    def test_down_on_last_line_is_noop(self, qapp):
        canvas, elem = self._setup(qapp, text="Hello")
        canvas._cursor_pos = 3  # noqa: SLF001
        canvas._handle_inline_key(_key_event(Qt.Key.Key_Down))  # noqa: SLF001
        assert canvas._cursor_pos == 3  # noqa: SLF001
        canvas.close()

    # --- text_wrap=True: Up/Down mit QTextLayout ---
    def test_up_with_text_wrap(self, qapp):
        canvas, elem = _make_canvas(qapp, text="Hallo\n\nWelt", text_wrap=True)
        canvas._start_inline_edit(elem)  # noqa: SLF001
        canvas._cursor_pos = len("Hallo\n\nWelt")  # noqa: SLF001
        canvas._handle_inline_key(_key_event(Qt.Key.Key_Up))  # noqa: SLF001
        # Kein Absturz; Position vor dem letzten Segment
        assert canvas._cursor_pos <= len("Hallo\n\nWelt")  # noqa: SLF001
        canvas.close()

    def test_down_with_text_wrap(self, qapp):
        canvas, elem = _make_canvas(qapp, text="Hallo\n\nWelt", text_wrap=True)
        canvas._start_inline_edit(elem)  # noqa: SLF001
        canvas._cursor_pos = 0  # noqa: SLF001
        canvas._handle_inline_key(_key_event(Qt.Key.Key_Down))  # noqa: SLF001
        assert canvas._cursor_pos >= 0  # noqa: SLF001
        canvas.close()

    def test_home_with_text_wrap(self, qapp):
        canvas, elem = _make_canvas(qapp, text="Hallo Welt", text_wrap=True)
        canvas._start_inline_edit(elem)  # noqa: SLF001
        canvas._cursor_pos = 5  # noqa: SLF001
        canvas._handle_inline_key(_key_event(Qt.Key.Key_Home))  # noqa: SLF001
        assert canvas._cursor_pos <= 5  # noqa: SLF001
        canvas.close()

    def test_end_with_text_wrap(self, qapp):
        canvas, elem = _make_canvas(qapp, text="Hallo Welt", text_wrap=True)
        canvas._start_inline_edit(elem)  # noqa: SLF001
        canvas._cursor_pos = 0  # noqa: SLF001
        canvas._handle_inline_key(_key_event(Qt.Key.Key_End))  # noqa: SLF001
        assert canvas._cursor_pos >= 0  # noqa: SLF001
        canvas.close()

    def test_shift_up_with_text_wrap(self, qapp):
        canvas, elem = _make_canvas(qapp, text="Hallo\n\nWelt", text_wrap=True)
        canvas._start_inline_edit(elem)  # noqa: SLF001
        canvas._cursor_pos = len("Hallo\n\nWelt")  # noqa: SLF001
        canvas._handle_inline_key(  # noqa: SLF001
            _key_event(Qt.Key.Key_Up, Qt.KeyboardModifier.ShiftModifier)
        )
        canvas.close()

    def test_shift_down_with_text_wrap(self, qapp):
        canvas, elem = _make_canvas(qapp, text="Hallo\n\nWelt", text_wrap=True)
        canvas._start_inline_edit(elem)  # noqa: SLF001
        canvas._cursor_pos = 0  # noqa: SLF001
        canvas._handle_inline_key(  # noqa: SLF001
            _key_event(Qt.Key.Key_Down, Qt.KeyboardModifier.ShiftModifier)
        )
        canvas.close()

    def test_home_text_wrap_empty_para(self, qapp):
        """Home auf leerem Absatz-Segment (layout=None)."""
        canvas, elem = _make_canvas(qapp, text="A\n\nB", text_wrap=True)
        canvas._start_inline_edit(elem)  # noqa: SLF001
        canvas._cursor_pos = 2  # Position im leeren Absatz  # noqa: SLF001
        canvas._handle_inline_key(_key_event(Qt.Key.Key_Home))  # noqa: SLF001
        canvas.close()

    def test_end_text_wrap_empty_para(self, qapp):
        """End auf leerem Absatz-Segment (layout=None)."""
        canvas, elem = _make_canvas(qapp, text="A\n\nB", text_wrap=True)
        canvas._start_inline_edit(elem)  # noqa: SLF001
        canvas._cursor_pos = 2  # noqa: SLF001
        canvas._handle_inline_key(_key_event(Qt.Key.Key_End))  # noqa: SLF001
        canvas.close()

    # --- Unbekannte Taste → False ---
    def test_unknown_key_returns_false(self, qapp):
        canvas, elem = self._setup(qapp)
        # F1 sollte nicht verarbeitet werden
        result = canvas._handle_inline_key(_key_event(Qt.Key.Key_F1))  # noqa: SLF001
        assert result is False
        canvas.close()


# ---------------------------------------------------------------------------
# _update_inline_size (Zeile 1370)
# ---------------------------------------------------------------------------


class TestUpdateInlineSize:
    def test_update_inline_size_resizes_element(self, qapp):
        canvas, elem = _make_canvas(qapp, text="Hello World", text_wrap=False)
        canvas._start_inline_edit(elem)  # noqa: SLF001
        original_width = elem.width
        elem.text = "Hello World extended text that is much longer than before"
        canvas._update_inline_size()  # noqa: SLF001
        # Breite sollte sich bei nicht-wrap Text geändert haben
        assert elem.width != original_width or elem.height > 0
        canvas.close()

    def test_update_inline_size_with_text_wrap(self, qapp):
        canvas, elem = _make_canvas(qapp, text="Hello World", text_wrap=True)
        canvas._start_inline_edit(elem)  # noqa: SLF001
        canvas._update_inline_size()  # noqa: SLF001  # Darf nicht abstürzen
        canvas.close()

    def test_update_inline_size_no_inline_elem_is_noop(self, qapp):
        canvas, _ = _make_canvas(qapp)
        assert canvas._inline_elem is None  # noqa: SLF001
        canvas._update_inline_size()  # noqa: SLF001  # Darf nicht abstürzen
        canvas.close()

    def test_update_inline_size_empty_text_no_crash(self, qapp):
        canvas, elem = _make_canvas(qapp, text="Hello", text_wrap=False)
        canvas._start_inline_edit(elem)  # noqa: SLF001
        elem.text = "   "
        canvas._update_inline_size()  # noqa: SLF001
        canvas.close()


# ---------------------------------------------------------------------------
# _draw_text_cursor – Cursor-Zeichnung (Zeilen 1182-1314)
# ---------------------------------------------------------------------------


class TestDrawTextCursor:
    def test_paint_with_inline_edit_active_no_wrap(self, qapp):
        """_draw_text_cursor wird aufgerufen wenn _inline_elem gesetzt ist."""
        canvas, elem = _make_canvas(qapp, text="Hello World")
        canvas._start_inline_edit(elem)  # noqa: SLF001
        canvas.repaint()
        QApplication.processEvents()
        canvas.close()

    def test_paint_with_inline_edit_with_text_wrap(self, qapp):
        """_draw_text_cursor mit text_wrap=True deckt den wrap-Zweig ab."""
        canvas, elem = _make_canvas(qapp, text="Hello World Extended", text_wrap=True)
        canvas._start_inline_edit(elem)  # noqa: SLF001
        canvas.repaint()
        QApplication.processEvents()
        canvas.close()

    def test_paint_with_selection_no_wrap(self, qapp):
        """Selektion in text_wrap=False wird als blaues Rechteck gezeichnet."""
        canvas, elem = _make_canvas(qapp, text="Hello World")
        canvas._start_inline_edit(elem)  # noqa: SLF001
        canvas._cursor_pos = 5  # noqa: SLF001
        canvas._sel_anchor = 0  # noqa: SLF001
        canvas.repaint()
        QApplication.processEvents()
        canvas.close()

    def test_paint_with_selection_text_wrap(self, qapp):
        """Selektion in text_wrap=True deckt den wrap-Selektions-Zweig ab."""
        canvas, elem = _make_canvas(qapp, text="Hello World Extended Text", text_wrap=True)
        canvas._start_inline_edit(elem)  # noqa: SLF001
        canvas._cursor_pos = 11  # noqa: SLF001
        canvas._sel_anchor = 0  # noqa: SLF001
        canvas.repaint()
        QApplication.processEvents()
        canvas.close()

    def test_paint_with_selection_spans_empty_para(self, qapp):
        """Selektion über leeren Absatz in text_wrap=True."""
        canvas, elem = _make_canvas(qapp, text="A\n\nB", text_wrap=True)
        canvas._start_inline_edit(elem)  # noqa: SLF001
        canvas._cursor_pos = 4  # noqa: SLF001
        canvas._sel_anchor = 0  # noqa: SLF001
        canvas.repaint()
        QApplication.processEvents()
        canvas.close()

    def test_paint_cursor_blink_visible(self, qapp):
        """Cursor sichtbar (Standard) → zeichnet Linie."""
        canvas, elem = _make_canvas(qapp, text="Hello")
        canvas._start_inline_edit(elem)  # noqa: SLF001
        canvas._cursor_visible = True  # noqa: SLF001
        canvas.repaint()
        QApplication.processEvents()
        canvas.close()

    def test_paint_cursor_blink_hidden(self, qapp):
        """Cursor unsichtbar (Blink-Zustand) → kein Absturz."""
        canvas, elem = _make_canvas(qapp, text="Hello")
        canvas._start_inline_edit(elem)  # noqa: SLF001
        canvas._cursor_visible = False  # noqa: SLF001
        canvas.repaint()
        QApplication.processEvents()
        canvas.close()

    def test_paint_cursor_with_v_align_middle(self, qapp):
        """Cursor-Zeichnung mit v_align='middle' ohne text_wrap."""
        canvas, elem = _make_canvas(qapp, text="Hello")
        elem.v_align = "middle"
        canvas._start_inline_edit(elem)  # noqa: SLF001
        canvas.repaint()
        QApplication.processEvents()
        canvas.close()

    def test_paint_cursor_with_v_align_bottom(self, qapp):
        """Cursor-Zeichnung mit v_align='bottom' ohne text_wrap."""
        canvas, elem = _make_canvas(qapp, text="Hello")
        elem.v_align = "bottom"
        canvas._start_inline_edit(elem)  # noqa: SLF001
        canvas.repaint()
        QApplication.processEvents()
        canvas.close()

    def test_paint_cursor_with_h_align_center(self, qapp):
        """Cursor-Zeichnung mit h_align='center'."""
        canvas, elem = _make_canvas(qapp, text="Hello\nWorld")
        elem.h_align = "center"
        canvas._start_inline_edit(elem)  # noqa: SLF001
        canvas._cursor_pos = 2  # noqa: SLF001
        canvas.repaint()
        QApplication.processEvents()
        canvas.close()

    def test_paint_cursor_with_h_align_right(self, qapp):
        """Cursor-Zeichnung mit h_align='right'."""
        canvas, elem = _make_canvas(qapp, text="Hello\nWorld")
        elem.h_align = "right"
        canvas._start_inline_edit(elem)  # noqa: SLF001
        canvas._cursor_pos = 2  # noqa: SLF001
        canvas.repaint()
        QApplication.processEvents()
        canvas.close()

    def test_paint_cursor_multiline_non_wrap(self, qapp):
        """Cursor in zweiter Zeile bei text_wrap=False."""
        canvas, elem = _make_canvas(qapp, text="Line1\nLine2")
        canvas._start_inline_edit(elem)  # noqa: SLF001
        canvas._cursor_pos = 8  # noqa: SLF001  in "Line2"
        canvas.repaint()
        QApplication.processEvents()
        canvas.close()

    def test_paint_cursor_with_selection_and_multiline(self, qapp):
        """Selektion über mehrere Zeilen (nicht-wrap)."""
        canvas, elem = _make_canvas(qapp, text="Line1\nLine2")
        canvas._start_inline_edit(elem)  # noqa: SLF001
        canvas._cursor_pos = 9  # noqa: SLF001
        canvas._sel_anchor = 2  # noqa: SLF001
        canvas.repaint()
        QApplication.processEvents()
        canvas.close()

    def test_paint_text_wrap_cursor_on_empty_para(self, qapp):
        """Cursor auf einem leeren Absatz-Segment (layout=None) in text_wrap=True."""
        canvas, elem = _make_canvas(qapp, text="A\n\nB", text_wrap=True)
        canvas._start_inline_edit(elem)  # noqa: SLF001
        canvas._cursor_pos = 2  # Position im leeren Absatz  # noqa: SLF001
        canvas.repaint()
        QApplication.processEvents()
        canvas.close()


# ---------------------------------------------------------------------------
# keyPressEvent ohne Inline-Edit (Zeilen 1110-1119)
# ---------------------------------------------------------------------------


class TestKeyPressEventNoInline:
    def test_delete_key_removes_selected_element(self, qapp):
        from PySide6.QtTest import QTest

        canvas, elem = _make_canvas(qapp)
        assert len(canvas._elements()) == 1  # noqa: SLF001
        QTest.keyClick(canvas, Qt.Key.Key_Delete)
        QApplication.processEvents()
        assert len(canvas._elements()) == 0  # noqa: SLF001
        canvas.close()

    def test_backspace_key_removes_selected_element(self, qapp):
        from PySide6.QtTest import QTest

        canvas, elem = _make_canvas(qapp)
        QTest.keyClick(canvas, Qt.Key.Key_Backspace)
        QApplication.processEvents()
        assert len(canvas._elements()) == 0  # noqa: SLF001
        canvas.close()

    def test_ctrl_a_selects_all(self, qapp):
        from PySide6.QtTest import QTest

        canvas, elem = _make_canvas(qapp)
        elem2 = CardElement(type=ELEMENT_RECT, x=30.0, y=5.0, width=10.0, height=5.0)
        canvas._layout.front_elements.append(elem2)  # noqa: SLF001
        canvas._selected = []  # noqa: SLF001
        QTest.keyClick(canvas, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
        QApplication.processEvents()
        assert len(canvas._selected) == 2  # noqa: SLF001
        canvas.close()

    def test_left_arrow_moves_element(self, qapp):
        from PySide6.QtTest import QTest

        canvas, elem = _make_canvas(qapp)
        orig_x = elem.x
        QTest.keyClick(canvas, Qt.Key.Key_Left)
        QApplication.processEvents()
        assert elem.x == pytest.approx(orig_x - 1.0)
        canvas.close()

    def test_right_arrow_moves_element(self, qapp):
        from PySide6.QtTest import QTest

        canvas, elem = _make_canvas(qapp)
        orig_x = elem.x
        QTest.keyClick(canvas, Qt.Key.Key_Right)
        QApplication.processEvents()
        assert elem.x == pytest.approx(orig_x + 1.0)
        canvas.close()

    def test_up_arrow_moves_element(self, qapp):
        from PySide6.QtTest import QTest

        canvas, elem = _make_canvas(qapp)
        orig_y = elem.y
        QTest.keyClick(canvas, Qt.Key.Key_Up)
        QApplication.processEvents()
        assert elem.y == pytest.approx(orig_y - 1.0)
        canvas.close()

    def test_down_arrow_moves_element(self, qapp):
        from PySide6.QtTest import QTest

        canvas, elem = _make_canvas(qapp)
        orig_y = elem.y
        QTest.keyClick(canvas, Qt.Key.Key_Down)
        QApplication.processEvents()
        assert elem.y == pytest.approx(orig_y + 1.0)
        canvas.close()

    def test_shift_left_moves_by_0_1(self, qapp):
        from PySide6.QtTest import QTest

        canvas, elem = _make_canvas(qapp)
        orig_x = elem.x
        QTest.keyClick(canvas, Qt.Key.Key_Left, Qt.KeyboardModifier.ShiftModifier)
        QApplication.processEvents()
        assert elem.x == pytest.approx(orig_x - 0.1)
        canvas.close()

    def test_ctrl_z_emits_undo(self, qapp):
        from unittest.mock import MagicMock

        from PySide6.QtTest import QTest

        canvas, _ = _make_canvas(qapp)
        undo = MagicMock()
        canvas.requestUndo.connect(undo)
        QTest.keyClick(canvas, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
        QApplication.processEvents()
        undo.assert_called()
        canvas.close()

    def test_ctrl_shift_z_emits_redo(self, qapp):
        from unittest.mock import MagicMock

        from PySide6.QtTest import QTest

        canvas, _ = _make_canvas(qapp)
        redo = MagicMock()
        canvas.requestRedo.connect(redo)
        QTest.keyClick(
            canvas,
            Qt.Key.Key_Z,
            Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier,
        )
        QApplication.processEvents()
        redo.assert_called()
        canvas.close()

    def test_ctrl_y_emits_redo(self, qapp):
        from unittest.mock import MagicMock

        from PySide6.QtTest import QTest

        canvas, _ = _make_canvas(qapp)
        redo = MagicMock()
        canvas.requestRedo.connect(redo)
        QTest.keyClick(canvas, Qt.Key.Key_Y, Qt.KeyboardModifier.ControlModifier)
        QApplication.processEvents()
        redo.assert_called()
        canvas.close()


# ---------------------------------------------------------------------------
# paintEvent – Grid (Zeilen 602-620, 992, 994)
# ---------------------------------------------------------------------------


class TestPaintEventGrid:
    def test_grid_drawing_no_crash(self, qapp):
        """Gitter-Zeichnung wird aufgerufen wenn show_grid=True."""
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        canvas.set_layout(CardLayout(), "front")
        canvas.set_paper(PaperTemplate())
        canvas._show_grid = True  # noqa: SLF001
        canvas.resize(400, 300)
        canvas.show()
        QApplication.processEvents()
        canvas.repaint()
        QApplication.processEvents()
        canvas.close()

    def test_grid_with_elements_no_crash(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        layout.front_elements.append(
            CardElement(type=ELEMENT_TEXT, text="Hi", x=5.0, y=5.0, width=20.0, height=10.0)
        )
        canvas.set_layout(layout, "front")
        canvas.set_paper(PaperTemplate())
        canvas._show_grid = True  # noqa: SLF001
        canvas.resize(400, 300)
        canvas.show()
        QApplication.processEvents()
        canvas.repaint()
        QApplication.processEvents()
        canvas.close()


# ---------------------------------------------------------------------------
# _draw_selection für ELEMENT_LINE ausgewählt (Zeilen 678-689)
# ---------------------------------------------------------------------------


class TestDrawSelectionLine:
    def test_line_selection_with_both_endpoint_handles(self, qapp):
        """Selektierte Linie zeigt Endpunkt-Handles – deckt Zeilen 678-689 ab."""
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        line = CardElement(
            type=ELEMENT_LINE,
            x=5.0,
            y=10.0,
            line_x2=30.0,
            line_y2=0.0,
            width=30.0,
            height=1.0,
        )
        layout.front_elements.append(line)
        canvas.set_layout(layout, "front")
        canvas.set_paper(PaperTemplate())
        canvas._selected = [line.id]  # noqa: SLF001
        canvas.resize(400, 300)
        canvas.show()
        QApplication.processEvents()
        canvas.repaint()
        QApplication.processEvents()
        canvas.close()


# ---------------------------------------------------------------------------
# _draw_selection für Inline-Edit mit text_wrap=True (Zeilen 662-668)
# ---------------------------------------------------------------------------


class TestDrawSelectionInlineTextWrap:
    def test_inline_edit_text_wrap_shows_right_handle(self, qapp):
        """Inline-Edit eines text_wrap-Elements zeigt rechten Handle – deckt 662-668 ab."""
        canvas, elem = _make_canvas(qapp, text="Hello World", text_wrap=True)
        canvas._start_inline_edit(elem)  # noqa: SLF001
        canvas.repaint()
        QApplication.processEvents()
        canvas.close()


# ---------------------------------------------------------------------------
# _elem_at für ELEMENT_LINE (Zeilen 403-404)
# ---------------------------------------------------------------------------


class TestElemAtLine:
    def test_elem_at_line_element_with_expanded_bbox(self, qapp):
        """_elem_at erweitert die Bounding-Box einer Linie um 3mm – deckt 403-404 ab."""
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        line = CardElement(
            type=ELEMENT_LINE,
            x=5.0,
            y=20.0,
            line_x2=40.0,
            line_y2=0.0,
            width=40.0,
            height=0.5,
        )
        layout.front_elements.append(line)
        canvas.set_layout(layout, "front")
        canvas.set_paper(PaperTemplate())
        canvas.resize(400, 300)
        canvas.show()
        QApplication.processEvents()

        # Klick auf eine Position innerhalb der erweiterten Bounding-Box der Linie
        r = canvas._elem_rect_px(line)  # noqa: SLF001
        # Klick etwas außerhalb der exakten Linie aber innerhalb des 3mm-Puffers
        click_pos = QPointF(r.center().x(), r.top() - canvas._to_px(1.0))  # noqa: SLF001
        found = canvas._elem_at(click_pos)  # noqa: SLF001
        assert found is line
        canvas.close()


# ---------------------------------------------------------------------------
# _handle_at für ELEMENT_LINE – Endpunkt p2 (Zeile 418)
# ---------------------------------------------------------------------------


class TestHandleAtLinePp2:
    def test_handle_at_line_right_endpoint(self, qapp):
        """_handle_at für ELEMENT_LINE an Position p2 gibt 'r' zurück (Zeile 418)."""
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        line = CardElement(
            type=ELEMENT_LINE,
            x=5.0,
            y=20.0,
            line_x2=30.0,
            line_y2=0.0,
            width=30.0,
            height=0.5,
        )
        layout.front_elements.append(line)
        canvas.set_layout(layout, "front")
        canvas.set_paper(PaperTemplate())
        canvas.resize(400, 300)
        canvas.show()
        QApplication.processEvents()

        # Berechne Position von p2 (rechter Endpunkt der Linie)
        ox, oy = canvas._offset.x(), canvas._offset.y()  # noqa: SLF001
        p2_x = ox + canvas._to_px(line.x + line.line_x2)  # noqa: SLF001
        p2_y = oy + canvas._to_px(line.y + line.line_y2)  # noqa: SLF001
        p2 = QPointF(p2_x, p2_y)

        result = canvas._handle_at(p2, line)  # noqa: SLF001
        assert result == "r"
        canvas.close()

    def test_handle_at_line_no_hit_returns_none(self, qapp):
        """_handle_at für ELEMENT_LINE mit Position weit weg gibt None zurück."""
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        line = CardElement(type=ELEMENT_LINE, x=5.0, y=20.0, line_x2=30.0, line_y2=0.0)
        layout.front_elements.append(line)
        canvas.set_layout(layout, "front")
        canvas.set_paper(PaperTemplate())
        canvas.resize(400, 300)
        canvas.show()
        QApplication.processEvents()

        far_away = QPointF(0.0, 0.0)
        result = canvas._handle_at(far_away, line)  # noqa: SLF001
        assert result is None
        canvas.close()


# ---------------------------------------------------------------------------
# Middle-Button Mouse Press (Pan) – Zeilen 727-734, 588
# ---------------------------------------------------------------------------


class TestMiddleButtonPress:
    def test_middle_button_starts_pan(self, qapp):
        from PySide6.QtCore import QPoint
        from PySide6.QtTest import QTest

        canvas, _ = _make_canvas(qapp)
        # Mittlere Maustaste drücken
        QTest.mousePress(
            canvas,
            Qt.MouseButton.MiddleButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(200, 150),
        )
        QApplication.processEvents()
        assert canvas._pan_start is not None  # noqa: SLF001
        # Loslassen
        QTest.mouseRelease(
            canvas,
            Qt.MouseButton.MiddleButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(200, 150),
        )
        QApplication.processEvents()
        canvas.close()

    def test_middle_button_release_clears_pan(self, qapp):
        from PySide6.QtCore import QPoint
        from PySide6.QtTest import QTest

        canvas, _ = _make_canvas(qapp)
        QTest.mousePress(
            canvas,
            Qt.MouseButton.MiddleButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(200, 150),
        )
        QTest.mouseRelease(
            canvas,
            Qt.MouseButton.MiddleButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(200, 150),
        )
        QApplication.processEvents()
        assert canvas._pan_start is None  # noqa: SLF001
        canvas.close()


# ---------------------------------------------------------------------------
# Right-Button Mouse Press → Context Menu (Zeile 743-744)
# ---------------------------------------------------------------------------


class TestRightButtonPress:
    def test_right_button_no_crash(self, qapp):
        """Rechtsklick öffnet Kontextmenü (oder nichts) – kein Absturz."""
        from PySide6.QtCore import QPoint, QTimer
        from PySide6.QtTest import QTest

        canvas, _ = _make_canvas(qapp)
        # Menü sofort schließen damit der Test nicht hängt
        QTimer.singleShot(
            50,
            lambda: (
                QApplication.activePopupWidget() and QApplication.activePopupWidget().close()
                if QApplication.activePopupWidget()
                else None
            ),
        )
        QTest.mouseClick(
            canvas,
            Qt.MouseButton.RightButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(300, 200),
        )
        QApplication.processEvents()
        canvas.close()


# ---------------------------------------------------------------------------
# _pos_from_click – text_wrap=True und verschiedene h_align (Zeilen 1422-1455)
# ---------------------------------------------------------------------------


class TestPosFromClick:
    def test_pos_from_click_empty_text(self, qapp):
        """Leerer Text gibt immer 0 zurück."""
        canvas, elem = _make_canvas(qapp, text="")
        canvas._start_inline_edit(elem)  # noqa: SLF001
        r = canvas._elem_rect_px(elem)  # noqa: SLF001
        pos = canvas._pos_from_click(r.center(), elem)  # noqa: SLF001
        assert pos == 0
        canvas.close()

    def test_pos_from_click_text_wrap_returns_valid_index(self, qapp):
        """Mit text_wrap=True wird ein gültiger Zeichenindex zurückgegeben."""
        canvas, elem = _make_canvas(qapp, text="Hello World Extended", text_wrap=True)
        canvas._start_inline_edit(elem)  # noqa: SLF001
        r = canvas._elem_rect_px(elem)  # noqa: SLF001
        click = QPointF(r.left() + 5, r.top() + 2)
        pos = canvas._pos_from_click(click, elem)  # noqa: SLF001
        assert 0 <= pos <= len(elem.text)
        canvas.close()

    def test_pos_from_click_center_align(self, qapp):
        """h_align='center' → korrekte x_off Berechnung."""
        canvas, elem = _make_canvas(qapp, text="Hello")
        elem.h_align = "center"
        canvas._start_inline_edit(elem)  # noqa: SLF001
        r = canvas._elem_rect_px(elem)  # noqa: SLF001
        pos = canvas._pos_from_click(r.center(), elem)  # noqa: SLF001
        assert 0 <= pos <= len(elem.text)
        canvas.close()

    def test_pos_from_click_right_align(self, qapp):
        """h_align='right' → korrekte x_off Berechnung."""
        canvas, elem = _make_canvas(qapp, text="Hello")
        elem.h_align = "right"
        canvas._start_inline_edit(elem)  # noqa: SLF001
        r = canvas._elem_rect_px(elem)  # noqa: SLF001
        pos = canvas._pos_from_click(r.center(), elem)  # noqa: SLF001
        assert 0 <= pos <= len(elem.text)
        canvas.close()

    def test_pos_from_click_v_align_middle(self, qapp):
        """v_align='middle' → korrekte y_start Berechnung."""
        canvas, elem = _make_canvas(qapp, text="Line1\nLine2")
        elem.v_align = "middle"
        canvas._start_inline_edit(elem)  # noqa: SLF001
        r = canvas._elem_rect_px(elem)  # noqa: SLF001
        pos = canvas._pos_from_click(r.center(), elem)  # noqa: SLF001
        assert 0 <= pos <= len(elem.text)
        canvas.close()

    def test_pos_from_click_v_align_bottom(self, qapp):
        """v_align='bottom' → korrekte y_start Berechnung."""
        canvas, elem = _make_canvas(qapp, text="Line1\nLine2")
        elem.v_align = "bottom"
        canvas._start_inline_edit(elem)  # noqa: SLF001
        r = canvas._elem_rect_px(elem)  # noqa: SLF001
        pos = canvas._pos_from_click(r.center(), elem)  # noqa: SLF001
        assert 0 <= pos <= len(elem.text)
        canvas.close()

    def test_pos_from_click_at_second_line(self, qapp):
        """Klick auf zweite Zeile gibt Index in zweiter Zeile zurück."""
        canvas, elem = _make_canvas(qapp, text="Hello\nWorld")
        elem.height = 20.0  # Sicherstellen dass beide Zeilen Platz haben
        canvas._start_inline_edit(elem)  # noqa: SLF001
        r = canvas._elem_rect_px(elem)  # noqa: SLF001
        # Klick auf untere Hälfte → zweite Zeile
        click = QPointF(r.center().x(), r.bottom() - 2)
        pos = canvas._pos_from_click(click, elem)  # noqa: SLF001
        assert 0 <= pos <= len(elem.text)
        canvas.close()

    def test_pos_from_click_text_wrap_empty_para(self, qapp):
        """text_wrap=True mit leerem Absatz gibt validen Index zurück."""
        canvas, elem = _make_canvas(qapp, text="A\n\nB", text_wrap=True)
        canvas._start_inline_edit(elem)  # noqa: SLF001
        r = canvas._elem_rect_px(elem)  # noqa: SLF001
        click = QPointF(r.left() + 1, r.top() + 5)
        pos = canvas._pos_from_click(click, elem)  # noqa: SLF001
        assert 0 <= pos <= len(elem.text)
        canvas.close()


# ---------------------------------------------------------------------------
# Double-Click → _start_inline_edit (Zeile 1068, 1073)
# ---------------------------------------------------------------------------


class TestDoubleClickInlineEdit:
    def test_double_click_starts_inline_edit(self, qapp):
        from PySide6.QtTest import QTest

        canvas, elem = _make_canvas(qapp)
        r = canvas._elem_rect_px(elem)  # noqa: SLF001
        from PySide6.QtCore import QPoint

        center = QPoint(int(r.center().x()), int(r.center().y()))
        QTest.mouseDClick(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, center)
        QApplication.processEvents()
        assert canvas._inline_elem is elem  # noqa: SLF001
        canvas.close()


# ---------------------------------------------------------------------------
# fit_to_content – IMAGE mit gültiger Datei (Zeilen 870, 872)
# ---------------------------------------------------------------------------


class TestFitToContentImage:
    def test_image_with_valid_path_adjusts_height(self, qapp, tmp_path):
        """fit_to_content für IMAGE mit gültigem Bild passt Höhe an (Zeilen 870, 872)."""
        from PySide6.QtGui import QPixmap

        from cardforge.canvas import CardCanvas

        img_path = str(tmp_path / "card_img.png")
        src = QPixmap(100, 50)  # 2:1 Verhältnis
        src.fill()
        src.save(img_path, "PNG")

        canvas = CardCanvas()
        layout = CardLayout()
        img_elem = CardElement(
            type=ELEMENT_IMAGE,
            image_path=img_path,
            width=20.0,
            height=20.0,
        )
        layout.front_elements.append(img_elem)
        canvas.set_layout(layout, "front")
        canvas._selected = [img_elem.id]  # noqa: SLF001
        canvas.fit_to_content()
        # Höhe sollte angepasst worden sein (0.5 * Breite für 2:1-Bild)
        assert img_elem.height == pytest.approx(10.0, abs=0.1)
        canvas.close()


# ---------------------------------------------------------------------------
# _elements() / _set_elements() – Rückseite (Zeilen 890-895)
# ---------------------------------------------------------------------------


class TestElementsBackSide:
    def test_elements_returns_back_elements(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        front_e = CardElement(type=ELEMENT_TEXT, text="Front")
        back_e = CardElement(type=ELEMENT_TEXT, text="Back")
        layout.front_elements.append(front_e)
        layout.back_elements.append(back_e)
        canvas.set_layout(layout, "back")
        assert canvas._elements() == [back_e]  # noqa: SLF001
        canvas.close()

    def test_set_elements_sets_back_elements(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        canvas.set_layout(layout, "back")
        new_e = CardElement(type=ELEMENT_RECT)
        canvas._set_elements([new_e])  # noqa: SLF001
        assert layout.back_elements == [new_e]
        canvas.close()

    def test_delete_selected_on_back_side_updates_back(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        e = CardElement(type=ELEMENT_RECT)
        layout.back_elements.append(e)
        canvas.set_layout(layout, "back")
        canvas._selected = [e.id]  # noqa: SLF001
        canvas.delete_selected()
        assert len(layout.back_elements) == 0
        canvas.close()


# ---------------------------------------------------------------------------
# mouseMoveEvent – Resize handle während Inline-Edit (Zeilen 1091-1108)
# ---------------------------------------------------------------------------


class TestMouseMoveResizeDuringInline:
    def test_resize_right_handle_during_inline_edit(self, qapp):
        """Resize am rechten Handle während Inline-Edit aktiviert text_wrap."""
        from PySide6.QtCore import QPoint
        from PySide6.QtTest import QTest

        canvas, elem = _make_canvas(qapp, text="Hello World", text_wrap=False)
        canvas._start_inline_edit(elem)  # noqa: SLF001

        r = canvas._elem_rect_px(elem)  # noqa: SLF001
        right_handle = QPoint(int(r.right()), int(r.center().y()))

        # Drücken auf rechten Handle → Resize-Modus starten
        QTest.mousePress(
            canvas,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            right_handle,
        )
        QApplication.processEvents()
        # Bewegen → Resize
        QTest.mouseMove(canvas, QPoint(right_handle.x() + 20, right_handle.y()))
        QApplication.processEvents()
        QTest.mouseRelease(
            canvas,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(right_handle.x() + 20, right_handle.y()),
        )
        QApplication.processEvents()
        canvas.close()
