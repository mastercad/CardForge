"""
Papiervorlagen-Editor-Dialog – visueller WYSIWYG-Editor.
Links: kompakte Einstellungen.  Rechts: maßstabsgetreue Vorschau.
"""

from __future__ import annotations

from PySide6.QtCore import QCoreApplication, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .models import PaperTemplate

# Sprachunabhängige Schlüssel → Abmessungen (Breite, Höhe in mm) oder None
_PAPER_SIZE_DIMS: dict[str, tuple[float, float] | None] = {
    "a4_portrait": (210.0, 297.0),
    "a4_landscape": (297.0, 210.0),
    "a5_portrait": (148.0, 210.0),
    "a5_landscape": (210.0, 148.0),
    "letter_portrait": (215.9, 279.4),
    "letter_landscape": (279.4, 215.9),
    "custom": None,
}


def _paper_size_labels() -> dict[str, str]:
    """Gibt übersetzte Anzeigenamen für jeden Papierformat-Schlüssel zurück."""
    tr = lambda s: QCoreApplication.translate("PaperTemplateDialog", s)  # noqa: E731
    return {
        "a4_portrait": tr("A4 Portrait"),
        "a4_landscape": tr("A4 Landscape"),
        "a5_portrait": tr("A5 Portrait"),
        "a5_landscape": tr("A5 Landscape"),
        "letter_portrait": tr("Letter Portrait"),
        "letter_landscape": tr("Letter Landscape"),
        "custom": tr("Custom"),
    }


_C_BG = QColor("#1e1f26")
_C_PAPER = QColor("#ffffff")
_C_SHADOW = QColor(0, 0, 0, 60)
_C_MARGIN = QColor(79, 142, 247, 35)
_C_MARGIN_BD = QColor("#4f8ef7")
_C_CARD = QColor(200, 230, 255, 160)
_C_CARD_BD = QColor("#3a7fd4")
_C_LABEL = QColor("#3a6ed4")


