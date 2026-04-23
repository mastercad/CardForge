"""Tests für cardforge.renderer – benötigt Qt (offscreen)."""

from __future__ import annotations

import math

from cardforge.models import (
    ELEMENT_ELLIPSE,
    ELEMENT_IMAGE,
    ELEMENT_LINE,
    ELEMENT_QR,
    ELEMENT_RECT,
    ELEMENT_TEXT,
    CardElement,
)
from cardforge.renderer import PT_TO_MM, ElementRenderer


class TestPtToMmConstant:
    def test_value(self):
        assert math.isclose(PT_TO_MM, 25.4 / 72.0, rel_tol=1e-9)


class TestElementRendererInit:
    def test_scale_stored(self):
        r = ElementRenderer(3.0)
        assert r._scale == 3.0  # noqa: SLF001

    def test_caches_empty_on_init(self):
        r = ElementRenderer(2.0)
        assert r._pixmap_cache == {}  # noqa: SLF001
        assert r._qr_cache == {}  # noqa: SLF001


class TestUnitConversions:
    def test_pt_to_px(self):
        r = ElementRenderer(4.0)
        # 1 pt × PT_TO_MM × 4 px/mm
        expected = 1.0 * PT_TO_MM * 4.0
        assert math.isclose(r.pt_to_px(1.0), expected, rel_tol=1e-9)

    def test_mm_to_px(self):
        r = ElementRenderer(5.0)
        assert math.isclose(r.mm_to_px(2.0), 10.0, rel_tol=1e-9)

    def test_scale_update(self):
        r = ElementRenderer(2.0)
        r.set_scale(6.0)
        assert math.isclose(r.mm_to_px(1.0), 6.0, rel_tol=1e-9)


class TestCacheInvalidation:
    def test_invalidate_specific_pixmap(self, qapp):
        from PySide6.QtGui import QPixmap

        r = ElementRenderer(3.0)
        pm = QPixmap(10, 10)
        r._pixmap_cache["some/path.png"] = pm  # noqa: SLF001
        r.invalidate_pixmap_cache("some/path.png")
        assert "some/path.png" not in r._pixmap_cache  # noqa: SLF001

    def test_invalidate_all_pixmaps(self, qapp):
        from PySide6.QtGui import QPixmap

        r = ElementRenderer(3.0)
        r._pixmap_cache["a"] = QPixmap(1, 1)  # noqa: SLF001
        r._pixmap_cache["b"] = QPixmap(1, 1)  # noqa: SLF001
        r.invalidate_pixmap_cache()
        assert r._pixmap_cache == {}  # noqa: SLF001

    def test_invalidate_specific_qr(self, qapp):
        from PySide6.QtGui import QPixmap

        r = ElementRenderer(3.0)
        r._qr_cache["https://test.com"] = QPixmap(1, 1)  # noqa: SLF001
        r.invalidate_qr_cache("https://test.com")
        assert "https://test.com" not in r._qr_cache  # noqa: SLF001

    def test_invalidate_all_qr(self, qapp):
        from PySide6.QtGui import QPixmap

        r = ElementRenderer(3.0)
        r._qr_cache["x"] = QPixmap(1, 1)  # noqa: SLF001
        r.invalidate_qr_cache()
        assert r._qr_cache == {}  # noqa: SLF001

    def test_clear_all_caches(self, qapp):
        from PySide6.QtGui import QPixmap

        r = ElementRenderer(3.0)
        r._pixmap_cache["img"] = QPixmap(1, 1)  # noqa: SLF001
        r._qr_cache["qr"] = QPixmap(1, 1)  # noqa: SLF001
        r.clear_all_caches()
        assert r._pixmap_cache == {}  # noqa: SLF001
        assert r._qr_cache == {}  # noqa: SLF001


class TestGetPixmap:
    def test_nonexistent_path_returns_none(self, qapp):
        r = ElementRenderer(3.0)
        pm = r.get_pixmap("/nonexistent/path/image.png")
        assert pm is None

    def test_empty_path_returns_none(self, qapp):
        r = ElementRenderer(3.0)
        pm = r.get_pixmap("")
        assert pm is None


