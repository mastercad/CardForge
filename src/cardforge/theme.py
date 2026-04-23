"""
Theme-System: Dark- und Light-Mode.

Verwendung::

    # Einmalig beim Start, vor jeder Palette-Änderung:
    detect_system_theme()

    # Theme aus QSettings laden und anwenden:
    apply_theme(app, get_saved_theme())

    # Theme-Wechsel zur Laufzeit:
    save_theme("dark")
    apply_theme(app, "dark")
"""

from __future__ import annotations

from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

# ── Farb-Token ────────────────────────────────────────────────────────────────

DARK: dict[str, str] = {
    "BG_APP": "#1e1f26",
    "BG_PANEL": "#252632",
    "BG_WIDGET": "#2e2f3e",
    "BG_HOVER": "#363748",
    "ACCENT": "#4f8ef7",
    "ACCENT_D": "#3a6ed4",
    "TEXT_PRI": "#e8e9f0",
    "TEXT_SEC": "#9a9bb0",
    "TEXT_DIM": "#6b7099",
    "BORDER": "#3a3b4d",
}

LIGHT: dict[str, str] = {
    "BG_APP": "#f0f2f5",
    "BG_PANEL": "#e4e7ed",
    "BG_WIDGET": "#ffffff",
    "BG_HOVER": "#d0d5e0",
    "ACCENT": "#1a73e8",
    "ACCENT_D": "#1557b0",
    "TEXT_PRI": "#1a1b26",
    "TEXT_SEC": "#6b7280",
    "TEXT_DIM": "#8b9099",
    "BORDER": "#c4c8d4",
}

# Systemthema, einmalig vor Palette-Überschreibung gespeichert
_SYSTEM_DARK: bool | None = None


# ── Hilfsfunktionen ───────────────────────────────────────────────────────────


def detect_system_theme() -> None:
    """Einmalig direkt nach QApplication()-Erstellung aufrufen (vor apply_theme)."""
    global _SYSTEM_DARK
    app = QApplication.instance()
    if not isinstance(app, QApplication):
        return
    try:
        from PySide6.QtCore import Qt

        _SYSTEM_DARK = app.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except AttributeError:
        # Qt < 6.5: Helligkeit der aktuellen (System-)Palette prüfen
        bg = app.palette().color(QPalette.ColorRole.Window)
        _SYSTEM_DARK = bg.lightness() < 128


def is_system_dark() -> bool:
    """Gibt zurück, ob das System-Theme dunkel ist."""
    if _SYSTEM_DARK is None:
        detect_system_theme()
    return _SYSTEM_DARK if _SYSTEM_DARK is not None else True


def resolve_theme(name: str) -> str:
    """Löst 'system' zu 'dark' oder 'light' auf."""
    if name == "system":
        return "dark" if is_system_dark() else "light"
    return name if name in ("dark", "light") else "dark"


def get_saved_theme() -> str:
    """Liefert das gespeicherte Theme ('system', 'dark' oder 'light')."""
    s = QSettings("CardForge", "CardForge")
    return str(s.value("theme", "system"))


def save_theme(name: str) -> None:
    """Speichert die Theme-Einstellung dauerhaft."""
    s = QSettings("CardForge", "CardForge")
    s.setValue("theme", name)


# ── Palette aufbauen ──────────────────────────────────────────────────────────


def _build_palette(t: dict[str, str]) -> QPalette:
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(t["BG_APP"]))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(t["TEXT_PRI"]))
    pal.setColor(QPalette.ColorRole.Base, QColor(t["BG_WIDGET"]))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(t["BG_PANEL"]))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor(t["BG_PANEL"]))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor(t["TEXT_PRI"]))
    pal.setColor(QPalette.ColorRole.Text, QColor(t["TEXT_PRI"]))
    pal.setColor(QPalette.ColorRole.Button, QColor(t["BG_WIDGET"]))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(t["TEXT_PRI"]))
    pal.setColor(QPalette.ColorRole.BrightText, QColor("#ff6b6b"))
    pal.setColor(QPalette.ColorRole.Link, QColor(t["ACCENT"]))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(t["ACCENT"]))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(t["TEXT_SEC"]))
    # Zusätzliche Rollen für palette()-Referenzen in Inline-Stylesheets:
    pal.setColor(QPalette.ColorRole.Mid, QColor(t["BORDER"]))
    pal.setColor(QPalette.ColorRole.Dark, QColor(t["BG_HOVER"]))
    pal.setColor(QPalette.ColorRole.Shadow, QColor(t["TEXT_DIM"]))
    return pal


