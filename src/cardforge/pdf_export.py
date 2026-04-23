"""
PDF-Export und Druckvorbereitung.
"""

from __future__ import annotations

import os

from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdf_canvas

from .models import (
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


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return r / 255.0, g / 255.0, b / 255.0


def _register_font(family: str):
    """Versucht eine TTF-Schriftart zu registrieren (best-effort)."""
    try:
        pdfmetrics.getFont(family)
        return True
    except Exception:
        pass
    # Suche auf gängigen Pfaden
    search_dirs = [
        "/usr/share/fonts",
        "/usr/local/share/fonts",
        os.path.expanduser("~/.fonts"),
        "C:/Windows/Fonts",
        "/Library/Fonts",
        os.path.expanduser("~/Library/Fonts"),
    ]
    for d in search_dirs:
        for root, _, files in os.walk(d):
            for f in files:
                if f.lower().endswith(".ttf") and family.lower() in f.lower():
                    try:
                        pdfmetrics.registerFont(TTFont(family, os.path.join(root, f)))
                        return True
                    except Exception:
                        pass
    return False


def _safe_font(family: str) -> str:
    if _register_font(family):
        return family
    return "Helvetica"


def _draw_element(c: pdf_canvas.Canvas, elem: CardElement, ox: float, oy: float, card_h_mm: float):
    """
    Zeichnet ein Element auf den PDF-Canvas.
    ox/oy: Offset des Kartenursprungs in mm (von unten-links des Blattes).
    card_h_mm: Kartenhöhe in mm (für Y-Spiegelung, da PDF-Koordinaten unten-links).
    """
    # PDF-Koordinaten: Y von unten, Canvas-Koordinaten: Y von oben
    x_mm = ox + elem.x
    y_mm = oy + (card_h_mm - elem.y - elem.height)
    w_mm = elem.width
    h_mm = elem.height

    x_pt = x_mm * mm
    y_pt = y_mm * mm
    w_pt = w_mm * mm
    h_pt = h_mm * mm

    c.saveState()
    if elem.rotation != 0:
        cx = x_pt + w_pt / 2
        cy = y_pt + h_pt / 2
        c.translate(cx, cy)
        c.rotate(-elem.rotation)
        c.translate(-cx, -cy)

    if elem.type == ELEMENT_RECT:
        r, g, b = _hex_to_rgb(elem.fill_color)
        c.setFillColorRGB(r, g, b)
        br, bg, bb = _hex_to_rgb(elem.border_color)
        c.setStrokeColorRGB(br, bg, bb)
        c.setLineWidth(elem.border_width)
        c.rect(x_pt, y_pt, w_pt, h_pt, stroke=1, fill=1)

    elif elem.type == ELEMENT_ELLIPSE:
        r, g, b = _hex_to_rgb(elem.fill_color)
        c.setFillColorRGB(r, g, b)
        br, bg, bb = _hex_to_rgb(elem.border_color)
        c.setStrokeColorRGB(br, bg, bb)
        c.setLineWidth(elem.border_width)
        c.ellipse(x_pt, y_pt, x_pt + w_pt, y_pt + h_pt, stroke=1, fill=1)

    elif elem.type == ELEMENT_LINE:
        br, bg, bb = _hex_to_rgb(elem.border_color)
        c.setStrokeColorRGB(br, bg, bb)
        c.setLineWidth(elem.border_width)
        # Startpunkt (e.x, e.y) und Endpunkt (e.x+line_x2, e.y+line_y2) in mm
        # PDF: Y von unten → card_h_mm - y
        lx1 = (ox + elem.x) * mm
        ly1 = (oy + card_h_mm - elem.y) * mm
        lx2 = (ox + elem.x + elem.line_x2) * mm
        ly2 = (oy + card_h_mm - elem.y - elem.line_y2) * mm
        c.line(lx1, ly1, lx2, ly2)

    elif elem.type == ELEMENT_TEXT:
        font_name = _safe_font(elem.font_family)
        r, g, b = _hex_to_rgb(elem.color)
        c.setFillColorRGB(r, g, b)
        # Schriftgröße in pt
        fs = elem.font_size
        c.setFont(font_name, fs)
        # Mehrzeiliger Text
        lines = elem.text.split("\n")
        line_h = fs * 1.2
        total_h = len(lines) * line_h
        if elem.v_align == "middle":
            text_y = y_pt + h_pt / 2 + total_h / 2 - line_h
        elif elem.v_align == "bottom":
            text_y = y_pt + line_h
        else:
            text_y = y_pt + h_pt - line_h
        for line in lines:
            if elem.h_align == "center":
                c.drawCentredString(x_pt + w_pt / 2, text_y, line)
            elif elem.h_align == "right":
                c.drawRightString(x_pt + w_pt, text_y, line)
            else:
                c.drawString(x_pt, text_y, line)
            text_y -= line_h

    elif elem.type == ELEMENT_IMAGE:
        if elem.image_path and os.path.exists(elem.image_path):
            try:
                img = ImageReader(elem.image_path)
                if elem.keep_aspect:
                    iw, ih = img.getSize()
                    ratio = min(w_pt / iw, h_pt / ih)
                    dw, dh = iw * ratio, ih * ratio
                    dx = (w_pt - dw) / 2
                    dy = (h_pt - dh) / 2
                    c.drawImage(
                        img, x_pt + dx, y_pt + dy, dw, dh, preserveAspectRatio=True, mask="auto"
                    )
                else:
                    c.drawImage(img, x_pt, y_pt, w_pt, h_pt, mask="auto")
            except Exception:
                pass

    elif elem.type == ELEMENT_QR:
        if elem.qr_data:
            try:
                import io

                import qrcode

                qr_img = qrcode.make(elem.qr_data)
                buf = io.BytesIO()
                qr_img.save(buf, format="PNG")
                buf.seek(0)
                ir = ImageReader(buf)
                c.drawImage(ir, x_pt, y_pt, w_pt, h_pt, mask="auto")
            except Exception:
                pass

    c.restoreState()


def _draw_card_to_canvas(
    c: pdf_canvas.Canvas,
    layout: CardLayout,
    side: str,
    ox_mm: float,
    oy_mm: float,
    card_w_mm: float,
    card_h_mm: float,
    bg_color: str = "#ffffff",
):
    """Zeichnet eine einzelne Karte (Vorder- oder Rückseite) auf den PDF-Canvas."""
    x_pt = ox_mm * mm
    y_pt = oy_mm * mm
    w_pt = card_w_mm * mm
    h_pt = card_h_mm * mm

    # Hintergrundfarbe
    r, g, b = _hex_to_rgb(bg_color)
    c.saveState()
    c.setFillColorRGB(r, g, b)
    c.rect(x_pt, y_pt, w_pt, h_pt, stroke=0, fill=1)
    c.restoreState()

    elems = sorted(
        (layout.front_elements if side == "front" else layout.back_elements),
        key=lambda e: e.z_order,
    )
    for elem in elems:
        if elem.visible:
            _draw_element(c, elem, ox_mm, oy_mm, card_h_mm)


def _draw_cut_marks(
    c: pdf_canvas.Canvas,
    ox_mm: float,
    oy_mm: float,
    w_mm: float,
    h_mm: float,
    bleed_mm: float = 3.0,
):
    """Zeichnet Schnittmarken um eine Karte."""
    x = ox_mm * mm
    y = oy_mm * mm
    w = w_mm * mm
    h = h_mm * mm
    bl = bleed_mm * mm
    mark = 5 * mm
    c.saveState()
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(0.25)
    # Ecken: links-unten, rechts-unten, rechts-oben, links-oben
    for cx, cy in [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]:
        dx = -1 if cx == x else 1
        dy = -1 if cy == y else 1
        c.line(cx + dx * bl, cy, cx + dx * (bl + mark), cy)
        c.line(cx, cy + dy * bl, cx, cy + dy * (bl + mark))
    c.restoreState()


def export_pdf(
    project: Project,
    output_path: str,
    card_indices: list[int],  # Indizes in project.cards
    side: str = "both",  # "front" | "back" | "both"
    cut_marks: bool = True,
    duplex_flip: str = "long-edge",  # "long-edge" | "short-edge"
):
    """Exportiert Visitenkarten als druckfertiges PDF.

    Bei side="both" wird die Rückseite so gespiegelt, dass sie bei Duplex-Druck
    korrekt hinter der Vorderseite liegt:
      long-edge  (Hochformat-Standard): Spalten werden gespiegelt (links↔rechts)
      short-edge (Querformat-Standard): Zeilen werden gespiegelt (oben↔unten)
    """
    pt = project.paper_template
    pw = pt.paper_width * mm
    ph = pt.paper_height * mm

    c = pdf_canvas.Canvas(output_path, pagesize=(pw, ph))

    def _card_index_for_slot(row: int, col: int, is_back_duplex: bool) -> int:
        """Gibt den card_indices-Index für einen Slot zurück.

        Für die Rückseite im Duplex-Modus wird der gegenüberliegende Slot
        (gespiegelt) abgefragt, damit Vorder- und Rückseite physisch übereinander
        liegen.
        """
        if is_back_duplex:
            if duplex_flip == "long-edge":
                col = pt.cols - 1 - col
            else:  # short-edge
                row = pt.rows - 1 - row
        slot_idx = row * pt.cols + col
        return card_indices[slot_idx % len(card_indices)]

    def _make_page(current_side: str, is_back_duplex: bool = False):
        """Erstellt eine Seite (alle Karten-Slots) für die gegebene Seite."""
        if not card_indices:
            return
        for row in range(pt.rows):
            for col in range(pt.cols):
                ci = _card_index_for_slot(row, col, is_back_duplex)
                if ci >= len(project.cards):
                    continue
                layout = project.cards[ci]

                ox = pt.margin_left + col * (pt.card_width + pt.gap_h)
                # PDF Y von unten
                oy_from_top = pt.margin_top + row * (pt.card_height + pt.gap_v)
                oy = pt.paper_height - oy_from_top - pt.card_height

                bg = layout.front_bg if current_side == "front" else layout.back_bg
                _draw_card_to_canvas(
                    c, layout, current_side, ox, oy, pt.card_width, pt.card_height, bg
                )
                if cut_marks:
                    _draw_cut_marks(c, ox, oy, pt.card_width, pt.card_height)

        c.showPage()

    if side in ("front", "both"):
        _make_page("front", is_back_duplex=False)
    if side in ("back", "both"):
        _make_page("back", is_back_duplex=(side == "both"))

    c.save()
