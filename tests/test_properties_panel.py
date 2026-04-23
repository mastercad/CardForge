"""Tests für cardforge.properties_panel – ColorButton und PropertiesPanel."""

from __future__ import annotations

from cardforge.models import (
    ELEMENT_ELLIPSE,
    ELEMENT_IMAGE,
    ELEMENT_LINE,
    ELEMENT_QR,
    ELEMENT_RECT,
    ELEMENT_TEXT,
    CardElement,
)


class TestColorButton:
    def test_default_color(self, qapp):
        from cardforge.properties_panel import ColorButton

        btn = ColorButton()
        assert btn.color() == "#000000"
        btn.close()

    def test_custom_initial_color(self, qapp):
        from cardforge.properties_panel import ColorButton

        btn = ColorButton("#ff0000")
        assert btn.color() == "#ff0000"
        btn.close()

    def test_set_color(self, qapp):
        from cardforge.properties_panel import ColorButton

        btn = ColorButton()
        btn.set_color("#00ff00")
        assert btn.color() == "#00ff00"
        btn.close()

    def test_color_changed_signal(self, qapp):
        from cardforge.properties_panel import ColorButton

        btn = ColorButton("#000000")
        received = []
        btn.colorChanged.connect(received.append)
        btn.set_color("#123456")
        # Signal wird nur durch _pick() ausgelöst (QColorDialog), nicht durch set_color
        # Daher: set_color ändert intern, Signal wird NICHT emittiert
        assert btn.color() == "#123456"
        btn.close()

    def test_has_fixed_size(self, qapp):
        from cardforge.properties_panel import ColorButton

        btn = ColorButton()
        assert btn.width() == 28
        assert btn.height() == 26
        btn.close()


class TestPropertiesPanel:
    def test_creates_without_crash(self, qapp):
        from cardforge.properties_panel import PropertiesPanel

        panel = PropertiesPanel()
        assert panel is not None
        panel.close()

    def test_initial_no_elements(self, qapp):
        from cardforge.properties_panel import PropertiesPanel

        panel = PropertiesPanel()
        assert panel._elements == []  # noqa: SLF001
        panel.close()

    def test_set_elements_empty(self, qapp):
        from cardforge.properties_panel import PropertiesPanel

        panel = PropertiesPanel()
        panel.set_elements([])
        assert panel._elements == []  # noqa: SLF001
        panel.close()

    def test_set_text_element(self, qapp):
        from cardforge.properties_panel import PropertiesPanel

        panel = PropertiesPanel()
        e = CardElement(type=ELEMENT_TEXT, text="Test", font_size=12.0)
        panel.set_elements([e])
        assert len(panel._elements) == 1  # noqa: SLF001
        panel.close()

    def test_set_image_element(self, qapp):
        from cardforge.properties_panel import PropertiesPanel

        panel = PropertiesPanel()
        e = CardElement(type=ELEMENT_IMAGE, image_path="/some/path.png")
        panel.set_elements([e])
        panel.close()

    def test_set_rect_element(self, qapp):
        from cardforge.properties_panel import PropertiesPanel

        panel = PropertiesPanel()
        e = CardElement(type=ELEMENT_RECT, fill_color="#aabbcc")
        panel.set_elements([e])
        panel.close()

    def test_set_ellipse_element(self, qapp):
        from cardforge.properties_panel import PropertiesPanel

        panel = PropertiesPanel()
        e = CardElement(type=ELEMENT_ELLIPSE)
        panel.set_elements([e])
        panel.close()

    def test_set_line_element(self, qapp):
        from cardforge.properties_panel import PropertiesPanel

        panel = PropertiesPanel()
        e = CardElement(type=ELEMENT_LINE)
        panel.set_elements([e])
        panel.close()

    def test_set_qr_element(self, qapp):
        from cardforge.properties_panel import PropertiesPanel

        panel = PropertiesPanel()
        e = CardElement(type=ELEMENT_QR, qr_data="https://example.com")
        panel.set_elements([e])
        panel.close()

    def test_set_multiple_elements(self, qapp):
        from cardforge.properties_panel import PropertiesPanel

        panel = PropertiesPanel()
        elements = [
            CardElement(type=ELEMENT_TEXT, text="A"),
            CardElement(type=ELEMENT_TEXT, text="B"),
        ]
        panel.set_elements(elements)
        assert len(panel._elements) == 2  # noqa: SLF001
        panel.close()

    def test_element_changed_signal_exists(self, qapp):
        from cardforge.properties_panel import PropertiesPanel

        panel = PropertiesPanel()
        received = []
        panel.elementChanged.connect(lambda: received.append(True))
        panel.close()


