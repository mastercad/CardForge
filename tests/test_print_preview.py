"""Tests für cardforge.print_preview – Renderer und Dialog."""

from __future__ import annotations

from cardforge.models import ELEMENT_TEXT, CardElement, CardLayout, Project


def _make_project() -> Project:
    p = Project(name="PreviewTest")
    layout = CardLayout(name="Karte 1")
    layout.front_elements.append(
        CardElement(type=ELEMENT_TEXT, text="Vorschau", x=5.0, y=5.0, width=40.0, height=10.0)
    )
    p.cards.append(layout)
    return p


class TestRenderPageToPixmap:
    def test_basic_front_page(self, qapp):
        from cardforge.print_preview import render_page_to_pixmap

        p = _make_project()
        pm = render_page_to_pixmap(p, "front", [0])
        assert not pm.isNull()
        assert pm.width() > 0
        assert pm.height() > 0

    def test_back_page(self, qapp):
        from cardforge.print_preview import render_page_to_pixmap

        p = _make_project()
        pm = render_page_to_pixmap(p, "back", [0])
        assert not pm.isNull()

    def test_with_cut_marks(self, qapp):
        from cardforge.print_preview import render_page_to_pixmap

        p = _make_project()
        pm = render_page_to_pixmap(p, "front", [0], cut_marks=True)
        assert not pm.isNull()

    def test_without_cut_marks(self, qapp):
        from cardforge.print_preview import render_page_to_pixmap

        p = _make_project()
        pm = render_page_to_pixmap(p, "front", [0], cut_marks=False)
        assert not pm.isNull()

    def test_empty_card_indices(self, qapp):
        from cardforge.print_preview import render_page_to_pixmap

        p = _make_project()
        pm = render_page_to_pixmap(p, "front", [])
        assert not pm.isNull()

    def test_size_proportional_to_paper(self, qapp):
        from cardforge.print_preview import render_page_to_pixmap

        p = _make_project()
        px_per_mm = 2.0
        pt = p.paper_template
        pm = render_page_to_pixmap(p, "front", [0], px_per_mm=px_per_mm)
        expected_w = int(pt.paper_width * px_per_mm)
        expected_h = int(pt.paper_height * px_per_mm)
        assert pm.width() == expected_w
        assert pm.height() == expected_h

    def test_back_duplex_long_edge(self, qapp):
        from cardforge.print_preview import render_page_to_pixmap

        p = _make_project()
        pm = render_page_to_pixmap(p, "back", [0], back_duplex=True, duplex_flip="long-edge")
        assert not pm.isNull()

    def test_back_duplex_short_edge(self, qapp):
        from cardforge.print_preview import render_page_to_pixmap

        p = _make_project()
        pm = render_page_to_pixmap(p, "back", [0], back_duplex=True, duplex_flip="short-edge")
        assert not pm.isNull()


