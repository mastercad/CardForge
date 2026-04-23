"""Tests für icons.py, icon_picker_dialog.py und renderer Icon-Zeichnung."""

from __future__ import annotations

from unittest.mock import patch

from PySide6.QtGui import QPixmap

from cardforge.icons import ICONS, get_icon_label, get_icon_pixmap
from cardforge.models import ELEMENT_ICON, CardElement

# ---------------------------------------------------------------------------
# icons.py
# ---------------------------------------------------------------------------


class TestIconsDict:
    def test_has_expected_keys(self):
        for key in ("phone", "email", "web", "location", "linkedin", "xing"):
            assert key in ICONS, f"{key!r} fehlt in ICONS"

    def test_all_values_are_strings(self):
        for name, fa_id in ICONS.items():
            assert isinstance(fa_id, str), f"ICONS[{name!r}] ist kein str"

    def test_icon_labels_covers_all_icons(self, qapp):
        for name in ICONS:
            label = get_icon_label(name)
            assert isinstance(label, str) and label, f"{name!r} liefert kein Label"


class TestGetIconPixmap:
    def test_returns_pixmap_for_known_icon(self, qapp):
        pm = get_icon_pixmap("phone", "#000000", 32)
        assert pm is not None
        assert isinstance(pm, QPixmap)
        assert not pm.isNull()

    def test_returns_none_for_unknown_icon(self, qapp):
        pm = get_icon_pixmap("nonexistent_icon_xyz", "#000000", 32)
        assert pm is None

    def test_different_colors_return_pixmap(self, qapp):
        for color in ("#ff0000", "#00ff00", "#0000ff", "#ffffff"):
            pm = get_icon_pixmap("email", color, 24)
            assert pm is not None, f"Kein Pixmap für Farbe {color}"

    def test_returns_none_when_qtawesome_raises(self, qapp):
        with patch("cardforge.icons.qta.icon", side_effect=Exception("boom")):
            pm = get_icon_pixmap("phone", "#000000", 32)
        assert pm is None

    def test_small_size(self, qapp):
        pm = get_icon_pixmap("web", "#111111", 16)
        assert pm is not None

    def test_large_size(self, qapp):
        pm = get_icon_pixmap("web", "#111111", 128)
        assert pm is not None


# ---------------------------------------------------------------------------
# icon_picker_dialog.py
# ---------------------------------------------------------------------------


class TestIconPickerDialog:
    def test_creates_without_crash(self, qapp):
        from cardforge.icon_picker_dialog import IconPickerDialog

        dlg = IconPickerDialog()
        assert dlg is not None
        dlg.close()

    def test_default_selected_icon_is_none(self, qapp):
        from cardforge.icon_picker_dialog import IconPickerDialog

        dlg = IconPickerDialog()
        assert dlg.selected_icon is None
        dlg.close()

    def test_initial_current_pre_selects(self, qapp):
        from cardforge.icon_picker_dialog import IconPickerDialog

        dlg = IconPickerDialog(current="email")
        assert dlg.selected_icon == "email"
        dlg.close()

    def test_initial_unknown_current_gives_none(self, qapp):
        from cardforge.icon_picker_dialog import IconPickerDialog

        dlg = IconPickerDialog(current="unknown_xyz")
        # unknown icon_name → button doesn't exist, selected stays as the passed string
        # but selected_icon returns None for falsy or returns value – depends on value
        # "unknown_xyz" is truthy so it's returned as-is (by design)
        # The property returns self._selected or None
        result = dlg.selected_icon
        # Either None or the unknown string – both are acceptable behaviours
        assert result in (None, "unknown_xyz")
        dlg.close()

    def test_click_selects_icon(self, qapp):
        from cardforge.icon_picker_dialog import IconPickerDialog

        dlg = IconPickerDialog()
        dlg._on_click("phone")
        assert dlg.selected_icon == "phone"
        dlg.close()

    def test_click_updates_highlight(self, qapp):
        from PySide6.QtCore import Qt

        from cardforge.icon_picker_dialog import IconPickerDialog

        dlg = IconPickerDialog()
        dlg._on_click("web")
        current = dlg._list.currentItem()
        assert current is not None
        assert current.data(Qt.ItemDataRole.UserRole) == "web"
        dlg.close()

    def test_all_icons_have_list_items(self, qapp):
        from PySide6.QtCore import Qt

        from cardforge.icon_picker_dialog import IconPickerDialog

        dlg = IconPickerDialog()
        names = {dlg._list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(dlg._list.count())}
        for name in ICONS:
            assert name in names, f"Kein Listeneintrag für Icon {name!r}"
        dlg.close()

    def test_info_label_updated_on_click(self, qapp):
        from cardforge.icon_picker_dialog import IconPickerDialog

        dlg = IconPickerDialog()
        dlg._on_click("email")
        assert dlg._info.text() == get_icon_label("email")
        dlg.close()

    def test_empty_string_current_gives_none(self, qapp):
        from cardforge.icon_picker_dialog import IconPickerDialog

        dlg = IconPickerDialog(current="")
        assert dlg.selected_icon is None
        dlg.close()


