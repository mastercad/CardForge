"""
Datenmodelle für CardForge.
Alle Maße intern in Millimetern (float), Konvertierung bei Bedarf.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def mm_to_pt(mm: float) -> float:
    return mm * 2.8346456692913385


def pt_to_mm(pt: float) -> float:
    return pt / 2.8346456692913385


# ---------------------------------------------------------------------------
# Element-Typen
# ---------------------------------------------------------------------------

ELEMENT_TEXT = "text"
ELEMENT_IMAGE = "image"
ELEMENT_RECT = "rect"
ELEMENT_ELLIPSE = "ellipse"
ELEMENT_LINE = "line"
ELEMENT_QR = "qr"
ELEMENT_ICON = "icon"


@dataclass
class CardElement:
    """Basis-Datensatz für ein Element auf der Visitenkarte."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = ELEMENT_TEXT  # text | image | rect | ellipse | line | qr | icon
    x: float = 0.0  # mm von links
    y: float = 0.0  # mm von oben
    width: float = 30.0  # mm
    height: float = 8.0  # mm
    rotation: float = 0.0  # Grad
    locked: bool = False
    visible: bool = True
    z_order: int = 0

    # Text-spezifisch
    text: str = ""
    font_family: str = "Arial"
    font_size: float = 10.0  # pt
    font_bold: bool = False
    font_italic: bool = False
    font_underline: bool = False
    color: str = "#000000"  # Vordergrundfarbe (Text / Strich)
    h_align: str = "left"  # left | center | right
    v_align: str = "top"  # top | middle | bottom
    text_wrap: bool = False  # Breite fixiert, Höhe folgt dem umgebrochenen Inhalt

    # Bild-spezifisch
    image_path: str = ""
    keep_aspect: bool = True

    # Form-spezifisch
    fill_color: str = "#ffffff"
    border_color: str = "#000000"
    border_width: float = 0.5  # pt
    line_x2: float = 0.0  # mm – nur für Linien (Endpunkt relativ zum Element)
    line_y2: float = 0.0

    # QR-spezifisch
    qr_data: str = ""

    # Icon-spezifisch
    icon_name: str = "phone"

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @staticmethod
    def from_dict(d: dict) -> CardElement:
        e = CardElement()
        e.__dict__.update(d)
        # Migration: alte Linien hatten width als Länge, line_x2/line_y2 == 0
        if e.type == ELEMENT_LINE and e.line_x2 == 0.0 and e.line_y2 == 0.0:
            e.line_x2 = e.width
            e.line_y2 = 0.0
        return e


# ---------------------------------------------------------------------------
# Kartenlayout (Vorder- und Rückseite einer Karte)
# ---------------------------------------------------------------------------


@dataclass
class CardLayout:
    """Ein einzelnes Kartenlayout (gehört zu einem Projekt)."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Neue Karte"
    front_elements: list[CardElement] = field(default_factory=list)
    back_elements: list[CardElement] = field(default_factory=list)
    # Hintergrundfarbe der Karte (Vorder-/Rückseite)
    front_bg: str = "#ffffff"
    back_bg: str = "#ffffff"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "front_bg": self.front_bg,
            "back_bg": self.back_bg,
            "front_elements": [e.to_dict() for e in self.front_elements],
            "back_elements": [e.to_dict() for e in self.back_elements],
        }

    @staticmethod
    def from_dict(d: dict) -> CardLayout:
        cl = CardLayout()
        cl.id = d.get("id", cl.id)
        cl.name = d.get("name", cl.name)
        cl.front_bg = d.get("front_bg", "#ffffff")
        cl.back_bg = d.get("back_bg", "#ffffff")
        cl.front_elements = [CardElement.from_dict(e) for e in d.get("front_elements", [])]
        cl.back_elements = [CardElement.from_dict(e) for e in d.get("back_elements", [])]
        return cl


# ---------------------------------------------------------------------------
# Papiervorlage
# ---------------------------------------------------------------------------


@dataclass
class PaperTemplate:
    """Beschreibt das Papier-/Stanzlayout für die Druckvorbereitung."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Neue Vorlage"
    # Papierformat in mm
    paper_width: float = 210.0
    paper_height: float = 297.0
    # Visitenkartenmaß in mm
    card_width: float = 85.6
    card_height: float = 54.0
    # Ränder in mm
    margin_top: float = 13.5
    margin_left: float = 8.0
    margin_right: float = 8.0
    margin_bottom: float = 13.5
    # Abstände zwischen Karten in mm
    gap_h: float = 3.0  # horizontal (zwischen Spalten)
    gap_v: float = 3.0  # vertikal   (zwischen Zeilen)
    # Anzahl Karten (wird automatisch berechnet, kann aber überschrieben werden)
    cols: int = 2
    rows: int = 5

    def auto_calc(self):
        """Berechnet cols/rows aus den Maßen (Fallback)."""
        usable_w = self.paper_width - self.margin_left - self.margin_right
        usable_h = self.paper_height - self.margin_top - self.margin_bottom
        self.cols = max(1, int((usable_w + self.gap_h) / (self.card_width + self.gap_h)))
        self.rows = max(1, int((usable_h + self.gap_v) / (self.card_height + self.gap_v)))

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @staticmethod
    def from_dict(d: dict) -> PaperTemplate:
        pt = PaperTemplate()
        pt.__dict__.update(d)
        return pt


# ---------------------------------------------------------------------------
# Projekt
# ---------------------------------------------------------------------------


@dataclass
class Project:
    """Root-Objekt: enthält Papiervorlage + alle Kartenlayouts."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Unbenanntes Projekt"
    paper_template: PaperTemplate = field(default_factory=PaperTemplate)
    cards: list[CardLayout] = field(default_factory=list)
    color_palette: list[str] = field(
        default_factory=lambda: ["#000000", "#ffffff", "#cccccc", "#1a1a2e", "#e94560"]
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "paper_template": self.paper_template.to_dict(),
            "cards": [c.to_dict() for c in self.cards],
            "color_palette": self.color_palette,
        }

    @staticmethod
    def from_dict(d: dict) -> Project:
        p = Project()
        p.id = d.get("id", p.id)
        p.name = d.get("name", p.name)
        p.paper_template = PaperTemplate.from_dict(d.get("paper_template", {}))
        p.cards = [CardLayout.from_dict(c) for c in d.get("cards", [])]
        p.color_palette = d.get("color_palette", p.color_palette)
        return p

    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @staticmethod
    def load(path: str) -> Project:
        with open(path, encoding="utf-8") as f:
            return Project.from_dict(json.load(f))