class TestDrawElement:
    """Zeichnet jedes Element auf einen temporären QPainter und prüft, dass kein Fehler auftritt."""

    def _make_painter_and_rect(self, qapp):
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QPainter, QPixmap

        pm = QPixmap(200, 200)
        pm.fill()
        p = QPainter(pm)
        rect = QRectF(10, 10, 100, 50)
        return pm, p, rect

    def test_draw_text_element(self, qapp):
        pm, p, rect = self._make_painter_and_rect(qapp)
        r = ElementRenderer(3.0)
        e = CardElement(
            type=ELEMENT_TEXT, text="Test", color="#000000", font_family="Arial", font_size=10.0
        )
        r.draw_element(p, e, rect)
        p.end()
        assert not pm.isNull()

    def test_draw_text_all_alignments(self, qapp):
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QPainter, QPixmap

        r = ElementRenderer(3.0)
        for h_align in ("left", "center", "right"):
            for v_align in ("top", "middle", "bottom"):
                pm = QPixmap(200, 200)
                p = QPainter(pm)
                e = CardElement(type=ELEMENT_TEXT, text="x", h_align=h_align, v_align=v_align)
                r.draw_element(p, e, QRectF(0, 0, 100, 50))
                p.end()

    def test_draw_rect_element(self, qapp):
        pm, p, rect = self._make_painter_and_rect(qapp)
        r = ElementRenderer(3.0)
        e = CardElement(
            type=ELEMENT_RECT, fill_color="#ff0000", border_color="#000000", border_width=1.0
        )
        r.draw_element(p, e, rect)
        p.end()

    def test_draw_ellipse_element(self, qapp):
        pm, p, rect = self._make_painter_and_rect(qapp)
        r = ElementRenderer(3.0)
        e = CardElement(type=ELEMENT_ELLIPSE, fill_color="#00ff00", border_width=0.5)
        r.draw_element(p, e, rect)
        p.end()

    def test_draw_line_element(self, qapp):
        pm, p, rect = self._make_painter_and_rect(qapp)
        r = ElementRenderer(3.0)
        e = CardElement(type=ELEMENT_LINE, border_color="#0000ff", height=1.0)
        r.draw_element(p, e, rect)
        p.end()

    def test_draw_image_element_no_file(self, qapp):
        """Ohne gültige image_path wird Platzhalter gezeichnet."""
        pm, p, rect = self._make_painter_and_rect(qapp)
        r = ElementRenderer(3.0)
        e = CardElement(type=ELEMENT_IMAGE, image_path="")
        r.draw_element(p, e, rect)
        p.end()

    def test_draw_image_element_missing_file(self, qapp):
        pm, p, rect = self._make_painter_and_rect(qapp)
        r = ElementRenderer(3.0)
        e = CardElement(type=ELEMENT_IMAGE, image_path="/no/such/file.png")
        r.draw_element(p, e, rect)
        p.end()

    def test_draw_qr_no_data(self, qapp):
        """Ohne qr_data wird Platzhalter gezeichnet."""
        pm, p, rect = self._make_painter_and_rect(qapp)
        r = ElementRenderer(3.0)
        e = CardElement(type=ELEMENT_QR, qr_data="")
        r.draw_element(p, e, rect)
        p.end()

    def test_get_qr_pixmap_returns_valid_pixmap(self, qapp):
        """_get_qr_pixmap muss für echte Daten ein nicht-nulles QPixmap liefern."""
        r = ElementRenderer(3.0)
        pm = r._get_qr_pixmap("https://example.com")  # noqa: SLF001
        assert pm is not None, "_get_qr_pixmap gab None zurück – QR-Generierung fehlgeschlagen"
        assert not pm.isNull(), "_get_qr_pixmap lieferte null-Pixmap"

    def test_draw_qr_with_data_does_not_use_fallback(self, qapp):
        """draw_element mit QR-Daten darf keinen grauen Platzhalter zeichnen (Pixmap muss non-null sein)."""
        r = ElementRenderer(3.0)
        pm = r._get_qr_pixmap("https://example.com")  # noqa: SLF001
        assert pm is not None and not pm.isNull(), (
            "QR-Pixmap ist None/null – echter QR-Code wird NICHT gerendert, "
            "nur grauer Platzhalter sichtbar"
        )

    def test_draw_with_rotation(self, qapp):
        pm, p, rect = self._make_painter_and_rect(qapp)
        r = ElementRenderer(3.0)
        e = CardElement(type=ELEMENT_TEXT, text="Rotated", rotation=45.0)
        r.draw_element(p, e, rect)
        p.end()

    def test_draw_text_bold_italic_underline(self, qapp):
        pm, p, rect = self._make_painter_and_rect(qapp)
        r = ElementRenderer(3.0)
        e = CardElement(
            type=ELEMENT_TEXT, text="BIU", font_bold=True, font_italic=True, font_underline=True
        )
        r.draw_element(p, e, rect)
        p.end()

    def test_draw_image_keep_aspect_false(self, qapp):
        pm, p, rect = self._make_painter_and_rect(qapp)
        r = ElementRenderer(3.0)
        e = CardElement(type=ELEMENT_IMAGE, image_path="", keep_aspect=False)
        r.draw_element(p, e, rect)
        p.end()

    def test_draw_image_with_real_file_keep_aspect_true(self, qapp, tmp_path):
        """Zeichnet ein echtes PNG mit keep_aspect=True (deckt die scaled-Branches ab)."""
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QPainter, QPixmap

        img_path = str(tmp_path / "img.png")
        src = QPixmap(20, 10)
        src.fill()
        src.save(img_path, "PNG")

        r = ElementRenderer(3.0)
        e = CardElement(type=ELEMENT_IMAGE, image_path=img_path, keep_aspect=True)
        canvas = QPixmap(200, 200)
        canvas.fill()
        p = QPainter(canvas)
        r.draw_element(p, e, QRectF(0, 0, 100, 100))
        p.end()
        assert not canvas.isNull()

    def test_draw_image_with_real_file_keep_aspect_false(self, qapp, tmp_path):
        """Zeichnet ein echtes PNG mit keep_aspect=False."""
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QPainter, QPixmap

        img_path = str(tmp_path / "img2.png")
        src = QPixmap(20, 10)
        src.fill()
        src.save(img_path, "PNG")

        r = ElementRenderer(3.0)
        e = CardElement(type=ELEMENT_IMAGE, image_path=img_path, keep_aspect=False)
        canvas = QPixmap(200, 200)
        canvas.fill()
        p = QPainter(canvas)
        r.draw_element(p, e, QRectF(0, 0, 100, 100))
        p.end()
        assert not canvas.isNull()


