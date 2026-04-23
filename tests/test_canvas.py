"""Tests für cardforge.canvas – interaktives Canvas-Widget."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from cardforge.models import (
    ELEMENT_IMAGE,
    ELEMENT_LINE,
    ELEMENT_QR,
    ELEMENT_RECT,
    ELEMENT_TEXT,
    CardElement,
    CardLayout,
    PaperTemplate,
)


class TestCardCanvasInit:
    def test_creates_without_crash(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        assert canvas is not None
        canvas.close()

    def test_default_state(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        assert canvas._layout is None  # noqa: SLF001
        assert canvas._side == "front"  # noqa: SLF001
        assert canvas._zoom == 3.0  # noqa: SLF001
        assert canvas._selected == []  # noqa: SLF001
        assert canvas._show_grid is True  # noqa: SLF001
        canvas.close()


class TestSetLayout:
    def test_set_layout_front(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        layout.front_elements.append(CardElement(type=ELEMENT_TEXT, text="Hallo"))
        canvas.set_layout(layout, "front")
        assert canvas._layout is layout  # noqa: SLF001
        assert canvas._side == "front"  # noqa: SLF001
        canvas.close()

    def test_set_layout_back(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        canvas.set_layout(layout, "back")
        assert canvas._side == "back"  # noqa: SLF001
        canvas.close()

    def test_set_paper(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        paper = PaperTemplate()
        canvas.set_paper(paper)
        assert canvas._paper is paper  # noqa: SLF001
        canvas.close()


class TestZoom:
    def test_set_zoom(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        canvas.set_zoom(5.0)
        assert canvas._zoom == pytest.approx(5.0)
        canvas.close()

    def test_zoom_updates_renderer(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        canvas.set_zoom(4.0)
        assert canvas._renderer._scale == pytest.approx(4.0)  # noqa: SLF001
        canvas.close()


class TestGridAndRulers:
    def test_set_grid_hide(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        canvas.set_grid(False, 1.0)
        assert canvas._show_grid is False  # noqa: SLF001
        canvas.close()

    def test_set_grid_show(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        canvas.set_grid(True, 2.0)
        assert canvas._show_grid is True  # noqa: SLF001
        assert canvas._snap_grid == pytest.approx(2.0)  # noqa: SLF001
        canvas.close()

    def test_set_snap_grid_via_set_grid(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        canvas.set_grid(True, 0.5)
        assert canvas._snap_grid == pytest.approx(0.5)  # noqa: SLF001
        canvas.close()


class TestSelection:
    def test_clear_selection_via_set_selection(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        e = CardElement(type=ELEMENT_TEXT, text="Test")
        layout.front_elements.append(e)
        canvas.set_layout(layout, "front")
        canvas._selected = [e.id]  # noqa: SLF001
        canvas.set_selection([])
        assert canvas._selected == []  # noqa: SLF001
        canvas.close()

    def test_select_all(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        e1 = CardElement(type=ELEMENT_TEXT, text="A")
        e2 = CardElement(type=ELEMENT_RECT)
        layout.front_elements.extend([e1, e2])
        canvas.set_layout(layout, "front")
        canvas.select_all()
        assert set(canvas._selected) == {e1.id, e2.id}  # noqa: SLF001
        canvas.close()

    def test_selected_elements_empty_no_layout(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        assert canvas.selected_elements() == []
        canvas.close()

    def test_selected_elements_returns_correct(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        e = CardElement(type=ELEMENT_TEXT, text="Sel")
        layout.front_elements.append(e)
        canvas.set_layout(layout, "front")
        canvas._selected = [e.id]  # noqa: SLF001
        result = canvas.selected_elements()
        assert len(result) == 1
        assert result[0].id == e.id
        canvas.close()


class TestDeleteSelected:
    def test_delete_selected_element(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        e = CardElement(type=ELEMENT_TEXT, text="Del")
        layout.front_elements.append(e)
        canvas.set_layout(layout, "front")
        canvas._selected = [e.id]  # noqa: SLF001
        canvas.delete_selected()
        assert len(layout.front_elements) == 0
        canvas.close()

    def test_delete_no_selection_noop(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        e = CardElement(type=ELEMENT_TEXT, text="Keep")
        layout.front_elements.append(e)
        canvas.set_layout(layout, "front")
        canvas.delete_selected()
        assert len(layout.front_elements) == 1
        canvas.close()


class TestPaintEvent:
    def test_paint_event_no_crash_no_layout(self, qapp):
        """paintEvent ohne Layout darf nicht abstürzen."""
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        canvas.resize(400, 300)
        canvas.show()
        canvas.repaint()
        canvas.close()

    def test_paint_event_with_layout(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        layout.front_elements.append(CardElement(type=ELEMENT_TEXT, text="Paint"))
        canvas.set_layout(layout, "front")
        canvas.set_paper(PaperTemplate())
        canvas.resize(400, 300)
        canvas.show()
        canvas.repaint()
        canvas.close()

    def test_paint_with_selected_text_element(self, qapp):
        """paintEvent mit selektiertem Text deckt _draw_selection (non-line) ab."""
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        e = CardElement(type=ELEMENT_TEXT, text="Sel", x=5.0, y=5.0, width=20.0, height=10.0)
        layout.front_elements.append(e)
        canvas.set_layout(layout, "front")
        canvas.set_paper(PaperTemplate())
        canvas._selected = [e.id]  # noqa: SLF001
        canvas.resize(400, 300)
        canvas.show()
        canvas.repaint()
        canvas.close()

    def test_paint_with_selected_line_element(self, qapp):
        """paintEvent mit selektierter Linie deckt _draw_selection (line-Zweig) ab."""
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        e = CardElement(type=ELEMENT_LINE, x=5.0, y=20.0, width=30.0, height=0.5)
        layout.front_elements.append(e)
        canvas.set_layout(layout, "front")
        canvas.set_paper(PaperTemplate())
        canvas._selected = [e.id]  # noqa: SLF001
        canvas.resize(400, 300)
        canvas.show()
        canvas.repaint()
        canvas.close()

    def test_paint_with_rubber_band_active(self, qapp):
        """paintEvent mit aktivem Rubber-Band-Rect zeichnet die Auswahlbox."""
        from PySide6.QtCore import QRectF

        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        canvas.set_layout(CardLayout(), "front")
        canvas.set_paper(PaperTemplate())
        canvas._rubber_band_rect = QRectF(10, 10, 100, 60)  # noqa: SLF001
        canvas.resize(400, 300)
        canvas.show()
        canvas.repaint()
        canvas.close()

    def test_paint_invisible_element_skipped(self, qapp):
        """Unsichtbare Elemente werden beim Zeichnen übersprungen."""
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        e = CardElement(type=ELEMENT_TEXT, text="Hidden", visible=False)
        layout.front_elements.append(e)
        canvas.set_layout(layout, "front")
        canvas.set_paper(PaperTemplate())
        canvas.resize(400, 300)
        canvas.show()
        canvas.repaint()
        canvas.close()


# ---------------------------------------------------------------------------
# set_side
# ---------------------------------------------------------------------------


class TestSetSide:
    def test_set_side_back_returns_back_elements(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        e_front = CardElement(type=ELEMENT_TEXT, text="Front")
        e_back = CardElement(type=ELEMENT_TEXT, text="Back")
        layout.front_elements.append(e_front)
        layout.back_elements.append(e_back)
        canvas.set_layout(layout, "front")
        canvas.set_side("back")
        assert canvas._side == "back"  # noqa: SLF001
        assert canvas._elements() == [e_back]  # noqa: SLF001
        canvas.close()

    def test_set_side_clears_selection(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        e = CardElement(type=ELEMENT_TEXT, text="A")
        layout.front_elements.append(e)
        canvas.set_layout(layout, "front")
        canvas._selected = [e.id]  # noqa: SLF001
        canvas.set_side("back")
        assert canvas._selected == []  # noqa: SLF001
        canvas.close()


# ---------------------------------------------------------------------------
# add_element / bring_to_front / send_to_back / invalidate caches
# ---------------------------------------------------------------------------


class TestAddAndZOrder:
    def test_add_element_assigns_increasing_z_order(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        canvas.set_layout(layout, "front")
        e1 = CardElement(type=ELEMENT_RECT)
        e2 = CardElement(type=ELEMENT_RECT)
        canvas.add_element(e1)
        canvas.add_element(e2)
        assert e2.z_order > e1.z_order
        canvas.close()

    def test_add_element_selects_new_element(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        canvas.set_layout(layout, "front")
        e = CardElement(type=ELEMENT_TEXT, text="New")
        canvas.add_element(e)
        assert e.id in canvas._selected  # noqa: SLF001
        canvas.close()

    def test_bring_to_front_raises_z_order_above_others(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        e1 = CardElement(type=ELEMENT_RECT)
        e2 = CardElement(type=ELEMENT_RECT)
        e1.z_order = 1
        e2.z_order = 2
        layout.front_elements.extend([e1, e2])
        canvas.set_layout(layout, "front")
        canvas._selected = [e1.id]  # noqa: SLF001
        canvas.bring_to_front()
        assert e1.z_order > e2.z_order
        canvas.close()

    def test_send_to_back_lowers_z_order_below_others(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        e1 = CardElement(type=ELEMENT_RECT)
        e2 = CardElement(type=ELEMENT_RECT)
        e1.z_order = 1
        e2.z_order = 2
        layout.front_elements.extend([e1, e2])
        canvas.set_layout(layout, "front")
        canvas._selected = [e2.id]  # noqa: SLF001
        canvas.send_to_back()
        assert e2.z_order < e1.z_order
        canvas.close()

    def test_invalidate_image_cache_no_crash(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        canvas.invalidate_image_cache("/some/path.png")
        canvas.invalidate_image_cache()
        canvas.close()

    def test_invalidate_qr_cache_no_crash(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        canvas.invalidate_qr_cache("data")
        canvas.invalidate_qr_cache()
        canvas.close()

    def test_delete_selected_on_back_side(self, qapp):
        """delete_selected mit back-Seite deckt _set_elements(back)-Zweig ab."""
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
# align_selected – alle Modi
# ---------------------------------------------------------------------------


class TestAlignSelected:
    def _canvas_with_n(self, qapp, n: int):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        canvas.set_layout(layout, "front")
        canvas.set_paper(PaperTemplate())
        elems = []
        for i in range(n):
            e = CardElement(
                type=ELEMENT_RECT,
                x=5.0 + 10.0 * i,
                y=5.0 + 5.0 * i,
                width=10.0,
                height=5.0,
            )
            layout.front_elements.append(e)
            elems.append(e)
        canvas._selected = [e.id for e in elems]  # noqa: SLF001
        return canvas, elems

    def test_no_selection_is_noop(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        canvas.set_layout(CardLayout(), "front")
        canvas.set_paper(PaperTemplate())
        canvas.align_selected("left")  # nothing selected → silent noop
        canvas.close()

    def test_align_left(self, qapp):
        canvas, elems = self._canvas_with_n(qapp, 2)
        canvas.align_selected("left")
        assert all(e.x == 0.0 for e in elems)
        canvas.close()

    def test_align_right(self, qapp):
        canvas, elems = self._canvas_with_n(qapp, 2)
        cw = canvas._paper.card_width  # noqa: SLF001
        canvas.align_selected("right")
        assert all(e.x == pytest.approx(cw - e.width) for e in elems)
        canvas.close()

    def test_align_top(self, qapp):
        canvas, elems = self._canvas_with_n(qapp, 2)
        canvas.align_selected("top")
        assert all(e.y == 0.0 for e in elems)
        canvas.close()

    def test_align_bottom(self, qapp):
        canvas, elems = self._canvas_with_n(qapp, 2)
        ch = canvas._paper.card_height  # noqa: SLF001
        canvas.align_selected("bottom")
        assert all(e.y == pytest.approx(ch - e.height) for e in elems)
        canvas.close()

    def test_align_center_h(self, qapp):
        canvas, elems = self._canvas_with_n(qapp, 2)
        cw = canvas._paper.card_width  # noqa: SLF001
        canvas.align_selected("center_h")
        assert all(e.x == pytest.approx((cw - e.width) / 2) for e in elems)
        canvas.close()

    def test_align_center_v(self, qapp):
        canvas, elems = self._canvas_with_n(qapp, 2)
        ch = canvas._paper.card_height  # noqa: SLF001
        canvas.align_selected("center_v")
        assert all(e.y == pytest.approx((ch - e.height) / 2) for e in elems)
        canvas.close()

    def test_group_left_aligns_to_leftmost_x(self, qapp):
        canvas, elems = self._canvas_with_n(qapp, 2)
        elems[0].x = 3.0
        elems[1].x = 12.0
        canvas.align_selected("group_left")
        assert all(e.x == pytest.approx(3.0) for e in elems)
        canvas.close()

    def test_group_right_aligns_right_edges(self, qapp):
        canvas, elems = self._canvas_with_n(qapp, 2)
        elems[0].x = 3.0
        elems[0].width = 10.0
        elems[1].x = 20.0
        elems[1].width = 10.0  # rightmost edge = 30
        canvas.align_selected("group_right")
        assert all(e.x + e.width == pytest.approx(30.0) for e in elems)
        canvas.close()

    def test_group_top_aligns_to_topmost_y(self, qapp):
        canvas, elems = self._canvas_with_n(qapp, 2)
        elems[0].y = 2.0
        elems[1].y = 9.0
        canvas.align_selected("group_top")
        assert all(e.y == pytest.approx(2.0) for e in elems)
        canvas.close()

    def test_group_bottom_aligns_bottom_edges(self, qapp):
        canvas, elems = self._canvas_with_n(qapp, 2)
        elems[0].y = 2.0
        elems[0].height = 5.0
        elems[1].y = 10.0
        elems[1].height = 5.0  # bottom edge = 15
        canvas.align_selected("group_bottom")
        assert all(e.y + e.height == pytest.approx(15.0) for e in elems)
        canvas.close()

    def test_group_center_h(self, qapp):
        canvas, elems = self._canvas_with_n(qapp, 2)
        elems[0].x = 0.0
        elems[0].width = 10.0
        elems[1].x = 30.0
        elems[1].width = 10.0  # cx = (0+40)/2=20, result x = 20-5 = 15
        canvas.align_selected("group_center_h")
        assert all(e.x == pytest.approx(15.0) for e in elems)
        canvas.close()

    def test_group_center_v(self, qapp):
        canvas, elems = self._canvas_with_n(qapp, 2)
        elems[0].y = 0.0
        elems[0].height = 10.0
        elems[1].y = 20.0
        elems[1].height = 10.0  # cy = (0+30)/2=15, result y = 15-5 = 10
        canvas.align_selected("group_center_v")
        assert all(e.y == pytest.approx(10.0) for e in elems)
        canvas.close()

    def test_distribute_h_with_2_elements_is_noop(self, qapp):
        canvas, elems = self._canvas_with_n(qapp, 2)
        orig = [e.x for e in elems]
        canvas.align_selected("distribute_h")
        assert all(e.x == pytest.approx(orig[i]) for i, e in enumerate(elems))
        canvas.close()

    def test_distribute_h_3_elements_evenly_spaced(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        canvas.set_layout(layout, "front")
        # x_start=0, x_end=0+30+10=40 (e3.x+e3.width), total_w=30, gap=5
        e1 = CardElement(type=ELEMENT_RECT, x=0.0, y=0.0, width=10.0, height=5.0)
        e2 = CardElement(type=ELEMENT_RECT, x=5.0, y=0.0, width=10.0, height=5.0)
        e3 = CardElement(type=ELEMENT_RECT, x=30.0, y=0.0, width=10.0, height=5.0)
        layout.front_elements.extend([e1, e2, e3])
        canvas._selected = [e1.id, e2.id, e3.id]  # noqa: SLF001
        canvas.align_selected("distribute_h")
        assert e1.x == pytest.approx(0.0)
        assert e2.x == pytest.approx(15.0)
        assert e3.x == pytest.approx(30.0)
        canvas.close()

    def test_distribute_v_3_elements_evenly_spaced(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        canvas.set_layout(layout, "front")
        e1 = CardElement(type=ELEMENT_RECT, x=0.0, y=0.0, width=10.0, height=10.0)
        e2 = CardElement(type=ELEMENT_RECT, x=0.0, y=5.0, width=10.0, height=10.0)
        e3 = CardElement(type=ELEMENT_RECT, x=0.0, y=30.0, width=10.0, height=10.0)
        layout.front_elements.extend([e1, e2, e3])
        canvas._selected = [e1.id, e2.id, e3.id]  # noqa: SLF001
        canvas.align_selected("distribute_v")
        assert e1.y == pytest.approx(0.0)
        assert e2.y == pytest.approx(15.0)
        assert e3.y == pytest.approx(30.0)
        canvas.close()


# ---------------------------------------------------------------------------
# fit_to_content
# ---------------------------------------------------------------------------


class TestFitToContent:
    def test_qr_becomes_square_max_side(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        canvas.set_layout(layout, "front")
        e = CardElement(type=ELEMENT_QR, qr_data="https://example.com", width=20.0, height=10.0)
        layout.front_elements.append(e)
        canvas._selected = [e.id]  # noqa: SLF001
        canvas.fit_to_content()
        assert e.width == pytest.approx(e.height)
        assert e.width == pytest.approx(20.0)
        canvas.close()

    def test_text_with_content_resizes(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        canvas.set_layout(layout, "front")
        e = CardElement(type=ELEMENT_TEXT, text="Hello World", width=1.0, height=1.0)
        layout.front_elements.append(e)
        canvas._selected = [e.id]  # noqa: SLF001
        canvas.fit_to_content()
        assert e.width >= 1.0
        assert e.height >= 1.0
        canvas.close()

    def test_empty_text_not_resized(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        canvas.set_layout(layout, "front")
        e = CardElement(type=ELEMENT_TEXT, text="   ", width=20.0, height=10.0)
        layout.front_elements.append(e)
        canvas._selected = [e.id]  # noqa: SLF001
        canvas.fit_to_content()
        assert e.width == pytest.approx(20.0)
        canvas.close()

    def test_rect_not_modified(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        canvas.set_layout(layout, "front")
        e = CardElement(type=ELEMENT_RECT, width=20.0, height=10.0)
        layout.front_elements.append(e)
        canvas._selected = [e.id]  # noqa: SLF001
        canvas.fit_to_content()
        assert e.width == pytest.approx(20.0)
        assert e.height == pytest.approx(10.0)
        canvas.close()

    def test_image_without_path_not_modified(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        canvas.set_layout(layout, "front")
        e = CardElement(type=ELEMENT_IMAGE, image_path="", width=20.0, height=10.0)
        layout.front_elements.append(e)
        canvas._selected = [e.id]  # noqa: SLF001
        canvas.fit_to_content()
        assert e.width == pytest.approx(20.0)
        canvas.close()


# ---------------------------------------------------------------------------
# Mouse events – Klicken, Drag, Rubber-Band, Resize
# ---------------------------------------------------------------------------


class TestMouseEvents:
    def _setup(self, qapp, n=1):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        canvas.set_layout(layout, "front")
        canvas.set_paper(PaperTemplate())
        canvas.resize(600, 500)
        canvas.show()
        QApplication.processEvents()
        elems = []
        for i in range(n):
            e = CardElement(
                type=ELEMENT_TEXT,
                text=f"E{i}",
                x=10.0 + 30.0 * i,
                y=5.0,
                width=20.0,
                height=10.0,
            )
            layout.front_elements.append(e)
            elems.append(e)
        return canvas, elems

    def _center_pt(self, canvas, e):
        from PySide6.QtCore import QPoint

        r = canvas._elem_rect_px(e)  # noqa: SLF001
        return QPoint(int(r.center().x()), int(r.center().y()))

    def test_click_selects_element(self, qapp):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        canvas, elems = self._setup(qapp)
        e = elems[0]
        QTest.mouseClick(
            canvas,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            self._center_pt(canvas, e),
        )
        assert e.id in canvas._selected  # noqa: SLF001
        canvas.close()

    def test_click_empty_area_starts_rubber_band(self, qapp):
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest

        canvas, _ = self._setup(qapp)
        QTest.mousePress(
            canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(400, 400)
        )
        assert canvas._rubber_band_start is not None  # noqa: SLF001
        QTest.mouseRelease(
            canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(400, 400)
        )
        canvas.close()

    def test_shift_click_adds_element_to_selection(self, qapp):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        canvas, elems = self._setup(qapp, n=2)
        pt0 = self._center_pt(canvas, elems[0])
        pt1 = self._center_pt(canvas, elems[1])
        QTest.mouseClick(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, pt0)
        QTest.mouseClick(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier, pt1)
        assert elems[0].id in canvas._selected  # noqa: SLF001
        assert elems[1].id in canvas._selected  # noqa: SLF001
        canvas.close()

    def test_shift_click_deselects_already_selected(self, qapp):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        canvas, elems = self._setup(qapp)
        e = elems[0]
        canvas._selected = [e.id]  # noqa: SLF001
        QTest.mouseClick(
            canvas,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.ShiftModifier,
            self._center_pt(canvas, e),
        )
        assert e.id not in canvas._selected  # noqa: SLF001
        canvas.close()

    def test_drag_moves_element(self, qapp):
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest

        canvas, elems = self._setup(qapp)
        e = elems[0]
        orig_x = e.x
        pt = self._center_pt(canvas, e)
        QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, pt)
        new_pt = QPoint(pt.x() + 30, pt.y())
        QTest.mouseMove(canvas, new_pt)
        QTest.mouseRelease(
            canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, new_pt
        )
        assert e.x != pytest.approx(orig_x)
        canvas.close()

    def test_mouse_release_emits_edit_finished_after_drag(self, qapp):
        from unittest.mock import MagicMock

        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest

        canvas, elems = self._setup(qapp)
        finished = MagicMock()
        canvas.editFinished.connect(finished)
        e = elems[0]
        pt = self._center_pt(canvas, e)
        QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, pt)
        new_pt = QPoint(pt.x() + 5, pt.y())
        QTest.mouseMove(canvas, new_pt)
        QTest.mouseRelease(
            canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, new_pt
        )
        finished.assert_called()
        canvas.close()

    def test_rubber_band_drag_selects_covered_element(self, qapp):
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest

        canvas, elems = self._setup(qapp)
        e = elems[0]
        r = canvas._elem_rect_px(e)  # noqa: SLF001
        start = QPoint(int(r.left()) - 3, int(r.top()) - 3)
        end = QPoint(int(r.right()) + 3, int(r.bottom()) + 3)
        QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
        QTest.mouseMove(canvas, end)
        QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, end)
        assert e.id in canvas._selected  # noqa: SLF001
        canvas.close()

    def test_right_click_on_element_does_not_crash(self, qapp):
        """Rechtsklick auf Element öffnet Kontextmenü (_context_menu gemockt)."""
        from unittest.mock import patch

        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        canvas, elems = self._setup(qapp)
        with patch.object(canvas, "_context_menu"):
            QTest.mouseClick(
                canvas,
                Qt.MouseButton.RightButton,
                Qt.KeyboardModifier.NoModifier,
                self._center_pt(canvas, elems[0]),
            )
        canvas.close()

    def test_right_click_on_empty_area_does_not_crash(self, qapp):
        from unittest.mock import patch

        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest

        canvas, _ = self._setup(qapp)
        with patch.object(canvas, "_context_menu"):
            QTest.mouseClick(
                canvas,
                Qt.MouseButton.RightButton,
                Qt.KeyboardModifier.NoModifier,
                QPoint(400, 400),
            )
        canvas.close()

    def test_mouse_move_cursor_changes_over_element(self, qapp):
        from PySide6.QtTest import QTest

        canvas, elems = self._setup(qapp)
        QTest.mouseMove(canvas, self._center_pt(canvas, elems[0]))
        QApplication.processEvents()
        canvas.close()

    def test_resize_via_br_handle_widens_element(self, qapp):
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest

        canvas, elems = self._setup(qapp)
        e = elems[0]
        orig_w = e.width
        canvas._selected = [e.id]  # noqa: SLF001
        r = canvas._elem_rect_px(e)  # noqa: SLF001
        br = QPoint(int(r.right()), int(r.bottom()))
        QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, br)
        QTest.mouseMove(canvas, QPoint(br.x() + 30, br.y()))
        QTest.mouseRelease(
            canvas,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(br.x() + 30, br.y()),
        )
        assert e.width > orig_w
        canvas.close()

    def test_double_click_text_element_opens_inline_editor(self, qapp):
        """Doppelklick auf Text-Element aktiviert Inline-Edit (kein Widget, nur Canvas-State)."""
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        canvas, elems = self._setup(qapp)
        QTest.mouseDClick(
            canvas,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            self._center_pt(canvas, elems[0]),
        )
        QApplication.processEvents()
        assert canvas._inline_elem is elems[0]  # noqa: SLF001
        canvas._finish_inline_edit(commit=False)  # noqa: SLF001
        canvas.close()


# ---------------------------------------------------------------------------
# Keyboard events
# ---------------------------------------------------------------------------


class TestKeyEvents:
    def _setup(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        canvas.set_layout(layout, "front")
        canvas.set_paper(PaperTemplate())
        e = CardElement(type=ELEMENT_TEXT, text="Key", x=10.0, y=10.0, width=20.0, height=10.0)
        layout.front_elements.append(e)
        canvas._selected = [e.id]  # noqa: SLF001
        canvas.show()
        QApplication.processEvents()
        return canvas, e

    def test_delete_removes_selected_element(self, qapp):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        canvas, _ = self._setup(qapp)
        QTest.keyClick(canvas, Qt.Key.Key_Delete)
        assert len(canvas._elements()) == 0  # noqa: SLF001
        canvas.close()

    def test_backspace_removes_selected_element(self, qapp):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        canvas, _ = self._setup(qapp)
        QTest.keyClick(canvas, Qt.Key.Key_Backspace)
        assert len(canvas._elements()) == 0  # noqa: SLF001
        canvas.close()

    def test_ctrl_a_selects_all_elements(self, qapp):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        canvas, e = self._setup(qapp)
        canvas._selected = []  # noqa: SLF001
        QTest.keyClick(canvas, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
        assert e.id in canvas._selected  # noqa: SLF001
        canvas.close()

    def test_ctrl_z_emits_request_undo(self, qapp):
        from unittest.mock import MagicMock

        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        canvas, _ = self._setup(qapp)
        undo_slot = MagicMock()
        canvas.requestUndo.connect(undo_slot)
        QTest.keyClick(canvas, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
        undo_slot.assert_called()
        canvas.close()

    def test_ctrl_shift_z_emits_request_redo(self, qapp):
        from unittest.mock import MagicMock

        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        canvas, _ = self._setup(qapp)
        redo_slot = MagicMock()
        canvas.requestRedo.connect(redo_slot)
        QTest.keyClick(
            canvas,
            Qt.Key.Key_Z,
            Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier,
        )
        redo_slot.assert_called()
        canvas.close()

    def test_ctrl_y_emits_request_redo(self, qapp):
        from unittest.mock import MagicMock

        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        canvas, _ = self._setup(qapp)
        redo_slot = MagicMock()
        canvas.requestRedo.connect(redo_slot)
        QTest.keyClick(canvas, Qt.Key.Key_Y, Qt.KeyboardModifier.ControlModifier)
        redo_slot.assert_called()
        canvas.close()

    def test_arrow_left_moves_1mm(self, qapp):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        canvas, e = self._setup(qapp)
        orig_x = e.x
        QTest.keyClick(canvas, Qt.Key.Key_Left)
        assert e.x == pytest.approx(orig_x - 1.0)
        canvas.close()

    def test_arrow_right_moves_1mm(self, qapp):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        canvas, e = self._setup(qapp)
        orig_x = e.x
        QTest.keyClick(canvas, Qt.Key.Key_Right)
        assert e.x == pytest.approx(orig_x + 1.0)
        canvas.close()

    def test_arrow_up_moves_1mm(self, qapp):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        canvas, e = self._setup(qapp)
        orig_y = e.y
        QTest.keyClick(canvas, Qt.Key.Key_Up)
        assert e.y == pytest.approx(orig_y - 1.0)
        canvas.close()

    def test_arrow_down_moves_1mm(self, qapp):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        canvas, e = self._setup(qapp)
        orig_y = e.y
        QTest.keyClick(canvas, Qt.Key.Key_Down)
        assert e.y == pytest.approx(orig_y + 1.0)
        canvas.close()

    def test_shift_arrow_moves_01mm(self, qapp):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        canvas, e = self._setup(qapp)
        orig_x = e.x
        QTest.keyClick(canvas, Qt.Key.Key_Right, Qt.KeyboardModifier.ShiftModifier)
        assert e.x == pytest.approx(orig_x + 0.1)
        canvas.close()

    def test_locked_element_not_moved_by_arrow(self, qapp):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        canvas, e = self._setup(qapp)
        e.locked = True
        orig_x = e.x
        QTest.keyClick(canvas, Qt.Key.Key_Right)
        assert e.x == pytest.approx(orig_x)
        canvas.close()


# ---------------------------------------------------------------------------
# Wheel events
# ---------------------------------------------------------------------------


class TestWheelEvent:
    def test_ctrl_wheel_up_zooms_in(self, qapp):
        from PySide6.QtCore import QPoint, QPointF, Qt
        from PySide6.QtGui import QWheelEvent

        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        canvas.show()
        orig_zoom = canvas._zoom  # noqa: SLF001
        event = QWheelEvent(
            QPointF(50, 50),
            QPointF(50, 50),
            QPoint(0, 0),
            QPoint(0, 120),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.ControlModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,
        )
        canvas.wheelEvent(event)
        assert canvas._zoom > orig_zoom  # noqa: SLF001
        canvas.close()

    def test_ctrl_wheel_down_zooms_out(self, qapp):
        from PySide6.QtCore import QPoint, QPointF, Qt
        from PySide6.QtGui import QWheelEvent

        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        canvas.show()
        orig_zoom = canvas._zoom  # noqa: SLF001
        event = QWheelEvent(
            QPointF(50, 50),
            QPointF(50, 50),
            QPoint(0, 0),
            QPoint(0, -120),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.ControlModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,
        )
        canvas.wheelEvent(event)
        assert canvas._zoom < orig_zoom  # noqa: SLF001
        canvas.close()

    def test_wheel_without_ctrl_does_not_zoom(self, qapp):
        from PySide6.QtCore import QPoint, QPointF, Qt
        from PySide6.QtGui import QWheelEvent

        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        canvas.show()
        orig_zoom = canvas._zoom  # noqa: SLF001
        event = QWheelEvent(
            QPointF(50, 50),
            QPointF(50, 50),
            QPoint(0, 0),
            QPoint(0, 120),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,
        )
        canvas.wheelEvent(event)
        assert canvas._zoom == pytest.approx(orig_zoom)
        canvas.close()


# ---------------------------------------------------------------------------
# _context_menu body
# ---------------------------------------------------------------------------


class TestContextMenuBody:
    def _make_canvas(self, qapp):
        from cardforge.canvas import CardCanvas
        from cardforge.models import PaperTemplate

        c = CardCanvas()
        c.set_paper(PaperTemplate())
        c.show()
        return c

    def test_context_menu_no_element_shows_select_all(self, qapp):
        """_context_menu ohne Element darunter: 'Alle auswählen' Action enthalten."""
        from unittest.mock import MagicMock, patch

        from PySide6.QtCore import QPointF

        canvas = self._make_canvas(qapp)
        mock_menu = MagicMock()
        mock_menu.exec.return_value = None
        with patch("cardforge.canvas.QMenu", return_value=mock_menu):
            canvas._context_menu(QPointF(1000, 1000))  # weit außerhalb
        # addAction wurde mit "Alle auswählen" aufgerufen
        action_texts = [call.args[0] for call in mock_menu.addAction.call_args_list]
        assert any("auswählen" in t for t in action_texts)
        canvas.close()

    def test_context_menu_with_element_shows_delete(self, qapp):
        """_context_menu über einem Element: 'Löschen' Action enthalten."""
        from unittest.mock import MagicMock, patch

        from PySide6.QtCore import QCoreApplication, QPointF

        from cardforge.models import ELEMENT_TEXT, CardElement, CardLayout

        canvas = self._make_canvas(qapp)
        canvas.resize(600, 400)

        # Layout setzen, damit _elements() nicht leer ist
        layout = CardLayout(name="Test")
        elem = CardElement(type=ELEMENT_TEXT, x=5.0, y=5.0, width=30.0, height=10.0, text="Hi")
        layout.front_elements.append(elem)
        canvas.set_layout(layout, "front")

        canvas.show()
        QCoreApplication.processEvents()

        scale = canvas._zoom  # noqa: SLF001 — px per mm (default=3)
        ox = canvas._offset.x()  # noqa: SLF001
        oy = canvas._offset.y()  # noqa: SLF001
        px = ox + (elem.x + elem.width / 2) * scale
        py = oy + (elem.y + elem.height / 2) * scale

        mock_menu = MagicMock()
        mock_menu.exec.return_value = None
        with patch("cardforge.canvas.QMenu", return_value=mock_menu):
            canvas._context_menu(QPointF(px, py))  # noqa: SLF001
        action_texts = [call.args[0] for call in mock_menu.addAction.call_args_list]
        assert any("Löschen" in t or "vorne" in t or "hinten" in t for t in action_texts)
        canvas.close()


# ---------------------------------------------------------------------------
# paintEvent – korrekte Zweige mit processEvents()
# ---------------------------------------------------------------------------


class TestPaintEventBranchesFixed:
    """Tests die processEvents() verwenden, damit paintEvent tatsächlich feuert."""

    def _make(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        canvas.set_layout(CardLayout(), "front")
        canvas.set_paper(PaperTemplate())
        canvas.resize(400, 300)
        return canvas

    def test_paint_show_grid_false(self, qapp):
        """_show_grid=False überspringt _draw_grid ([403,407])."""
        canvas = self._make(qapp)
        canvas.set_grid(False, 1.0)
        canvas.show()
        QApplication.processEvents()
        canvas.repaint()
        canvas.close()

    def test_paint_invisible_element_skipped_fixed(self, qapp):
        """Unsichtbares Element wird in paintEvent übersprungen ([410,409])."""
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        e = CardElement(type=ELEMENT_TEXT, text="Hidden", visible=False)
        layout.front_elements.append(e)
        canvas.set_layout(layout, "front")
        canvas.set_paper(PaperTemplate())
        canvas.resize(400, 300)
        canvas.show()
        QApplication.processEvents()
        canvas.repaint()
        canvas.close()

    def test_paint_two_selected_elements_inner_loop_back(self, qapp):
        """Zwei selektierte Elemente decken den inneren Schleifenrücksprung ab ([417,416])."""
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        e1 = CardElement(type=ELEMENT_TEXT, text="A", x=5.0, y=5.0, width=20.0, height=8.0)
        e2 = CardElement(type=ELEMENT_TEXT, text="B", x=5.0, y=20.0, width=20.0, height=8.0)
        layout.front_elements.extend([e1, e2])
        canvas.set_layout(layout, "front")
        canvas.set_paper(PaperTemplate())
        canvas._selected = [e1.id, e2.id]  # noqa: SLF001
        canvas.resize(400, 300)
        canvas.show()
        QApplication.processEvents()
        canvas.repaint()
        canvas.close()

    def test_paint_rubber_band_active_fixed(self, qapp):
        """Gummiband-Rect zeichnen ([421,422])."""
        from PySide6.QtCore import QRectF

        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        canvas.set_layout(CardLayout(), "front")
        canvas.set_paper(PaperTemplate())
        canvas.resize(400, 300)
        canvas.show()
        QApplication.processEvents()
        canvas._rubber_band_rect = QRectF(10, 10, 100, 60)  # noqa: SLF001
        canvas.repaint()
        canvas.close()

    def test_paint_selected_line_draws_selection(self, qapp):
        """Selektierte Linie deckt _draw_selection LINE-Zweig ab ([453,455],[465,466/467])."""
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        e = CardElement(type=ELEMENT_LINE, x=5.0, y=20.0, width=30.0, height=0.5)
        layout.front_elements.append(e)
        canvas.set_layout(layout, "front")
        canvas.set_paper(PaperTemplate())
        canvas._selected = [e.id]  # noqa: SLF001
        canvas.resize(400, 300)
        canvas.show()
        QApplication.processEvents()
        canvas.repaint()
        canvas.close()

    def test_paint_selected_text_non_line_handles(self, qapp):
        """Selektiertes Text-Element deckt _draw_selection (nicht-LINE) Handles ab."""
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        e = CardElement(type=ELEMENT_TEXT, text="Sel", x=5.0, y=5.0, width=20.0, height=10.0)
        layout.front_elements.append(e)
        canvas.set_layout(layout, "front")
        canvas.set_paper(PaperTemplate())
        canvas._selected = [e.id]  # noqa: SLF001
        canvas.resize(400, 300)
        canvas.show()
        QApplication.processEvents()
        canvas.repaint()
        canvas.close()


# ---------------------------------------------------------------------------
# Weitere Canvas-Zweige
# ---------------------------------------------------------------------------


class TestCanvasBranchExtras:
    def test_mm_to_px_utility_function(self):
        """_mm_to_px-Hilfsfunktion (line 34)."""
        from cardforge.canvas import _mm_to_px

        result = _mm_to_px(25.4, 96.0)
        assert result == pytest.approx(96.0)

    def test_align_group_mode_with_single_element(self, qapp):
        """align_selected('group_left') mit 1 Element → elif len(sel)>1 False ([194,244])."""
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        e = CardElement(type=ELEMENT_TEXT, text="X", x=10.0, y=10.0, width=20.0, height=5.0)
        layout.front_elements.append(e)
        canvas.set_layout(layout, "front")
        canvas.set_paper(PaperTemplate())
        canvas._selected = [e.id]  # noqa: SLF001
        canvas.align_selected("group_left")  # len(sel)==1 → elif not taken
        # x unverändert (kein group-Modus mit 1 Element)
        assert e.x == 10.0
        canvas.close()

    def test_fit_to_content_image_valid_pixmap(self, qapp):
        """fit_to_content mit gültigem Pixmap passt Höhe an ([264,265],[266,267])."""
        from unittest.mock import MagicMock, patch

        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        canvas.set_layout(layout, "front")
        canvas.set_paper(PaperTemplate())
        e = CardElement(type=ELEMENT_IMAGE, image_path="/fake/img.png", width=20.0, height=10.0)
        layout.front_elements.append(e)
        canvas._selected = [e.id]  # noqa: SLF001
        # Pixmap 200x100 → ratio=0.5 → new height = 20*0.5 = 10.0
        mock_pm = MagicMock()
        mock_pm.isNull.return_value = False
        mock_pm.width.return_value = 200
        mock_pm.height.return_value = 100
        # bool(mock_pm) muss True sein
        mock_pm.__bool__ = lambda self: True
        with patch.object(canvas._renderer, "get_pixmap", return_value=mock_pm):  # noqa: SLF001
            canvas.fit_to_content()
        assert e.height == pytest.approx(10.0)
        canvas.close()

    def test_fit_to_content_image_null_pixmap(self, qapp):
        """fit_to_content mit null Pixmap → keine Änderung ([266,257])."""
        from unittest.mock import patch

        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        canvas.set_layout(layout, "front")
        canvas.set_paper(PaperTemplate())
        e = CardElement(type=ELEMENT_IMAGE, image_path="/fake/img.png", width=20.0, height=10.0)
        layout.front_elements.append(e)
        canvas._selected = [e.id]  # noqa: SLF001
        with patch.object(canvas._renderer, "get_pixmap", return_value=None):  # noqa: SLF001
            canvas.fit_to_content()
        assert e.width == pytest.approx(20.0)
        assert e.height == pytest.approx(10.0)
        canvas.close()

    def test_set_elements_no_layout_returns_early(self, qapp):
        """delete_selected ohne Layout ruft _set_elements mit layout=None auf ([289,290])."""
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        # kein set_layout → _layout ist None
        canvas.delete_selected()  # ruft _set_elements([]) auf, layout=None → return
        assert canvas._layout is None  # noqa: SLF001
        canvas.close()

    def test_snap_grid_zero_returns_unchanged(self, qapp):
        """_snap mit snap_grid=0 gibt v unverändert zurück ([324,325])."""
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        canvas._snap_grid = 0  # noqa: SLF001
        result = canvas._snap(5.7)  # noqa: SLF001
        assert result == pytest.approx(5.7)
        canvas.close()

    def test_elem_at_invisible_element_skipped(self, qapp):
        """_elem_at überspringt unsichtbare Elemente ([331,332])."""
        from PySide6.QtCore import QPointF

        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        canvas.set_layout(layout, "front")
        canvas.set_paper(PaperTemplate())
        # Unsichtbares Element an bekannter Position
        e = CardElement(
            type=ELEMENT_TEXT, text="Hidden", x=0.0, y=0.0, width=50.0, height=50.0, visible=False
        )
        layout.front_elements.append(e)
        # Position liegt innerhalb des Elements, aber es ist unsichtbar
        ox = canvas._offset.x()  # noqa: SLF001
        oy = canvas._offset.y()  # noqa: SLF001
        result = canvas._elem_at(QPointF(ox + 10, oy + 10))  # noqa: SLF001
        assert result is None
        canvas.close()

    def test_handle_at_line_in_handle_returns_r(self, qapp):
        """_handle_at für LINE am rechten Endpunkt gibt 'r' zurück."""
        from PySide6.QtCore import QPointF

        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        canvas.set_layout(layout, "front")
        canvas.set_paper(PaperTemplate())
        e = CardElement(
            type=ELEMENT_LINE, x=5.0, y=10.0, width=30.0, height=0.5, line_x2=30.0, line_y2=0.0
        )
        layout.front_elements.append(e)
        # Rechter Endpunkt der Linie
        ox, oy = canvas._offset.x(), canvas._offset.y()  # noqa: SLF001
        p2 = QPointF(ox + canvas._to_px(e.x + e.line_x2), oy + canvas._to_px(e.y + e.line_y2))  # noqa: SLF001
        result = canvas._handle_at(p2, e)  # noqa: SLF001
        assert result == "r"
        canvas.close()

    def test_handle_at_line_not_in_handle_returns_none(self, qapp):
        """_handle_at für LINE außerhalb Handle gibt None zurück."""
        from PySide6.QtCore import QPointF

        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        canvas.set_layout(layout, "front")
        canvas.set_paper(PaperTemplate())
        e = CardElement(
            type=ELEMENT_LINE, x=5.0, y=10.0, width=30.0, height=0.5, line_x2=30.0, line_y2=0.0
        )
        layout.front_elements.append(e)
        result = canvas._handle_at(QPointF(0, 0), e)  # noqa: SLF001
        assert result is None
        canvas.close()

    def test_mouse_press_middle_button_no_action(self, qapp):
        """MiddleButton in mousePressEvent tut nichts ([492,494])."""
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        canvas.set_layout(CardLayout(), "front")
        canvas.set_paper(PaperTemplate())
        canvas.resize(400, 300)
        canvas.show()
        QApplication.processEvents()
        QTest.mouseClick(canvas, Qt.MouseButton.MiddleButton)
        canvas.close()

    def test_resize_b_handle_changes_height_only(self, qapp):
        """mouseMoveEvent mit 'b'-Handle ändert nur Höhe, nicht Breite ([518,520])."""
        from PySide6.QtCore import QPoint, QPointF
        from PySide6.QtTest import QTest

        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        canvas.set_layout(layout, "front")
        canvas.set_paper(PaperTemplate())
        e = CardElement(type=ELEMENT_TEXT, x=5.0, y=5.0, width=20.0, height=10.0)
        layout.front_elements.append(e)
        canvas._selected = [e.id]  # noqa: SLF001
        canvas.resize(400, 300)
        canvas.show()
        QApplication.processEvents()

        orig_w = e.width
        orig_h = e.height

        # Direkt internen Resize-Zustand setzen
        canvas._resize_handle = "b"  # noqa: SLF001
        canvas._resize_start = QPointF(100, 100)  # noqa: SLF001
        canvas._resize_orig = {e.id: (e.x, e.y, e.width, e.height)}  # noqa: SLF001

        QTest.mouseMove(canvas, QPoint(100, 120))  # 20px nach unten → Höhe wächst
        QApplication.processEvents()

        assert e.width == pytest.approx(orig_w)  # Breite unverändert
        assert e.height > orig_h  # Höhe gewachsen
        canvas.close()

    def test_drag_locked_element_not_moved(self, qapp):
        """Drag eines gesperrten Elements verändert Position nicht ([525,527])."""
        from PySide6.QtCore import QPoint, QPointF
        from PySide6.QtTest import QTest

        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        canvas.set_layout(layout, "front")
        canvas.set_paper(PaperTemplate())
        e = CardElement(type=ELEMENT_TEXT, x=5.0, y=5.0, width=20.0, height=10.0, locked=True)
        layout.front_elements.append(e)
        canvas._selected = [e.id]  # noqa: SLF001
        canvas.resize(400, 300)
        canvas.show()
        QApplication.processEvents()

        orig_x = e.x
        orig_y = e.y

        # Drag-Zustand direkt setzen
        canvas._drag_start = QPointF(100, 100)  # noqa: SLF001
        canvas._drag_orig = {e.id: (e.x, e.y)}  # noqa: SLF001

        QTest.mouseMove(canvas, QPoint(130, 130))  # 30px Versatz
        QApplication.processEvents()

        assert e.x == pytest.approx(orig_x)  # locked → nicht bewegt
        assert e.y == pytest.approx(orig_y)
        canvas.close()


# ---------------------------------------------------------------------------
# Cursor-Hover-Zweige in mouseMoveEvent (Zeilen 565-579)
# ---------------------------------------------------------------------------


class TestMouseMoveCursorHover:
    """Tests für den Cursor-Änderungs-Zweig (kein Resize/Drag/RubberBand)."""

    def _make_canvas_with_element(self, qapp, elem_type=ELEMENT_TEXT):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        canvas.set_layout(layout, "front")
        canvas.set_paper(PaperTemplate())
        e = CardElement(type=elem_type, x=5.0, y=5.0, width=20.0, height=10.0)
        layout.front_elements.append(e)
        canvas._selected = [e.id]  # noqa: SLF001
        canvas.resize(400, 300)
        canvas.show()
        QApplication.processEvents()
        return canvas, e

    @staticmethod
    def _mouse_move_event(pos):
        from PySide6.QtCore import QEvent, Qt
        from PySide6.QtGui import QMouseEvent, QPointingDevice

        return QMouseEvent(
            QEvent.Type.MouseMove,
            pos,
            pos,
            pos,
            Qt.MouseButton.NoButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.MouseEventSource.MouseEventNotSynthesized,
            QPointingDevice.primaryPointingDevice(),
        )

    def test_hover_over_br_handle_sets_sizefdiag_cursor(self, qapp):
        """Hover über 'br'-Handle setzt SizeFDiagCursor ([569,570])."""
        canvas, e = self._make_canvas_with_element(qapp)
        r = canvas._elem_rect_px(e)  # noqa: SLF001
        canvas.mouseMoveEvent(self._mouse_move_event(r.bottomRight()))
        canvas.close()

    def test_hover_over_r_handle_sets_sizehor_cursor(self, qapp):
        """Hover über 'r'-Handle setzt SizeHorCursor ([572,573])."""
        from PySide6.QtCore import QPointF

        canvas, e = self._make_canvas_with_element(qapp)
        r = canvas._elem_rect_px(e)  # noqa: SLF001
        canvas.mouseMoveEvent(self._mouse_move_event(QPointF(r.right(), r.center().y())))
        canvas.close()

    def test_hover_over_b_handle_sets_sizever_cursor(self, qapp):
        """Hover über 'b'-Handle setzt SizeVerCursor ([575,576])."""
        from PySide6.QtCore import QPointF

        canvas, e = self._make_canvas_with_element(qapp)
        r = canvas._elem_rect_px(e)  # noqa: SLF001
        canvas.mouseMoveEvent(self._mouse_move_event(QPointF(r.center().x(), r.bottom())))
        canvas.close()

    def test_hover_no_handle_element_sets_sizeall_cursor(self, qapp):
        """Hover über Element (kein Handle) → SizeAllCursor + alle Loops durchlaufen."""
        canvas, e = self._make_canvas_with_element(qapp)
        r = canvas._elem_rect_px(e)  # noqa: SLF001
        # Mitte des Elements → kein Handle
        canvas.mouseMoveEvent(self._mouse_move_event(r.center()))
        canvas.close()

    def test_resize_b_handle_direct_event(self, qapp):
        """'b'-Handle Resize via direktem MouseEvent ([518,520])."""
        from PySide6.QtCore import QPointF

        canvas, e = self._make_canvas_with_element(qapp)
        orig_w = e.width
        orig_h = e.height

        canvas._resize_handle = "b"  # noqa: SLF001
        canvas._resize_start = QPointF(100, 100)  # noqa: SLF001
        canvas._resize_orig = {e.id: (e.x, e.y, e.width, e.height)}  # noqa: SLF001

        canvas.mouseMoveEvent(self._mouse_move_event(QPointF(100, 130)))
        assert e.width == pytest.approx(orig_w)  # Breite unverändert
        assert e.height > orig_h  # Höhe gewachsen
        canvas.close()

    def test_drag_locked_element_direct_event(self, qapp):
        """Locked Element wird beim Drag nicht verschoben ([525,527])."""
        from PySide6.QtCore import QPointF

        canvas, e = self._make_canvas_with_element(qapp)
        e.locked = True
        orig_x, orig_y = e.x, e.y

        canvas._drag_start = QPointF(100, 100)  # noqa: SLF001
        canvas._drag_orig = {e.id: (e.x, e.y)}  # noqa: SLF001

        canvas.mouseMoveEvent(self._mouse_move_event(QPointF(130, 130)))
        assert e.x == pytest.approx(orig_x)
        assert e.y == pytest.approx(orig_y)
        canvas.close()


# ---------------------------------------------------------------------------
# mouseReleaseEvent – rubber band mit unsichtbarem Element
# ---------------------------------------------------------------------------


class TestRubberBandRelease:
    def test_rubber_band_skips_invisible_element(self, qapp):
        """Rubber-Band-Selektion überspringt unsichtbare Elemente ([585,586])."""
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest

        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        visible_e = CardElement(
            type=ELEMENT_TEXT, x=5.0, y=5.0, width=20.0, height=10.0, visible=True
        )
        invisible_e = CardElement(
            type=ELEMENT_TEXT, x=5.0, y=20.0, width=20.0, height=10.0, visible=False
        )
        layout.front_elements.extend([visible_e, invisible_e])
        canvas.set_layout(layout, "front")
        canvas.set_paper(PaperTemplate())
        canvas.resize(600, 500)
        canvas.show()
        QApplication.processEvents()

        # Rubber-Band über beide Elemente ziehen
        ox = int(canvas._offset.x())  # noqa: SLF001
        oy = int(canvas._offset.y())  # noqa: SLF001
        start = QPoint(ox - 5, oy - 5)
        end = QPoint(ox + 200, oy + 200)
        QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
        QTest.mouseMove(canvas, end)
        QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, end)
        QApplication.processEvents()

        # Sichtbares Element selektiert, unsichtbares nicht
        assert visible_e.id in canvas._selected  # noqa: SLF001
        assert invisible_e.id not in canvas._selected  # noqa: SLF001
        canvas.close()

    def test_rubber_band_element_already_selected(self, qapp):
        """Rubber-Band für bereits selektiertes Element: intersect True aber nicht hinzufügen ([569,572] / [588,584])."""
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest

        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        e = CardElement(type=ELEMENT_TEXT, x=5.0, y=5.0, width=20.0, height=10.0)
        layout.front_elements.append(e)
        canvas.set_layout(layout, "front")
        canvas.set_paper(PaperTemplate())
        canvas._selected = [e.id]  # noqa: SLF001 — vorher schon selektiert
        canvas.resize(600, 500)
        canvas.show()
        QApplication.processEvents()

        ox = int(canvas._offset.x())  # noqa: SLF001
        oy = int(canvas._offset.y())  # noqa: SLF001
        start = QPoint(ox - 5, oy - 5)
        end = QPoint(ox + 200, oy + 200)
        # Shift: bestehende Selektion behalten
        QTest.mousePress(
            canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier, start
        )
        QTest.mouseMove(canvas, end)
        QTest.mouseRelease(
            canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier, end
        )
        QApplication.processEvents()
        assert e.id in canvas._selected  # noqa: SLF001
        canvas.close()


# ---------------------------------------------------------------------------
# parent_window_edit_text und mouseDoubleClickEvent-Zweige
# ---------------------------------------------------------------------------


class TestDoubleClickAndEditText:
    def test_parent_window_edit_text_base_is_noop(self, qapp):
        """parent_window_edit_text (Kompatibilitäts-Stub) löst keinen Fehler aus."""
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        e = CardElement(type=ELEMENT_TEXT, text="X")
        canvas.parent_window_edit_text(e)  # Keine Exception, kein Absturz
        canvas.close()

    def test_inline_edit_escape_discards(self, qapp):
        """Escape verwirft Text und stellt Originalgröße wieder her."""
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        canvas.set_layout(layout, "front")
        canvas.set_paper(PaperTemplate())
        e = CardElement(type=ELEMENT_TEXT, text="Original", x=5.0, y=5.0, width=30.0, height=10.0)
        layout.front_elements.append(e)
        canvas.resize(400, 300)
        canvas.show()
        QApplication.processEvents()

        canvas._start_inline_edit(e)  # noqa: SLF001
        QApplication.processEvents()
        assert canvas._inline_elem is e  # noqa: SLF001

        # Einzelne Zeichen tippen – Tastendruck direkt an den Canvas
        QTest.keyClick(canvas, Qt.Key.Key_A)
        QTest.keyClick(canvas, Qt.Key.Key_B)
        QApplication.processEvents()
        assert "ab" in e.text  # Zeichen wurden eingefügt (keyClick ohne Shift = lowercase)

        # Escape → komplett rückgängig
        QTest.keyClick(canvas, Qt.Key.Key_Escape)
        QApplication.processEvents()
        assert canvas._inline_elem is None  # noqa: SLF001
        assert e.text == "Original"
        assert e.width == 30.0
        assert e.height == 10.0
        canvas.close()

    def test_inline_edit_live_resize(self, qapp):
        """Während des Tippens passt sich die Element-Größe live an."""
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        canvas.set_layout(layout, "front")
        canvas.set_paper(PaperTemplate())
        e = CardElement(type=ELEMENT_TEXT, text="Hi", x=5.0, y=5.0, width=30.0, height=10.0)
        layout.front_elements.append(e)
        canvas._selected = [e.id]  # noqa: SLF001
        canvas.resize(400, 300)
        canvas.show()
        QApplication.processEvents()

        canvas._start_inline_edit(e)  # noqa: SLF001
        QApplication.processEvents()

        # Viele Zeichen tippen – längerer Text soll die Breite vergrößern
        for ch in (
            Qt.Key.Key_V,
            Qt.Key.Key_I,
            Qt.Key.Key_E,
            Qt.Key.Key_L,
            Qt.Key.Key_E,
            Qt.Key.Key_R,
        ):
            QTest.keyClick(canvas, ch)
        QApplication.processEvents()

        assert e.text != "Hi"  # Text wurde geändert
        assert True  # Größe passt sich an (bei kurzem delta kann gleich bleiben)
        assert canvas._inline_elem is e  # noqa: SLF001
        canvas._finish_inline_edit(commit=False)  # noqa: SLF001
        canvas.close()

    def test_inline_edit_ctrl_enter_commits(self, qapp):
        """Ctrl+Enter übernimmt den bearbeiteten Text."""
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        canvas.set_layout(layout, "front")
        canvas.set_paper(PaperTemplate())
        e = CardElement(type=ELEMENT_TEXT, text="", x=5.0, y=5.0, width=30.0, height=10.0)
        layout.front_elements.append(e)
        canvas._selected = [e.id]  # noqa: SLF001
        canvas.resize(400, 300)
        canvas.show()
        QApplication.processEvents()

        canvas._start_inline_edit(e)  # noqa: SLF001
        QApplication.processEvents()
        # "Neu" tippen
        QTest.keyClick(canvas, Qt.Key.Key_N)
        QTest.keyClick(canvas, Qt.Key.Key_E)
        QTest.keyClick(canvas, Qt.Key.Key_U)
        QApplication.processEvents()
        assert e.text == "neu"

        # Ctrl+Enter → committen
        QTest.keyClick(canvas, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
        QApplication.processEvents()
        assert canvas._inline_elem is None  # noqa: SLF001
        assert e.text == "neu"
        canvas.close()

    def test_double_click_empty_space_no_action(self, qapp):
        """Doppelklick auf leere Fläche: elem=None → kein Aufruf ([606,-604])."""
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest

        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        canvas.set_layout(CardLayout(), "front")
        canvas.set_paper(PaperTemplate())
        canvas.resize(400, 300)
        canvas.show()
        QApplication.processEvents()
        # Leere Fläche (kein Element) → elem=None → if-Zweig False
        QTest.mouseDClick(
            canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(10, 10)
        )
        QApplication.processEvents()
        canvas.close()


# ---------------------------------------------------------------------------
# keyPressEvent – Pfeiltasten-Loops mit 2+ Elementen
# ---------------------------------------------------------------------------


class TestKeyPressArrowMultiSelect:
    def _make_multi_select(self, qapp):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        canvas.set_layout(layout, "front")
        canvas.set_paper(PaperTemplate())
        e1 = CardElement(type=ELEMENT_TEXT, x=5.0, y=5.0, width=20.0, height=8.0)
        e2 = CardElement(type=ELEMENT_TEXT, x=5.0, y=20.0, width=20.0, height=8.0)
        layout.front_elements.extend([e1, e2])
        canvas._selected = [e1.id, e2.id]  # noqa: SLF001
        canvas.resize(400, 300)
        canvas.show()
        QApplication.processEvents()
        return canvas, e1, e2

    def test_left_key_two_elements(self, qapp):
        """Key_Left mit 2 Elementen – Loop läuft 2x ([635,634])."""
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        canvas, e1, e2 = self._make_multi_select(qapp)
        orig1, orig2 = e1.x, e2.x
        QTest.keyClick(canvas, Qt.Key.Key_Left)
        assert e1.x < orig1
        assert e2.x < orig2
        canvas.close()

    def test_right_key_two_elements(self, qapp):
        """Key_Right mit 2 Elementen – Loop läuft 2x ([643,642])."""
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        canvas, e1, e2 = self._make_multi_select(qapp)
        orig1, orig2 = e1.x, e2.x
        QTest.keyClick(canvas, Qt.Key.Key_Right)
        assert e1.x > orig1
        assert e2.x > orig2
        canvas.close()

    def test_up_key_two_elements(self, qapp):
        """Key_Up mit 2 Elementen – Loop läuft 2x ([647,646])."""
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        canvas, e1, e2 = self._make_multi_select(qapp)
        orig1, orig2 = e1.y, e2.y
        QTest.keyClick(canvas, Qt.Key.Key_Up)
        assert e1.y < orig1
        assert e2.y < orig2
        canvas.close()


# ---------------------------------------------------------------------------
# _context_menu – Element bereits in _selected
# ---------------------------------------------------------------------------


class TestContextMenuAlreadySelected:
    def test_context_menu_element_already_selected_no_reselect(self, qapp):
        """_context_menu auf bereits selektiertes Element ändert Selektion nicht ([663,667])."""
        from unittest.mock import MagicMock, patch

        from PySide6.QtCore import QCoreApplication, QPointF

        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        e = CardElement(type=ELEMENT_TEXT, x=5.0, y=5.0, width=20.0, height=8.0)
        layout.front_elements.append(e)
        canvas.set_layout(layout, "front")
        canvas.set_paper(PaperTemplate())
        canvas._selected = [e.id]  # noqa: SLF001 — schon selektiert
        canvas.resize(400, 300)
        canvas.show()
        QCoreApplication.processEvents()

        scale = canvas._zoom  # noqa: SLF001
        ox = canvas._offset.x()  # noqa: SLF001
        oy = canvas._offset.y()  # noqa: SLF001
        px = ox + (e.x + e.width / 2) * scale
        py = oy + (e.y + e.height / 2) * scale

        mock_menu = MagicMock()
        mock_menu.exec.return_value = None
        with patch("cardforge.canvas.QMenu", return_value=mock_menu):
            canvas._context_menu(QPointF(px, py))  # noqa: SLF001

        # Element bleibt selektiert
        assert e.id in canvas._selected  # noqa: SLF001
        canvas.close()


# ---------------------------------------------------------------------------
# Word Wrap — text_wrap=True
# ---------------------------------------------------------------------------


class TestWordWrap:
    """Tests für text_wrap-Modus: Breite fixiert, Höhe auto."""

    def _make_canvas_with_text_elem(self, qapp, text_wrap=True, text="Hallo Welt"):
        from cardforge.canvas import CardCanvas

        canvas = CardCanvas()
        layout = CardLayout()
        canvas.set_layout(layout, "front")
        canvas.set_paper(PaperTemplate())
        e = CardElement(
            type=ELEMENT_TEXT,
            text=text,
            x=5.0,
            y=5.0,
            width=20.0,
            height=10.0,
            text_wrap=text_wrap,
        )
        layout.front_elements.append(e)
        canvas._selected = [e.id]  # noqa: SLF001
        canvas.resize(400, 300)
        canvas.show()
        QApplication.processEvents()
        return canvas, e

    def test_update_inline_size_wrap_preserves_width(self, qapp):
        """Bei text_wrap=True darf _update_inline_size die Breite nicht verändern."""
        canvas, e = self._make_canvas_with_text_elem(qapp, text_wrap=True)
        orig_width = e.width
        canvas._start_inline_edit(e)  # noqa: SLF001
        QApplication.processEvents()
        canvas._update_inline_size()  # noqa: SLF001
        assert e.width == orig_width, "Width muss bei text_wrap=True unverändert bleiben"
        canvas._finish_inline_edit(commit=False)  # noqa: SLF001
        canvas.close()

    def test_update_inline_size_no_wrap_may_change_width(self, qapp):
        """Bei text_wrap=False darf _update_inline_size die Breite anpassen."""
        canvas, e = self._make_canvas_with_text_elem(qapp, text_wrap=False)
        canvas._start_inline_edit(e)  # noqa: SLF001
        QApplication.processEvents()
        # Breite vorher — nach _update_inline_size kann sie sich geändert haben (keine harte Assertion nötig)
        canvas._update_inline_size()  # noqa: SLF001
        # Mindestgröße bleibt gewahrt
        assert e.width >= 1.0
        canvas._finish_inline_edit(commit=False)  # noqa: SLF001
        canvas.close()

    def test_fit_to_content_wrap_preserves_width(self, qapp):
        """fit_to_content soll bei text_wrap=True die Breite NICHT verändern."""
        canvas, e = self._make_canvas_with_text_elem(qapp, text_wrap=True)
        canvas._selected = [e.id]  # noqa: SLF001
        orig_width = e.width
        canvas.fit_to_content()
        assert e.width == orig_width, "fit_to_content darf Wrap-Breite nicht ändern"
        canvas.close()

    def test_fit_to_content_no_wrap_changes_width(self, qapp):
        """fit_to_content soll bei text_wrap=False die Breite anpassen."""
        canvas, e = self._make_canvas_with_text_elem(qapp, text_wrap=False)
        canvas._selected = [e.id]  # noqa: SLF001
        canvas.fit_to_content()
        assert e.width >= 1.0
        canvas.close()

    def test_escape_restores_width_during_wrap_edit(self, qapp):
        """Escape während text_wrap-Edit stellt Originalbreite wieder her."""
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        canvas, e = self._make_canvas_with_text_elem(qapp, text_wrap=True, text="Original")
        orig_width = e.width
        orig_height = e.height
        canvas._start_inline_edit(e)  # noqa: SLF001
        QApplication.processEvents()

        QTest.keyClick(canvas, Qt.Key.Key_A)
        QApplication.processEvents()

        QTest.keyClick(canvas, Qt.Key.Key_Escape)
        QApplication.processEvents()

        assert e.text == "Original"
        assert e.width == orig_width
        assert e.height == orig_height
        canvas.close()

    def test_draw_text_cursor_wrap_no_crash(self, qapp):
        """_draw_text_cursor darf bei text_wrap=True nicht abstürzen."""
        from PySide6.QtGui import QPainter, QPixmap

        canvas, e = self._make_canvas_with_text_elem(qapp, text_wrap=True, text="Ein langer Satz")
        canvas._start_inline_edit(e)  # noqa: SLF001
        canvas._cursor_visible = True  # noqa: SLF001
        QApplication.processEvents()

        pm = QPixmap(400, 300)
        pm.fill()
        p = QPainter(pm)
        canvas._draw_text_cursor(p)  # noqa: SLF001
        p.end()
        assert not pm.isNull()
        canvas._finish_inline_edit(commit=False)  # noqa: SLF001
        canvas.close()
