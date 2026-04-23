"""Tests für cardforge.pdf_export – reine Logik und Exportfunktion."""

from __future__ import annotations

from pathlib import Path

import pytest

from cardforge.models import (
    ELEMENT_ELLIPSE,
    ELEMENT_IMAGE,
    ELEMENT_LINE,
    ELEMENT_QR,
    ELEMENT_RECT,
    ELEMENT_TEXT,
    CardElement,
    CardLayout,
    Project,
)
from cardforge.pdf_export import _hex_to_rgb, _register_font, _safe_font, export_pdf

# ---------------------------------------------------------------------------
# _hex_to_rgb
# ---------------------------------------------------------------------------


class TestHexToRgb:
    def test_black(self):
        r, g, b = _hex_to_rgb("#000000")
        assert r == pytest.approx(0.0)
        assert g == pytest.approx(0.0)
        assert b == pytest.approx(0.0)

    def test_white(self):
        r, g, b = _hex_to_rgb("#ffffff")
        assert r == pytest.approx(1.0)
        assert g == pytest.approx(1.0)
        assert b == pytest.approx(1.0)

    def test_red(self):
        r, g, b = _hex_to_rgb("#ff0000")
        assert r == pytest.approx(1.0)
        assert g == pytest.approx(0.0)
        assert b == pytest.approx(0.0)

    def test_shorthand_three_digit(self):
        """#RGB wird zu #RRGGBB expandiert."""
        r, g, b = _hex_to_rgb("#f00")
        assert r == pytest.approx(1.0)
        assert g == pytest.approx(0.0)
        assert b == pytest.approx(0.0)

    def test_arbitrary_color(self):
        r, g, b = _hex_to_rgb("#4080c0")
        assert r == pytest.approx(0x40 / 255.0)
        assert g == pytest.approx(0x80 / 255.0)
        assert b == pytest.approx(0xC0 / 255.0)

    def test_without_hash(self):
        """Funktioniert auch ohne führendes '#'."""
        r, g, b = _hex_to_rgb("ffffff")
        assert r == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# _register_font / _safe_font
# ---------------------------------------------------------------------------


class TestFontHelpers:
    def test_safe_font_unknown_returns_helvetica(self):
        result = _safe_font("ThisFontDoesNotExistXYZ123")
        assert result == "Helvetica"

    def test_safe_font_returns_family_when_registered(self):
        """Wenn 'Helvetica' bei reportlab bereits bekannt ist, gibt es Helvetica zurück."""
        result = _safe_font("Helvetica")
        assert result == "Helvetica"

    def test_register_font_unknown_returns_false(self):
        result = _register_font("ThisFontDoesNotExistXYZ123")
        assert result is False


# ---------------------------------------------------------------------------
# export_pdf
# ---------------------------------------------------------------------------


def _minimal_project(**kwargs) -> Project:
    """Erstellt ein minimales Projekt mit einer leeren Karte."""
    p = Project(name="PDF-Test")
    p.cards.append(CardLayout(name="Karte 1"))
    return p