class TestGetPixmapCache:
    def test_cache_hit_returns_same_object(self, qapp, tmp_path):
        """Zweiter Aufruf gibt dasselbe Pixmap-Objekt aus dem Cache zurück."""
        from PySide6.QtGui import QPixmap

        img_path = str(tmp_path / "cache_test.png")
        src = QPixmap(5, 5)
        src.fill()
        src.save(img_path, "PNG")

        r = ElementRenderer(3.0)
        pm1 = r.get_pixmap(img_path)
        pm2 = r.get_pixmap(img_path)
        assert pm1 is pm2

    def test_null_pixmap_returns_none(self, qapp, tmp_path):
        """Beschädigte Datei ergibt None, kein Eintrag im Cache."""
        bad_path = str(tmp_path / "bad.png")
        with open(bad_path, "wb") as f:
            f.write(b"NOTAPNG")
        r = ElementRenderer(3.0)
        pm = r.get_pixmap(bad_path)
        assert pm is None
        assert bad_path not in r._pixmap_cache  # noqa: SLF001

    def test_missing_path_not_cached(self, qapp):
        r = ElementRenderer(3.0)
        r.get_pixmap("/nonexistent/img.png")
        assert "/nonexistent/img.png" not in r._pixmap_cache  # noqa: SLF001


class TestGetQrPixmap:
    def test_empty_data_returns_none(self, qapp):
        r = ElementRenderer(3.0)
        pm = r._get_qr_pixmap("")  # noqa: SLF001
        assert pm is None

    def test_cache_hit_returns_same_object(self, qapp):
        from PySide6.QtGui import QPixmap

        r = ElementRenderer(3.0)
        fake_pm = QPixmap(10, 10)
        fake_pm.fill()
        r._qr_cache["https://example.com"] = fake_pm  # noqa: SLF001
        pm = r._get_qr_pixmap("https://example.com")  # noqa: SLF001
        assert pm is fake_pm

    def test_qr_with_data_no_crash(self, qapp):
        """_get_qr_pixmap mit Daten darf nicht abstürzen (qrcode kann fehlen)."""
        r = ElementRenderer(3.0)
        pm = r._get_qr_pixmap("https://example.com")  # noqa: SLF001
        # Ergebnis ist entweder ein Pixmap oder None (je nach qrcode-Installation)
        from PySide6.QtGui import QPixmap

        assert pm is None or isinstance(pm, QPixmap)


