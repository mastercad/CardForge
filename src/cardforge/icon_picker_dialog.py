"""
Icon-Auswahldialog für CardForge.
Zeigt alle verfügbaren Icons als Grid mit Label.
"""

from __future__ import annotations

import contextlib

import qtawesome as qta
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

from .icons import ICONS, get_icon_label

_ICON_SIZE = 48
_GRID_SIZE = 90


class IconPickerDialog(QDialog):
    """
    Kleiner Dialog zum Auswählen eines Icons.

    Rückgabe: ``selected_icon`` (str, interner Name) oder ``None`` bei Abbruch.
    """

    def __init__(self, current: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Choose Icon"))
        self.resize(600, 440)
        self._selected: str = current
        self._build_ui()
        self._highlight(current)

    @property
    def selected_icon(self) -> str | None:
        return self._selected or None

    # ------------------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(8)

        app = QApplication.instance()
        icon_color = (
            app.palette().color(QPalette.ColorRole.PlaceholderText).name()
            if isinstance(app, QApplication)
            else "#cccccc"
        )

        self._list = QListWidget()
        self._list.setViewMode(QListWidget.ViewMode.IconMode)
        self._list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self._list.setMovement(QListWidget.Movement.Static)
        self._list.setWrapping(True)
        self._list.setIconSize(QSize(_ICON_SIZE, _ICON_SIZE))
        self._list.setGridSize(QSize(_GRID_SIZE, _GRID_SIZE))
        self._list.setSpacing(4)
        self._list.setUniformItemSizes(True)
        root.addWidget(self._list)

        for name, fa_id in ICONS.items():
            item = QListWidgetItem(get_icon_label(name))
            item.setData(Qt.ItemDataRole.UserRole, name)
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
            with contextlib.suppress(Exception):
                item.setIcon(qta.icon(fa_id, color=icon_color))
            self._list.addItem(item)

        self._list.currentItemChanged.connect(self._on_item_changed)

        # Label unterhalb
        self._info = QLabel("")
        self._info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._info.setStyleSheet("color: palette(link); font-size: 11px;")
        root.addWidget(self._info)

        bbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        root.addWidget(bbox)

    # ------------------------------------------------------------------
    def _on_item_changed(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None):
        if current is None:
            return
        name = current.data(Qt.ItemDataRole.UserRole)
        self._selected = name
        self._info.setText(get_icon_label(name))

    def _on_click(self, name: str):
        """Kept for test compatibility."""
        self._selected = name
        self._highlight(name)

    def _highlight(self, name: str):
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == name:
                self._list.setCurrentItem(item)
                break
        self._info.setText(get_icon_label(name) if name else "")