class TestPrintPreviewDialog:
    def test_creates_without_crash(self, qapp):
        from cardforge.print_preview import PrintPreviewDialog

        p = _make_project()
        dlg = PrintPreviewDialog(p)
        assert dlg is not None
        dlg.close()

    def test_window_title(self, qapp):
        from cardforge.print_preview import PrintPreviewDialog

        p = _make_project()
        dlg = PrintPreviewDialog(p)
        assert "Print" in dlg.windowTitle() or "Preview" in dlg.windowTitle()
        dlg.close()

    def test_initial_side_front(self, qapp):
        from cardforge.print_preview import PrintPreviewDialog

        p = _make_project()
        dlg = PrintPreviewDialog(p)
        assert dlg._side == "front"  # noqa: SLF001
        dlg.close()

    def test_initial_cut_marks_enabled(self, qapp):
        from cardforge.print_preview import PrintPreviewDialog

        p = _make_project()
        dlg = PrintPreviewDialog(p)
        assert dlg._cut_marks is True  # noqa: SLF001
        dlg.close()

    def test_project_stored(self, qapp):
        from cardforge.print_preview import PrintPreviewDialog

        p = _make_project()
        dlg = PrintPreviewDialog(p)
        assert dlg._project is p  # noqa: SLF001
        dlg.close()

    def test_on_side_changed_to_back(self, qapp):
        from cardforge.print_preview import PrintPreviewDialog

        p = _make_project()
        dlg = PrintPreviewDialog(p)
        dlg._rb_back.setChecked(True)  # noqa: SLF001
        # Löst _on_side_changed aus
        assert dlg._side == "back"  # noqa: SLF001
        dlg.close()

    def test_on_side_changed_to_both(self, qapp):
        from cardforge.print_preview import PrintPreviewDialog

        p = _make_project()
        dlg = PrintPreviewDialog(p)
        dlg._rb_both_prev.setChecked(True)  # noqa: SLF001
        assert dlg._side == "both"  # noqa: SLF001
        dlg.close()

    def test_on_zoom_updates_label_and_zoom(self, qapp):
        from cardforge.print_preview import PrintPreviewDialog

        p = _make_project()
        dlg = PrintPreviewDialog(p)
        dlg._zoom_slider.setValue(150)  # noqa: SLF001
        assert "150" in dlg._zoom_lbl.text()  # noqa: SLF001
        dlg.close()

    def test_refresh_both_sides_no_crash(self, qapp):
        from cardforge.print_preview import PrintPreviewDialog

        p = _make_project()
        dlg = PrintPreviewDialog(p)
        dlg._rb_both_prev.setChecked(True)  # noqa: SLF001
        dlg._refresh()  # noqa: SLF001 – kein Absturz
        dlg.close()

    def test_open_print_dialog_launches(self, qapp):
        from unittest.mock import MagicMock, patch

        from cardforge.print_preview import PrintPreviewDialog

        p = _make_project()
        dlg = PrintPreviewDialog(p)
        mock_inst = MagicMock()
        mock_inst.exec.return_value = 0
        # _open_print_dialog importiert lokal: from .print_dialog import PrintExportDialog
        with patch("cardforge.print_dialog.PrintExportDialog", return_value=mock_inst):
            dlg._open_print_dialog()  # noqa: SLF001
            mock_inst.exec.assert_called_once()
        dlg.close()


# ---------------------------------------------------------------------------
# _PreviewWidget.paintEvent – pixmap None und gesetzt
# ---------------------------------------------------------------------------


class TestPreviewWidgetPaint:
    def test_paint_no_pixmap_grey_background(self, qapp):
        """paintEvent ohne Pixmap zeichnet nur den grauen Hintergrund."""
        from PySide6.QtWidgets import QApplication

        from cardforge.print_preview import _PreviewWidget

        w = _PreviewWidget()
        w.resize(200, 200)
        w.show()
        QApplication.processEvents()
        # _pixmap ist None → grauer Hintergrund, kein Absturz
        w.repaint()
        w.close()

    def test_paint_with_pixmap_draws_image(self, qapp):
        """paintEvent mit gesetztem Pixmap zeichnet das Bild zentriert."""
        from PySide6.QtGui import QPixmap
        from PySide6.QtWidgets import QApplication

        from cardforge.print_preview import _PreviewWidget

        w = _PreviewWidget()
        w.resize(200, 200)
        pm = QPixmap(50, 50)
        pm.fill()
        w.set_pixmap(pm)
        w.show()
        QApplication.processEvents()
        w.repaint()
        w.close()


# ---------------------------------------------------------------------------
# _Renderer.render_page – ci out of bounds und unsichtbares Element
# ---------------------------------------------------------------------------


class TestRendererSpecialBranches:
    def test_render_page_ci_out_of_bounds(self, qapp):
        """ci >= len(cards) löst continue aus – kein Absturz."""
        from cardforge.print_preview import render_page_to_pixmap

        p = _make_project()
        # card_indices=[5] aber p.cards hat nur 1 Element → ci=5 >= 1 → continue
        pm = render_page_to_pixmap(p, "front", [5])
        assert not pm.isNull()

    def test_render_page_invisible_element_skipped(self, qapp):
        """Unsichtbares Element in _draw_card deckt [127, 126]-Zweig ab."""
        from cardforge.models import ELEMENT_TEXT, CardElement, CardLayout, Project
        from cardforge.print_preview import render_page_to_pixmap

        p = Project(name="T")
        layout = CardLayout()
        visible_e = CardElement(type=ELEMENT_TEXT, text="Vis", visible=True)
        invisible_e = CardElement(type=ELEMENT_TEXT, text="Hid", visible=False)
        layout.front_elements.extend([visible_e, invisible_e])
        p.cards.append(layout)
        pm = render_page_to_pixmap(p, "front", [0])
        assert not pm.isNull()