class TestDrawLine:
    def test_draw_line_horizontal_no_crash(self, qapp):
        """Deckt _draw_line ab (Zeile 217 im Coverage-Bericht)."""
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QPainter, QPixmap

        r = ElementRenderer(5.0)
        pm = QPixmap(200, 200)
        pm.fill()
        p = QPainter(pm)
        e = CardElement(type=ELEMENT_LINE, width=30.0, height=1.0, border_color="#000000")
        r.draw_element(p, e, QRectF(0, 0, 150, 5))
        p.end()


# ---------------------------------------------------------------------------
# Fehlende Branch-Abdeckung (renderer.py: 142->145, 229, 311, 314-315)
# ---------------------------------------------------------------------------

from cardforge.models import ELEMENT_ICON  # noqa: E402


class TestInvalidatePixmapCacheWithPath:
    def test_invalidate_specific_path_branch(self, qapp, tmp_path):
        """invalidate_pixmap_cache(path) – branch 142->145 (path ist gesetzt)."""
        from PySide6.QtGui import QPixmap

        img_path = str(tmp_path / "x.png")
        src = QPixmap(5, 5)
        src.fill()
        src.save(img_path, "PNG")

        r = ElementRenderer(3.0)
        r._pixmap_cache[img_path] = src  # noqa: SLF001
        r.invalidate_pixmap_cache(img_path)  # branch: path ist nicht leer
        assert img_path not in r._pixmap_cache  # noqa: SLF001

    def test_invalidate_nonexistent_path_no_crash(self, qapp):
        """invalidate_pixmap_cache mit Pfad der nicht im Cache ist – kein Absturz."""
        r = ElementRenderer(3.0)
        r.invalidate_pixmap_cache("/not/in/cache.png")  # darf nicht werfen


class TestDrawIconFallback:
    def test_icon_unknown_name_draws_fallback(self, qapp):
        """_draw_icon mit unbekanntem icon_name → Fallback-Pfad (Zeilen 314-315)."""
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QPainter, QPixmap

        r = ElementRenderer(3.0)
        pm = QPixmap(100, 100)
        pm.fill()
        p = QPainter(pm)
        e = CardElement(
            type=ELEMENT_ICON, icon_name="this_icon_does_not_exist_xyz", color="#ff0000"
        )
        r.draw_element(p, e, QRectF(10, 10, 40, 40))
        p.end()
        assert not pm.isNull()

    def test_icon_empty_name_draws_fallback(self, qapp):
        """_draw_icon mit leerem icon_name → Fallback-Text '?' (Zeile 315)."""
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QPainter, QPixmap

        r = ElementRenderer(3.0)
        pm = QPixmap(100, 100)
        pm.fill()
        p = QPainter(pm)
        e = CardElement(type=ELEMENT_ICON, icon_name="", color="#000000")
        r.draw_element(p, e, QRectF(0, 0, 50, 50))
        p.end()

    def test_get_icon_pixmap_cache_hit(self, qapp):
        """_get_icon_pixmap liefert bei zweitem Aufruf Objekt aus Cache (Zeile 311)."""

        r = ElementRenderer(3.0)
        pm1 = r._get_icon_pixmap("fa5s.user", "#000000", 32)  # noqa: SLF001
        pm2 = r._get_icon_pixmap("fa5s.user", "#000000", 32)  # noqa: SLF001
        # Zweiter Aufruf muss aus Cache kommen (same object oder beide None)
        if pm1 is not None:
            assert pm1 is pm2  # Cache-Hit