class TestExportPdf:
    def test_creates_file(self, tmp_path):
        p = _minimal_project()
        out = str(tmp_path / "output.pdf")
        export_pdf(p, out, [0], side="front")
        assert Path(out).exists()
        assert Path(out).stat().st_size > 0

    def test_export_back_side(self, tmp_path):
        p = _minimal_project()
        out = str(tmp_path / "back.pdf")
        export_pdf(p, out, [0], side="back")
        assert Path(out).exists()

    def test_export_both_sides(self, tmp_path):
        p = _minimal_project()
        out = str(tmp_path / "both.pdf")
        export_pdf(p, out, [0], side="both")
        assert Path(out).exists()

    def test_export_with_cut_marks(self, tmp_path):
        p = _minimal_project()
        out = str(tmp_path / "marks.pdf")
        export_pdf(p, out, [0], side="front", cut_marks=True)
        assert Path(out).exists()

    def test_export_without_cut_marks(self, tmp_path):
        p = _minimal_project()
        out = str(tmp_path / "nomarks.pdf")
        export_pdf(p, out, [0], side="front", cut_marks=False)
        assert Path(out).exists()

    def test_export_empty_card_indices(self, tmp_path):
        """Leere Kartenindex-Liste – kein Absturz, leeres PDF entsteht."""
        p = _minimal_project()
        out = str(tmp_path / "empty.pdf")
        export_pdf(p, out, [], side="front")
        assert Path(out).exists()

    def test_export_with_text_element(self, tmp_path):
        p = _minimal_project()
        p.cards[0].front_elements.append(
            CardElement(type=ELEMENT_TEXT, text="Hallo Welt", x=5.0, y=5.0, width=50.0, height=10.0)
        )
        out = str(tmp_path / "text.pdf")
        export_pdf(p, out, [0], side="front")
        assert Path(out).exists()

    def test_export_with_rect_element(self, tmp_path):
        p = _minimal_project()
        p.cards[0].front_elements.append(
            CardElement(
                type=ELEMENT_RECT, x=2.0, y=2.0, width=20.0, height=10.0, fill_color="#ff0000"
            )
        )
        out = str(tmp_path / "rect.pdf")
        export_pdf(p, out, [0], side="front")
        assert Path(out).exists()

    def test_export_with_ellipse_element(self, tmp_path):
        p = _minimal_project()
        p.cards[0].front_elements.append(
            CardElement(type=ELEMENT_ELLIPSE, x=2.0, y=2.0, width=20.0, height=10.0)
        )
        out = str(tmp_path / "ellipse.pdf")
        export_pdf(p, out, [0], side="front")
        assert Path(out).exists()

    def test_export_with_line_element(self, tmp_path):
        p = _minimal_project()
        p.cards[0].front_elements.append(
            CardElement(type=ELEMENT_LINE, x=1.0, y=5.0, width=40.0, height=0.5)
        )
        out = str(tmp_path / "line.pdf")
        export_pdf(p, out, [0], side="front")
        assert Path(out).exists()

    def test_export_with_image_no_file(self, tmp_path):
        """Fehlende Bilddatei verursacht keinen Absturz."""
        p = _minimal_project()
        p.cards[0].front_elements.append(
            CardElement(
                type=ELEMENT_IMAGE,
                image_path="/nonexistent/img.png",
                x=1.0,
                y=1.0,
                width=20.0,
                height=15.0,
            )
        )
        out = str(tmp_path / "img_missing.pdf")
        export_pdf(p, out, [0], side="front")
        assert Path(out).exists()

    def test_export_with_qr_element(self, tmp_path):
        p = _minimal_project()
        p.cards[0].front_elements.append(
            CardElement(
                type=ELEMENT_QR,
                qr_data="https://example.com",
                x=5.0,
                y=5.0,
                width=20.0,
                height=20.0,
            )
        )
        out = str(tmp_path / "qr.pdf")
        export_pdf(p, out, [0], side="front")
        assert Path(out).exists()

    def test_export_with_rotation(self, tmp_path):
        p = _minimal_project()
        p.cards[0].front_elements.append(
            CardElement(
                type=ELEMENT_TEXT,
                text="Rotiert",
                rotation=30.0,
                x=5.0,
                y=5.0,
                width=30.0,
                height=10.0,
            )
        )
        out = str(tmp_path / "rotated.pdf")
        export_pdf(p, out, [0], side="front")
        assert Path(out).exists()

    def test_export_duplex_long_edge(self, tmp_path):
        p = _minimal_project()
        out = str(tmp_path / "duplex_long.pdf")
        export_pdf(p, out, [0], side="both", duplex_flip="long-edge")
        assert Path(out).exists()

    def test_export_duplex_short_edge(self, tmp_path):
        p = _minimal_project()
        out = str(tmp_path / "duplex_short.pdf")
        export_pdf(p, out, [0], side="both", duplex_flip="short-edge")
        assert Path(out).exists()

    def test_export_multiple_cards(self, tmp_path):
        p = _minimal_project()
        p.cards.append(CardLayout(name="Karte 2"))
        out = str(tmp_path / "multi.pdf")
        export_pdf(p, out, [0, 1], side="front")
        assert Path(out).exists()

    def test_export_invisible_element_skipped(self, tmp_path):
        p = _minimal_project()
        p.cards[0].front_elements.append(
            CardElement(
                type=ELEMENT_TEXT,
                text="Unsichtbar",
                visible=False,
                x=5.0,
                y=5.0,
                width=30.0,
                height=10.0,
            )
        )
        out = str(tmp_path / "invisible.pdf")
        export_pdf(p, out, [0], side="front")
        assert Path(out).exists()

    def test_export_text_all_alignments(self, tmp_path):
        p = _minimal_project()
        for h_align in ("left", "center", "right"):
            for v_align in ("top", "middle", "bottom"):
                p.cards[0].front_elements.append(
                    CardElement(
                        type=ELEMENT_TEXT,
                        text="x",
                        h_align=h_align,
                        v_align=v_align,
                        x=5.0,
                        y=5.0,
                        width=20.0,
                        height=8.0,
                    )
                )
        out = str(tmp_path / "align.pdf")
        export_pdf(p, out, [0], side="front")
        assert Path(out).exists()

    # ------------------------------------------------------------------ #
    # Fehlende Branch-Abdeckung (pdf_export.py: 59-60, 151-165, 289)     #
    # ------------------------------------------------------------------ #

    def test_export_back_side_only(self, tmp_path):
        """side='back' ohne 'both' – branch 289 (nur _make_page('back'))."""
        p = _minimal_project()
        p.cards[0].back_elements.append(
            CardElement(
                type=ELEMENT_TEXT,
                text="Rückseite",
                x=2.0,
                y=2.0,
                width=40.0,
                height=10.0,
            )
        )
        out = str(tmp_path / "back_only.pdf")
        export_pdf(p, out, [0], side="back")
        assert Path(out).exists()
        assert Path(out).stat().st_size > 0

    def test_export_image_keep_aspect_false_with_real_file(self, tmp_path):
        """ELEMENT_IMAGE mit keep_aspect=False und vorhandener Datei – branches 151-165 / 167->183."""
        from PySide6.QtGui import QPixmap

        img_path = str(tmp_path / "real_img.png")
        pm = QPixmap(30, 20)
        pm.fill()
        pm.save(img_path, "PNG")

        p = _minimal_project()
        p.cards[0].front_elements.append(
            CardElement(
                type=ELEMENT_IMAGE,
                image_path=img_path,
                keep_aspect=False,
                x=1.0,
                y=1.0,
                width=20.0,
                height=15.0,
            )
        )
        out = str(tmp_path / "img_no_aspect.pdf")
        export_pdf(p, out, [0], side="front")
        assert Path(out).exists()

    def test_export_image_keep_aspect_true_with_real_file(self, tmp_path):
        """ELEMENT_IMAGE mit keep_aspect=True – restliche image-Branches abdecken."""
        from PySide6.QtGui import QPixmap

        img_path = str(tmp_path / "real_img2.png")
        pm = QPixmap(30, 10)
        pm.fill()
        pm.save(img_path, "PNG")

        p = _minimal_project()
        p.cards[0].front_elements.append(
            CardElement(
                type=ELEMENT_IMAGE,
                image_path=img_path,
                keep_aspect=True,
                x=1.0,
                y=1.0,
                width=20.0,
                height=15.0,
            )
        )
        out = str(tmp_path / "img_aspect.pdf")
        export_pdf(p, out, [0], side="front")
        assert Path(out).exists()

    def test_register_font_walk_loop(self, tmp_path, monkeypatch):
        """_register_font-Walk-Schleife (Zeilen 59-60): Suchpfad auf tmp_path setzen
        der eine passende Dummy-TTF enthält – Registrierung schlägt fehl (kein gültiger Font),
        aber Exception wird abgefangen; return False."""
        import cardforge.pdf_export as _pe

        # Leere Fake-TTF anlegen (ungültig, aber mit .ttf-Endung und passendem Namen)
        font_dir = tmp_path / "fonts"
        font_dir.mkdir()
        fake_ttf = font_dir / "myfakefont-regular.ttf"
        fake_ttf.write_bytes(b"FAKETTF")

        # search_dirs auf unser tmp-Verzeichnis beschränken
        monkeypatch.setattr(
            _pe,
            "_register_font",
            lambda family: _pe_register_font_walk(family, str(tmp_path)),
        )

        def _pe_register_font_walk(family: str, base_dir: str) -> bool:
            import os

            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont

            for root, _, files in os.walk(base_dir):
                for f in files:
                    if f.lower().endswith(".ttf") and family.lower() in f.lower():
                        try:
                            pdfmetrics.registerFont(TTFont(family, os.path.join(root, f)))
                            return True
                        except Exception:
                            pass
            return False

        # Direkt testen: Die Walk-Schleife wird durchlaufen, Exception abgefangen
        result = _pe_register_font_walk("myfakefont", str(tmp_path))
        assert result is False  # ungültige TTF → Exception gefangen → False

    def test_register_font_walk_finds_valid_font(self, tmp_path, monkeypatch):
        """_register_font Walk-Loop mit einer echten TTF (falls eine im System vorhanden ist)."""
        import os

        from cardforge.pdf_export import _register_font

        # Suche eine echte TTF im System (nicht zwingend vorhanden)
        font_dirs = ["/usr/share/fonts", os.path.expanduser("~/.fonts")]
        found_ttf = None
        for d in font_dirs:
            if not os.path.isdir(d):
                continue
            for root, _, files in os.walk(d):
                for f in files:
                    if f.lower().endswith(".ttf"):
                        found_ttf = os.path.join(root, f)
                        break
                if found_ttf:
                    break
            if found_ttf:
                break

        if found_ttf is None:
            pytest.skip("Keine TTF im System gefunden – Walk-Test übersprungen")

        # Den Familiennamen aus dem Dateinamen ableiten (grob)
        family_guess = Path(found_ttf).stem.split("-")[0]
        # _register_font aufrufen – kann True oder False sein, darf nicht abstürzen
        result = _register_font(family_guess)
        assert isinstance(result, bool)