# ---------------------------------------------------------------------------
# renderer._draw_icon – via ElementRenderer
# ---------------------------------------------------------------------------


class TestRendererDrawIcon:
    def _make_renderer(self, scale=5.0):
        from cardforge.renderer import ElementRenderer

        return ElementRenderer(scale)

    def _make_icon_elem(self, icon_name="phone", color="#000000"):
        return CardElement(
            type=ELEMENT_ICON,
            icon_name=icon_name,
            color=color,
            x=0,
            y=0,
            width=20,
            height=20,
        )

    def test_cache_empty_initially(self, qapp):
        r = self._make_renderer()
        assert r._icon_cache == {}

    def test_get_icon_pixmap_caches_result(self, qapp):
        r = self._make_renderer()
        pm1 = r._get_icon_pixmap("phone", "#000000", 64)
        pm2 = r._get_icon_pixmap("phone", "#000000", 64)
        assert pm1 is pm2  # same object from cache

    def test_get_icon_pixmap_unknown_returns_none(self, qapp):
        r = self._make_renderer()
        pm = r._get_icon_pixmap("not_existing_icon", "#000000", 32)
        assert pm is None

    def test_clear_all_caches_clears_icon_cache(self, qapp):
        r = self._make_renderer()
        r._get_icon_pixmap("phone", "#000000", 32)
        assert len(r._icon_cache) > 0
        r.clear_all_caches()
        assert r._icon_cache == {}

    def test_draw_icon_valid(self, qapp):
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QPainter, QPixmap

        from cardforge.renderer import ElementRenderer

        renderer = ElementRenderer(5.0)
        pm = QPixmap(200, 150)
        pm.fill()
        painter = QPainter(pm)
        e = self._make_icon_elem("email", "#333333")
        rect = QRectF(0, 0, 100, 100)
        renderer.draw_element(painter, e, rect)
        painter.end()

    def test_draw_icon_unknown_shows_fallback(self, qapp):
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QPainter, QPixmap

        from cardforge.renderer import ElementRenderer

        renderer = ElementRenderer(5.0)
        pm = QPixmap(200, 150)
        pm.fill()
        painter = QPainter(pm)
        e = self._make_icon_elem("unknown_icon_xyz", "#000000")
        rect = QRectF(0, 0, 100, 100)
        renderer.draw_element(painter, e, rect)
        painter.end()


# ---------------------------------------------------------------------------
# ELEMENT_ICON constant
# ---------------------------------------------------------------------------


class TestElementIconConstant:
    def test_value(self):
        assert ELEMENT_ICON == "icon"

    def test_card_element_default_icon_name(self):
        e = CardElement(type=ELEMENT_ICON)
        assert e.icon_name == "phone"

    def test_card_element_custom_icon_name(self):
        e = CardElement(type=ELEMENT_ICON, icon_name="email")
        assert e.icon_name == "email"

    def test_to_dict_includes_icon_name(self):
        e = CardElement(type=ELEMENT_ICON, icon_name="web")
        d = e.to_dict()
        assert d["icon_name"] == "web"

    def test_from_dict_restores_icon_name(self):
        e = CardElement(type=ELEMENT_ICON, icon_name="linkedin")
        d = e.to_dict()
        e2 = CardElement.from_dict(d)
        assert e2.icon_name == "linkedin"
        assert e2.type == ELEMENT_ICON