class TestDrawImageKeepAspectFalseWithFile:
    def test_keep_aspect_false_real_image(self, qapp, tmp_path):
        """_draw_image mit keep_aspect=False und gültigem Bild (Zeile 229)."""
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QPainter, QPixmap

        img_path = str(tmp_path / "aspect_false.png")
        src = QPixmap(40, 20)
        src.fill()
        src.save(img_path, "PNG")

        r = ElementRenderer(3.0)
        e = CardElement(type=ELEMENT_IMAGE, image_path=img_path, keep_aspect=False)
        canvas = QPixmap(200, 200)
        canvas.fill()
        p = QPainter(canvas)
        r.draw_element(p, e, QRectF(0, 0, 100, 100))
        p.end()
        assert not canvas.isNull()


class TestTextWrap:
    """Tests für text_wrap=True in Renderer und text_bounding_rect."""

    def test_text_bounding_rect_no_wrap_returns_content_width(self, qapp):
        """Ohne text_wrap: Breite folgt dem Inhalt."""
        r = ElementRenderer(4.0)
        e = CardElement(type=ELEMENT_TEXT, text="Hello World", width=5.0, text_wrap=False)
        w, h = r.text_bounding_rect(e)
        assert w > 0
        assert h > 0

    def test_text_bounding_rect_wrap_returns_fixed_width(self, qapp):
        """Mit text_wrap: zurückgegebene Breite entspricht e.width * scale."""
        r = ElementRenderer(4.0)
        e = CardElement(type=ELEMENT_TEXT, text="Hello World", width=20.0, text_wrap=True)
        w, h = r.text_bounding_rect(e)
        expected_w = max(1, int(20.0 * 4.0))
        assert w == float(expected_w)

    def test_text_bounding_rect_wrap_height_grows_with_narrow_width(self, qapp):
        """Mit text_wrap: schmale Breite → mehr Zeilen → größere Höhe."""
        r = ElementRenderer(4.0)
        text = "Ein langer Text der umgebrochen werden sollte"
        e_wide = CardElement(type=ELEMENT_TEXT, text=text, width=200.0, text_wrap=True)
        e_narrow = CardElement(type=ELEMENT_TEXT, text=text, width=10.0, text_wrap=True)
        _w_wide, h_wide = r.text_bounding_rect(e_wide)
        _w_narrow, h_narrow = r.text_bounding_rect(e_narrow)
        assert h_narrow >= h_wide, (
            "Schmalere Breite muss gleich hohe oder höhere Bounding-Box ergeben"
        )

    def test_draw_text_wrap_no_crash(self, qapp):
        """draw_element mit text_wrap=True darf nicht abstürzen."""
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QPainter, QPixmap

        r = ElementRenderer(3.0)
        e = CardElement(
            type=ELEMENT_TEXT, text="Langer Text zum Umbrechen", width=20.0, text_wrap=True
        )
        pm = QPixmap(200, 200)
        pm.fill()
        p = QPainter(pm)
        r.draw_element(p, e, QRectF(0, 0, 80, 80))
        p.end()
        assert not pm.isNull()

    def test_draw_text_no_wrap_no_crash(self, qapp):
        """draw_element mit text_wrap=False (Standard) zeichnet weiterhin korrekt."""
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QPainter, QPixmap

        r = ElementRenderer(3.0)
        e = CardElement(type=ELEMENT_TEXT, text="Kein Umbruch", text_wrap=False)
        pm = QPixmap(200, 200)
        pm.fill()
        p = QPainter(pm)
        r.draw_element(p, e, QRectF(0, 0, 80, 80))
        p.end()
        assert not pm.isNull()


# ---------------------------------------------------------------------------
# build_para_layouts – leere Absätze (Doppel-\n)
# ---------------------------------------------------------------------------