class _PaperPreview(QWidget):
    """Maßstabsgetreue Papier-Vorschau mit Rändern und Karten-Slots."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tmpl: PaperTemplate = PaperTemplate()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(500, 400)

    def set_template(self, t: PaperTemplate):
        self._tmpl = t
        self.update()

    def paintEvent(self, _event):
        t = self._tmpl
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), _C_BG)

        W, H = self.width(), self.height()
        PADDING = 24

        pw_mm, ph_mm = t.paper_width, t.paper_height
        scale = min((W - 2 * PADDING) / pw_mm, (H - 2 * PADDING - 20) / ph_mm)

        pw_px = pw_mm * scale
        ph_px = ph_mm * scale
        ox = (W - pw_px) / 2
        oy = (H - ph_px) / 2 - 10

        def mm(v):
            return v * scale

        # Schatten
        painter.fillRect(QRectF(ox + 3, oy + 3, pw_px, ph_px), _C_SHADOW)

        # Papier
        paper_r = QRectF(ox, oy, pw_px, ph_px)
        painter.fillRect(paper_r, _C_PAPER)
        painter.setPen(QPen(QColor("#b0b0b0"), 1))
        painter.drawRect(paper_r)

        # Ränder einfärben
        ml = mm(t.margin_left)
        mr = mm(t.margin_right)
        mt = mm(t.margin_top)
        mb = mm(t.margin_bottom)
        inner_x = ox + ml
        inner_y = oy + mt
        inner_w = pw_px - ml - mr
        inner_h = ph_px - mt - mb

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_C_MARGIN)
        painter.drawRect(QRectF(ox, oy, pw_px, mt))
        painter.drawRect(QRectF(ox, oy + ph_px - mb, pw_px, mb))
        painter.drawRect(QRectF(ox, oy + mt, ml, inner_h))
        painter.drawRect(QRectF(ox + pw_px - mr, oy + mt, mr, inner_h))

        painter.setPen(QPen(_C_MARGIN_BD, 0.8, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(inner_x, inner_y, inner_w, inner_h))

        # Karten-Slots
        cw = mm(t.card_width)
        ch = mm(t.card_height)
        gh = mm(t.gap_h)
        gv = mm(t.gap_v)

        painter.setBrush(_C_CARD)
        painter.setPen(QPen(_C_CARD_BD, 0.8))

        for row in range(t.rows):
            for col in range(t.cols):
                cx = inner_x + col * (cw + gh)
                cy = inner_y + row * (ch + gv)
                if cx + cw <= ox + pw_px + 0.5 and cy + ch <= oy + ph_px + 0.5:
                    painter.drawRect(QRectF(cx, cy, cw, ch))

        # Maß-Label
        font = QFont()
        font.setPixelSize(10)
        painter.setFont(font)
        painter.setPen(QColor("#6b7099"))
        painter.drawText(
            QRectF(ox, oy + ph_px + 6, pw_px, 16),
            Qt.AlignmentFlag.AlignCenter,
            f"{t.paper_width:.0f} × {t.paper_height:.0f} mm  |  "
            f"{t.cols} × {t.rows} = {t.cols * t.rows} Karten/Seite",
        )

        if t.rows > 0 and t.cols > 0:
            painter.setPen(_C_LABEL)
            font2 = QFont()
            font2.setPixelSize(max(8, int(min(cw, ch) * 0.18)))
            painter.setFont(font2)
            painter.drawText(
                QRectF(inner_x, inner_y, cw, ch),
                Qt.AlignmentFlag.AlignCenter,
                f"{t.card_width:.1f}×{t.card_height:.1f}",
            )

        painter.end()


class PaperTemplateDialog(QDialog):
    def __init__(self, template: PaperTemplate | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Edit Paper Template"))
        self._template = template or PaperTemplate()
        self._build_ui()
        self._load()
        self.adjustSize()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # ── Linke Spalte ──────────────────────────────────────────────
        left = QWidget()
        left.setFixedWidth(340)
        left.setStyleSheet("background:palette(alternate-base);")
        lv = QVBoxLayout(left)
        lv.setContentsMargins(12, 14, 12, 12)
        lv.setSpacing(8)

        hdr = QLabel(self.tr("PAPER TEMPLATE"))
        hdr.setStyleSheet(
            "color:palette(shadow); font-size:10px; font-weight:700; letter-spacing:1px;"
        )
        lv.addWidget(hdr)

        self._name = QLineEdit()
        self._name.setPlaceholderText(self.tr("Template name …"))
        lv.addWidget(self._name)

        # Paper format
        grp_paper = QGroupBox(self.tr("Paper Format"))
        fl = QFormLayout(grp_paper)
        fl.setSpacing(4)
        self._paper_preset = QComboBox()
        labels = _paper_size_labels()
        for key, label in labels.items():
            self._paper_preset.addItem(label, key)  # label angezeigt, key als UserData
        self._paper_preset.currentIndexChanged.connect(self._on_preset)
        fl.addRow(self.tr("Preset:"), self._paper_preset)
        self._pw = self._dbl(1, 2000, " mm")
        self._ph = self._dbl(1, 2000, " mm")
        fl.addRow(self.tr("Width:"), self._pw)
        fl.addRow(self.tr("Height:"), self._ph)
        lv.addWidget(grp_paper)

        # Business card
        grp_card = QGroupBox(self.tr("Business Card"))
        fl2 = QFormLayout(grp_card)
        fl2.setSpacing(4)
        self._cw = self._dbl(1, 500, " mm")
        self._ch = self._dbl(1, 500, " mm")
        fl2.addRow(self.tr("Width:"), self._cw)
        fl2.addRow(self.tr("Height:"), self._ch)
        lv.addWidget(grp_card)

        # Margins
        grp_margin = QGroupBox(self.tr("Page Margins"))
        fl3 = QFormLayout(grp_margin)
        fl3.setSpacing(4)
        self._mt = self._dbl(0, 200, " mm")
        self._mb = self._dbl(0, 200, " mm")
        self._ml = self._dbl(0, 200, " mm")
        self._mr = self._dbl(0, 200, " mm")
        fl3.addRow(self.tr("Top:"), self._mt)
        fl3.addRow(self.tr("Bottom:"), self._mb)
        fl3.addRow(self.tr("Left:"), self._ml)
        fl3.addRow(self.tr("Right:"), self._mr)
        lv.addWidget(grp_margin)

        # Gaps & count
        grp_gap = QGroupBox(self.tr("Gaps & Count"))
        fl4 = QFormLayout(grp_gap)
        fl4.setSpacing(4)
        self._gh = self._dbl(0, 100, " mm")
        self._gv = self._dbl(0, 100, " mm")
        fl4.addRow(self.tr("Horizontal:"), self._gh)
        fl4.addRow(self.tr("Vertical:"), self._gv)

        self._cols = QSpinBox()
        self._cols.setRange(1, 20)
        self._cols.setMinimumWidth(80)
        self._rows = QSpinBox()
        self._rows.setRange(1, 40)
        self._rows.setMinimumWidth(80)
        fl4.addRow(self.tr("Columns:"), self._cols)
        fl4.addRow(self.tr("Rows:"), self._rows)

        btn_auto = QPushButton(self.tr("↺  Auto-calculate"))
        btn_auto.clicked.connect(self._auto_calc)
        fl4.addRow("", btn_auto)
        lv.addWidget(grp_gap)

        lv.addStretch()

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._accept)
        btns.rejected.connect(self.reject)
        lv.addWidget(btns)

        root.addWidget(left)

        # Trennlinie
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("background:palette(mid);")
        sep.setFixedWidth(1)
        root.addWidget(sep)

        # ── Rechte Spalte: Vorschau ───────────────────────────────────
        self._preview = _PaperPreview()
        root.addWidget(self._preview, 1)

        # Signale → Vorschau
        for w in (
            self._pw,
            self._ph,
            self._cw,
            self._ch,
            self._mt,
            self._mb,
            self._ml,
            self._mr,
            self._gh,
            self._gv,
        ):
            w.valueChanged.connect(self._update_preview)
        for w2 in (self._cols, self._rows):
            w2.valueChanged.connect(self._update_preview)

    def _dbl(self, min_v, max_v, suffix="") -> QDoubleSpinBox:
        s = QDoubleSpinBox()
        s.setRange(min_v, max_v)
        s.setDecimals(2)
        s.setSuffix(suffix)
        s.setMinimumWidth(120)
        return s

    def _load(self):
        t = self._template
        # Signale blockieren: _gather() würde sonst halb-gesetzte Werte
        # in self._template zurückschreiben und nachfolgende setValue()-
        # Aufrufe greifen auf korrupte Werte zurück.
        all_spinboxes = (
            self._pw,
            self._ph,
            self._cw,
            self._ch,
            self._mt,
            self._mb,
            self._ml,
            self._mr,
            self._gh,
            self._gv,
            self._cols,
            self._rows,
        )
        for w in all_spinboxes:
            w.blockSignals(True)
        self._name.setText(t.name)
        self._pw.setValue(t.paper_width)
        self._ph.setValue(t.paper_height)
        self._cw.setValue(t.card_width)
        self._ch.setValue(t.card_height)
        self._mt.setValue(t.margin_top)
        self._mb.setValue(t.margin_bottom)
        self._ml.setValue(t.margin_left)
        self._mr.setValue(t.margin_right)
        self._gh.setValue(t.gap_h)
        self._gv.setValue(t.gap_v)
        self._cols.setValue(t.cols)
        self._rows.setValue(t.rows)
        for w in all_spinboxes:
            w.blockSignals(False)
        self._update_preview()

    def _on_preset(self, _index: int):
        key = self._paper_preset.currentData()
        size = _PAPER_SIZE_DIMS.get(key)
        if size:
            self._pw.setValue(size[0])
            self._ph.setValue(size[1])

    def _auto_calc(self):
        t = self._gather()
        t.auto_calc()
        self._cols.setValue(t.cols)
        self._rows.setValue(t.rows)

    def _update_preview(self):
        self._preview.set_template(self._gather())

    def _gather(self) -> PaperTemplate:
        t = self._template
        t.name = self._name.text() or self.tr("Template")
        t.paper_width = self._pw.value()
        t.paper_height = self._ph.value()
        t.card_width = self._cw.value()
        t.card_height = self._ch.value()
        t.margin_top = self._mt.value()
        t.margin_bottom = self._mb.value()
        t.margin_left = self._ml.value()
        t.margin_right = self._mr.value()
        t.gap_h = self._gh.value()
        t.gap_v = self._gv.value()
        t.cols = self._cols.value()
        t.rows = self._rows.value()
        return t

    def _accept(self):
        self._gather()
        self.accept()

    def result_template(self) -> PaperTemplate:
        return self._template
