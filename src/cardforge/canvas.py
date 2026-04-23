"""
Canvas-Widget für den Karten-Layout-Editor.
Zeigt eine Visitenkarte (Vorder- oder Rückseite) und erlaubt
das interaktive Bearbeiten von Elementen (Text, Bild, Form, QR).
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPointF, QRectF, QSize, QSizeF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import QApplication, QMenu, QSizePolicy, QWidget

from .models import (
    ELEMENT_IMAGE,
    ELEMENT_LINE,
    ELEMENT_QR,
    ELEMENT_TEXT,
    CardElement,
    CardLayout,
    PaperTemplate,
)
from .renderer import ElementRenderer, build_para_layouts

# ---------------------------------------------------------------------------
# Hilfsfunktionen für Multi-Paragraph-Cursor-Operationen
# ---------------------------------------------------------------------------


def _seg_for_pos(segs: list, pos: int) -> dict:
    """Gibt das Segment zurück, das die globale Textposition pos enthält."""
    best = segs[0]
    for seg in segs:
        if seg["char_start"] <= pos:
            best = seg
        else:
            break
    return best


def _line_for_pos(segs: list, pos: int):
    """Gibt (seg, line_or_None) für eine globale Textposition zurück."""
    seg = _seg_for_pos(segs, pos)
    if seg["layout"] is None:
        return seg, None
    local_pos = pos - seg["char_start"]
    line = seg["layout"].lineForTextPosition(local_pos)
    if not line.isValid():
        n = seg["layout"].lineCount()
        if n > 0:
            line = seg["layout"].lineAt(n - 1)
    return seg, line


def _all_visual_lines(segs: list) -> list:
    """Flache Liste aller (seg, line_or_None) – eine Eintrag pro visueller Zeile."""
    result = []
    for seg in segs:
        if seg["layout"] is None:
            result.append((seg, None))
        else:
            for i in range(seg["layout"].lineCount()):
                result.append((seg, seg["layout"].lineAt(i)))
    return result


# Handle size in pixel
HANDLE_SIZE = 8
MIN_ELEM_SIZE = 2.0  # mm


def _mm_to_px(mm: float, dpi: float) -> float:
    return mm / 25.4 * dpi


class CardCanvas(QWidget):
    """Interaktiver Canvas für eine Kartenseite."""

    selectionChanged = Signal(list)  # Liste selektierter CardElement-IDs
    elementMoved = Signal()
    elementResized = Signal()
    requestUndo = Signal()
    requestRedo = Signal()
    editStarted = Signal()  # Drag oder Resize beginnt
    editFinished = Signal()  # Drag oder Resize beendet
    zoomChanged = Signal(float)  # Neuer Zoom-Faktor (px/mm)

    # ------------------------------------------------------------------
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)

        self._layout: CardLayout | None = None
        self._side: str = "front"  # "front" | "back"
        self._paper: PaperTemplate | None = None

        self._zoom: float = 3.0  # px/mm
        self._offset = QPointF(24, 24)  # canvas-padding in px (mind. HANDLE_SIZE*2)

        self._selected: list[str] = []  # element IDs
        self._drag_start: QPointF | None = None
        self._drag_orig: dict = {}  # id -> (x,y)
        self._resize_handle: str | None = None  # "br" | "r" | "b"
        self._resize_start: QPointF | None = None
        self._resize_orig: dict = {}

        self._show_grid: bool = True
        self._snap_grid: float = 1.0  # mm
        self._show_rulers: bool = True

        self._rubber_band_start: QPointF | None = None
        self._rubber_band_rect: QRectF | None = None

        self._pan_start: QPointF | None = None  # MMB-Panning
        self._pan_scroll_orig: tuple[int, int] = (0, 0)

        self._inline_elem: CardElement | None = None
        self._inline_orig: tuple | None = None  # (text, width, height) bei Edit-Start
        self._cursor_pos: int = 0
        self._sel_anchor: int | None = None  # Selektions-Ankerpunkt (None = keine Selektion)
        self._cursor_visible: bool = True
        self._cursor_timer = QTimer(self)
        self._cursor_timer.setInterval(500)
        self._cursor_timer.timeout.connect(self._toggle_cursor_blink)

        self._renderer = ElementRenderer(self._zoom)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_layout(self, layout: CardLayout, side: str = "front"):
        self._finish_inline_edit(commit=False)
        self._layout = layout
        self._side = side
        self._selected.clear()
        self._renderer.clear_all_caches()
        self.resize(self.sizeHint())
        self.update()
        self.selectionChanged.emit([])

    def set_side(self, side: str):
        self._finish_inline_edit(commit=False)
        self._side = side
        self._selected.clear()
        self.update()
        self.selectionChanged.emit([])

    def set_paper(self, paper: PaperTemplate):
        self._paper = paper
        self.resize(self.sizeHint())
        self.update()

    def set_zoom(self, zoom: float):
        self._finish_inline_edit(commit=True)
        self._zoom = max(0.5, zoom)
        self._renderer.set_scale(self._zoom)
        self.resize(self.sizeHint())  # Scroll-Area bekommt neue Größe → Scrollbalken bei Bedarf
        self.update()
        self.zoomChanged.emit(self._zoom)

    def set_grid(self, show: bool, snap: float = 1.0):
        self._show_grid = show
        self._snap_grid = snap
        self.update()

    def selected_elements(self) -> list[CardElement]:
        elems = self._elements()
        return [e for e in elems if e.id in self._selected]

    def select_all(self):
        self._selected = [e.id for e in self._elements()]
        self.selectionChanged.emit(self._selected)
        self.update()

    def delete_selected(self):
        elems = self._elements()
        keep = [e for e in elems if e.id not in self._selected]
        self._set_elements(keep)
        self._selected.clear()
        self.selectionChanged.emit([])
        self.update()

    def add_element(self, elem: CardElement):
        elems = self._elements()
        elem.z_order = max((e.z_order for e in elems), default=0) + 1
        elems.append(elem)
        self._set_elements(elems)
        self._selected = [elem.id]
        self.selectionChanged.emit(self._selected)
        self.update()

    def bring_to_front(self):
        for e in self.selected_elements():
            e.z_order = max((x.z_order for x in self._elements()), default=0) + 1
        self.update()

    def send_to_back(self):
        for e in self.selected_elements():
            e.z_order = min((x.z_order for x in self._elements()), default=0) - 1
        self.update()

    def invalidate_image_cache(self, path: str = ""):
        self._renderer.invalidate_pixmap_cache(path)
        self.update()

    def invalidate_qr_cache(self, data: str = ""):
        self._renderer.invalidate_qr_cache(data)
        self.update()

    def set_selection(self, ids: list[str]):
        """Setzt die Selektion von außen (z. B. aus der Ebenen-Liste)."""
        valid = {e.id for e in self._elements()}
        self._selected = [i for i in ids if i in valid]
        self.selectionChanged.emit(self._selected)
        self.update()

    def align_selected(self, mode: str):
        """
        mode: left | right | top | bottom | center_h | center_v |
              group_left | group_right | group_top | group_bottom |
              group_center_h | group_center_v
        """
        sel = self.selected_elements()
        if not sel:
            return
        card_w = self._paper.card_width if self._paper else 85.6
        card_h = self._paper.card_height if self._paper else 54.0

        if mode == "left":
            for e in sel:
                e.x = 0
        elif mode == "right":
            for e in sel:
                e.x = card_w - e.width
        elif mode == "top":
            for e in sel:
                e.y = 0
        elif mode == "bottom":
            for e in sel:
                e.y = card_h - e.height
        elif mode == "center_h":
            for e in sel:
                e.x = (card_w - e.width) / 2
        elif mode == "center_v":
            for e in sel:
                e.y = (card_h - e.height) / 2
        elif len(sel) > 1:
            xs = [e.x for e in sel]
            ys = [e.y for e in sel]
            xe = [e.x + e.width for e in sel]
            ye = [e.y + e.height for e in sel]
            if mode == "group_left":
                ref = min(xs)
                for e in sel:
                    e.x = ref
            elif mode == "group_right":
                ref = max(xe)
                for e in sel:
                    e.x = ref - e.width
            elif mode == "group_top":
                ref = min(ys)
                for e in sel:
                    e.y = ref
            elif mode == "group_bottom":
                ref = max(ye)
                for e in sel:
                    e.y = ref - e.height
            elif mode == "group_center_h":
                cx = (min(xs) + max(xe)) / 2
                for e in sel:
                    e.x = cx - e.width / 2
            elif mode == "group_center_v":
                cy = (min(ys) + max(ye)) / 2
                for e in sel:
                    e.y = cy - e.height / 2
            elif mode == "distribute_h" and len(sel) > 2:
                # Linke und rechte Kante bleiben, Mitte gleichmäßig aufteilen
                srt = sorted(sel, key=lambda e: e.x)
                x_start = srt[0].x
                x_end = srt[-1].x + srt[-1].width
                total_w = sum(e.width for e in srt)
                gap = (x_end - x_start - total_w) / (len(srt) - 1)
                x = x_start
                for e in srt:
                    e.x = x
                    x += e.width + gap
            elif mode == "distribute_v" and len(sel) > 2:
                srt = sorted(sel, key=lambda e: e.y)
                y_start = srt[0].y
                y_end = srt[-1].y + srt[-1].height
                total_h = sum(e.height for e in srt)
                gap = (y_end - y_start - total_h) / (len(srt) - 1)
                y = y_start
                for e in srt:
                    e.y = y
                    y += e.height + gap
        self.update()
        self.elementMoved.emit()

    def fit_to_content(self):
        """Passt Breite/Höhe der markierten Elemente an ihren Inhalt an.

        * Text  → engste Bounding-Box ohne Zeilenumbruch-Zwang
        * Bild  → Höhe wird so angepasst, dass das Seitenverhältnis stimmt
        * QR    → Breite = Höhe (Quadrat)
        * Form/Linie → keine Änderung
        """
        sel = self.selected_elements()
        changed = False
        for e in sel:
            if e.type == ELEMENT_TEXT and e.text.strip():
                w_px, h_px = self._renderer.text_bounding_rect(e)
                # 2 px Rand auf jeder Seite für saubere Darstellung
                if not e.text_wrap:
                    e.width = max(1.0, round((w_px + 4) / self._zoom, 2))
                e.height = max(1.0, round((h_px + 4) / self._zoom, 2))
                changed = True
            elif e.type == ELEMENT_IMAGE and e.image_path:
                pm = self._renderer.get_pixmap(e.image_path)
                if pm and not pm.isNull() and pm.width() > 0:
                    ratio = pm.height() / pm.width()
                    e.height = round(e.width * ratio, 2)
                    changed = True
            elif e.type == ELEMENT_QR:
                side = max(e.width, e.height)
                e.width = side
                e.height = side
                changed = True
        if changed:
            self.update()
            self.elementMoved.emit()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _elements(self) -> list[CardElement]:
        if self._layout is None:
            return []
        return self._layout.front_elements if self._side == "front" else self._layout.back_elements

    def _set_elements(self, elems: list[CardElement]):
        if self._layout is None:
            return
        if self._side == "front":
            self._layout.front_elements = elems
        else:
            self._layout.back_elements = elems

    def _card_w_px(self) -> float:
        w = self._paper.card_width if self._paper else 85.6
        return w * self._zoom

    def _card_h_px(self) -> float:
        h = self._paper.card_height if self._paper else 54.0
        return h * self._zoom

    def _to_px(self, mm: float) -> float:
        return mm * self._zoom

    def _to_mm(self, px: float) -> float:
        return px / self._zoom

    def _card_rect(self) -> QRectF:
        return QRectF(self._offset, QSizeF(self._card_w_px(), self._card_h_px()))

    def _elem_rect_px(self, e: CardElement) -> QRectF:
        ox, oy = self._offset.x(), self._offset.y()
        if e.type == ELEMENT_LINE:
            # Startpunkt (e.x, e.y), Endpunkt (e.x + line_x2, e.y + line_y2)
            x1 = ox + self._to_px(e.x)
            y1 = oy + self._to_px(e.y)
            x2 = ox + self._to_px(e.x + e.line_x2)
            y2 = oy + self._to_px(e.y + e.line_y2)
            return QRectF(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
        cx = ox + self._to_px(e.x)
        cy = oy + self._to_px(e.y)
        return QRectF(cx, cy, self._to_px(e.width), self._to_px(e.height))

    def _snap(self, v: float) -> float:
        if self._snap_grid <= 0:
            return v
        return round(v / self._snap_grid) * self._snap_grid

    def _elem_at(self, pos: QPointF) -> CardElement | None:
        elems = sorted(self._elements(), key=lambda e: -e.z_order)
        for e in elems:
            if not e.visible:
                continue
            r = self._elem_rect_px(e)
            if e.type == ELEMENT_LINE:
                # Bounding-Box der Linie um 3 mm aufblasen für einfaches Anklicken
                m = self._to_px(3.0)
                r = r.adjusted(-m, -m, m, m)
            if r.contains(pos):
                return e
        return None

    def _handle_at(self, pos: QPointF, elem: CardElement) -> str | None:
        hs = HANDLE_SIZE
        if elem.type == ELEMENT_LINE:
            ox, oy = self._offset.x(), self._offset.y()
            p1 = QPointF(ox + self._to_px(elem.x), oy + self._to_px(elem.y))
            p2 = QPointF(
                ox + self._to_px(elem.x + elem.line_x2), oy + self._to_px(elem.y + elem.line_y2)
            )
            if QRectF(p1.x() - hs, p1.y() - hs, hs * 2, hs * 2).contains(pos):
                return "l"
            if QRectF(p2.x() - hs, p2.y() - hs, hs * 2, hs * 2).contains(pos):
                return "r"
            return None
        r = self._elem_rect_px(elem)
        handles = {
            "br": QRectF(r.right() - hs, r.bottom() - hs, hs * 2, hs * 2),
            "r": QRectF(r.right() - hs, r.center().y() - hs, hs * 2, hs * 2),
            "b": QRectF(r.center().x() - hs, r.bottom() - hs, hs * 2, hs * 2),
        }
        for name, hr in handles.items():
            if hr.contains(pos):
                return name
        return None

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def sizeHint(self) -> QSize:
        off = self._offset.x()
        cw = self._card_w_px() + off * 2
        ch = self._card_h_px() + off * 2
        for e in self._elements():
            r = self._elem_rect_px(e)
            cw = max(cw, r.right() + off)
            ch = max(ch, r.bottom() + off)
        return QSize(int(cw), int(ch))

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Hintergrund Widget
        painter.fillRect(self.rect(), QColor("#1e1f26"))

        cr = self._card_rect()

        # Weicher Schatten (mehrere Ebenen)
        for i in range(6, 0, -1):
            shade = cr.adjusted(-i, -i, i + 3, i + 3)
            painter.fillRect(shade, QColor(0, 0, 0, 18 - i * 2))

        # Karten-Hintergrund
        bg = (
            (self._layout.front_bg if self._side == "front" else self._layout.back_bg)
            if self._layout
            else "#ffffff"
        )
        painter.fillRect(cr, QColor(bg))

        # Rahmen (dezent)
        painter.setPen(QPen(QColor("#3a3b4d"), 1))
        painter.drawRect(cr)

        if self._show_grid:
            self._draw_grid(painter, cr)

        # Elemente zeichnen – auf Kartenbereich clippen
        painter.setClipRect(cr)
        elems = sorted(self._elements(), key=lambda e: e.z_order)
        for e in elems:
            if e.visible:
                self._draw_element(painter, e)
        # Text-Cursor zeichnen (überlagert das Element, kein Widget)
        if self._inline_elem is not None:
            self._draw_text_cursor(painter)
        painter.setClipping(False)

        # Selektions-Handles (außerhalb Clip, damit Handles am Rand sichtbar bleiben)
        for eid in self._selected:
            for e in self._elements():
                if e.id == eid:
                    self._draw_selection(painter, e)

        # Gummiband-Selektion
        if self._rubber_band_rect:
            painter.save()
            painter.setPen(QPen(QColor("#4f8ef7"), 1, Qt.PenStyle.DashLine))
            painter.setBrush(QColor(79, 142, 247, 25))
            painter.drawRect(self._rubber_band_rect)
            painter.restore()

        painter.end()

    def _draw_grid(self, painter: QPainter, cr: QRectF):
        """Punkt-Raster – moderner als Linien."""
        card_w = self._paper.card_width if self._paper else 85.6
        card_h = self._paper.card_height if self._paper else 54.0
        step = self._snap_grid
        dot_color = QColor(100, 104, 140, 90)
        painter.setPen(QPen(dot_color, 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        y = 0.0
        while y <= card_h:
            x = 0.0
            while x <= card_w:
                px = cr.left() + self._to_px(x)
                py = cr.top() + self._to_px(y)
                painter.drawPoint(QPointF(px, py))
                x += step
            y += step

    def _draw_element(self, painter: QPainter, e: CardElement):
        r = self._elem_rect_px(e)
        self._renderer.draw_element(painter, e, r)

    def _draw_selection(self, painter: QPainter, e: CardElement):
        # Während Inline-Edit: Fokus-Rahmen; bei text_wrap auch rechter Handle
        if self._inline_elem is not None and e.id == self._inline_elem.id:
            hs = HANDLE_SIZE
            painter.save()
            painter.setPen(QPen(QColor("#4f8ef7"), 2.0, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            r = self._elem_rect_px(e)
            painter.drawRect(r)
            if e.text_wrap:
                # Rechten Handle anzeigen: Nutzer kann Wrap-Breite per Drag einstellen
                h_rect = QRectF(r.right() - hs, r.center().y() - hs, hs * 2, hs * 2)
                painter.setBrush(QColor("#ffffff"))
                painter.setPen(QPen(QColor("#4f8ef7"), 1.5, Qt.PenStyle.SolidLine))
                painter.drawEllipse(h_rect)
            painter.restore()
            return
        hs = HANDLE_SIZE
        if e.type == ELEMENT_LINE:
            # Linie: kein Rechteck-Rahmen – Endpunkt-Handles an tatsächlichen Positionen
            hs = HANDLE_SIZE
            ox, oy = self._offset.x(), self._offset.y()
            p1 = QPointF(ox + self._to_px(e.x), oy + self._to_px(e.y))
            p2 = QPointF(ox + self._to_px(e.x + e.line_x2), oy + self._to_px(e.y + e.line_y2))
            painter.save()
            painter.setPen(QPen(QColor("#4f8ef7"), 2.0))
            painter.drawLine(p1, p2)
            painter.setBrush(QColor("#ffffff"))
            painter.setPen(QPen(QColor("#4f8ef7"), 1.5))
            for pt in (p1, p2):
                painter.drawEllipse(QRectF(pt.x() - hs, pt.y() - hs, hs * 2, hs * 2))
            painter.restore()
            return
        r = self._elem_rect_px(e)
        # Selektionsrahmen
        pen = QPen(QColor("#4f8ef7"), 1.5, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(r)
        # Handles: runde weiße Kreise mit blauem Rand, auf dem Element-Rand zentriert
        handles = [
            QRectF(r.right() - hs, r.bottom() - hs, hs * 2, hs * 2),
            QRectF(r.right() - hs, r.center().y() - hs, hs * 2, hs * 2),
            QRectF(r.center().x() - hs, r.bottom() - hs, hs * 2, hs * 2),
        ]
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(QPen(QColor("#4f8ef7"), 1.5))
        for h in handles:
            painter.drawEllipse(h)

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_start = event.globalPosition()
            scroll = self._scroll_area()
            if scroll:
                self._pan_scroll_orig = (
                    scroll.horizontalScrollBar().value(),
                    scroll.verticalScrollBar().value(),
                )
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        if event.button() != Qt.MouseButton.LeftButton:
            if event.button() == Qt.MouseButton.RightButton:
                self._context_menu(event.position())
            return
        pos = event.position()
        # Während Inline-Edit: nur rechten Handle (text_wrap) oder Klick-ignorieren erlauben
        if self._inline_elem is not None:
            inline_elem = self._inline_elem
            if inline_elem.text_wrap and not inline_elem.locked:
                h = self._handle_at(pos, inline_elem)
                if h == "r":
                    self._resize_handle = "r"
                    self._resize_start = pos
                    self._resize_orig = {
                        inline_elem.id: (
                            inline_elem.x,
                            inline_elem.y,
                            inline_elem.width,
                            inline_elem.height,
                        )
                    }
                    self.editStarted.emit()
                    return
            # Klick innerhalb des Elements → Cursor an Klickposition setzen
            if self._elem_rect_px(inline_elem).contains(pos):
                self._cursor_pos = self._pos_from_click(pos, inline_elem)
                self._sel_anchor = None
                self._cursor_visible = True
                self._cursor_timer.start()
                self.update()
                return
            # Klick außerhalb → commit, dann normal verarbeiten
            self._finish_inline_edit(commit=True)
        # Check handles of selected elements first
        for eid in self._selected:
            for e in self._elements():
                if e.id == eid and not e.locked:
                    h = self._handle_at(pos, e)
                    if h:
                        self._resize_handle = h
                        self._resize_start = pos
                        self._resize_orig = {
                            e.id: (e.x, e.y, e.line_x2, e.line_y2)
                            if e.type == ELEMENT_LINE
                            else (e.x, e.y, e.width, e.height)
                            for e in self.selected_elements()
                        }
                        self.editStarted.emit()
                        return
        # Hit test
        elem = self._elem_at(pos)
        if elem:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                if elem.id in self._selected:
                    self._selected.remove(elem.id)
                else:
                    self._selected.append(elem.id)
            else:
                if elem.id not in self._selected:
                    self._selected = [elem.id]
            self._drag_start = pos
            self._drag_orig = {e.id: (e.x, e.y) for e in self.selected_elements()}
            self.editStarted.emit()
        else:
            # Gummiband starten
            if not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                self._selected.clear()
            self._rubber_band_start = pos
            self._rubber_band_rect = QRectF(pos, pos)
        self.selectionChanged.emit(self._selected)
        self.update()

    def mouseMoveEvent(self, event):
        if self._pan_start is not None:
            delta = event.globalPosition() - self._pan_start
            scroll = self._scroll_area()
            if scroll:
                scroll.horizontalScrollBar().setValue(self._pan_scroll_orig[0] - int(delta.x()))
                scroll.verticalScrollBar().setValue(self._pan_scroll_orig[1] - int(delta.y()))
            event.accept()
            return
        pos = event.position()
        if self._resize_handle and self._resize_start:
            dx = self._to_mm(pos.x() - self._resize_start.x())
            dy = self._to_mm(pos.y() - self._resize_start.y())
            for e in self.selected_elements():
                if e.id in self._resize_orig and not e.locked:
                    ox, oy, ow, oh = self._resize_orig[e.id]
                    if e.type == ELEMENT_LINE:
                        # ow = orig line_x2, oh = orig line_y2
                        if self._resize_handle == "l":
                            # Startpunkt verschieben, Endpunkt bleibt fest
                            new_x = self._snap(ox + dx)
                            new_y = self._snap(oy + dy)
                            e.line_x2 = (ox + ow) - new_x
                            e.line_y2 = (oy + oh) - new_y
                            e.x = new_x
                            e.y = new_y
                        elif self._resize_handle == "r":
                            # Endpunkt verschieben, Startpunkt bleibt fest
                            e.line_x2 = self._snap(ow + dx)
                            e.line_y2 = self._snap(oh + dy)
                    else:
                        if self._resize_handle in ("br", "r"):
                            e.width = max(MIN_ELEM_SIZE, self._snap(ow + dx))
                            # Rechter Handle an Textelement → Umbruch aktivieren, Höhe auto
                            if e.type == ELEMENT_TEXT and self._resize_handle == "r":
                                e.text_wrap = True
                                if e.text.strip():
                                    _, h_px = self._renderer.text_bounding_rect(e)
                                    e.height = max(1.0, round((h_px + 4) / self._zoom, 2))
                        if self._resize_handle in ("br", "b"):
                            e.height = max(MIN_ELEM_SIZE, self._snap(oh + dy))
            # Während Inline-Edit mit text_wrap: Höhe automatisch an neuen Wrap-Bereich anpassen
            if (
                self._inline_elem is not None
                and self._inline_elem.text_wrap
                and self._inline_elem.text.strip()
            ):
                _w_px, h_px = self._renderer.text_bounding_rect(self._inline_elem)
                self._inline_elem.height = max(1.0, round((h_px + 4) / self._zoom, 2))
            self.resize(self.sizeHint())
            self.update()
            self.elementResized.emit()
            return
        if self._drag_start and self._drag_orig is not None:
            dx = self._to_mm(pos.x() - self._drag_start.x())
            dy = self._to_mm(pos.y() - self._drag_start.y())
            for e in self.selected_elements():
                if e.id in self._drag_orig and not e.locked:
                    ox, oy = self._drag_orig[e.id]
                    e.x = self._snap(ox + dx)
                    e.y = self._snap(oy + dy)
            self.resize(self.sizeHint())
            self.update()
            self.elementMoved.emit()
            return
        if self._rubber_band_start:
            self._rubber_band_rect = QRectF(self._rubber_band_start, pos).normalized()
            self.update()
            return
        # Cursor ändern
        if self._inline_elem is not None:
            if self._inline_elem.text_wrap:
                h = self._handle_at(pos, self._inline_elem)
                self.setCursor(
                    Qt.CursorShape.SizeHorCursor if h == "r" else Qt.CursorShape.IBeamCursor
                )
            else:
                self.setCursor(Qt.CursorShape.IBeamCursor)
            return
        for eid in self._selected:
            for e in self._elements():
                if e.id == eid:
                    h = self._handle_at(pos, e)
                    if h == "br":
                        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                        return
                    elif h in ("l", "r") and e.type == ELEMENT_LINE:
                        self.setCursor(Qt.CursorShape.SizeAllCursor)
                        return
                    elif h == "r":
                        self.setCursor(Qt.CursorShape.SizeHorCursor)
                        return
                    elif h in ("b",):
                        self.setCursor(Qt.CursorShape.SizeVerCursor)
                        return
        elem_at_pos = self._elem_at(pos)
        self.setCursor(Qt.CursorShape.SizeAllCursor if elem_at_pos else Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_start = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        # Gummiband abschließen
        if self._rubber_band_rect and self._rubber_band_rect.width() > 3:
            for e in self._elements():
                if not e.visible:
                    continue
                r = self._elem_rect_px(e)
                if self._rubber_band_rect.intersects(r) and e.id not in self._selected:
                    self._selected.append(e.id)
            self.selectionChanged.emit(self._selected)
        # Drag/Resize beendet → Undo-Schritt anlegen
        _had_edit = bool(self._drag_start or self._resize_handle)
        self._rubber_band_start = None
        self._rubber_band_rect = None
        self._drag_start = None
        self._drag_orig = {}
        self._resize_handle = None
        self._resize_start = None
        self._resize_orig = {}
        if _had_edit:
            self.editFinished.emit()
        self.update()

    def mouseDoubleClickEvent(self, event):
        pos = event.position()
        # Doppelklick auf Handle → fit_to_content (Auto-Größe)
        for eid in self._selected:
            for e in self._elements():
                if e.id == eid and not e.locked and self._handle_at(pos, e):
                    self.fit_to_content()
                    self.elementMoved.emit()
                    event.accept()
                    return
        # Doppelklick auf Element-Körper → Inline-Edit
        elem = self._elem_at(pos)
        if elem and elem.type == ELEMENT_TEXT and not elem.locked:
            self._start_inline_edit(elem, pos)
            event.accept()

    def _start_inline_edit(self, elem: CardElement, click_pos: QPointF | None = None):
        """Startet In-Place-Editing: kein Widget, nur Canvas-State + Cursor-Overlay."""
        if self._inline_elem is not None:
            self._finish_inline_edit(commit=True)

        self._inline_orig = (elem.text, elem.width, elem.height)
        self._inline_elem = elem
        if click_pos is not None:
            self._cursor_pos = self._pos_from_click(click_pos, elem)
        else:
            self._cursor_pos = len(elem.text)  # Cursor ans Ende
        self._sel_anchor = None
        self._cursor_visible = True
        self._cursor_timer.start()

        self._selected = [elem.id]
        self.selectionChanged.emit(self._selected)
        self.setFocus()
        self.update()
        self.editStarted.emit()

    def _toggle_cursor_blink(self):
        self._cursor_visible = not self._cursor_visible
        self.update()

    def _elem_font(self, elem: CardElement) -> QFont:
        """Erstellt den QFont des Elements identisch zum Renderer."""
        from .renderer import PT_TO_MM

        px_size = max(1, int(elem.font_size * PT_TO_MM * self._zoom))
        font = QFont(elem.font_family)
        font.setPixelSize(px_size)
        font.setBold(elem.font_bold)
        font.setItalic(elem.font_italic)
        font.setUnderline(elem.font_underline)
        return font

    def _pos_from_click(self, click: QPointF, elem: CardElement) -> int:
        """Gibt den Textzeigerindex für einen Maus-Klick innerhalb von elem zurück."""
        text = elem.text
        if not text:
            return 0
        if elem.text_wrap:
            segs, r, y_off = self._para_layouts(elem)
            rel_x = click.x() - r.left()
            rel_y = click.y() - y_off
            # Segment finden: letztes dessen y_top ≤ rel_y
            target_seg = segs[0]
            for seg in segs:
                if seg["y_top"] <= rel_y:
                    target_seg = seg
                else:
                    break
            if target_seg["layout"] is None:
                return target_seg["char_start"]
            layout = target_seg["layout"]
            seg_rel_y = rel_y - target_seg["y_top"]
            target_line = layout.lineAt(0)
            for i in range(layout.lineCount()):
                line = layout.lineAt(i)
                target_line = line
                if seg_rel_y < line.position().y() + line.height():
                    break
            local_pos = target_line.xToCursor(rel_x)
            return target_seg["char_start"] + local_pos
        else:
            fm = QFontMetrics(self._elem_font(elem))
            r = self._elem_rect_px(elem)
            all_lines = text.split("\n") if text else [""]
            line_h = fm.height()
            total_h = len(all_lines) * line_h
            if elem.v_align == "middle":
                y_start = r.top() + (r.height() - total_h) / 2
            elif elem.v_align == "bottom":
                y_start = r.bottom() - total_h
            else:
                y_start = r.top()
            line_idx = max(0, min(len(all_lines) - 1, int((click.y() - y_start) / line_h)))
            line_text = all_lines[line_idx]
            line_full_w = fm.horizontalAdvance(line_text)
            if elem.h_align == "center":
                x_off = r.left() + (r.width() - line_full_w) / 2
            elif elem.h_align == "right":
                x_off = r.right() - line_full_w
            else:
                x_off = r.left()
            rel_x = click.x() - x_off
            # Zeichenposition per halber Zeichenbreite bestimmen
            best = len(line_text)
            for i in range(len(line_text) + 1):
                w = fm.horizontalAdvance(line_text[:i])
                if w >= rel_x:
                    if i > 0:
                        w_prev = fm.horizontalAdvance(line_text[: i - 1])
                        best = i - 1 if rel_x - w_prev < w - rel_x else i
                    else:
                        best = 0
                    break
            char_offset = sum(len(all_lines[j]) + 1 for j in range(line_idx))
            return min(char_offset + best, len(text))

    def _para_layouts(self, elem: CardElement):
        """Multi-Paragraph-Layout für Cursor-Berechnungen bei text_wrap=True.

        Gibt (segs, r, y_off) zurück:
        - segs: Liste aus build_para_layouts
        - r:    Element-Rect in Pixel
        - y_off: absolutes y der Blockoberseite (v_align berücksichtigt)
        """
        r = self._elem_rect_px(elem)
        font = self._elem_font(elem)
        segs, total_h = build_para_layouts(elem.text, font, r.width(), elem.h_align)
        if elem.v_align == "middle":
            y_off = r.top() + (r.height() - total_h) / 2
        elif elem.v_align == "bottom":
            y_off = r.bottom() - total_h
        else:
            y_off = r.top()
        return segs, r, y_off

    def _draw_text_cursor(self, painter: QPainter):
        """Zeichnet Selektion (immer sichtbar) und blinkenden Cursor als Overlay."""
        if self._inline_elem is None:
            return
        elem = self._inline_elem
        r = self._elem_rect_px(elem)
        font = self._elem_font(elem)

        text = elem.text
        pos = min(self._cursor_pos, len(text))

        if elem.text_wrap:
            segs, r, y_off = self._para_layouts(elem)
            sel = self._sel_range()
            sel_color = QColor(100, 149, 237, 120)

            # Selektion zeichnen (immer sichtbar)
            if sel:
                painter.save()
                for seg in segs:
                    if seg["layout"] is None:
                        # Leere Zeile: schmaler Balken wenn Selektion drübergeht
                        cs = seg["char_start"]
                        if sel[0] <= cs < sel[1]:
                            painter.fillRect(
                                QRectF(r.left(), y_off + seg["y_top"], 8.0, seg["height"]),
                                sel_color,
                            )
                        continue
                    layout = seg["layout"]
                    cs = seg["char_start"]
                    for i in range(layout.lineCount()):
                        ll = layout.lineAt(i)
                        ls = ll.textStart() + cs
                        ov_s = max(sel[0], ls)
                        ov_e = min(sel[1], ls + ll.textLength())
                        if ov_s < ov_e:
                            x1, _ = ll.cursorToX(ov_s - cs)
                            x2, _ = ll.cursorToX(ov_e - cs)
                            lp = ll.position()
                            painter.fillRect(
                                QRectF(
                                    r.left() + x1,
                                    y_off + seg["y_top"] + lp.y(),
                                    x2 - x1,
                                    ll.height(),
                                ),
                                sel_color,
                            )
                painter.restore()

            # Cursor-Position
            cx = r.left()
            cy_top = y_off
            cy_bot = cy_top + 14.0
            seg, cur_line = _line_for_pos(segs, pos)
            if seg["layout"] is None:
                cy_top = y_off + seg["y_top"]
                cy_bot = cy_top + seg["height"]
            elif cur_line is not None and cur_line.isValid():
                local_pos = pos - seg["char_start"]
                x_in_line, _ = cur_line.cursorToX(local_pos)
                cx = r.left() + x_in_line
                lp = cur_line.position()
                cy_top = y_off + seg["y_top"] + lp.y()
                cy_bot = cy_top + cur_line.height()
        else:
            fm = QFontMetrics(font)
            text_before = text[:pos]
            lines_before = text_before.split("\n")
            line_idx = len(lines_before) - 1
            last_line_before = lines_before[-1]

            all_lines = text.split("\n") if text else [""]
            n_lines = len(all_lines)
            line_h = fm.height()
            total_h = n_lines * line_h

            if elem.v_align == "middle":
                y_start = r.top() + (r.height() - total_h) / 2
            elif elem.v_align == "bottom":
                y_start = r.bottom() - total_h
            else:
                y_start = r.top()

            # Selektion zeichnen
            sel = self._sel_range()
            if sel:
                painter.save()
                sel_color = QColor(100, 149, 237, 120)
                char_offset = 0
                for i, line_text in enumerate(all_lines):
                    line_end_offset = char_offset + len(line_text)
                    ov_s = max(sel[0], char_offset)
                    ov_e = min(sel[1], line_end_offset)
                    if ov_s < ov_e:
                        before_sel = line_text[: ov_s - char_offset]
                        in_sel = line_text[ov_s - char_offset : ov_e - char_offset]
                        x1 = fm.horizontalAdvance(before_sel)
                        x2 = x1 + fm.horizontalAdvance(in_sel)
                        line_full_w = fm.horizontalAdvance(line_text)
                        if elem.h_align == "center":
                            x_off = r.left() + (r.width() - line_full_w) / 2
                        elif elem.h_align == "right":
                            x_off = r.right() - line_full_w
                        else:
                            x_off = r.left()
                        painter.fillRect(
                            QRectF(x_off + x1, y_start + i * line_h, x2 - x1, line_h), sel_color
                        )
                    char_offset = line_end_offset + 1  # +1 für \n
                painter.restore()

            cur_full_line = all_lines[line_idx] if line_idx < len(all_lines) else ""
            line_full_w = fm.horizontalAdvance(cur_full_line)
            before_w = fm.horizontalAdvance(last_line_before)
            if elem.h_align == "center":
                x_start = r.left() + (r.width() - line_full_w) / 2
            elif elem.h_align == "right":
                x_start = r.right() - line_full_w
            else:
                x_start = r.left()

            cx = x_start + before_w
            cy_top = y_start + line_idx * line_h
            cy_bot = cy_top + line_h

        painter.save()
        painter.setPen(QPen(QColor(elem.color), 1.5))
        if self._cursor_visible:
            painter.drawLine(QPointF(cx, cy_top), QPointF(cx, cy_bot))
        painter.restore()

    def _finish_inline_edit(self, commit: bool = True):
        """Beendet Inline-Edit; commit=False stellt Original wieder her."""
        if self._inline_elem is None:
            return
        elem = self._inline_elem
        orig = self._inline_orig
        # Refs zuerst löschen – verhindert Re-Entrant (z. B. via focusOutEvent)
        self._inline_elem = None
        self._inline_orig = None
        self._cursor_pos = 0
        self._sel_anchor = None
        self._cursor_timer.stop()

        if not commit and orig is not None:
            elem.text, elem.width, elem.height = orig

        if commit:
            self.editFinished.emit()
        self.update()

    def _sel_range(self) -> tuple[int, int] | None:
        """Gibt (start, end) der aktuellen Selektion zurück, oder None."""
        if self._sel_anchor is None or self._sel_anchor == self._cursor_pos:
            return None
        return (min(self._sel_anchor, self._cursor_pos), max(self._sel_anchor, self._cursor_pos))

    def _handle_inline_key(self, event) -> bool:
        """Tastatureingabe während Inline-Edit verarbeiten. Gibt True zurück wenn konsumiert."""
        if self._inline_elem is None:
            return False
        key = event.key()
        mods = event.modifiers()
        elem = self._inline_elem
        text = elem.text
        pos = self._cursor_pos
        Ctrl = Qt.KeyboardModifier.ControlModifier
        Shift = Qt.KeyboardModifier.ShiftModifier

        if key == Qt.Key.Key_Escape:
            self._finish_inline_edit(commit=False)
            return True
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and (mods & Ctrl):
            self._finish_inline_edit(commit=True)
            return True

        # --- Clipboard-Operationen ---
        if key == Qt.Key.Key_A and (mods & Ctrl):
            self._sel_anchor = 0
            self._cursor_pos = len(text)
        elif key == Qt.Key.Key_C and (mods & Ctrl):
            sel = self._sel_range()
            clip = text[sel[0] : sel[1]] if sel else text
            QApplication.clipboard().setText(clip)
        elif key == Qt.Key.Key_X and (mods & Ctrl):
            sel = self._sel_range()
            if sel:
                QApplication.clipboard().setText(text[sel[0] : sel[1]])
                elem.text = text[: sel[0]] + text[sel[1] :]
                self._cursor_pos = sel[0]
            else:
                QApplication.clipboard().setText(text)
                elem.text = ""
                self._cursor_pos = 0
            self._sel_anchor = None
            self._update_inline_size()
        elif key == Qt.Key.Key_V and (mods & Ctrl):
            paste = QApplication.clipboard().text()
            sel = self._sel_range()
            if sel:
                elem.text = text[: sel[0]] + paste + text[sel[1] :]
                self._cursor_pos = sel[0] + len(paste)
            else:
                elem.text = text[:pos] + paste + text[pos:]
                self._cursor_pos = pos + len(paste)
            self._sel_anchor = None
            self._update_inline_size()
        # --- Cursor-Bewegung (mit/ohne Shift-Selektion) ---
        elif key == Qt.Key.Key_Left:
            if mods & Shift:
                if self._sel_anchor is None:
                    self._sel_anchor = pos
                self._cursor_pos = max(0, pos - 1)
            else:
                self._sel_anchor = None
                self._cursor_pos = max(0, pos - 1)
        elif key == Qt.Key.Key_Right:
            if mods & Shift:
                if self._sel_anchor is None:
                    self._sel_anchor = pos
                self._cursor_pos = min(len(text), pos + 1)
            else:
                self._sel_anchor = None
                self._cursor_pos = min(len(text), pos + 1)
        elif key == Qt.Key.Key_Up:
            if elem.text_wrap:
                segs, _, _ = self._para_layouts(elem)
                all_lines = _all_visual_lines(segs)
                seg, cur_line = _line_for_pos(segs, pos)
                cur_x = 0.0
                if cur_line is not None and cur_line.isValid():
                    cur_x, _ = cur_line.cursorToX(pos - seg["char_start"])
                # Index in der flachen Zeilen-Liste finden
                cur_idx = 0
                for i, (s, ln) in enumerate(all_lines):
                    if s is seg and (
                        (ln is None and cur_line is None)
                        or (
                            ln is not None
                            and cur_line is not None
                            and ln.lineNumber() == cur_line.lineNumber()
                        )
                    ):
                        cur_idx = i
                        break
                if cur_idx > 0:
                    prev_seg, prev_line = all_lines[cur_idx - 1]
                    if prev_line is None:
                        new_pos = prev_seg["char_start"]
                    else:
                        new_pos = prev_seg["char_start"] + prev_line.xToCursor(cur_x)
                    if mods & Shift:
                        if self._sel_anchor is None:
                            self._sel_anchor = pos
                    else:
                        self._sel_anchor = None
                    self._cursor_pos = new_pos
            else:
                before = text[:pos]
                nl = before.rfind("\n")
                if nl >= 0:
                    col = pos - nl - 1
                    prev_line_end = nl
                    prev_nl = before.rfind("\n", 0, nl)
                    prev_line_start = prev_nl + 1
                    new_pos = min(prev_line_start + col, prev_line_end)
                    if mods & Shift:
                        if self._sel_anchor is None:
                            self._sel_anchor = pos
                    else:
                        self._sel_anchor = None
                    self._cursor_pos = new_pos
        elif key == Qt.Key.Key_Down:
            if elem.text_wrap:
                segs, _, _ = self._para_layouts(elem)
                all_lines = _all_visual_lines(segs)
                seg, cur_line = _line_for_pos(segs, pos)
                cur_x = 0.0
                if cur_line is not None and cur_line.isValid():
                    cur_x, _ = cur_line.cursorToX(pos - seg["char_start"])
                cur_idx = len(all_lines) - 1
                for i, (s, ln) in enumerate(all_lines):
                    if s is seg and (
                        (ln is None and cur_line is None)
                        or (
                            ln is not None
                            and cur_line is not None
                            and ln.lineNumber() == cur_line.lineNumber()
                        )
                    ):
                        cur_idx = i
                        break
                if cur_idx < len(all_lines) - 1:
                    nxt_seg, nxt_line = all_lines[cur_idx + 1]
                    if nxt_line is None:
                        new_pos = nxt_seg["char_start"]
                    else:
                        new_pos = nxt_seg["char_start"] + nxt_line.xToCursor(cur_x)
                    if mods & Shift:
                        if self._sel_anchor is None:
                            self._sel_anchor = pos
                    else:
                        self._sel_anchor = None
                    self._cursor_pos = new_pos
            else:
                after = text[pos:]
                nl = after.find("\n")
                if nl >= 0:
                    before = text[:pos]
                    line_start = before.rfind("\n") + 1
                    col = pos - line_start
                    next_line_start = pos + nl + 1
                    next_nl = text.find("\n", next_line_start)
                    next_line_end = next_nl if next_nl >= 0 else len(text)
                    new_pos = min(next_line_start + col, next_line_end)
                    if mods & Shift:
                        if self._sel_anchor is None:
                            self._sel_anchor = pos
                    else:
                        self._sel_anchor = None
                    self._cursor_pos = new_pos
        elif key == Qt.Key.Key_Home:
            if elem.text_wrap:
                segs, _, _ = self._para_layouts(elem)
                seg, cur_line = _line_for_pos(segs, pos)
                if cur_line is None:
                    new_pos = seg["char_start"]
                else:
                    new_pos = seg["char_start"] + cur_line.textStart()
                if mods & Shift:
                    if self._sel_anchor is None:
                        self._sel_anchor = pos
                else:
                    self._sel_anchor = None
                self._cursor_pos = new_pos
            else:
                before = text[:pos]
                nl = before.rfind("\n")
                new_pos = nl + 1 if nl >= 0 else 0
                if mods & Shift:
                    if self._sel_anchor is None:
                        self._sel_anchor = pos
                else:
                    self._sel_anchor = None
                self._cursor_pos = new_pos
        elif key == Qt.Key.Key_End:
            if elem.text_wrap:
                segs, _, _ = self._para_layouts(elem)
                seg, cur_line = _line_for_pos(segs, pos)
                if cur_line is None:
                    new_pos = seg["char_start"]
                else:
                    line_end = cur_line.textStart() + cur_line.textLength()
                    # Trailing-Space der Zeile ausschließen (nächste Zeile beginnt dort)
                    ln = cur_line.lineNumber()
                    if ln + 1 < seg["layout"].lineCount():
                        line_end = min(line_end, seg["layout"].lineAt(ln + 1).textStart())
                    new_pos = seg["char_start"] + min(line_end, len(seg["layout"].text()))
                if mods & Shift:
                    if self._sel_anchor is None:
                        self._sel_anchor = pos
                else:
                    self._sel_anchor = None
                self._cursor_pos = new_pos
            else:
                after = text[pos:]
                nl = after.find("\n")
                new_pos = pos + nl if nl >= 0 else len(text)
                if mods & Shift:
                    if self._sel_anchor is None:
                        self._sel_anchor = pos
                else:
                    self._sel_anchor = None
                self._cursor_pos = new_pos
        elif key == Qt.Key.Key_Backspace:
            sel = self._sel_range()
            if sel:
                elem.text = text[: sel[0]] + text[sel[1] :]
                self._cursor_pos = sel[0]
                self._sel_anchor = None
            elif pos > 0:
                elem.text = text[: pos - 1] + text[pos:]
                self._cursor_pos = pos - 1
            self._update_inline_size()
        elif key == Qt.Key.Key_Delete:
            sel = self._sel_range()
            if sel:
                elem.text = text[: sel[0]] + text[sel[1] :]
                self._cursor_pos = sel[0]
                self._sel_anchor = None
            elif pos < len(text):
                elem.text = text[:pos] + text[pos + 1 :]
            self._update_inline_size()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            sel = self._sel_range()
            if sel:
                elem.text = text[: sel[0]] + "\n" + text[sel[1] :]
                self._cursor_pos = sel[0] + 1
                self._sel_anchor = None
            else:
                elem.text = text[:pos] + "\n" + text[pos:]
                self._cursor_pos = pos + 1
            self._update_inline_size()
        elif event.text() and not (mods & (Ctrl | Qt.KeyboardModifier.AltModifier)):
            char = event.text()
            sel = self._sel_range()
            if sel:
                elem.text = text[: sel[0]] + char + text[sel[1] :]
                self._cursor_pos = sel[0] + len(char)
                self._sel_anchor = None
            else:
                elem.text = text[:pos] + char + text[pos:]
                self._cursor_pos = pos + len(char)
            self._update_inline_size()
        else:
            return False

        # Cursor nach Taste sichtbar machen
        self._cursor_visible = True
        self._cursor_timer.start()  # Intervall neu starten
        self.update()
        return True

    def _update_inline_size(self):
        """Passt Elementgröße live an den neuen Textinhalt an."""
        if self._inline_elem is None:
            return
        elem = self._inline_elem
        if elem.text.strip():
            w_px, h_px = self._renderer.text_bounding_rect(elem)
            if not elem.text_wrap:
                elem.width = max(1.0, round((w_px + 4) / self._zoom, 2))
            elem.height = max(1.0, round((h_px + 4) / self._zoom, 2))
        self.resize(self.sizeHint())
        self.elementResized.emit()

    def parent_window_edit_text(self, elem: CardElement):
        # Kompatibilitäts-Stub – nicht mehr aktiv genutzt
        pass

    def event(self, event):
        # ShortcutOverride: verhindert dass Qt Window-Shortcuts (Ctrl+A etc.)
        # während Inline-Edit vor keyPressEvent feuern.
        if (
            getattr(self, "_inline_elem", None) is not None
            and event.type() == QEvent.Type.ShortcutOverride
        ):
            key = event.key()
            mods = event.modifiers()
            Ctrl = Qt.KeyboardModifier.ControlModifier
            if (mods & Ctrl) and key in (
                Qt.Key.Key_A,
                Qt.Key.Key_C,
                Qt.Key.Key_X,
                Qt.Key.Key_V,
                Qt.Key.Key_Return,
                Qt.Key.Key_Enter,
            ):
                event.accept()
                return True
            # Escape, Pfeiltasten, Home/End, Backspace, Delete etc. immer akzeptieren
            if key in (
                Qt.Key.Key_Escape,
                Qt.Key.Key_Left,
                Qt.Key.Key_Right,
                Qt.Key.Key_Up,
                Qt.Key.Key_Down,
                Qt.Key.Key_Home,
                Qt.Key.Key_End,
                Qt.Key.Key_Backspace,
                Qt.Key.Key_Delete,
            ):
                event.accept()
                return True
        return super().event(event)

    def focusOutEvent(self, event):
        if self._inline_elem is not None:
            self._finish_inline_edit(commit=True)
        super().focusOutEvent(event)

    def keyPressEvent(self, event):
        if self._inline_elem is not None:
            self._handle_inline_key(event)
            return
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            self.delete_selected()
        elif (
            event.key() == Qt.Key.Key_A and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            self.select_all()
        elif (
            event.key() == Qt.Key.Key_Z and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.requestRedo.emit()
            else:
                self.requestUndo.emit()
        elif (
            event.key() == Qt.Key.Key_Y and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            self.requestRedo.emit()
        # Pfeiltasten: Elementeverschieben 1mm
        delta = 0.1 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1.0
        if event.key() == Qt.Key.Key_Left:
            for e in self.selected_elements():
                if not e.locked:
                    e.x -= delta
        elif event.key() == Qt.Key.Key_Right:
            for e in self.selected_elements():
                if not e.locked:
                    e.x += delta
        elif event.key() == Qt.Key.Key_Up:
            for e in self.selected_elements():
                if not e.locked:
                    e.y -= delta
        elif event.key() == Qt.Key.Key_Down:
            for e in self.selected_elements():
                if not e.locked:
                    e.y += delta
        self.update()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            factor = 1.1 if delta > 0 else 0.9
            old_zoom = self._zoom
            scroll = self._scroll_area()
            if scroll:
                # Cursor-Position im Canvas-Widget (lokale px-Koordinaten)
                cursor = event.position()
                h_bar = scroll.horizontalScrollBar()
                v_bar = scroll.verticalScrollBar()
                # Position des Cursors relativ zum sichtbaren Viewport
                vp_x = cursor.x() - h_bar.value()
                vp_y = cursor.y() - v_bar.value()

                self.set_zoom(old_zoom * factor)

                new_zoom = self._zoom  # nach Clamp in set_zoom
                scale = new_zoom / old_zoom
                off_x = self._offset.x()
                off_y = self._offset.y()
                # Neue Canvas-Position der logischen mm-Stelle, die unter dem Cursor lag
                new_cx = (cursor.x() - off_x) * scale + off_x
                new_cy = (cursor.y() - off_y) * scale + off_y
                # Scrollbalken so setzen, dass der Cursor über dem selben Punkt bleibt
                h_bar.setValue(int(round(new_cx - vp_x)))
                v_bar.setValue(int(round(new_cy - vp_y)))
            else:
                self.set_zoom(old_zoom * factor)
            event.accept()
        else:
            super().wheelEvent(event)

    def _scroll_area(self):
        """Gibt die übergeordnete QScrollArea zurück, falls vorhanden."""
        from PySide6.QtWidgets import QScrollArea

        p = self.parent()
        while p is not None:
            if isinstance(p, QScrollArea):
                return p
            p = p.parent()
        return None

    def _context_menu(self, pos: QPointF):
        menu = QMenu(self)
        elem = self._elem_at(pos)
        if elem:
            if elem.id not in self._selected:
                self._selected = [elem.id]
                self.selectionChanged.emit(self._selected)
                self.update()
            menu.addAction("Nach vorne", self.bring_to_front)
            menu.addAction("Nach hinten", self.send_to_back)
            menu.addSeparator()
            menu.addAction("Löschen", self.delete_selected)
        else:
            menu.addAction("Alle auswählen", self.select_all)
        menu.exec(self.mapToGlobal(pos.toPoint()))
