"""
Moderner About/Info-Dialog für CardForge.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QDesktopServices,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPalette,
)
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ._app_icon import get_app_icon

_APP_VERSION = "1.0.0"
_COPYRIGHT = "© 2024 – 2026 Andreas Kempe"
_WEBSITE = "https://cardforge.byte-artist.de"
_GITHUB = "https://github.com/mastercad/cardforge"
_EMAIL = "andreas.kempe@byte-artist.de"


# ── Gradient-Header ────────────────────────────────────────────────────────────


class _HeaderWidget(QWidget):
    """Gemalt: Farbverlauf + App-Icon + Name + Version."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        pal = QApplication.palette()
        self._col_top = pal.color(QPalette.ColorRole.Highlight)
        self._col_bot = pal.color(QPalette.ColorRole.AlternateBase)

        icon = get_app_icon()
        self._icon_px = icon.pixmap(QSize(72, 72))

    def paintEvent(self, _event) -> None:  # noqa: ANN001
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        grad = QLinearGradient(0, 0, self.width(), self.height())
        c_top = QColor(self._col_top)
        c_top.setAlpha(200)
        c_bot = QColor(self._col_bot)
        grad.setColorAt(0.0, c_top)
        grad.setColorAt(1.0, c_bot)
        path = QPainterPath()
        path.addRect(0, 0, self.width(), self.height())
        p.fillPath(path, grad)

        p.setPen(QColor(255, 255, 255, 40))
        p.drawLine(0, 0, self.width(), 0)

        icon_x = 28
        icon_y = (self.height() - self._icon_px.height()) // 2
        p.drawPixmap(icon_x, icon_y, self._icon_px)

        name_x = icon_x + self._icon_px.width() + 20
        text_color = QColor(255, 255, 255, 230)
        p.setPen(text_color)

        font_name = QFont()
        font_name.setPointSize(22)
        font_name.setWeight(QFont.Weight.Bold)
        p.setFont(font_name)
        p.drawText(name_x, icon_y + 30, "CardForge")

        font_tag = QFont()
        font_tag.setPointSize(10)
        font_tag.setWeight(QFont.Weight.Normal)
        text_color.setAlpha(170)
        p.setPen(text_color)
        p.setFont(font_tag)
        p.drawText(
            name_x,
            icon_y + 52,
            self.tr("Professional Business Card Editor"),
        )

        badge_text = f"v{_APP_VERSION}"
        font_badge = QFont()
        font_badge.setPointSize(9)
        font_badge.setWeight(QFont.Weight.DemiBold)
        p.setFont(font_badge)
        fm = p.fontMetrics()
        bw = fm.horizontalAdvance(badge_text) + 18
        bh = fm.height() + 8
        bx = name_x
        by = icon_y + 66

        p.setBrush(QColor(255, 255, 255, 35))
        p.setPen(QColor(255, 255, 255, 60))
        p.drawRoundedRect(bx, by, bw, bh, 6, 6)

        p.setPen(QColor(255, 255, 255, 210))
        p.drawText(bx + 9, by + fm.ascent() + 4, badge_text)


# ── Link-Button ────────────────────────────────────────────────────────────────


def _link_btn(label: str, url: str, accent: str) -> QPushButton:
    btn = QPushButton(label)
    btn.setObjectName("about_link_btn")
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(
        f"""
        QPushButton#about_link_btn {{
            background: transparent;
            color: {accent};
            border: none;
            padding: 0;
            font-size: 13px;
            text-align: left;
        }}
        QPushButton#about_link_btn:hover {{
            text-decoration: underline;
        }}
    """
    )
    btn.clicked.connect(lambda: QDesktopServices.openUrl(url))
    return btn


# ── Haupt-Dialog ───────────────────────────────────────────────────────────────