# ---------------------------------------------------------------------------
# ColorButton._pick – QColorDialog-Integration
# ---------------------------------------------------------------------------


class TestColorButtonPick:
    def test_pick_invalid_color_no_change(self, qapp):
        """_pick mit ungültiger Farbe ändert nichts und sendet kein Signal."""
        from unittest.mock import patch

        from PySide6.QtGui import QColor

        from cardforge.properties_panel import ColorButton

        btn = ColorButton("#ff0000")
        received = []
        btn.colorChanged.connect(received.append)
        with patch(
            "cardforge.properties_panel.QColorDialog.getColor",
            return_value=QColor(),  # invalid color
        ):
            btn._pick()
        assert btn.color() == "#ff0000"
        assert received == []
        btn.close()

    def test_pick_valid_color_updates_and_emits(self, qapp):
        """_pick mit gültiger Farbe aktualisiert Farbe und sendet Signal."""
        from unittest.mock import patch

        from PySide6.QtGui import QColor

        from cardforge.properties_panel import ColorButton

        btn = ColorButton("#ff0000")
        received = []
        btn.colorChanged.connect(received.append)
        with patch(
            "cardforge.properties_panel.QColorDialog.getColor",
            return_value=QColor("#00ff00"),
        ):
            btn._pick()
        assert btn.color() == "#00ff00"
        assert received == ["#00ff00"]
        btn.close()


# ---------------------------------------------------------------------------
# PropertiesPanel._apply und _browse_image
# ---------------------------------------------------------------------------


class TestPropertiesPanelApply:
    def test_apply_single_element_updates_position(self, qapp):
        """_apply mit einem Element aktualisiert x/y/w/h aus den Widgets."""
        from cardforge.properties_panel import PropertiesPanel

        panel = PropertiesPanel()
        e = CardElement(type=ELEMENT_TEXT, text="Test", x=1.0, y=2.0, width=10.0, height=5.0)
        panel.set_elements([e])
        # _updating wurde durch set_elements() auf False gesetzt
        panel._x.setValue(3.0)  # noqa: SLF001
        panel._y.setValue(4.0)  # noqa: SLF001
        panel._apply()
        assert e.x == 3.0
        assert e.y == 4.0
        panel.close()

    def test_apply_multiple_elements_skips_xywh(self, qapp):
        """_apply mit mehreren Elementen überspringt x/y/w/h."""
        from cardforge.properties_panel import PropertiesPanel

        panel = PropertiesPanel()
        e1 = CardElement(type=ELEMENT_TEXT, text="A", x=1.0, y=2.0, width=10.0, height=5.0)
        e2 = CardElement(type=ELEMENT_TEXT, text="B", x=3.0, y=4.0, width=12.0, height=6.0)
        panel.set_elements([e1, e2])
        panel._apply()
        # x/y/w/h bleiben unberührt (multi-element skip)
        assert e1.x == 1.0
        assert e2.x == 3.0
        panel.close()

    def test_browse_image_no_path_no_change(self, qapp):
        """_browse_image ohne Dateiauswahl ändert nichts."""
        from unittest.mock import patch

        from cardforge.properties_panel import PropertiesPanel

        panel = PropertiesPanel()
        e = CardElement(type=ELEMENT_IMAGE, image_path="/old/path.png")
        panel.set_elements([e])
        old_text = panel._img_path.text()  # noqa: SLF001
        with patch(
            "cardforge.properties_panel.QFileDialog.getOpenFileName",
            return_value=("", ""),
        ):
            panel._browse_image()
        assert panel._img_path.text() == old_text  # noqa: SLF001
        panel.close()

    def test_browse_image_with_path_updates_field(self, qapp):
        """_browse_image mit gewähltem Pfad setzt das Textfeld."""
        from unittest.mock import patch

        from cardforge.properties_panel import PropertiesPanel

        panel = PropertiesPanel()
        e = CardElement(type=ELEMENT_IMAGE)
        panel.set_elements([e])
        with patch(
            "cardforge.properties_panel.QFileDialog.getOpenFileName",
            return_value=("/new/image.png", ""),
        ):
            panel._browse_image()
        assert panel._img_path.text() == "/new/image.png"  # noqa: SLF001
        panel.close()
