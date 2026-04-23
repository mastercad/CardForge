"""
Zentrale Zeichenlogik für CardForge.

Wird von ``canvas.py`` (interaktiver Editor) UND von ``print_preview.py``
(Druckvorschau) gemeinsam genutzt.  Damit ist sichergestellt, dass beide
Ansichten *exakt dieselben* Formeln, Maßstäbe und Konvertierungen verwenden.

Maßeinheiten-Konventionen (intern):
  - Elementkoordinaten / -größen: Millimeter (float)
  - Schriftgröße: typographische Punkte  (float)  →  1 pt = 25.4/72 mm
  - Linienstärke: typographische Punkte
  - QPainter-Zeichenbefehle: immer Pixel
  - scale_px_per_mm: Umrechnungsfaktor  mm → px

Gemeinsame Formel für Schriftgröße und Linienstärke:
    pixel = value_pt  ×  PT_TO_MM  ×  scale_px_per_mm
"""

from __future__ import annotations

import os

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPen,
    QPixmap,
)

from .icons import get_icon_pixmap
from .models import (
    ELEMENT_ELLIPSE,
    ELEMENT_ICON,
    ELEMENT_IMAGE,
    ELEMENT_LINE,
    ELEMENT_QR,
    ELEMENT_RECT,
    ELEMENT_TEXT,
    CardElement,
)

# ---------------------------------------------------------------------------
# Einheiten-Konstante (ein einziger Ort im gesamten Projekt)
# ---------------------------------------------------------------------------

PT_TO_MM: float = 25.4 / 72.0
"""Typographische Punkte in Millimeter: 1 pt = 25.4/72 mm ≈ 0.3528 mm"""


# ---------------------------------------------------------------------------
# Gemeinsame Multi-Paragraph-Layout-Funktion
# ---------------------------------------------------------------------------


def build_para_layouts(
    text: str,
    font: QFont,
    width: float,
    h_align: str = "left",
) -> tuple[list[dict], float]:
    """Baut pro \\n-Paragraph einen eigenen QTextLayout auf.

    QTextLayout verarbeitet kein \\n – deshalb wird der Text an \\n gesplittet
    und jeder Absatz bekommt seinen eigenen Layout-Pass.  Leere Absätze
    (Leerzeilen) reservieren genau eine Zeilenhöhe.

    Rückgabe:
        (segments, total_height)

    Jedes Segment ist ein dict::

        {
          'layout':     QTextLayout | None,   # None = leere Zeile
          'char_start': int,                   # abs. Char-Offset im Original-Text
          'y_top':      float,                 # y relativ zur Blockoberseite
          'height':     float,                 # Pixel-Höhe dieses Absatzes
        }
    """
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QFontMetrics, QTextLayout, QTextOption

    align_map = {
        "left": Qt.AlignmentFlag.AlignLeft,
        "center": Qt.AlignmentFlag.AlignHCenter,
        "right": Qt.AlignmentFlag.AlignRight,
        "justify": Qt.AlignmentFlag.AlignJustify,
    }
    paragraphs = text.split("\n")
    fm = QFontMetrics(font)
    empty_h = float(fm.height())
    segments: list[dict] = []
    y = 0.0
    char_start = 0
    for para in paragraphs:
        if para:
            layout = QTextLayout(para, font)
            opt = QTextOption()
            opt.setWrapMode(QTextOption.WrapMode.WordWrap)
            opt.setAlignment(align_map.get(h_align, Qt.AlignmentFlag.AlignLeft))
            layout.setTextOption(opt)
            layout.beginLayout()
            y_acc = 0.0
            while True:
                line = layout.createLine()
                if not line.isValid():
                    break
                line.setLineWidth(max(1.0, width))
                line.setPosition(QPointF(0.0, y_acc))
                y_acc += line.height()
            layout.endLayout()
            segments.append(
                {"layout": layout, "char_start": char_start, "y_top": y, "height": y_acc}
            )
            y += y_acc
        else:
            segments.append(
                {"layout": None, "char_start": char_start, "y_top": y, "height": empty_h}
            )
            y += empty_h
        char_start += len(para) + 1  # +1 für \n
    return segments, y


# ---------------------------------------------------------------------------
# ElementRenderer
# ---------------------------------------------------------------------------