class AboutDialog(QDialog):
    """Moderner Info-Dialog für Endnutzer."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("About CardForge"))
        self.setFixedWidth(460)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.MSWindowsFixedSizeDialogHint
        )

        self._build_ui()
        self._apply_style()

    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        pal = QApplication.palette()
        accent = pal.color(QPalette.ColorRole.Highlight).name()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(_HeaderWidget())

        body = QWidget()
        body.setObjectName("about_body")
        body_vl = QVBoxLayout(body)
        body_vl.setContentsMargins(28, 22, 28, 24)
        body_vl.setSpacing(0)

        # Beschreibung
        desc = QLabel(
            self.tr(
                "CardForge lets you design, manage and print professional business cards "
                "with full layout freedom \u2014 text, images, icons, QR codes and shapes, "
                "all on a pixel-perfect canvas with PDF export and mail merge built in."
            )
        )
        desc.setObjectName("about_desc")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        body_vl.addWidget(desc)

        body_vl.addSpacing(20)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("about_sep")
        body_vl.addWidget(sep)

        body_vl.addSpacing(16)

        # Links
        links_title = QLabel(self.tr("Links"))
        links_title.setObjectName("about_section_title")
        body_vl.addWidget(links_title)

        body_vl.addSpacing(8)

        for label, url in (
            (f"  {_WEBSITE}", _WEBSITE),
            (f"  {_GITHUB}", _GITHUB),
        ):
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(0)
            btn = _link_btn(label, url, accent)
            row.addWidget(btn)
            row.addStretch()
            body_vl.addLayout(row)
            body_vl.addSpacing(4)

        body_vl.addSpacing(4)

        # Kontakt
        mail_row = QHBoxLayout()
        mail_row.setContentsMargins(0, 0, 0, 0)
        mail_lbl = QLabel(self.tr("Contact:"))
        mail_lbl.setObjectName("about_meta")
        mail_row.addWidget(mail_lbl)
        mail_row.addSpacing(6)
        mail_btn = _link_btn(_EMAIL, f"mailto:{_EMAIL}", accent)
        mail_row.addWidget(mail_btn)
        mail_row.addStretch()
        body_vl.addLayout(mail_row)

        body_vl.addSpacing(16)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setObjectName("about_sep")
        body_vl.addWidget(sep2)

        body_vl.addSpacing(14)

        # Copyright + Lizenz
        copy_lbl = QLabel(f"{_COPYRIGHT}  ·  MIT License")
        copy_lbl.setObjectName("about_meta")
        body_vl.addWidget(copy_lbl)

        body_vl.addSpacing(18)

        # Schließen
        btn_row = QHBoxLayout()
        btn_row.setSpacing(0)
        btn_row.addStretch()
        close_btn = QPushButton(self.tr("Close"))
        close_btn.setObjectName("about_close_btn")
        close_btn.setDefault(True)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        body_vl.addLayout(btn_row)

        root.addWidget(body)

        self._feedback = QLabel("")
        self._feedback.setObjectName("about_feedback")
        self._feedback.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._feedback.hide()
        body_vl.addWidget(self._feedback)

    # ------------------------------------------------------------------

    def _apply_style(self) -> None:
        pal = QApplication.palette()
        accent = pal.color(QPalette.ColorRole.Highlight).name()
        accent_d = pal.color(QPalette.ColorRole.Highlight).darker(120).name()
        bg = pal.color(QPalette.ColorRole.Window).name()
        text = pal.color(QPalette.ColorRole.WindowText).name()
        text_sec = pal.color(QPalette.ColorRole.PlaceholderText).name()
        border = pal.color(QPalette.ColorRole.Mid).name()

        self.setStyleSheet(f"""
            QDialog {{
                background: {bg};
            }}
            #about_body {{
                background: {bg};
            }}
            #about_desc {{
                color: {text};
                font-size: 13px;
            }}
            #about_section_title {{
                color: {text_sec};
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.06em;
            }}
            #about_meta {{
                color: {text_sec};
                font-size: 12px;
            }}
            #about_sep {{
                color: {border};
                background: {border};
                max-height: 1px;
                border: none;
            }}
            #about_close_btn {{
                background: {accent};
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 7px 24px;
                font-size: 13px;
                font-weight: 600;
            }}
            #about_close_btn:hover {{
                background: {accent_d};
            }}
            #about_close_btn:pressed {{
                background: {accent_d};
            }}
            #about_feedback {{
                color: {accent};
                font-size: 11px;
                padding-bottom: 2px;
            }}
        """)

    # ------------------------------------------------------------------

    def _show_feedback(self, msg: str) -> None:
        self._feedback.setText(msg)
        self._feedback.show()
        QTimer.singleShot(2500, self._feedback.hide)
