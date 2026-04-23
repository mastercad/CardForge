"""
Druckvorschau-Dialog.
Zeigt das Papierblatt so wie es gedruckt würde – mit allen Karten,
korrekten Abständen, Rändern und optionalen Schnittmarken.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from .models import (
    CardElement,
    CardLayout,
    Project,
)
from .renderer import ElementRenderer

# ---------------------------------------------------------------------------
# Standalone Seiten-Renderer (QPainter-basiert, keine Widget-Abhängigkeit)
# ---------------------------------------------------------------------------


class _Renderer:
    """Rendert eine komplette Druckseite auf einen QPainter."""

    def __init__(self, project: Project, px_per_mm: float):
        self._project = project
        self._scale = px_per_mm  # px pro mm
        self._renderer = ElementRenderer(px_per_mm)

    def _px(self, mm: float) -> float:
        return mm * self._scale

    # ------------------------------------------------------------------
    # Öffentliche Methode
    # ------------------------------------------------------------------

    def render_page(
        self,
        painter: QPainter,
        side: str,
        card_indices: list[int],
        cut_marks: bool,
        back_duplex: bool = False,
        duplex_flip: str = "long-edge",
    ):
        """Zeichnet die gesamte Seite auf den painter (Ursprung = oben-links).

        back_duplex=True: Slot-Mapping wird gespiegelt (für Duplex-Rückseite).
        """
        pt = self._project.paper_template

        # Papierhintergrund
        pw = self._px(pt.paper_width)
        ph = self._px(pt.paper_height)
        painter.fillRect(QRectF(0, 0, pw, ph), QColor("white"))
        painter.setPen(QPen(QColor("#cccccc"), 0.5))
        painter.drawRect(QRectF(0, 0, pw, ph))

        if not card_indices:
            return
        for row in range(pt.rows):
            for col in range(pt.cols):
                # Duplex-Spiegelung: gespiegelten Slot für Kartenindex verwenden
                if back_duplex:
                    src_col = (pt.cols - 1 - col) if duplex_flip == "long-edge" else col
                    src_row = (pt.rows - 1 - row) if duplex_flip == "short-edge" else row
                else:
                    src_col, src_row = col, row
                slot_idx = src_row * pt.cols + src_col
                ci = card_indices[slot_idx % len(card_indices)]
                if ci >= len(self._project.cards):
                    continue
                layout = self._project.cards[ci]

                ox_mm = pt.margin_left + col * (pt.card_width + pt.gap_h)
                oy_mm = pt.margin_top + row * (pt.card_height + pt.gap_v)

                card_r = QRectF(
                    self._px(ox_mm),
                    self._px(oy_mm),
                    self._px(pt.card_width),
                    self._px(pt.card_height),
                )

                self._draw_card(painter, layout, side, card_r)

                if cut_marks:
                    self._draw_cut_marks(painter, card_r)

    # ------------------------------------------------------------------
    # Karte
    # ------------------------------------------------------------------

    def _draw_card(self, painter: QPainter, layout: CardLayout, side: str, card_r: QRectF):
        # Hintergrundfarbe
        bg = layout.front_bg if side == "front" else layout.back_bg
        painter.fillRect(card_r, QColor(bg))
        painter.setPen(QPen(QColor("#aaaaaa"), 0.3))
        painter.drawRect(card_r)

        # Elemente clippen auf Kartenbereich
        painter.save()
        painter.setClipRect(card_r)
        elems = sorted(
            (layout.front_elements if side == "front" else layout.back_elements),
            key=lambda e: e.z_order,
        )
        for e in elems:
            if e.visible:
                self._draw_element(painter, e, card_r)
        painter.restore()

    def _draw_element(self, painter: QPainter, e: CardElement, card_r: QRectF):
        r = QRectF(
            card_r.left() + self._px(e.x),
            card_r.top() + self._px(e.y),
            self._px(e.width),
            self._px(e.height),
        )
        self._renderer.draw_element(painter, e, r)

    # ------------------------------------------------------------------
    # Schnittmarken
    # ------------------------------------------------------------------

    def _draw_cut_marks(self, painter: QPainter, card_r: QRectF):
        mark_len = self._px(3.0)  # 3 mm Markenlänge
        gap = self._px(1.5)  # 1.5 mm Abstand zur Kartenkante
        pen = QPen(QColor("#444444"), 0.4)
        painter.setPen(pen)
        corners = [
            (card_r.left(), card_r.top(), 1, 1),
            (card_r.right(), card_r.top(), -1, 1),
            (card_r.right(), card_r.bottom(), -1, -1),
            (card_r.left(), card_r.bottom(), 1, -1),
        ]
        for cx, cy, sx, sy in corners:
            # Horizontale Marke
            painter.drawLine(QPointF(cx + sx * gap, cy), QPointF(cx + sx * (gap + mark_len), cy))
            # Vertikale Marke
            painter.drawLine(QPointF(cx, cy + sy * gap), QPointF(cx, cy + sy * (gap + mark_len)))


def render_page_to_pixmap(
    project: Project,
    side: str,
    card_indices: list[int],
    cut_marks: bool = True,
    px_per_mm: float = 3.78,
    back_duplex: bool = False,
    duplex_flip: str = "long-edge",
) -> QPixmap:
    """Rendert eine Druckseite als QPixmap."""
    pt = project.paper_template
    W = max(1, int(pt.paper_width * px_per_mm))
    H = max(1, int(pt.paper_height * px_per_mm))
    pm = QPixmap(W, H)
    pm.fill(QColor("white"))

    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    r = _Renderer(project, px_per_mm)
    r.render_page(
        painter, side, card_indices, cut_marks, back_duplex=back_duplex, duplex_flip=duplex_flip
    )
    painter.end()
    return pm


# ---------------------------------------------------------------------------
# Vorschau-Widget
# ---------------------------------------------------------------------------


class _PreviewWidget(QWidget):
    """Zeigt die gerenderte Seite zentriert, skaliert nach Zoom."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap: QPixmap | None = None
        self.setMinimumSize(200, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_pixmap(self, pm: QPixmap):
        self._pixmap = pm
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#555555"))
        if self._pixmap:
            # Zentriert zeichnen (1:1, Scrollbereich übernimmt Zoom)
            x = max(0, (self.width() - self._pixmap.width()) // 2)
            y = max(0, (self.height() - self._pixmap.height()) // 2)
            painter.drawPixmap(x, y, self._pixmap)
        painter.end()


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------


class PrintPreviewDialog(QDialog):
    def __init__(self, project: Project, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Print Preview"))
        self.resize(900, 700)
        self._project = project
        self._side: str = "front"
        self._cut_marks: bool = True
        self._px_per_mm: float = 3.0  # Render-Auflösung (Basis)
        self._zoom: float = 1.0  # Anzeigeskalierung
        self._build_ui()
        self._refresh()

    # ------------------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)

        # --- Toolbar oben ---
        toolbar = QHBoxLayout()

        # Side selection
        side_box = QGroupBox(self.tr("Side"))
        side_hl = QHBoxLayout(side_box)
        side_hl.setContentsMargins(4, 2, 4, 2)
        self._rb_front = QRadioButton(self.tr("Front"))
        self._rb_front.setChecked(True)
        self._rb_back = QRadioButton(self.tr("Back"))
        self._rb_both_prev = QRadioButton(self.tr("Duplex"))
        bg = QButtonGroup(self)
        bg.addButton(self._rb_front)
        bg.addButton(self._rb_back)
        bg.addButton(self._rb_both_prev)
        self._rb_front.toggled.connect(self._on_side_changed)
        self._rb_back.toggled.connect(self._on_side_changed)
        self._rb_both_prev.toggled.connect(self._on_side_changed)
        side_hl.addWidget(self._rb_front)
        side_hl.addWidget(self._rb_back)
        side_hl.addWidget(self._rb_both_prev)
        toolbar.addWidget(side_box)

        # Bindekante (nur bei Beidseitig relevant)
        from PySide6.QtWidgets import QComboBox

        self._flip_combo_prev = QComboBox()
        self._flip_combo_prev.addItem(self.tr("Long edge"), "long-edge")
        self._flip_combo_prev.addItem(self.tr("Short edge"), "short-edge")
        self._flip_combo_prev.setEnabled(False)
        self._flip_combo_prev.currentIndexChanged.connect(self._refresh)
        toolbar.addWidget(QLabel(self.tr("Binding edge:")))
        toolbar.addWidget(self._flip_combo_prev)

        # Cut marks
        self._chk_marks = QCheckBox(self.tr("Cut marks"))
        self._chk_marks.setChecked(True)
        self._chk_marks.stateChanged.connect(self._refresh)
        toolbar.addWidget(self._chk_marks)

        toolbar.addSpacerItem(QSpacerItem(20, 0, QSizePolicy.Policy.Expanding))

        # Zoom
        toolbar.addWidget(QLabel(self.tr("Zoom:")))
        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setFixedWidth(140)
        self._zoom_slider.setRange(20, 200)  # 20 % … 200 %
        self._zoom_slider.setValue(100)
        self._zoom_slider.setTickInterval(20)
        self._zoom_slider.valueChanged.connect(self._on_zoom)
        self._zoom_lbl = QLabel("100 %")
        self._zoom_lbl.setFixedWidth(44)
        toolbar.addWidget(self._zoom_slider)
        toolbar.addWidget(self._zoom_lbl)

        # Seite: Infos
        self._info_lbl = QLabel()
        self._info_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        toolbar.addWidget(self._info_lbl)

        root.addLayout(toolbar)

        # --- Scroll-Bereich mit Vorschau ---
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(False)
        self._scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._scroll.setStyleSheet("background:#555;")
        self._preview = _PreviewWidget()
        self._scroll.setWidget(self._preview)
        root.addWidget(self._scroll, 1)

        # --- Buttons unten ---
        btn_row = QHBoxLayout()
        btn_print = QPushButton(self.tr("Print / Export…"))
        btn_print.clicked.connect(self._open_print_dialog)
        btn_close = QPushButton(self.tr("Close"))
        btn_close.clicked.connect(self.reject)
        btn_row.addWidget(btn_print)
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        root.addLayout(btn_row)

    # ------------------------------------------------------------------
    def _on_side_changed(self, checked: bool):
        is_both = self._rb_both_prev.isChecked()
        self._flip_combo_prev.setEnabled(is_both)
        self._refresh()

    def _on_zoom(self, value: int):
        self._zoom = value / 100.0
        self._zoom_lbl.setText(f"{value} %")
        self._refresh()

    def _refresh(self):
        is_both = self._rb_both_prev.isChecked()
        if self._rb_front.isChecked():
            self._side = "front"
        elif self._rb_back.isChecked():
            self._side = "back"
        else:
            self._side = "both"
        self._cut_marks = self._chk_marks.isChecked()

        indices = list(range(len(self._project.cards)))
        slots = self._project.paper_template.cols * self._project.paper_template.rows
        pages = max(1, -(-len(indices) // slots)) if slots > 0 else 1

        px_per_mm = self._px_per_mm * self._zoom
        flip = self._flip_combo_prev.currentData()

        if is_both:
            # Beide Seiten nebeneinander rendern
            pm_front = render_page_to_pixmap(
                self._project,
                "front",
                indices,
                cut_marks=self._cut_marks,
                px_per_mm=max(0.3, px_per_mm),
                back_duplex=False,
            )
            pm_back = render_page_to_pixmap(
                self._project,
                "back",
                indices,
                cut_marks=self._cut_marks,
                px_per_mm=max(0.3, px_per_mm),
                back_duplex=True,
                duplex_flip=flip,
            )
            GAP = 20
            W = pm_front.width() + GAP + pm_back.width()
            H = max(pm_front.height(), pm_back.height())
            combined = QPixmap(W, H)
            combined.fill(QColor("#555555"))
            p = QPainter(combined)
            p.drawPixmap(0, 0, pm_front)
            # Trennlinie
            p.setPen(QPen(QColor("#888888"), 1, Qt.PenStyle.DashLine))
            p.drawLine(pm_front.width() + GAP // 2, 0, pm_front.width() + GAP // 2, H)
            p.drawPixmap(pm_front.width() + GAP, 0, pm_back)
            # Labels
            from PySide6.QtGui import QFont as _QFont

            lbl_font = _QFont()
            lbl_font.setPixelSize(13)
            lbl_font.setBold(True)
            p.setFont(lbl_font)
            p.setPen(QColor("#dddddd"))
            p.drawText(8, 18, self.tr("Front"))
            p.drawText(pm_front.width() + GAP + 8, 18, self.tr("Back"))
            p.end()
            pm = combined
        else:
            pm = render_page_to_pixmap(
                self._project,
                self._side,
                indices,
                cut_marks=self._cut_marks,
                px_per_mm=max(0.3, px_per_mm),
            )

        self._preview.set_pixmap(pm)
        self._preview.setFixedSize(pm.size())

        pt = self._project.paper_template
        self._info_lbl.setText(
            self.tr(
                "{w}×{h} mm  |  {slots} slots/page  |  {cards} card(s)  |  {pages} page(s)"
            ).format(
                w=f"{pt.paper_width:.0f}",
                h=f"{pt.paper_height:.0f}",
                slots=slots,
                cards=len(indices),
                pages=pages,
            )
        )

    def _open_print_dialog(self):
        from .print_dialog import PrintExportDialog

        dlg = PrintExportDialog(self._project, self)
        dlg.exec()