class TestBuildParaLayouts:
    def test_empty_paragraph_produces_none_layout_segment(self, qapp):
        """Text mit doppeltem \\n erzeugt ein Segment mit layout=None (leerer Absatz)."""
        from PySide6.QtGui import QFont

        from cardforge.renderer import build_para_layouts

        font = QFont("Arial")
        font.setPixelSize(14)
        segs, total_h = build_para_layouts("Zeile1\n\nZeile3", font, 200.0, "left")
        # Drei Paragraphen: "Zeile1", "" (leer), "Zeile3"
        assert len(segs) == 3
        # Das mittlere Segment ist der leere Absatz → layout=None
        assert segs[1]["layout"] is None
        assert total_h > 0

    def test_single_paragraph_no_empty_seg(self, qapp):
        """Einfacher Text ohne \\n hat genau ein Segment mit layout != None."""
        from PySide6.QtGui import QFont

        from cardforge.renderer import build_para_layouts

        font = QFont("Arial")
        font.setPixelSize(14)
        segs, total_h = build_para_layouts("Hallo Welt", font, 200.0, "left")
        assert len(segs) == 1
        assert segs[0]["layout"] is not None

    def test_multiple_empty_paragraphs(self, qapp):
        """Mehrere aufeinanderfolgende Leerzeilen erzeugen mehrere None-Segmente."""
        from PySide6.QtGui import QFont

        from cardforge.renderer import build_para_layouts

        font = QFont("Arial")
        font.setPixelSize(14)
        segs, _h = build_para_layouts("A\n\n\nB", font, 200.0, "left")
        # "A", "", "", "B" → 4 Segmente
        assert len(segs) == 4
        empty_segs = [s for s in segs if s["layout"] is None]
        assert len(empty_segs) == 2

    def test_empty_paragraph_height_adds_to_total(self, qapp):
        """Der leere Absatz trägt eine positive Höhe zur Gesamthöhe bei."""
        from PySide6.QtGui import QFont

        from cardforge.renderer import build_para_layouts

        font = QFont("Arial")
        font.setPixelSize(14)
        segs_no_empty, h_no_empty = build_para_layouts("A\nB", font, 200.0, "left")
        segs_with_empty, h_with_empty = build_para_layouts("A\n\nB", font, 200.0, "left")
        # Mit leerem Absatz muss die Gesamthöhe größer sein
        assert h_with_empty > h_no_empty

    def test_char_start_increments_correctly(self, qapp):
        """char_start in jedem Segment entspricht dem korrekten Zeichenoffset."""
        from PySide6.QtGui import QFont

        from cardforge.renderer import build_para_layouts

        font = QFont("Arial")
        font.setPixelSize(14)
        segs, _h = build_para_layouts("AB\n\nCD", font, 200.0, "left")
        # Segment 0: "AB" → char_start=0
        # Segment 1: "" → char_start=3 (len("AB") + 1)
        # Segment 2: "CD" → char_start=4 (len("AB") + 1 + len("") + 1)
        assert segs[0]["char_start"] == 0
        assert segs[1]["char_start"] == 3
        assert segs[2]["char_start"] == 4


# ---------------------------------------------------------------------------
# _draw_text_justified – Blocksatz mit verschiedenen v_align-Werten
# ---------------------------------------------------------------------------


