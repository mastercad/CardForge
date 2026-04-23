"""Tests für cardforge.models – reine Python-Logik, kein Qt nötig."""

from __future__ import annotations

import json
import math

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
    PaperTemplate,
    Project,
    mm_to_pt,
    pt_to_mm,
)

# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


class TestUnitConversions:
    def test_mm_to_pt_known_value(self):
        # 1 mm = 72/25.4 pt ≈ 2.8346
        assert math.isclose(mm_to_pt(1.0), 72 / 25.4, rel_tol=1e-9)

    def test_pt_to_mm_known_value(self):
        assert math.isclose(pt_to_mm(1.0), 25.4 / 72, rel_tol=1e-9)

    def test_roundtrip_mm_pt(self):
        for mm in (0.0, 1.0, 10.0, 85.6, 297.0):
            assert math.isclose(pt_to_mm(mm_to_pt(mm)), mm, rel_tol=1e-9)

    def test_zero(self):
        assert mm_to_pt(0.0) == pytest.approx(0.0)
        assert pt_to_mm(0.0) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# CardElement
# ---------------------------------------------------------------------------


class TestCardElement:
    def test_defaults(self):
        e = CardElement()
        assert e.type == ELEMENT_TEXT
        assert e.x == 0.0
        assert e.y == 0.0
        assert e.width == 30.0
        assert e.height == 8.0
        assert e.rotation == 0.0
        assert e.locked is False
        assert e.visible is True
        assert e.z_order == 0
        assert e.color == "#000000"
        assert e.font_family == "Arial"

    def test_unique_ids(self):
        ids = {CardElement().id for _ in range(100)}
        assert len(ids) == 100

    def test_to_dict_roundtrip(self):
        e = CardElement(
            type=ELEMENT_TEXT,
            text="Hello",
            x=5.0,
            y=10.0,
            width=50.0,
            height=15.0,
            font_bold=True,
            rotation=45.0,
        )
        d = e.to_dict()
        e2 = CardElement.from_dict(d)
        assert e2.id == e.id
        assert e2.text == "Hello"
        assert e2.x == 5.0
        assert e2.y == 10.0
        assert e2.width == 50.0
        assert e2.height == 15.0
        assert e2.font_bold is True
        assert e2.rotation == 45.0

    def test_from_dict_partial(self):
        """from_dict mit partiellen Daten überschreibt nur gegebene Felder."""
        e = CardElement.from_dict({"type": ELEMENT_IMAGE, "x": 3.0})
        assert e.type == ELEMENT_IMAGE
        assert e.x == 3.0
        # unberührte Felder bleiben Defaults
        assert e.width == 30.0

    def test_all_element_types_preserved(self):
        for etype in (
            ELEMENT_TEXT,
            ELEMENT_IMAGE,
            ELEMENT_RECT,
            ELEMENT_ELLIPSE,
            ELEMENT_LINE,
            ELEMENT_QR,
        ):
            e = CardElement(type=etype)
            d = e.to_dict()
            e2 = CardElement.from_dict(d)
            assert e2.type == etype

    def test_color_field(self):
        e = CardElement(color="#ff0000")
        assert e.to_dict()["color"] == "#ff0000"

    def test_qr_data(self):
        e = CardElement(type=ELEMENT_QR, qr_data="https://example.com")
        assert CardElement.from_dict(e.to_dict()).qr_data == "https://example.com"

    def test_line_fields(self):
        e = CardElement(type=ELEMENT_LINE, line_x2=10.0, line_y2=5.0)
        e2 = CardElement.from_dict(e.to_dict())
        assert e2.line_x2 == 10.0
        assert e2.line_y2 == 5.0


# ---------------------------------------------------------------------------
# CardLayout
# ---------------------------------------------------------------------------


class TestCardLayout:
    def test_defaults(self):
        layout = CardLayout()
        assert layout.name == "Neue Karte"
        assert layout.front_elements == []
        assert layout.back_elements == []
        assert layout.front_bg == "#ffffff"
        assert layout.back_bg == "#ffffff"

    def test_unique_ids(self):
        ids = {CardLayout().id for _ in range(50)}
        assert len(ids) == 50

    def test_to_dict_empty(self):
        layout = CardLayout(name="Empty")
        d = layout.to_dict()
        assert d["name"] == "Empty"
        assert d["front_elements"] == []
        assert d["back_elements"] == []

    def test_from_dict_roundtrip_with_elements(self):
        layout = CardLayout(name="Testkarte", front_bg="#cccccc")
        layout.front_elements.append(CardElement(text="Vorne"))
        layout.back_elements.append(CardElement(text="Hinten", type=ELEMENT_RECT))

        d = layout.to_dict()
        layout2 = CardLayout.from_dict(d)
        assert layout2.id == layout.id
        assert layout2.name == "Testkarte"
        assert layout2.front_bg == "#cccccc"
        assert len(layout2.front_elements) == 1
        assert layout2.front_elements[0].text == "Vorne"
        assert len(layout2.back_elements) == 1
        assert layout2.back_elements[0].type == ELEMENT_RECT

    def test_from_dict_missing_keys(self):
        """from_dict toleriert fehlende optionale Schlüssel."""
        layout = CardLayout.from_dict({"name": "Minimal"})
        assert layout.name == "Minimal"
        assert layout.front_elements == []

    def test_background_colors_preserved(self):
        layout = CardLayout(front_bg="#111111", back_bg="#222222")
        layout2 = CardLayout.from_dict(layout.to_dict())
        assert layout2.front_bg == "#111111"
        assert layout2.back_bg == "#222222"