class ElementRenderer:
    """
    Zeichnet einzelne ``CardElement``-Objekte auf einen QPainter.

    Instanziierung:
        renderer = ElementRenderer(scale_px_per_mm=3.0)

    Skalierung aktualisieren (z. B. nach Zoom-Änderung):
        renderer.set_scale(new_zoom)

    Element zeichnen (Rect ist bereits in Pixel, relativ zum Kartenursprung):
        renderer.draw_element(painter, element, rect_px)

    Hilfsmethoden:
        renderer.text_bounding_rect(element)  → (width_px, height_px)
        renderer.get_pixmap(path)             → QPixmap | None
    """

    def __init__(self, scale_px_per_mm: float):
        self._scale = scale_px_per_mm
        self._pixmap_cache: dict[str, QPixmap] = {}
        self._qr_cache: dict[str, QPixmap] = {}
        self._icon_cache: dict[str, QPixmap] = {}

    # ------------------------------------------------------------------
    # Konfiguration
    # ------------------------------------------------------------------

    def set_scale(self, scale_px_per_mm: float):
        self._scale = scale_px_per_mm

    # ------------------------------------------------------------------
    # Einheiten-Hilfsmethoden
    # ------------------------------------------------------------------

    def pt_to_px(self, pt: float) -> float:
        """Typographische Punkte → Pixel (DPI-unabhängig)."""
        return pt * PT_TO_MM * self._scale

    def mm_to_px(self, mm: float) -> float:
        """Millimeter → Pixel."""
        return mm * self._scale

    # ------------------------------------------------------------------
    # Cache-Verwaltung
    # ------------------------------------------------------------------

    def invalidate_pixmap_cache(self, path: str = ""):
        if path:
            self._pixmap_cache.pop(path, None)
        else:
            self._pixmap_cache.clear()

    def invalidate_qr_cache(self, data: str = ""):
        if data:
            self._qr_cache.pop(data, None)
        else:
            self._qr_cache.clear()

    def clear_all_caches(self):
        self._pixmap_cache.clear()
        self._qr_cache.clear()
        self._icon_cache.clear()

    # ------------------------------------------------------------------
    # Zentraler Dispatch
    # ------------------------------------------------------------------

    def draw_element(self, painter: QPainter, e: CardElement, r: QRectF):
        """
        Zeichnet *ein* Element auf den painter.
        ``r`` ist das Pixel-Rect des Elements (Ursprung = Kartenecke + Offset).
        """
        painter.save()
        if e.rotation != 0:
            painter.translate(r.center())
            painter.rotate(e.rotation)
            painter.translate(-r.center())

        if e.type == ELEMENT_TEXT:
            self._draw_text(painter, e, r)
        elif e.type == ELEMENT_IMAGE:
            self._draw_image(painter, e, r)
        elif e.type == ELEMENT_RECT:
            self._draw_rect(painter, e, r)
        elif e.type == ELEMENT_ELLIPSE:
            self._draw_ellipse(painter, e, r)
        elif e.type == ELEMENT_LINE:
            self._draw_line(painter, e, r)
        elif e.type == ELEMENT_QR:
            self._draw_qr(painter, e, r)
        elif e.type == ELEMENT_ICON:
            self._draw_icon(painter, e, r)

        painter.restore()

    # ------------------------------------------------------------------
    # Element-Zeichenroutinen
    # ------------------------------------------------------------------

    def _draw_text(self, painter: QPainter, e: CardElement, r: QRectF):
        px_size = max(1, int(e.font_size * PT_TO_MM * self._scale))
        font = QFont(e.font_family)
        font.setPixelSize(px_size)
        font.setBold(e.font_bold)
        font.setItalic(e.font_italic)
        font.setUnderline(e.font_underline)
        painter.setFont(font)
        painter.setPen(QColor(e.color))
        h_flags = {
            "left": Qt.AlignmentFlag.AlignLeft,
            "center": Qt.AlignmentFlag.AlignHCenter,
            "right": Qt.AlignmentFlag.AlignRight,
            "justify": Qt.AlignmentFlag.AlignJustify,
        }
        v_flags = {
            "top": Qt.AlignmentFlag.AlignTop,
            "middle": Qt.AlignmentFlag.AlignVCenter,
            "bottom": Qt.AlignmentFlag.AlignBottom,
        }
        flags = h_flags.get(e.h_align, Qt.AlignmentFlag.AlignLeft) | v_flags.get(
            e.v_align, Qt.AlignmentFlag.AlignTop
        )
        if e.text_wrap:
            flags |= Qt.TextFlag.TextWordWrap
        painter.setClipRect(r)
        # AlignJustify wird von QPainter::drawText() ignoriert → manuelle Wort-Spreizung
        if e.h_align == "justify":
            painter.setClipping(False)
            self._draw_text_justified(painter, e, r, font)
        else:
            painter.drawText(r, flags, e.text)
            painter.setClipping(False)

    def _draw_text_justified(self, painter: QPainter, e: CardElement, r: QRectF, font: QFont):
        """Blocksatz durch manuelle Wort-Spreizung pro Zeile.

        Qt bietet keine zuverlässige native API für Blocksatz-Rendering.
        Daher wird jede Nicht-Letzte-Zeile eines Absatzes manuell gesetzt:
        Die Wörter werden gleichmäßig auf die volle Breite verteilt.
        Die letzte Zeile jedes Absatzes bleibt linksbündig (standard Blocksatz).
        """
        # Zeilenstruktur aus QTextLayout (linksbündig, gleiche Umbrüche wie justify)
        segs, total_h = build_para_layouts(e.text, font, r.width(), "left")

        if e.v_align == "middle":
            y_off = r.top() + (r.height() - total_h) / 2
        elif e.v_align == "bottom":
            y_off = r.bottom() - total_h
        else:
            y_off = r.top()

        fm = QFontMetrics(font)

        painter.save()
        painter.setClipRect(r)
        painter.setFont(font)
        painter.setPen(QColor(e.color))

        for seg in segs:
            layout = seg["layout"]
            y_seg = y_off + seg["y_top"]
            if layout is None:
                continue

            para_text = layout.text()
            n_lines = layout.lineCount()

            for i in range(n_lines):
                line = layout.lineAt(i)
                ls = line.textStart()
                ll = line.textLength()
                line_str = para_text[ls : ls + ll].rstrip()
                line_y = y_seg + line.position().y() + fm.ascent()

                if not line_str.strip():
                    painter.drawText(QPointF(r.left(), line_y), line_str)
                    continue

                words = line_str.split()
                if len(words) <= 1:
                    painter.drawText(QPointF(r.left(), line_y), line_str)
                    continue

                total_w = sum(fm.horizontalAdvance(w) for w in words)
                gap_w = (r.width() - total_w) / (len(words) - 1)

                x = r.left()
                for j, word in enumerate(words):
                    painter.drawText(QPointF(x, line_y), word)
                    if j < len(words) - 1:
                        x += fm.horizontalAdvance(word) + gap_w

        painter.setClipping(False)
        painter.restore()

    def _draw_image(self, painter: QPainter, e: CardElement, r: QRectF):
        pm = self.get_pixmap(e.image_path)
        if pm:
            if e.keep_aspect:
                scaled = pm.scaled(
                    int(r.width()),
                    int(r.height()),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                dx = (r.width() - scaled.width()) / 2
                dy = (r.height() - scaled.height()) / 2
                painter.drawPixmap(int(r.left() + dx), int(r.top() + dy), scaled)
            else:
                painter.drawPixmap(r.toRect(), pm)
        else:
            painter.fillRect(r, QColor("#e0e0e0"))
            painter.setPen(Qt.GlobalColor.darkGray)
            painter.drawText(r, Qt.AlignmentFlag.AlignCenter, "Bild")

    def _pen_px(self, pt: float) -> float:
        return pt * PT_TO_MM * self._scale

    def _draw_rect(self, painter: QPainter, e: CardElement, r: QRectF):
        painter.setBrush(QBrush(QColor(e.fill_color)))
        painter.setPen(QPen(QColor(e.border_color), self._pen_px(e.border_width)))
        painter.drawRect(r)

    def _draw_ellipse(self, painter: QPainter, e: CardElement, r: QRectF):
        painter.setBrush(QBrush(QColor(e.fill_color)))
        painter.setPen(QPen(QColor(e.border_color), self._pen_px(e.border_width)))
        painter.drawEllipse(r)

    def _draw_line(self, painter: QPainter, e: CardElement, r: QRectF):
        # Strichstärke = e.height in mm; Farbe = border_color
        pen_w = max(0.5, self.mm_to_px(e.height))
        painter.setPen(
            QPen(QColor(e.border_color), pen_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        )
        # r ist die exakte Bounding-Box. P1 = (e.x, e.y), P2 = (e.x+line_x2, e.y+line_y2).
        # P1 liegt bei (max(0,-line_x2), max(0,-line_y2)) * scale relativ zu r.topLeft().
        scale = self._scale
        p1 = QPointF(
            r.left() + max(0.0, -e.line_x2) * scale,
            r.top() + max(0.0, -e.line_y2) * scale,
        )
        p2 = QPointF(p1.x() + e.line_x2 * scale, p1.y() + e.line_y2 * scale)
        painter.drawLine(p1, p2)

    def _draw_qr(self, painter: QPainter, e: CardElement, r: QRectF):
        pm = self._get_qr_pixmap(e.qr_data)
        if pm:
            painter.drawPixmap(r.toRect(), pm)
        else:
            painter.fillRect(r, QColor("#f0f0f0"))
            painter.setPen(Qt.GlobalColor.darkGray)
            painter.drawText(r, Qt.AlignmentFlag.AlignCenter, "QR")

    def _draw_icon(self, painter: QPainter, e: CardElement, r: QRectF):
        size = max(1, int(max(r.width(), r.height())))
        pm = self._get_icon_pixmap(e.icon_name, e.color, size)
        if pm and not pm.isNull():
            # Icon zentriert ins Rect einfügen (Seitenverhältnis beibehalten)
            scaled = pm.scaled(
                int(r.width()),
                int(r.height()),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            dx = (r.width() - scaled.width()) / 2
            dy = (r.height() - scaled.height()) / 2
            painter.drawPixmap(int(r.left() + dx), int(r.top() + dy), scaled)
        else:
            painter.fillRect(r, QColor("#f0f0f0"))
            painter.setPen(Qt.GlobalColor.darkGray)
            painter.drawText(r, Qt.AlignmentFlag.AlignCenter, e.icon_name or "?")

    def _get_icon_pixmap(self, icon_name: str, color: str, size: int) -> QPixmap | None:
        cache_key = f"{icon_name}:{color}:{size}"
        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]
        pm = get_icon_pixmap(icon_name, color, size)
        if pm is not None:
            self._icon_cache[cache_key] = pm
        return pm

    # ------------------------------------------------------------------
    # Hilfsmethoden (öffentlich, für fit_to_content etc.)
    # ------------------------------------------------------------------

    def text_bounding_rect(self, e: CardElement) -> tuple[float, float]:
        """
        Gibt (width_px, height_px) der minimalen Bounding-Box für ``e.text``
        zurück.
        - text_wrap=False: Breite und Höhe folgen dem Inhalt (nur \\n-Umbrüche).
        - text_wrap=True:  Breite = e.width * scale (fixiert), Höhe = umgebrochener Inhalt.
        Verwendung: fit_to_content und _update_inline_size im Canvas.
        """
        px_size = max(1, int(e.font_size * PT_TO_MM * self._scale))
        font = QFont(e.font_family)
        font.setPixelSize(px_size)
        font.setBold(e.font_bold)
        font.setItalic(e.font_italic)
        fm = QFontMetrics(font)
        if e.text_wrap:
            wrap_w = max(1, int(e.width * self._scale))
            br = fm.boundingRect(
                0, 0, wrap_w, 99999, Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignLeft, e.text
            )
            return float(wrap_w), float(br.height())
        br = fm.boundingRect(
            0, 0, 99999, 99999, Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignLeft, e.text
        )
        return float(br.width()), float(br.height())

    def get_pixmap(self, path: str) -> QPixmap | None:
        if path in self._pixmap_cache:
            return self._pixmap_cache[path]
        if not path or not os.path.exists(path):
            return None
        pm = QPixmap(path)
        if pm.isNull():
            return None
        self._pixmap_cache[path] = pm
        return pm

    def _get_qr_pixmap(self, data: str) -> QPixmap | None:
        if data in self._qr_cache:
            return self._qr_cache[data]
        if not data:
            return None
        try:
            import io

            import qrcode

            img = qrcode.make(data)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            pm = QPixmap()
            pm.loadFromData(buf.getvalue())
            if pm.isNull():
                return None
            self._qr_cache[data] = pm
            return pm
        except Exception:
            return None