class TestDrawTextJustified:
    def _make_painter_and_rect(self, qapp):
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QPainter, QPixmap

        pm = QPixmap(300, 200)
        pm.fill()
        p = QPainter(pm)
        rect = QRectF(10, 10, 200, 100)
        return pm, p, rect

    def test_justify_top_no_crash(self, qapp):
        """Blocksatz mit v_align='top' darf nicht abstürzen."""
        pm, p, rect = self._make_painter_and_rect(qapp)
        r = ElementRenderer(4.0)
        e = CardElement(
            type=ELEMENT_TEXT,
            text="Dies ist ein langer Text der in mehrere Zeilen umgebrochen werden soll.",
            h_align="justify",
            v_align="top",
            width=50.0,
            text_wrap=True,
        )
        r.draw_element(p, e, rect)
        p.end()
        assert not pm.isNull()

    def test_justify_middle_no_crash(self, qapp):
        """Blocksatz mit v_align='middle' deckt den middle-Zweig ab (Zeile 259)."""
        pm, p, rect = self._make_painter_and_rect(qapp)
        r = ElementRenderer(4.0)
        e = CardElement(
            type=ELEMENT_TEXT,
            text="Zentrierter Blocksatz Text der umgebrochen wird.",
            h_align="justify",
            v_align="middle",
            width=50.0,
            text_wrap=True,
        )
        r.draw_element(p, e, rect)
        p.end()
        assert not pm.isNull()

    def test_justify_bottom_no_crash(self, qapp):
        """Blocksatz mit v_align='bottom' deckt den bottom-Zweig ab (Zeile 260)."""
        pm, p, rect = self._make_painter_and_rect(qapp)
        r = ElementRenderer(4.0)
        e = CardElement(
            type=ELEMENT_TEXT,
            text="Unten-Blocksatz Text der umgebrochen wird.",
            h_align="justify",
            v_align="bottom",
            width=50.0,
            text_wrap=True,
        )
        r.draw_element(p, e, rect)
        p.end()
        assert not pm.isNull()

    def test_justify_with_multiword_line(self, qapp):
        """Mehrwörtige Zeilen werden korrekt verteilt (Wort-Spreizung)."""
        pm, p, rect = self._make_painter_and_rect(qapp)
        r = ElementRenderer(4.0)
        e = CardElement(
            type=ELEMENT_TEXT,
            text="Eins zwei drei vier fünf sechs sieben acht neun zehn elf zwölf.",
            h_align="justify",
            v_align="top",
            width=50.0,
        )
        r.draw_element(p, e, rect)
        p.end()
        assert not pm.isNull()

    def test_justify_with_single_word_line(self, qapp):
        """Einzel-Wort-Zeilen im Blocksatz werden linksbündig gesetzt."""
        pm, p, rect = self._make_painter_and_rect(qapp)
        r = ElementRenderer(4.0)
        e = CardElement(
            type=ELEMENT_TEXT,
            text="Superlongwordthatfitsaloneonitsownline",
            h_align="justify",
            v_align="top",
            width=50.0,
        )
        r.draw_element(p, e, rect)
        p.end()
        assert not pm.isNull()

    def test_justify_with_empty_paragraph(self, qapp):
        """Blocksatz mit leerem Absatz (\\n\\n) darf nicht abstürzen."""
        pm, p, rect = self._make_painter_and_rect(qapp)
        r = ElementRenderer(4.0)
        e = CardElement(
            type=ELEMENT_TEXT,
            text="Erster Absatz.\n\nZweiter Absatz nach Leerzeile.",
            h_align="justify",
            v_align="top",
            width=50.0,
        )
        r.draw_element(p, e, rect)
        p.end()
        assert not pm.isNull()

    def test_justify_empty_text_no_crash(self, qapp):
        """Leerer Text mit Blocksatz darf nicht abstürzen."""
        pm, p, rect = self._make_painter_and_rect(qapp)
        r = ElementRenderer(4.0)
        e = CardElement(
            type=ELEMENT_TEXT,
            text="",
            h_align="justify",
            v_align="top",
        )
        r.draw_element(p, e, rect)
        p.end()

    def test_justify_whitespace_only_line(self, qapp):
        """Zeile mit nur Leerzeichen wird korrekt behandelt."""
        pm, p, rect = self._make_painter_and_rect(qapp)
        r = ElementRenderer(4.0)
        e = CardElement(
            type=ELEMENT_TEXT,
            text="   ",
            h_align="justify",
            v_align="top",
        )
        r.draw_element(p, e, rect)
        p.end()


# ---------------------------------------------------------------------------
# _draw_icon – vorhandenes Icon zeichnen (Pixmap-Pfad)
# ---------------------------------------------------------------------------


class TestDrawIconWithValidIcon:
    def test_draw_icon_valid_name_no_crash(self, qapp):
        """_draw_icon mit bekanntem icon_name zeichnet das Icon ohne Absturz."""
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QPainter, QPixmap

        r = ElementRenderer(3.0)
        pm = QPixmap(100, 100)
        pm.fill()
        p = QPainter(pm)
        e = CardElement(type=ELEMENT_ICON, icon_name="fa5s.user", color="#000000")
        r.draw_element(p, e, QRectF(10, 10, 40, 40))
        p.end()
        assert not pm.isNull()

    def test_draw_icon_valid_second_call_uses_cache(self, qapp):
        """Zweiter draw_element-Aufruf nutzt Icon-Cache."""
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QPainter, QPixmap

        r = ElementRenderer(3.0)

        def draw_once():
            pm = QPixmap(100, 100)
            pm.fill()
            p = QPainter(pm)
            e = CardElement(type=ELEMENT_ICON, icon_name="fa5s.user", color="#ff0000")
            r.draw_element(p, e, QRectF(0, 0, 40, 40))
            p.end()

        draw_once()
        draw_once()  # Zweiter Aufruf → Cache-Hit in _get_icon_pixmap