# ---------------------------------------------------------------------------
# PaperTemplate
# ---------------------------------------------------------------------------


class TestPaperTemplate:
    def test_defaults(self):
        pt = PaperTemplate()
        assert pt.paper_width == 210.0
        assert pt.paper_height == 297.0
        assert pt.card_width == 85.6
        assert pt.card_height == 54.0
        assert pt.cols == 2
        assert pt.rows == 5

    def test_auto_calc_a4(self):
        pt = PaperTemplate()  # A4 mit Standard-Rändern und Visitenkartenmaßen
        pt.auto_calc()
        # A4: usable_w ≈ 210 - 8 - 8 = 194 mm, card_w = 85.6, gap_h = 3 → cols = 2
        assert pt.cols == 2
        assert pt.rows >= 1

    def test_auto_calc_wide_card(self):
        pt = PaperTemplate(card_width=180.0, gap_h=0.0, margin_left=5.0, margin_right=5.0)
        pt.auto_calc()
        assert pt.cols == 1

    def test_auto_calc_minimum_one(self):
        pt = PaperTemplate(card_width=1000.0)  # Karte größer als Papier
        pt.auto_calc()
        assert pt.cols >= 1
        assert pt.rows >= 1

    def test_to_dict_roundtrip(self):
        pt = PaperTemplate(
            name="Custom",
            paper_width=148.0,
            paper_height=210.0,
            card_width=60.0,
            card_height=40.0,
            cols=2,
            rows=4,
        )
        pt2 = PaperTemplate.from_dict(pt.to_dict())
        assert pt2.name == "Custom"
        assert pt2.paper_width == 148.0
        assert pt2.cols == 2
        assert pt2.rows == 4

    def test_from_dict_partial(self):
        pt = PaperTemplate.from_dict({"cols": 3, "rows": 8})
        assert pt.cols == 3
        assert pt.rows == 8
        assert pt.paper_width == 210.0  # Default erhalten


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------


class TestProject:
    def test_defaults(self):
        p = Project()
        assert p.name == "Unbenanntes Projekt"
        assert p.cards == []
        assert isinstance(p.paper_template, PaperTemplate)
        assert len(p.color_palette) == 5

    def test_unique_ids(self):
        ids = {Project().id for _ in range(50)}
        assert len(ids) == 50

    def test_to_dict_roundtrip(self):
        p = Project(name="Mein Projekt")
        p.cards.append(CardLayout(name="Karte 1"))
        p.cards.append(CardLayout(name="Karte 2"))
        p.color_palette = ["#000000", "#ffffff"]

        d = p.to_dict()
        p2 = Project.from_dict(d)
        assert p2.name == "Mein Projekt"
        assert len(p2.cards) == 2
        assert p2.cards[0].name == "Karte 1"
        assert p2.color_palette == ["#000000", "#ffffff"]

    def test_save_and_load(self, tmp_path):
        p = Project(name="Speichertest")
        p.cards.append(CardLayout(name="SaveKarte"))
        p.cards[0].front_elements.append(CardElement(text="Gespeichert"))

        path = str(tmp_path / "test.vcprj")
        p.save(path)

        p2 = Project.load(path)
        assert p2.name == "Speichertest"
        assert p2.cards[0].name == "SaveKarte"
        assert p2.cards[0].front_elements[0].text == "Gespeichert"

    def test_save_creates_valid_json(self, tmp_path):
        p = Project(name="JSON-Test")
        path = str(tmp_path / "test.vcprj")
        p.save(path)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert data["name"] == "JSON-Test"

    def test_load_nonexistent_raises(self):
        with pytest.raises(FileNotFoundError):
            Project.load("/tmp/nonexistent_file_xyz.vcprj")

    def test_from_dict_empty(self):
        p = Project.from_dict({})
        assert isinstance(p, Project)
        assert p.cards == []

    def test_color_palette_preserved(self):
        palette = ["#aabbcc", "#ddeeff"]
        p = Project(color_palette=palette)
        p2 = Project.from_dict(p.to_dict())
        assert p2.color_palette == palette