# ── Stylesheet aufbauen ───────────────────────────────────────────────────────


def _build_stylesheet(t: dict[str, str]) -> str:
    BG_APP = t["BG_APP"]
    BG_PANEL = t["BG_PANEL"]
    BG_WIDGET = t["BG_WIDGET"]
    BG_HOVER = t["BG_HOVER"]
    ACCENT = t["ACCENT"]
    ACCENT_D = t["ACCENT_D"]
    TEXT_PRI = t["TEXT_PRI"]
    TEXT_SEC = t["TEXT_SEC"]
    BORDER = t["BORDER"]

    return f"""
/* ── Basis ── */
QWidget {{
    background: {BG_APP};
    color: {TEXT_PRI};
    font-family: "Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}}

/* ── Hauptfenster / Splitter ── */
QMainWindow, QDialog {{
    background: {BG_APP};
}}
QSplitter::handle {{
    background: {BORDER};
    width: 1px;
    height: 1px;
}}

/* ── Menüleiste ── */
QMenuBar {{
    background: {BG_APP};
    color: {TEXT_PRI};
    border-bottom: 1px solid {BORDER};
    padding: 2px 4px;
    spacing: 2px;
}}
QMenuBar::item {{
    padding: 4px 10px;
    border-radius: 4px;
}}
QMenuBar::item:selected, QMenuBar::item:pressed {{
    background: {BG_HOVER};
    color: {ACCENT};
}}
QMenu {{
    background: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 20px 6px 12px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background: {ACCENT};
    color: #fff;
}}
QMenu::item:checked {{
    font-weight: 600;
}}
QMenu::separator {{
    height: 1px;
    background: {BORDER};
    margin: 4px 8px;
}}

/* ── Toolbar ── */
QToolBar {{
    background: {BG_PANEL};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 3px 4px;
    spacing: 3px;
}}
QToolBar::separator {{
    width: 1px;
    background: {BORDER};
    margin: 4px 2px;
}}
QToolButton {{
    background: transparent;
    color: {TEXT_PRI};
    border: none;
    border-radius: 5px;
    padding: 4px 8px;
    font-size: 12px;
}}
QToolButton:hover {{
    background: {BG_HOVER};
    color: {ACCENT};
}}
QToolButton:pressed {{
    background: {ACCENT_D};
    color: #fff;
}}
QToolButton:checked {{
    background: {ACCENT};
    color: #fff;
}}

/* ── Buttons ── */
QPushButton {{
    background: {BG_WIDGET};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 5px 14px;
    font-size: 13px;
    min-height: 26px;
}}
QPushButton:hover {{
    background: {BG_HOVER};
    border-color: {ACCENT};
    color: {ACCENT};
}}
QPushButton:pressed {{
    background: {ACCENT_D};
    border-color: {ACCENT_D};
    color: #fff;
}}
QPushButton:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
    color: #fff;
    font-weight: 600;
}}
QPushButton:disabled {{
    background: {BG_WIDGET};
    color: {TEXT_SEC};
    border-color: {BORDER};
}}

/* ── Eingabefelder ── */
QLineEdit, QTextEdit, QComboBox {{
    background: {BG_WIDGET};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 4px 8px;
    min-height: 26px;
    selection-background-color: {ACCENT};
}}
QSpinBox, QDoubleSpinBox {{
    min-height: 26px;
}}
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus,
QDoubleSpinBox:focus, QComboBox:focus {{
    border-color: {ACCENT};
    outline: none;
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 22px;
    border-left: 1px solid {BORDER};
    border-radius: 0 5px 5px 0;
}}
QComboBox QAbstractItemView {{
    background: {BG_PANEL};
    border: 1px solid {BORDER};
    selection-background-color: {ACCENT};
    selection-color: #fff;
    border-radius: 4px;
}}

/* ── Listen ── */
QListWidget {{
    background: {BG_WIDGET};
    border: 1px solid {BORDER};
    border-radius: 6px;
    outline: none;
    padding: 2px;
}}
QListWidget::item {{
    padding: 6px 8px;
    border-radius: 4px;
}}
QListWidget::item:hover {{
    background: {BG_HOVER};
}}
QListWidget::item:selected {{
    background: {ACCENT};
    color: #fff;
}}

/* ── Scroll-Bereich ── */
QScrollArea {{
    background: {BG_APP};
    border: none;
}}
QScrollBar:vertical {{
    background: {BG_WIDGET};
    width: 8px;
    border-radius: 4px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: {TEXT_SEC};
}}
QScrollBar:horizontal {{
    background: {BG_WIDGET};
    height: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER};
    border-radius: 4px;
    min-width: 20px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {TEXT_SEC};
}}
QScrollBar::add-line, QScrollBar::sub-line {{ background: none; }}

/* ── GroupBox ── */
QGroupBox {{
    color: {TEXT_SEC};
    border: 1px solid {BORDER};
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 8px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}}

/* ── Checkboxen & Radiobuttons ── */
QCheckBox, QRadioButton {{
    spacing: 6px;
    color: {TEXT_PRI};
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 15px;
    height: 15px;
    border: 1px solid {BORDER};
    border-radius: 3px;
    background: {BG_WIDGET};
}}
QRadioButton::indicator {{
    border-radius: 8px;
}}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}

/* ── Schieberegler ── */
QSlider::groove:horizontal {{
    height: 4px;
    background: {BG_WIDGET};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {ACCENT};
    border: none;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QSlider::sub-page:horizontal {{
    background: {ACCENT};
    border-radius: 2px;
}}

/* ── Tab-Widget ── */
QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 0 6px 6px 6px;
    background: {BG_PANEL};
}}
QTabBar::tab {{
    background: {BG_WIDGET};
    color: {TEXT_SEC};
    border: 1px solid {BORDER};
    border-bottom: none;
    border-radius: 6px 6px 0 0;
    padding: 5px 14px;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background: {BG_PANEL};
    color: {ACCENT};
    border-bottom: 2px solid {ACCENT};
}}
QTabBar::tab:hover:!selected {{
    background: {BG_HOVER};
    color: {TEXT_PRI};
}}

/* ── Statusleiste ── */
QStatusBar {{
    background: {BG_PANEL};
    color: {TEXT_SEC};
    border-top: 1px solid {BORDER};
    font-size: 12px;
    padding: 2px 6px;
}}
QStatusBar::item {{ border: none; }}

/* ── Rahmen / Trennlinien ── */
QFrame[frameShape="4"],   /* HLine */
QFrame[frameShape="5"] {{ /* VLine */
    color: {BORDER};
}}

/* ── Tooltip ── */
QToolTip {{
    background: {BG_PANEL};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 4px 8px;
}}
"""


# ── Öffentliche API ───────────────────────────────────────────────────────────


def apply_theme(app: QApplication, name: str) -> None:
    """Wendet das genannte Theme ('system', 'dark' oder 'light') auf *app* an."""
    effective = resolve_theme(name)
    tokens = DARK if effective == "dark" else LIGHT
    app.setPalette(_build_palette(tokens))
    app.setStyleSheet(_build_stylesheet(tokens))


def current_tokens() -> dict[str, str]:
    """Gibt die Token-Map des aktuell aktiven Themes zurück."""
    effective = resolve_theme(get_saved_theme())
    return DARK if effective == "dark" else LIGHT
