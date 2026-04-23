"""
Eigenschaften-Panel für selektierte Elemente.
Zeigt kontextabhängig Text-, Bild-, Form- oder QR-Eigenschaften.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFontDatabase
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .icon_picker_dialog import IconPickerDialog
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


class ColorButton(QPushButton):
    colorChanged = Signal(str)

    def __init__(self, color: str = "#000000", parent=None):
        super().__init__(parent)
        self._color = color
        self._refresh()
        self.clicked.connect(self._pick)

    def set_color(self, color: str):
        self._color = color
        self._refresh()

    def color(self) -> str:
        return self._color

    def _refresh(self):
        self.setFixedSize(28, 26)
        lum = sum(int(self._color.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)) / 3
        border = "#6b7099" if lum > 60 else "#9a9bb0"
        self.setStyleSheet(
            f"background:{self._color}; border:1px solid {border};border-radius:5px;"
        )

    def _pick(self):
        from PySide6.QtGui import QPalette
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        assert isinstance(app, QApplication)
        saved_ss = app.styleSheet()
        saved_pal = app.palette()
        app.setStyleSheet("")
        app.setPalette(QPalette())
        try:
            c = QColorDialog.getColor(QColor(self._color), self)
        finally:
            app.setStyleSheet(saved_ss)
            app.setPalette(saved_pal)
        if c.isValid():
            self._color = c.name()
            self._refresh()
            self.colorChanged.emit(self._color)


class PropertiesPanel(QWidget):
    """Rechtes Panel – zeigt Eigenschaften des selektierten Elements."""

    elementChanged = Signal()
    autoFitRequested = Signal()  # Textelement-Inhalt/-Font geändert → Rahmen anpassen

    def __init__(self, parent=None):
        super().__init__(parent)
        self._elements: list[CardElement] = []
        self._updating = False
        self._build_ui()

    # ------------------------------------------------------------------
    def set_elements(self, elements: list[CardElement]):
        self._elements = elements
        self._load()

    # ------------------------------------------------------------------
    def _build_ui(self):
        self.setStyleSheet("PropertiesPanel { border-left: 1px solid palette(mid); }")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # Panel-Header
        header = QWidget()
        header.setFixedHeight(28)
        header.setStyleSheet("background:palette(window); border-bottom:1px solid palette(mid);")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(10, 0, 10, 0)
        hdr_lbl = QLabel(self.tr("PROPERTIES"))
        hdr_lbl.setStyleSheet(
            "color:palette(shadow); font-size:10px; font-weight:700; letter-spacing:1px; background:transparent;"
        )
        hl.addWidget(hdr_lbl)
        root.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        root.addWidget(scroll)
        self._scroll = scroll

        # Platzhalter wenn nichts selektiert
        self._placeholder = QLabel(self.tr("No element\nselected"))
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet(
            "color:palette(mid); font-size:12px; background:transparent;"
        )
        root.addWidget(self._placeholder)

        inner = QWidget()
        scroll.setWidget(inner)
        self._inner_layout = QVBoxLayout(inner)
        self._inner_layout.setContentsMargins(8, 8, 8, 8)
        self._inner_layout.setSpacing(6)

        # --- Position & Größe ---
        grp_pos = QGroupBox(self.tr("Position & Size"))
        fl = QFormLayout(grp_pos)
        self._x = self._dbl(-9999, 9999, " mm")
        fl.addRow(self.tr("X:"), self._x)
        self._y = self._dbl(-9999, 9999, " mm")
        fl.addRow(self.tr("Y:"), self._y)
        self._w = self._dbl(0.1, 9999, " mm")
        fl.addRow(self.tr("Width:"), self._w)
        self._h = self._dbl(0.1, 9999, " mm")
        fl.addRow(self.tr("Height:"), self._h)
        self._rot = self._dbl(-360, 360, "°")
        fl.addRow(self.tr("Rotation:"), self._rot)
        self._inner_layout.addWidget(grp_pos)

        # --- Text ---
        self._grp_text = QGroupBox(self.tr("Text"))
        fl2 = QFormLayout(self._grp_text)
        self._text_edit = QTextEdit()
        self._text_edit.setFixedHeight(60)
        fl2.addRow(self.tr("Text:"), self._text_edit)

        self._font_family = QComboBox()
        self._font_family.setEditable(True)
        self._font_family.addItems(sorted(QFontDatabase.families()))
        fl2.addRow(self.tr("Font:"), self._font_family)

        self._font_size = self._dbl(1, 500, " pt")
        fl2.addRow(self.tr("Size:"), self._font_size)

        style_row = QHBoxLayout()
        self._bold = QCheckBox("B")
        self._bold.setStyleSheet("font-weight:bold")
        self._italic = QCheckBox("I")
        self._italic.setStyleSheet("font-style:italic")
        self._underline = QCheckBox("U")
        self._underline.setStyleSheet("text-decoration:underline")
        for w in (self._bold, self._italic, self._underline):
            style_row.addWidget(w)
        style_row.addStretch()
        fl2.addRow(self.tr("Style:"), style_row)

        self._text_color = ColorButton()
        fl2.addRow(self.tr("Color:"), self._text_color)

        h_align_row = QHBoxLayout()
        self._h_align = QComboBox()
        self._h_align.addItems(["left", "center", "right", "justify"])
        self._v_align = QComboBox()
        self._v_align.addItems(["top", "middle", "bottom"])
        h_align_row.addWidget(QLabel("H:"))
        h_align_row.addWidget(self._h_align)
        h_align_row.addWidget(QLabel("V:"))
        h_align_row.addWidget(self._v_align)
        fl2.addRow(self.tr("Alignment:"), h_align_row)

        self._text_wrap = QCheckBox(self.tr("Word wrap"))
        fl2.addRow("", self._text_wrap)
        self._inner_layout.addWidget(self._grp_text)

        # --- Bild ---
        self._grp_image = QGroupBox(self.tr("Image"))
        fl3 = QFormLayout(self._grp_image)
        self._img_path = QLineEdit()
        self._img_path.setReadOnly(True)
        btn_img = QPushButton(self.tr("Browse…"))
        btn_img.clicked.connect(self._browse_image)
        fl3.addRow(self.tr("File:"), self._img_path)
        fl3.addRow("", btn_img)
        self._keep_aspect = QCheckBox(self.tr("Keep aspect ratio"))
        fl3.addRow("", self._keep_aspect)
        self._inner_layout.addWidget(self._grp_image)

        # --- Formen / Rahmen ---
        self._grp_shape = QGroupBox(self.tr("Shape / Border"))
        fl4 = QFormLayout(self._grp_shape)
        self._fill_color = ColorButton("#ffffff")
        fl4.addRow(self.tr("Fill color:"), self._fill_color)
        self._border_color = ColorButton("#000000")
        fl4.addRow(self.tr("Border color:"), self._border_color)
        self._border_width = self._dbl(0, 50, " pt")
        fl4.addRow(self.tr("Border width:"), self._border_width)
        self._inner_layout.addWidget(self._grp_shape)

        # --- QR-Code ---
        self._grp_qr = QGroupBox(self.tr("QR Code"))
        fl5 = QFormLayout(self._grp_qr)
        self._qr_data = QLineEdit()
        fl5.addRow(self.tr("Content:"), self._qr_data)
        self._inner_layout.addWidget(self._grp_qr)

        # --- Icon ---
        self._grp_icon = QGroupBox(self.tr("Icon"))
        fl6 = QFormLayout(self._grp_icon)
        icon_row = QHBoxLayout()
        self._icon_name_lbl = QLabel()
        self._icon_name_lbl.setStyleSheet("font-style: italic; color: palette(placeholder-text);")
        self._btn_pick_icon = QPushButton(self.tr("Choose Icon…"))
        self._btn_pick_icon.clicked.connect(self._pick_icon)
        icon_row.addWidget(self._icon_name_lbl)
        icon_row.addWidget(self._btn_pick_icon)
        fl6.addRow(self.tr("Icon:"), icon_row)
        self._icon_color = ColorButton()
        fl6.addRow(self.tr("Color:"), self._icon_color)
        self._inner_layout.addWidget(self._grp_icon)

        grp_misc = QGroupBox(self.tr("Miscellaneous"))
        fl6 = QFormLayout(grp_misc)
        self._visible = QCheckBox(self.tr("Visible"))
        fl6.addRow("", self._visible)
        self._locked = QCheckBox(self.tr("Locked"))
        fl6.addRow("", self._locked)
        self._inner_layout.addWidget(grp_misc)

        self._inner_layout.addStretch()

        # Signale verbinden
        self._connect_signals()

    def _dbl(self, mn, mx, suffix="") -> QDoubleSpinBox:
        s = QDoubleSpinBox()
        s.setRange(mn, mx)
        s.setDecimals(2)
        s.setSuffix(suffix)
        return s

    def _connect_signals(self):
        self._x.valueChanged.connect(self._apply)
        self._y.valueChanged.connect(self._apply)
        self._w.valueChanged.connect(self._apply)
        self._h.valueChanged.connect(self._apply)
        self._rot.valueChanged.connect(self._apply)
        self._text_edit.textChanged.connect(self._apply)
        self._font_family.currentTextChanged.connect(self._apply)
        self._font_size.valueChanged.connect(self._apply)
        self._bold.stateChanged.connect(self._apply)
        self._italic.stateChanged.connect(self._apply)
        self._underline.stateChanged.connect(self._apply)
        self._text_color.colorChanged.connect(self._apply)
        self._h_align.currentTextChanged.connect(self._apply)
        self._v_align.currentTextChanged.connect(self._apply)
        self._text_wrap.stateChanged.connect(self._apply)
        self._img_path.textChanged.connect(self._apply)
        self._keep_aspect.stateChanged.connect(self._apply)
        self._fill_color.colorChanged.connect(self._apply)
        self._border_color.colorChanged.connect(self._apply)
        self._border_width.valueChanged.connect(self._apply)
        self._qr_data.textChanged.connect(self._apply)
        self._icon_color.colorChanged.connect(self._apply)
        self._visible.stateChanged.connect(self._apply)
        self._locked.stateChanged.connect(self._apply)

    # ------------------------------------------------------------------
    def _load(self):
        self._updating = True
        has = len(self._elements) > 0
        e = self._elements[0] if has else None

        if e:
            self._x.setValue(e.x)
            self._y.setValue(e.y)
            self._w.setValue(e.width)
            self._h.setValue(e.height)
            self._rot.setValue(e.rotation)

            self._text_edit.setPlainText(e.text)
            self._font_family.setCurrentText(e.font_family)
            self._font_size.setValue(e.font_size)
            self._bold.setChecked(e.font_bold)
            self._italic.setChecked(e.font_italic)
            self._underline.setChecked(e.font_underline)
            self._text_color.set_color(e.color)
            self._h_align.setCurrentText(e.h_align)
            self._v_align.setCurrentText(e.v_align)
            self._text_wrap.setChecked(e.text_wrap)

            self._img_path.setText(e.image_path)
            self._keep_aspect.setChecked(e.keep_aspect)

            self._fill_color.set_color(e.fill_color)
            self._border_color.set_color(e.border_color)
            self._border_width.setValue(e.border_width)

            self._qr_data.setText(e.qr_data)
            self._icon_name_lbl.setText(e.icon_name or "–")
            self._icon_color.set_color(e.color)
            self._visible.setChecked(e.visible)
            self._locked.setChecked(e.locked)

            is_text = e.type == ELEMENT_TEXT
            is_image = e.type == ELEMENT_IMAGE
            is_shape = e.type in (ELEMENT_RECT, ELEMENT_ELLIPSE, ELEMENT_LINE)
            is_qr = e.type == ELEMENT_QR
            is_icon = e.type == ELEMENT_ICON
        else:
            is_text = is_image = is_shape = is_qr = is_icon = False

        self._grp_text.setVisible(is_text)
        self._grp_image.setVisible(is_image)
        self._grp_shape.setVisible(is_shape)
        self._grp_qr.setVisible(is_qr)
        self._grp_icon.setVisible(is_icon)
        self._scroll.setVisible(has)
        self._placeholder.setVisible(not has)
        self._updating = False

    def _apply(self):
        if self._updating or not self._elements:
            return
        need_autofit = False
        for e in self._elements:
            if e.type == ELEMENT_TEXT and (
                e.text != self._text_edit.toPlainText()
                or e.font_family != self._font_family.currentText()
                or abs(e.font_size - self._font_size.value()) > 0.001
                or e.font_bold != self._bold.isChecked()
                or e.font_italic != self._italic.isChecked()
                or e.font_underline != self._underline.isChecked()
                or e.text_wrap != self._text_wrap.isChecked()
            ):
                need_autofit = True
            if len(self._elements) == 1:
                e.x = self._x.value()
                e.y = self._y.value()
                e.width = self._w.value()
                e.height = self._h.value()
            e.rotation = self._rot.value()
            e.text = self._text_edit.toPlainText()
            e.font_family = self._font_family.currentText()
            e.font_size = self._font_size.value()
            e.font_bold = self._bold.isChecked()
            e.font_italic = self._italic.isChecked()
            e.font_underline = self._underline.isChecked()
            e.color = self._text_color.color()
            e.h_align = self._h_align.currentText()
            # Blocksatz erfordert Zeilenumbruch; automatisch aktivieren
            if e.h_align == "justify":
                self._text_wrap.setChecked(True)
            e.v_align = self._v_align.currentText()
            e.text_wrap = self._text_wrap.isChecked()
            e.image_path = self._img_path.text()
            e.keep_aspect = self._keep_aspect.isChecked()
            e.fill_color = self._fill_color.color()
            e.border_color = self._border_color.color()
            e.border_width = self._border_width.value()
            e.qr_data = self._qr_data.text()
            if e.type == ELEMENT_ICON:
                e.color = self._icon_color.color()
            e.visible = self._visible.isChecked()
            e.locked = self._locked.isChecked()
        if need_autofit:
            self.autoFitRequested.emit()
        self.elementChanged.emit()

    def _browse_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Select Image"),
            "",
            self.tr("Images (*.png *.jpg *.jpeg *.bmp *.gif *.svg *.webp)"),
        )
        if path:
            self._img_path.setText(path)

    def _pick_icon(self):
        current = self._elements[0].icon_name if self._elements else ""
        dlg = IconPickerDialog(current, self)
        if dlg.exec() == IconPickerDialog.DialogCode.Accepted and dlg.selected_icon:
            for e in self._elements:
                e.icon_name = dlg.selected_icon
            self._icon_name_lbl.setText(dlg.selected_icon)
            self.elementChanged.emit()
