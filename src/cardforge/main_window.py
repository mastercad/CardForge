"""
Hauptfenster von CardForge.
"""

from __future__ import annotations

import copy
import json
import os

from PySide6.QtCore import QEvent, QSettings, QSize, Qt, QTimer
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QKeySequence,
    QUndoCommand,
    QUndoStack,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QAbstractSpinBox,
    QApplication,
    QCheckBox,
    QColorDialog,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSplitter,
    QStatusBar,
    QTextEdit,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .about_dialog import AboutDialog
from .canvas import CardCanvas
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
    CardLayout,
    PaperTemplate,
    Project,
)
from .paper_template_dialog import PaperTemplateDialog
from .properties_panel import ColorButton, PropertiesPanel
from .theme import apply_theme, get_saved_theme, save_theme
from .translations import SUPPORTED_LANGUAGES, effective_language, save_language

# ---------------------------------------------------------------------------
# Undo-Commands
# ---------------------------------------------------------------------------


class SnapshotCommand(QUndoCommand):
    """Generischer Undo-Schritt: Speichert eine Momentaufnahme der Kartenliste."""

    def __init__(
        self,
        project: Project,
        before: list,
        after: list,
        canvas: CardCanvas,
        panel: MainWindow,
        text: str,
    ):
        super().__init__(text)
        self._project = project
        self._before = before
        self._after = after
        self._canvas = canvas
        self._panel = panel
        # QUndoStack.push() ruft redo() sofort auf – beim ersten Mal
        # aber NICHT die Karten neu laden, da sie bereits korrekt im
        # Speicher stehen (Canvas hat Elemente direkt mutiert).
        self._first_redo = True

    def undo(self):
        self._project.cards = [CardLayout.from_dict(d) for d in self._before]
        self._panel._load_current_card()
        self._panel._refresh_card_list()
        self._canvas.update()

    def redo(self):
        if self._first_redo:
            self._first_redo = False
            return
        self._project.cards = [CardLayout.from_dict(d) for d in self._after]
        self._panel._load_current_card()
        self._panel._refresh_card_list()
        self._canvas.update()


# ---------------------------------------------------------------------------
# Hauptfenster
# ---------------------------------------------------------------------------


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle("CardForge")
        self.resize(1280, 800)

        self._project = Project()
        self._project.cards.append(CardLayout(name="Karte 1"))
        self._current_card_index: int = 0
        self._current_side: str = "front"
        self._project_path: str | None = None
        self._modified = False
        self._canvas: CardCanvas  # wird in _build_ui gesetzt

        self._undo_stack = QUndoStack(self)
        self._undo_stack.setUndoLimit(100)
        self._props_undo_timer = QTimer(self)
        self._props_undo_timer.setSingleShot(True)
        self._props_undo_timer.setInterval(600)
        self._props_undo_timer.timeout.connect(self._push_snapshot)

        self._build_ui()
        self._build_menus()
        self._build_toolbar()
        self._connect_signals()
        self._refresh_card_list()
        self._load_current_card()

    # ------------------------------------------------------------------
    # UI Aufbau
    # ------------------------------------------------------------------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_v = QVBoxLayout(central)
        root_v.setContentsMargins(0, 0, 0, 0)
        root_v.setSpacing(0)

        # ── Haupt-Arbeitsbereich ──────────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        root_v.addWidget(splitter, 1)

        # ── Linkes Panel ──────────────────────────────────────────────
        left_widget = QWidget()
        left_widget.setObjectName("leftPanel")
        left_widget.setStyleSheet(
            "#leftPanel { background:palette(alternate-base); border-right:1px solid palette(mid); }"
        )
        left_widget.setFixedWidth(220)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # Seiten-Toggle (Pill-Style)
        side_container = QWidget()
        side_container.setStyleSheet("background:palette(window); padding:8px;")
        side_hl = QHBoxLayout(side_container)
        side_hl.setContentsMargins(8, 8, 8, 8)
        side_hl.setSpacing(0)
        self._btn_front = QPushButton(self.tr("Front"))
        self._btn_back = QPushButton(self.tr("Back"))
        for b in (self._btn_front, self._btn_back):
            b.setCheckable(True)
            b.setFixedHeight(30)
            b.setStyleSheet("""
                QPushButton { border-radius:0; border:1px solid palette(mid);
                              padding:4px 10px; font-size:12px; }
                QPushButton:checked { background:palette(highlight); border-color:palette(highlight); color:#fff; font-weight:600; }
            """)
        self._btn_front.setStyleSheet(
            self._btn_front.styleSheet() + "QPushButton { border-radius: 6px 0 0 6px; }"
        )
        self._btn_back.setStyleSheet(
            self._btn_back.styleSheet() + "QPushButton { border-radius: 0 6px 6px 0; }"
        )
        self._btn_front.setChecked(True)
        self._btn_front.clicked.connect(lambda: self._switch_side("front"))
        self._btn_back.clicked.connect(lambda: self._switch_side("back"))
        side_hl.addWidget(self._btn_front, 1)
        side_hl.addWidget(self._btn_back, 1)
        left_layout.addWidget(side_container)

        # Trennlinie
        sep1 = QWidget()
        sep1.setFixedHeight(1)
        sep1.setStyleSheet("background:palette(mid);")
        left_layout.addWidget(sep1)

        # ── Karten + Ebenen (kombinierter Tree) ───────────────────────
        tree_section = QWidget()
        tree_section.setStyleSheet("background:palette(alternate-base);")
        tree_vl = QVBoxLayout(tree_section)
        tree_vl.setContentsMargins(0, 0, 0, 0)
        tree_vl.setSpacing(0)
        tree_vl.addWidget(self._section_label(self.tr("CARDS")))

        self._card_tree = QTreeWidget()
        self._card_tree.setHeaderHidden(True)
        self._card_tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._card_tree.setIndentation(14)
        self._card_tree.setStyleSheet("""
            QTreeWidget {
                border: none;
                background: palette(alternate-base);
                font-size: 12px;
                outline: none;
            }
            QTreeWidget::item {
                padding: 5px 6px;
                border-radius: 4px;
                margin: 1px 4px;
            }
            QTreeWidget::item:selected { background: palette(highlight); color: #fff; }
            QTreeWidget::item:hover:!selected { background: palette(dark); }
            QTreeWidget::branch {
                background: palette(alternate-base);
            }
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {
                image: url(none);
                border-image: none;
            }
        """)
        tree_vl.addWidget(self._card_tree, 1)

        def _icon_btn(sym, tip):
            b = QPushButton(sym)
            b.setToolTip(tip)
            b.setFixedSize(30, 26)
            b.setStyleSheet("""
                QPushButton { border-radius:5px; font-size:14px; padding:0; }
                QPushButton:hover { background:palette(highlight); color:#fff; border-color:palette(highlight); }
            """)
            return b

        # Karten-Buttons
        card_btn_row = QWidget()
        card_btn_row.setStyleSheet("background:palette(window);")
        card_btn_hl = QHBoxLayout(card_btn_row)
        card_btn_hl.setContentsMargins(4, 3, 4, 3)
        card_btn_hl.setSpacing(2)
        _lbl_karten = QLabel(self.tr("Cards:"))
        _lbl_karten.setStyleSheet(
            "color:palette(shadow); font-size:10px; background:transparent; padding-right:2px;"
        )
        card_btn_hl.addWidget(_lbl_karten)
        btn_add_card = _icon_btn("＋", self.tr("Add new card"))
        btn_dup_card = _icon_btn("⎘", self.tr("Duplicate current card"))
        btn_ren_card = _icon_btn("✎", self.tr("Rename card"))
        btn_del_card = _icon_btn("✕", self.tr("Delete card"))
        btn_del_card.setStyleSheet(
            btn_del_card.styleSheet()
            + "QPushButton:hover { background:#e05555; border-color:#e05555; }"
        )
        for b in (btn_add_card, btn_dup_card, btn_ren_card, btn_del_card):
            card_btn_hl.addWidget(b)
        card_btn_hl.addStretch()
        tree_vl.addWidget(card_btn_row)

        btn_add_card.clicked.connect(self._add_card)
        btn_dup_card.clicked.connect(self._duplicate_card)
        btn_del_card.clicked.connect(self._delete_card)
        btn_ren_card.clicked.connect(self._rename_card)

        # Trennlinie zwischen Karten- und Elementen-Buttons
        btn_sep = QWidget()
        btn_sep.setFixedHeight(1)
        btn_sep.setStyleSheet("background:palette(mid);")
        tree_vl.addWidget(btn_sep)

        # Schwebender Löschen-Button für Element-Einträge
        self._hover_del_btn = QPushButton("✕", self._card_tree)
        self._hover_del_btn.setFixedSize(20, 20)
        self._hover_del_btn.hide()
        self._hover_del_btn.setToolTip(self.tr("Delete element"))
        self._hover_del_btn.setStyleSheet(
            "QPushButton { border-radius:3px; font-size:11px; padding:0;"
            "  background:transparent; border:none; color:palette(placeholder-text); }"
            "QPushButton:hover { background:#e05555; color:#fff; }"
        )
        self._hover_del_elem_id: str | None = None
        self._card_tree.setMouseTracking(True)
        self._card_tree.itemEntered.connect(self._on_tree_item_entered)
        self._card_tree.installEventFilter(self)
        self._hover_del_btn.clicked.connect(self._delete_hovered_elem)

        left_layout.addWidget(tree_section, 1)

        # Trennlinie
        sep2 = QWidget()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet("background:palette(mid);")
        left_layout.addWidget(sep2)

        # Section: Ansicht
        left_layout.addWidget(self._section_label(self.tr("VIEW")))

        view_w = QWidget()
        view_w.setStyleSheet("background:palette(alternate-base);")
        view_layout = QVBoxLayout(view_w)
        view_layout.setContentsMargins(10, 4, 10, 8)
        view_layout.setSpacing(6)

        # Zoom
        zoom_lbl_row = QHBoxLayout()
        zoom_lbl_row.addWidget(QLabel(self.tr("Zoom")))
        self._zoom_lbl = QLabel("3.0×")
        self._zoom_lbl.setStyleSheet("color:palette(placeholder-text); font-size:12px;")
        self._zoom_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        zoom_lbl_row.addWidget(self._zoom_lbl)
        view_layout.addLayout(zoom_lbl_row)
        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setRange(10, 200)
        self._zoom_slider.setValue(30)
        self._zoom_slider.valueChanged.connect(self._on_zoom)
        view_layout.addWidget(self._zoom_slider)

        # Raster-Zeile
        grid_hl = QHBoxLayout()
        self._chk_grid = QCheckBox(self.tr("Grid"))
        self._chk_grid.setChecked(True)
        grid_hl.addWidget(self._chk_grid)
        grid_hl.addStretch()
        snap_lbl = QLabel(self.tr("Snap"))
        snap_lbl.setStyleSheet("color:palette(placeholder-text); font-size:12px;")
        grid_hl.addWidget(snap_lbl)
        self._snap_spin = QDoubleSpinBox()
        self._snap_spin.setRange(0.0, 10.0)
        self._snap_spin.setSingleStep(0.5)
        self._snap_spin.setValue(1.0)
        self._snap_spin.setSuffix(" mm")
        self._snap_spin.setFixedWidth(72)
        grid_hl.addWidget(self._snap_spin)
        view_layout.addLayout(grid_hl)

        # Hintergrundfarbe
        bg_hl = QHBoxLayout()
        bg_hl.addWidget(QLabel(self.tr("Background")))
        bg_hl.addStretch()
        self._bg_btn = ColorButton("#ffffff")
        self._bg_btn.colorChanged.connect(self._on_bg_changed)
        bg_hl.addWidget(self._bg_btn)
        view_layout.addLayout(bg_hl)

        left_layout.addWidget(view_w)

        splitter.addWidget(left_widget)

        # ── Mitte: Canvas ─────────────────────────────────────────────
        canvas_wrapper = QWidget()
        canvas_wrapper.setStyleSheet("background:palette(window);")
        canvas_vl = QVBoxLayout(canvas_wrapper)
        canvas_vl.setContentsMargins(0, 0, 0, 0)
        canvas_vl.setSpacing(0)

        # Vorlage-Infozeile
        paper_info_bar = QWidget()
        paper_info_bar.setFixedHeight(26)
        paper_info_bar.setStyleSheet(
            "background:palette(alternate-base); border-bottom:1px solid palette(mid);"
        )
        pib_hl = QHBoxLayout(paper_info_bar)
        pib_hl.setContentsMargins(10, 0, 10, 0)
        pib_prefix = QLabel(self.tr("Paper template:"))
        pib_prefix.setStyleSheet("color:palette(shadow); font-size:11px; background:transparent;")
        self._paper_label = QLabel()
        self._paper_label.setStyleSheet(
            "color:palette(window-text); font-size:11px; font-weight:600; background:transparent;"
        )
        btn_edit_paper = QPushButton(self.tr("✎ Edit"))
        btn_edit_paper.setFixedHeight(20)
        btn_edit_paper.setStyleSheet(
            "QPushButton{background:palette(base);color:palette(placeholder-text);border:1px solid palette(mid);"
            "border-radius:3px;font-size:10px;padding:0 6px;}"
            "QPushButton:hover{background:palette(dark);color:palette(window-text);}"
        )
        btn_edit_paper.clicked.connect(self._edit_paper_template)
        pib_hl.addWidget(pib_prefix)
        pib_hl.addWidget(self._paper_label)
        pib_hl.addStretch()
        pib_hl.addWidget(btn_edit_paper)
        canvas_vl.addWidget(paper_info_bar)

        canvas_container = QScrollArea()
        canvas_container.setWidgetResizable(False)
        canvas_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        canvas_container.setStyleSheet("QScrollArea { background:palette(window); border:none; }")
        self._canvas = CardCanvas()
        canvas_container.setWidget(self._canvas)
        canvas_vl.addWidget(canvas_container, 1)
        splitter.addWidget(canvas_wrapper)

        # ── Rechts: Properties ────────────────────────────────────────
        self._props = PropertiesPanel()
        splitter.addWidget(self._props)

        splitter.setSizes([220, 780, 280])
        splitter.setHandleWidth(1)

        # ── Farbpalette (horizontale Leiste unter Canvas) ─────────────
        self._palette_bar = self._build_palette_bar()
        root_v.addWidget(self._palette_bar)

        # ── Statusleiste ──────────────────────────────────────────────
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage(self.tr("Ready"))
        self._update_paper_label()

    def _section_label(self, text: str) -> QWidget:
        """Erzeugt einen Section-Header wie in modernen IDEs."""
        w = QWidget()
        w.setStyleSheet("background:palette(window);")
        w.setFixedHeight(28)
        hl = QHBoxLayout(w)
        hl.setContentsMargins(10, 0, 10, 0)
        lbl = QLabel(text.upper())
        lbl.setStyleSheet(
            "color:palette(shadow); font-size:10px; font-weight:700; letter-spacing:1px; background:transparent;"
        )
        hl.addWidget(lbl)
        return w

    def _build_palette_bar(self) -> QWidget:
        """Horizontale Farbpaletten-Leiste am unteren Rand."""
        bar = QWidget()
        bar.setStyleSheet("background:palette(alternate-base); border-top:1px solid palette(mid);")
        bar.setFixedHeight(36)
        hl = QHBoxLayout(bar)
        hl.setContentsMargins(8, 4, 8, 4)
        hl.setSpacing(4)
        lbl = QLabel(self.tr("Palette:"))
        lbl.setStyleSheet("color:palette(shadow); font-size:11px; background:transparent;")
        hl.addWidget(lbl)

        self._palette_buttons: list[ColorButton] = []
        for color in self._project.color_palette:
            btn = ColorButton(color)
            btn.colorChanged.connect(self._update_palette_color(len(self._palette_buttons)))
            btn.clicked.connect(self._apply_palette_color(color))
            hl.addWidget(btn)
            self._palette_buttons.append(btn)

        btn_add = QPushButton("＋")
        btn_add.setFixedSize(26, 26)
        btn_add.setToolTip(self.tr("Add color to palette"))
        btn_add.setStyleSheet(
            "QPushButton { border-radius:5px; font-size:13px; padding:0; }"
            "QPushButton:hover { background:palette(highlight); color:#fff; border-color:palette(highlight); }"
        )
        btn_add.clicked.connect(self._add_palette_color)
        hl.addWidget(btn_add)
        hl.addStretch()
        return bar

    def _update_palette_color(self, idx: int):
        def _inner(color: str):
            if idx < len(self._project.color_palette):
                self._project.color_palette[idx] = color

        return _inner

    def _apply_palette_color(self, color: str):
        def _inner():
            sel = self._canvas.selected_elements()
            for e in sel:
                if e.type == ELEMENT_TEXT:
                    e.color = color
                else:
                    e.fill_color = color
            self._props.set_elements(sel)
            self._canvas.update()

        return _inner

    def _add_palette_color(self):
        from PySide6.QtGui import QPalette

        app = QApplication.instance()
        assert isinstance(app, QApplication)
        saved_ss = app.styleSheet()
        saved_pal = app.palette()
        app.setStyleSheet("")
        app.setPalette(QPalette())
        try:
            c = QColorDialog.getColor(parent=self)
        finally:
            app.setStyleSheet(saved_ss)
            app.setPalette(saved_pal)
        if c.isValid():
            self._project.color_palette.append(c.name())
            btn = ColorButton(c.name())
            idx = len(self._palette_buttons)
            btn.colorChanged.connect(self._update_palette_color(idx))
            btn.clicked.connect(self._apply_palette_color(c.name()))
            # In horizontaler Palette vor dem Stretch (= vorletztes Widget) einfügen
            bar_layout = self._palette_bar.layout()
            assert isinstance(bar_layout, QHBoxLayout)
            insert_pos = bar_layout.count() - 2  # vor dem Stretch
            bar_layout.insertWidget(insert_pos, btn)
            self._palette_buttons.append(btn)

    # ------------------------------------------------------------------
    # Menüs
    # ------------------------------------------------------------------

    def _build_menus(self):
        mb = self.menuBar()

        # File
        m_file = mb.addMenu(self.tr("&File"))
        m_file.addAction(self.tr("New Project"), QKeySequence.StandardKey.New, self._new_project)
        m_file.addAction(self.tr("Open…"), QKeySequence.StandardKey.Open, self._open_project)
        self._recent_menu = m_file.addMenu(self.tr("Recent Files"))
        self._update_recent_menu()
        m_file.addSeparator()
        m_file.addAction(self.tr("Save"), QKeySequence.StandardKey.Save, self._save_project)
        m_file.addAction(self.tr("Save As…"), QKeySequence("Ctrl+Shift+S"), self._save_project_as)
        m_file.addSeparator()
        m_file.addAction(self.tr("Export as Template…")).triggered.connect(self._export_template)
        m_file.addAction(self.tr("Import Template…")).triggered.connect(self._import_template)
        m_file.addSeparator()
        m_file.addAction(
            self.tr("Print Preview…"), QKeySequence("Ctrl+Shift+P"), self._print_preview
        )
        m_file.addAction(
            self.tr("Export PDF / Print…"), QKeySequence.StandardKey.Print, self._print_dialog
        )
        m_file.addSeparator()
        m_file.addAction(self.tr("Quit"), QKeySequence.StandardKey.Quit, self.close)

        # Edit
        m_edit = mb.addMenu(self.tr("&Edit"))
        self._undo_action = self._undo_stack.createUndoAction(self, self.tr("Undo"))
        self._undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self._redo_action = self._undo_stack.createRedoAction(self, self.tr("Redo"))
        self._redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        m_edit.addAction(self._undo_action)
        m_edit.addAction(self._redo_action)
        m_edit.addSeparator()
        m_edit.addAction(
            self.tr("Select All"), QKeySequence.StandardKey.SelectAll, self._canvas.select_all
        )
        m_edit.addAction(
            self.tr("Delete Selected"),
            QKeySequence.StandardKey.Delete,
            self._canvas.delete_selected,
        )

        # Insert
        m_insert = mb.addMenu(self.tr("&Insert"))
        m_insert.addAction(self.tr("Text")).triggered.connect(self._insert_text)
        m_insert.addAction(self.tr("Image…")).triggered.connect(self._insert_image)
        m_insert.addAction(self.tr("Rectangle")).triggered.connect(self._insert_rect)
        m_insert.addAction(self.tr("Ellipse")).triggered.connect(self._insert_ellipse)
        m_insert.addAction(self.tr("Line")).triggered.connect(self._insert_line)
        m_insert.addAction(self.tr("QR Code")).triggered.connect(self._insert_qr)
        m_insert.addAction(self.tr("Icon…")).triggered.connect(self._insert_icon)

        # Align
        m_align = mb.addMenu(self.tr("&Align"))
        for label, mode in [
            (self.tr("Left (Card)"), "left"),
            (self.tr("Right (Card)"), "right"),
            (self.tr("Top (Card)"), "top"),
            (self.tr("Bottom (Card)"), "bottom"),
            (self.tr("Center H"), "center_h"),
            (self.tr("Center V"), "center_v"),
            (None, None),
            (self.tr("Group Left"), "group_left"),
            (self.tr("Group Right"), "group_right"),
            (self.tr("Group Top"), "group_top"),
            (self.tr("Group Bottom"), "group_bottom"),
            (self.tr("Group Center H"), "group_center_h"),
            (self.tr("Group Center V"), "group_center_v"),
            (None, None),
            (self.tr("Distribute Horizontally"), "distribute_h"),
            (self.tr("Distribute Vertically"), "distribute_v"),
        ]:
            if label is None:
                m_align.addSeparator()
            else:
                m_align.addAction(label, lambda m=mode: self._align(m))

        # Paper Template
        m_paper = mb.addMenu(self.tr("Paper &Template"))
        m_paper.addAction(self.tr("Edit…")).triggered.connect(self._edit_paper_template)
        m_paper.addAction(self.tr("Manage Library…")).triggered.connect(self._load_paper_preset)
        m_paper.addAction(self.tr("Save as Template to Library")).triggered.connect(
            self._save_paper_to_library
        )

        # Extras
        m_extras = mb.addMenu(self.tr("E&xtras"))
        m_extras.addAction(self.tr("Add Font…")).triggered.connect(self._add_font)
        m_extras.addAction(self.tr("Mail Merge…")).triggered.connect(self._mail_merge)
        m_extras.addSeparator()

        # Appearance (Dark / Light / System)
        m_theme = m_extras.addMenu(self.tr("Appearance"))
        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)
        current_saved = get_saved_theme()
        for tid, tlabel in (
            ("system", self.tr("System (Default)")),
            ("dark", self.tr("Dark")),
            ("light", self.tr("Light")),
        ):
            act = QAction(tlabel, self)
            act.setCheckable(True)
            act.setChecked(tid == current_saved)
            act.triggered.connect(lambda checked, t=tid: self._on_theme_changed(t))
            theme_group.addAction(act)
            m_theme.addAction(act)

        # Language submenu
        m_lang = m_extras.addMenu(self.tr("Language"))
        lang_group = QActionGroup(self)
        lang_group.setExclusive(True)
        current_lang = effective_language()
        for code, display in SUPPORTED_LANGUAGES.items():
            act = QAction(display, self)
            act.setCheckable(True)
            act.setChecked(code == current_lang)
            act.triggered.connect(lambda checked, c=code: self._on_language_changed(c))
            lang_group.addAction(act)
            m_lang.addAction(act)

        # Help
        m_help = mb.addMenu(self.tr("&Help"))
        m_help.addAction(self.tr("About CardForge…")).triggered.connect(self._show_about)

    # ------------------------------------------------------------------
    # Toolbar
    # ------------------------------------------------------------------

    def _build_toolbar(self):
        tb = QToolBar(self.tr("Elements"))
        tb.setMovable(False)
        tb.setIconSize(QSize(20, 20))
        self.addToolBar(tb)

        def _act(label: str, slot, shortcut: str = "", tip: str = ""):
            a = QAction(label, self)
            if shortcut:
                a.setShortcut(shortcut)
            if tip:
                a.setToolTip(tip)
                a.setStatusTip(tip)
            a.triggered.connect(slot)
            tb.addAction(a)
            return a

        _act(
            self.tr("T Text"),
            self._insert_text,
            "",
            self.tr("Insert text field (key T) – adjust size/position with mouse"),
        )
        _act(
            self.tr("🖼 Image"),
            self._insert_image,
            "",
            self.tr("Insert image from file (PNG, JPG, SVG …)"),
        )
        _act(
            self.tr("▭ Rectangle"),
            self._insert_rect,
            "",
            self.tr("Insert rectangle (key R) – fill and border color in right panel"),
        )
        _act(
            self.tr("◯ Ellipse"),
            self._insert_ellipse,
            "",
            self.tr("Insert ellipse / circle (key E)"),
        )
        _act(
            self.tr("╱ Line"),
            self._insert_line,
            "",
            self.tr(
                "Insert line (key L) – move endpoint with lower resize handle;"
                " color via \u201cBorder color\u201d in right panel"
            ),
        )
        _act(
            self.tr("▦ QR Code"),
            self._insert_qr,
            "",
            self.tr("Insert QR code – enter URL, text, or vCard data"),
        )
        _act(
            self.tr("★ Icon…"),
            self._insert_icon,
            "",
            self.tr("Insert business card icon – scalable and color-adjustable"),
        )
        tb.addSeparator()
        _act(
            self.tr("↑ Front"),
            self._canvas.bring_to_front,
            "",
            self.tr("Bring selected elements to front (highest layer)"),
        )
        _act(
            self.tr("↓ Back"),
            self._canvas.send_to_back,
            "",
            self.tr("Send selected elements to back (lowest layer)"),
        )
        tb.addSeparator()
        _act(self.tr("⟳ Undo"), self._undo_stack.undo, "Ctrl+Z", self.tr("Undo last step (Ctrl+Z)"))
        _act(
            self.tr("⟲ Redo"),
            self._undo_stack.redo,
            "Ctrl+Y",
            self.tr("Redo undone step (Ctrl+Y)"),
        )
        tb.addSeparator()
        _act(
            self.tr("🖨 Preview"),
            self._print_preview,
            "",
            self.tr("Open print preview – shows all cards on the print sheet"),
        )

        # Zweite Toolbar-Reihe: Ausrichten & Verteilen
        self._build_align_toolbar()

    def _build_align_toolbar(self):
        self.addToolBarBreak()
        tb = QToolBar(self.tr("Align"))
        tb.setMovable(False)
        tb.setIconSize(QSize(20, 20))
        self.addToolBar(tb)

        def _btn(symbol: str, tip: str, mode: str):
            a = QAction(symbol, self)
            a.setToolTip(tip)
            a.triggered.connect(lambda checked=False, m=mode: self._align(m))
            tb.addAction(a)

        from PySide6.QtWidgets import QLabel as _QL

        def _lbl(text: str):
            lbl = _QL(text)
            lbl.setStyleSheet("color:#aaa;font-size:11px;padding:0 4px;")
            tb.addWidget(lbl)

        _lbl(self.tr("To Card:"))
        _btn("⬛←", self.tr("Align left to card"), "left")
        _btn("⬛↔", self.tr("Center horizontally on card"), "center_h")
        _btn("⬛→", self.tr("Align right to card"), "right")
        _btn("⬛↑", self.tr("Align top to card"), "top")
        _btn("⬛↕", self.tr("Center vertically on card"), "center_v")
        _btn("⬛↓", self.tr("Align bottom to card"), "bottom")
        tb.addSeparator()
        _lbl(self.tr("To Selection:"))
        _btn("←|←", self.tr("Align left edges"), "group_left")
        _btn("↔|↔", self.tr("Center on common horizontal axis"), "group_center_h")
        _btn("→|→", self.tr("Align right edges"), "group_right")
        _btn("↑|↑", self.tr("Align top edges"), "group_top")
        _btn("↕|↕", self.tr("Center on common vertical axis"), "group_center_v")
        _btn("↓|↓", self.tr("Align bottom edges"), "group_bottom")
        tb.addSeparator()
        _lbl(self.tr("Distribute:"))
        _btn("⇿", self.tr("Distribute horizontally (≥3 elements)"), "distribute_h")
        _btn("⇳", self.tr("Distribute vertically (≥3 elements)"), "distribute_v")
        tb.addSeparator()
        _lbl(self.tr("Content:"))
        a = QAction(self.tr("⊡ Fit"), self)
        a.setToolTip(self.tr("Fit to content (text→text size, image→aspect ratio, QR→square)"))
        a.triggered.connect(lambda checked=False: self._fit_to_content())
        tb.addAction(a)

    def _align(self, mode: str):
        self._push_snapshot()
        self._canvas.align_selected(mode)

    def _fit_to_content(self):
        self._push_snapshot()
        self._canvas.fit_to_content()

    # ------------------------------------------------------------------
    # Signale
    # ------------------------------------------------------------------

    def _connect_signals(self):
        self._card_tree.currentItemChanged.connect(self._on_tree_current_changed)
        self._card_tree.itemClicked.connect(self._on_tree_item_clicked)
        self._canvas.selectionChanged.connect(self._on_selection_changed)
        self._canvas.elementMoved.connect(self._on_canvas_changed)
        self._canvas.elementResized.connect(self._on_canvas_changed)
        self._canvas.editStarted.connect(self._on_edit_started)
        self._canvas.editFinished.connect(self._on_edit_finished)
        self._canvas.requestUndo.connect(self._undo_stack.undo)
        self._canvas.requestRedo.connect(self._undo_stack.redo)
        self._canvas.zoomChanged.connect(self._on_canvas_zoom_changed)
        self._props.elementChanged.connect(self._on_props_changed)
        self._props.autoFitRequested.connect(self._on_auto_fit_requested)
        self._chk_grid.stateChanged.connect(self._on_grid_changed)
        self._snap_spin.valueChanged.connect(self._on_grid_changed)

    # ------------------------------------------------------------------
    # Kartenliste / Tree
    # ------------------------------------------------------------------

    def _refresh_card_list(self):
        """Baut den Karten-Tree komplett neu auf.

        Jede Karte ist ein aufklappbarer Eintrag.  Darunter stehen alle
        Elemente der aktuellen Seite, sortiert von oberster Ebene oben.
        """
        self._card_tree.blockSignals(True)
        self._card_tree.clear()
        canvas_sel = set(self._canvas._selected) if hasattr(self, "_canvas") else set()
        first_selected_item = None
        for ci, card in enumerate(self._project.cards):
            card_item = QTreeWidgetItem(self._card_tree)
            card_item.setText(0, card.name)
            card_item.setData(0, Qt.ItemDataRole.UserRole, ("card", ci))
            # Aktuelle Karte fett
            f = card_item.font(0)
            f.setBold(ci == self._current_card_index)
            f.setPointSize(f.pointSize())  # keine Größenänderung
            card_item.setFont(0, f)
            # Elemente der aktuellen Seite als Kinder
            side_elems = (
                card.front_elements if self._current_side == "front" else card.back_elements
            )
            for e in sorted(side_elems, key=lambda x: -x.z_order):
                icon = self._ELEM_ICONS.get(e.type, "?")
                label = icon + "  " + self._elem_preview_label(e)
                if not e.visible:
                    label = "○  " + label
                elem_item = QTreeWidgetItem(card_item)
                elem_item.setText(0, label)
                elem_item.setData(0, Qt.ItemDataRole.UserRole, ("elem", e.id))
                if e.id in canvas_sel:
                    elem_item.setSelected(True)
                    if first_selected_item is None:
                        first_selected_item = elem_item
            # Aktuelle Karte aufgeklappt + fokussiert
            if ci == self._current_card_index:
                card_item.setExpanded(True)
                if first_selected_item is None:
                    self._card_tree.setCurrentItem(card_item)
        if first_selected_item is not None:
            self._card_tree.setCurrentItem(first_selected_item)
        self._card_tree.blockSignals(False)

    def _refresh_elem_list(self):
        """Alias – delegiert an _refresh_card_list (eine einzige Quelle)."""
        self._refresh_card_list()

    def _on_tree_current_changed(self, current, previous):
        """Karte wird über Tastatur oder Klick auf Karten-Item gewechselt."""
        if current is None:
            return
        data = current.data(0, Qt.ItemDataRole.UserRole)
        if not data or data[0] != "card":
            return
        ci = data[1]
        if ci != self._current_card_index:
            self._current_card_index = ci
            self._load_current_card()

    def _on_tree_item_clicked(self, item, col):
        """Element-Item angeklickt → Selektion auf Canvas übertragen."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data[0] != "elem":
            return
        selected = self._card_tree.selectedItems()
        ids = [
            it.data(0, Qt.ItemDataRole.UserRole)[1]
            for it in selected
            if it.data(0, Qt.ItemDataRole.UserRole)
            and it.data(0, Qt.ItemDataRole.UserRole)[0] == "elem"
        ]
        self._canvas.set_selection(ids)

    def _load_current_card(self):
        if not self._project.cards:
            return
        card = self._project.cards[self._current_card_index]
        self._canvas.set_layout(card, self._current_side)
        self._canvas.set_paper(self._project.paper_template)
        self._update_paper_label()
        self._canvas.set_grid(self._chk_grid.isChecked(), self._snap_spin.value())
        bg = card.front_bg if self._current_side == "front" else card.back_bg
        self._bg_btn.set_color(bg)
        self._props.set_elements([])
        self._refresh_elem_list()
        self._status.showMessage(
            self.tr("Card: {name} | {side}").format(name=card.name, side=self._current_side)
        )

    def _switch_side(self, side: str):
        self._current_side = side
        self._btn_front.setChecked(side == "front")
        self._btn_back.setChecked(side == "back")
        self._canvas.set_side(side)
        if self._project.cards:
            card = self._project.cards[self._current_card_index]
            bg = card.front_bg if side == "front" else card.back_bg
            self._bg_btn.set_color(bg)
        self._refresh_card_list()
        self._status.showMessage(self.tr("Side: {side}").format(side=side))

    def _add_card(self):
        name, ok = QInputDialog.getText(self, self.tr("New Card"), self.tr("Name:"))
        if ok and name:
            self._snapshot(self.tr("Add card"))
            card = CardLayout(name=name)
            self._project.cards.append(card)
            self._current_card_index = len(self._project.cards) - 1
            self._refresh_card_list()
            self._load_current_card()

    def _duplicate_card(self):
        if not self._project.cards:
            return
        self._snapshot(self.tr("Duplicate card"))
        src = self._project.cards[self._current_card_index]
        new_card = copy.deepcopy(src)
        import uuid

        new_card.id = str(uuid.uuid4())
        new_card.name = src.name + self.tr(" (Copy)")
        self._project.cards.append(new_card)
        self._current_card_index = len(self._project.cards) - 1
        self._refresh_card_list()
        self._load_current_card()

    def _delete_card(self):
        if len(self._project.cards) <= 1:
            QMessageBox.warning(self, self.tr("Error"), self.tr("At least one card must remain."))
            return
        self._snapshot(self.tr("Delete card"))
        del self._project.cards[self._current_card_index]
        self._current_card_index = max(0, self._current_card_index - 1)
        self._refresh_card_list()
        self._load_current_card()

    def _rename_card(self):
        if not self._project.cards:
            return
        card = self._project.cards[self._current_card_index]
        name, ok = QInputDialog.getText(
            self, self.tr("Rename"), self.tr("New name:"), text=card.name
        )
        if ok and name:
            card.name = name
            self._refresh_card_list()

    # ------------------------------------------------------------------
    # Elemente einfügen
    # ------------------------------------------------------------------

    def _new_elem(self, etype: str) -> CardElement:
        e = CardElement(type=etype)
        # zentriert auf Karte platzieren
        pt = self._project.paper_template
        e.x = (pt.card_width - e.width) / 2
        e.y = (pt.card_height - e.height) / 2
        return e

    def _insert_text(self):
        e = self._new_elem(ELEMENT_TEXT)
        e.text = self.tr("Text")
        self._snapshot(self.tr("Insert text"))
        self._canvas.add_element(e)
        self._canvas.fit_to_content()  # Größe sofort an Inhalt anpassen

    def _insert_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Select Image"),
            "",
            self.tr("Images (*.png *.jpg *.jpeg *.bmp *.gif *.svg *.webp)"),
        )
        if not path:
            return
        e = self._new_elem(ELEMENT_IMAGE)
        e.image_path = path
        # Limit image size to card size
        pt = self._project.paper_template
        e.width = min(30.0, pt.card_width)
        e.height = min(20.0, pt.card_height)
        e.x = (pt.card_width - e.width) / 2
        e.y = (pt.card_height - e.height) / 2
        self._snapshot(self.tr("Insert image"))
        self._canvas.add_element(e)

    def _insert_rect(self):
        e = self._new_elem(ELEMENT_RECT)
        e.width = 20
        e.height = 10
        self._snapshot(self.tr("Insert rectangle"))
        self._canvas.add_element(e)

    def _insert_ellipse(self):
        e = self._new_elem(ELEMENT_ELLIPSE)
        e.width = 20
        e.height = 10
        self._snapshot(self.tr("Insert ellipse"))
        self._canvas.add_element(e)

    def _insert_line(self):
        e = self._new_elem(ELEMENT_LINE)
        e.line_x2 = 30.0  # Endpunkt relativ zum Startpunkt (horizontal)
        e.line_y2 = 0.0
        e.width = 30.0  # für Abwärtskompatibilität
        e.height = 0.5  # Strichstärke in mm
        e.border_color = "#000000"
        e.fill_color = "#00000000"
        self._snapshot(self.tr("Insert line"))
        self._canvas.add_element(e)

    def _insert_qr(self):
        data, ok = QInputDialog.getText(
            self, self.tr("QR Code"), self.tr("Content (URL, text, vCard …):")
        )
        if not ok or not data:
            return
        e = self._new_elem(ELEMENT_QR)
        e.qr_data = data
        e.width = 20
        e.height = 20
        self._snapshot(self.tr("Insert QR code"))
        self._canvas.add_element(e)
        self._canvas.invalidate_qr_cache(data)

    def _insert_icon(self):
        dlg = IconPickerDialog("", self)
        if dlg.exec() != IconPickerDialog.DialogCode.Accepted:
            return
        icon_name = dlg.selected_icon
        if not icon_name:
            return
        e = self._new_elem(ELEMENT_ICON)
        e.icon_name = icon_name
        e.color = "#000000"
        e.width = 10
        e.height = 10
        pt = self._project.paper_template
        e.x = (pt.card_width - e.width) / 2
        e.y = (pt.card_height - e.height) / 2
        self._snapshot(self.tr("Insert icon"))
        self._canvas.add_element(e)

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _on_selection_changed(self, ids: list[str]):
        sel = self._canvas.selected_elements()
        self._props.set_elements(sel)
        # Before-State für Eigenschaften-Änderungen vorhalten
        self._undo_before = [c.to_dict() for c in self._project.cards]
        self._undo_desc = self.tr("Properties changed")
        self._refresh_elem_list()
        if sel:
            e = sel[0]
            self._status.showMessage(
                self.tr("Selected: {etype} | {count} element(s)").format(
                    etype=e.type, count=len(sel)
                )
            )

    def _on_canvas_changed(self):
        self._mark_modified()
        sel = self._canvas.selected_elements()
        self._props.set_elements(sel)
        self._refresh_elem_list()

    def _on_edit_started(self):
        """Drag or resize begins – save state before change."""
        self._undo_before = [c.to_dict() for c in self._project.cards]
        self._undo_desc = self.tr("Move/Resize")

    def _on_edit_finished(self):
        """Drag oder Resize beendet – Undo-Schritt anlegen."""
        self._push_snapshot()

    def _on_props_changed(self):
        # Sofortiges Canvas-Update damit Änderung sichtbar ist
        self._canvas.invalidate_image_cache()
        self._canvas.invalidate_qr_cache()
        self._canvas.update()
        # Sicherstellen, dass ein Before-State existiert
        if not hasattr(self, "_undo_before"):
            self._undo_before = [c.to_dict() for c in self._project.cards]
            self._undo_desc = self.tr("Properties changed")
        # Debounce: Timer starten/neu starten (600 ms Pause → Undo-Schritt)
        self._props_undo_timer.start()

    def _on_auto_fit_requested(self):
        """Passt Textelemente automatisch an ihren Inhalt an (Sidebar-Trigger)."""
        self._canvas.fit_to_content()
        # Panel mit neuen W/H-Werten aktualisieren (kein Signal-Loop dank _updating)
        sel = self._canvas.selected_elements()
        self._props.set_elements(sel)

    # ------------------------------------------------------------------
    # Ebenen-Konstanten
    # ------------------------------------------------------------------

    _ELEM_ICONS = {
        "text": "T",
        "image": "🖼",
        "rect": "▭",
        "ellipse": "◯",
        "line": "╱",
        "qr": "▦",
        "icon": "★",
    }
    _ELEM_NAMES = {
        "text": "Text",
        "image": "Image",
        "rect": "Rectangle",
        "ellipse": "Ellipse",
        "line": "Line",
        "qr": "QR Code",
        "icon": "Icon",
    }

    def _elem_preview_label(self, e: CardElement) -> str:
        """Aussagekräftiger Kurztext für ein Element in der Sidebar."""
        if e.type == "text":
            t = e.text.replace("\n", " ").strip()
            return t[:28] if t else self.tr("(empty)")
        if e.type == "image":
            return os.path.basename(e.image_path) if e.image_path else self.tr("(no file)")
        if e.type == "icon":
            from .icons import get_icon_label

            return get_icon_label(e.icon_name)
        if e.type == "qr":
            t = e.qr_data.strip()
            return t[:28] if t else self.tr("(no data)")
        if e.type in ("rect", "ellipse"):
            return f"{e.width:.0f}×{e.height:.0f} mm  {e.fill_color}"
        if e.type == "line":
            return f"{e.color}  {e.width:.0f}×{e.height:.0f} mm"
        return self._ELEM_NAMES.get(e.type, e.type)

    def _on_zoom(self, value: int):
        zoom = value / 10.0
        self._zoom_lbl.setText(f"{zoom:.1f}×")
        self._canvas.set_zoom(zoom)

    def _on_canvas_zoom_changed(self, zoom: float):
        """Slider und Label aktualisieren wenn der Canvas selbst den Zoom ändert (z. B. Ctrl+Wheel)."""
        self._zoom_lbl.setText(f"{zoom:.1f}×")
        self._zoom_slider.blockSignals(True)
        self._zoom_slider.setValue(
            max(
                self._zoom_slider.minimum(), min(self._zoom_slider.maximum(), int(round(zoom * 10)))
            )
        )
        self._zoom_slider.blockSignals(False)

    def _on_language_changed(self, code: str) -> None:
        save_language(code)
        QMessageBox.information(
            self,
            self.tr("Language Changed"),
            self.tr("The language will change after restarting the application."),
        )

    # ------------------------------------------------------------------
    # Hover-Löschen im Element-Tree
    # ------------------------------------------------------------------

    def eventFilter(self, obj: object, event: object) -> bool:
        if (
            obj is self._card_tree
            and isinstance(event, QEvent)
            and event.type() == QEvent.Type.Leave
        ):
            self._hover_del_btn.hide()
            self._hover_del_elem_id = None
        return super().eventFilter(obj, event)  # type: ignore[misc, arg-type]

    def _on_tree_item_entered(self, item: QTreeWidgetItem, _col: int) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, tuple) and data[0] == "elem":
            self._hover_del_elem_id = data[1]
            rect = self._card_tree.visualItemRect(item)
            btn = self._hover_del_btn
            btn.move(
                rect.right() - btn.width() - 6,
                rect.top() + (rect.height() - btn.height()) // 2,
            )
            btn.show()
            btn.raise_()
        else:
            self._hover_del_elem_id = None
            self._hover_del_btn.hide()

    def _delete_hovered_elem(self) -> None:
        elem_id = self._hover_del_elem_id
        if elem_id is None:
            return
        card = self._project.cards[self._current_card_index]
        side = card.front_elements if self._current_side == "front" else card.back_elements
        elem = next((e for e in side if e.id == elem_id), None)
        if elem is None:
            return
        self._push_snapshot()
        if elem_id in self._canvas._selected:  # noqa: SLF001
            self._canvas._selected.remove(elem_id)  # noqa: SLF001
        side.remove(elem)
        self._hover_del_btn.hide()
        self._hover_del_elem_id = None
        self._refresh_card_list()
        self._canvas.update()
        self._mark_modified()

    def _on_theme_changed(self, name: str) -> None:
        from PySide6.QtWidgets import QApplication

        save_theme(name)
        app = QApplication.instance()
        if isinstance(app, QApplication):
            apply_theme(app, name)

    def _show_about(self) -> None:
        dlg = AboutDialog(self)
        dlg.exec()

    def _on_grid_changed(self):
        self._canvas.set_grid(self._chk_grid.isChecked(), self._snap_spin.value())

    def _on_bg_changed(self, color: str):
        if not self._project.cards:
            return
        card = self._project.cards[self._current_card_index]
        if self._current_side == "front":
            card.front_bg = color
        else:
            card.back_bg = color
        self._canvas.update()
        self._mark_modified()

    # ------------------------------------------------------------------
    # Papiervorlage
    # ------------------------------------------------------------------

    @staticmethod
    def _user_templates_path() -> str:
        from PySide6.QtCore import QStandardPaths

        d = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, "paper_templates.json")

    @staticmethod
    def _load_user_templates() -> list[PaperTemplate]:
        path = MainWindow._user_templates_path()
        if not os.path.exists(path):
            return []
        try:
            with open(path, encoding="utf-8") as f:
                return [PaperTemplate.from_dict(d) for d in json.load(f)]
        except Exception:
            return []

    @staticmethod
    def _save_user_templates(templates: list[PaperTemplate]):
        path = MainWindow._user_templates_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump([t.to_dict() for t in templates], f, ensure_ascii=False, indent=2)

    def _save_paper_to_library(self):
        t = self._project.paper_template
        name, ok = QInputDialog.getText(
            self, self.tr("Save Template"), self.tr("Template name:"), text=t.name
        )
        if not ok or not name.strip():
            return
        import copy as _copy

        saved = _copy.deepcopy(t)
        saved.name = name.strip()
        user = self._load_user_templates()
        # Replace existing entry with same name
        user = [u for u in user if u.name != saved.name]
        user.append(saved)
        self._save_user_templates(user)
        QMessageBox.information(
            self,
            self.tr("Saved"),
            self.tr("“{name}” has been saved to the library.").format(name=saved.name),
        )

    def _update_paper_label(self):
        pt = self._project.paper_template
        self._paper_label.setText(
            self.tr("{name}  ({pw:.0f}×{ph:.0f} mm,  {cols}×{rows} cards)").format(
                name=pt.name,
                pw=pt.paper_width,
                ph=pt.paper_height,
                cols=pt.cols,
                rows=pt.rows,
            )
        )

    def _edit_paper_template(self):
        import copy as _copy

        dlg = PaperTemplateDialog(_copy.deepcopy(self._project.paper_template), self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._project.paper_template = dlg.result_template()
            self._canvas.set_paper(self._project.paper_template)
            self._update_paper_label()
            self._mark_modified()

    def _load_paper_preset(self):
        """Öffnet den Bibliotheks-Dialog (Laden / Bearbeiten / Löschen)."""
        self._manage_paper_library()

    def _manage_paper_library(self):
        """Dialog: Bibliothek verwalten – Laden, Bearbeiten, Löschen."""
        builtin = _builtin_paper_presets()
        user = self._load_user_templates()

        dlg = QDialog(self)
        dlg.setWindowTitle(self.tr("Paper Template Library"))
        dlg.setMinimumWidth(480)
        dlg.setMinimumHeight(380)

        layout = QVBoxLayout(dlg)

        hint = QLabel(self.tr("★ = own template  –  double-click to load"))
        hint.setStyleSheet("color: palette(placeholder-text); font-size: 11px;")
        layout.addWidget(hint)

        lst = QListWidget()
        lst.setAlternatingRowColors(True)
        layout.addWidget(lst)

        def _rebuild():
            nonlocal user
            lst.clear()
            for t in builtin:
                item = QListWidgetItem(t.name)
                item.setData(Qt.ItemDataRole.UserRole, ("builtin", t))
                lst.addItem(item)
            for t in user:
                item = QListWidgetItem(f"★ {t.name}")
                item.setData(Qt.ItemDataRole.UserRole, ("user", t))
                lst.addItem(item)
            # Aktuelle Vorlage vorselektieren
            current = self._project.paper_template.name
            for i in range(lst.count()):
                it = lst.item(i)
                _, t = it.data(Qt.ItemDataRole.UserRole)
                if t.name == current:
                    lst.setCurrentRow(i)
                    break

        _rebuild()

        btn_row = QHBoxLayout()
        btn_load = QPushButton(self.tr("Load"))
        btn_edit = QPushButton(self.tr("Edit…"))
        btn_delete = QPushButton(self.tr("Delete"))
        btn_close = QPushButton(self.tr("Close"))
        btn_row.addWidget(btn_load)
        btn_row.addWidget(btn_edit)
        btn_row.addWidget(btn_delete)
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        def _selected():
            item = lst.currentItem()
            if item is None:
                return None, None
            return item.data(Qt.ItemDataRole.UserRole)

        def _update_buttons():
            kind, _ = _selected()
            btn_load.setEnabled(kind is not None)
            btn_edit.setEnabled(kind == "user")
            btn_delete.setEnabled(kind == "user")

        lst.currentItemChanged.connect(lambda *_: _update_buttons())
        _update_buttons()

        def _do_load():
            kind, t = _selected()
            if t is None:
                return
            self._project.paper_template = copy.deepcopy(t)
            self._canvas.set_paper(self._project.paper_template)
            self._update_paper_label()
            self._mark_modified()
            dlg.accept()

        def _do_edit():
            kind, t = _selected()
            if t is None or kind != "user":
                return
            orig_name = t.name
            edit_dlg = PaperTemplateDialog(copy.deepcopy(t), self)
            if edit_dlg.exec() != QDialog.DialogCode.Accepted:
                return
            updated = edit_dlg.result_template()
            user[:] = [updated if u.name == orig_name else u for u in user]
            self._save_user_templates(user)
            _rebuild()
            _update_buttons()

        def _do_delete():
            kind, t = _selected()
            if t is None or kind != "user":
                return
            ans = QMessageBox.question(
                dlg,
                self.tr("Delete Template"),
                self.tr("“{name}” will be permanently deleted from the library. Continue?").format(
                    name=t.name
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ans != QMessageBox.StandardButton.Yes:
                return
            user[:] = [u for u in user if u.name != t.name]
            self._save_user_templates(user)
            _rebuild()
            _update_buttons()

        btn_load.clicked.connect(_do_load)
        btn_edit.clicked.connect(_do_edit)
        btn_delete.clicked.connect(_do_delete)
        btn_close.clicked.connect(dlg.reject)
        lst.itemDoubleClicked.connect(lambda _: _do_load())

        dlg.exec()

    # ------------------------------------------------------------------
    # Datei-Operationen
    # ------------------------------------------------------------------

    def _new_project(self):
        if self._modified and not self._confirm_discard():
            return
        self._project = Project()
        self._project.cards.append(CardLayout(name=self.tr("Card 1")))
        self._current_card_index = 0
        self._project_path = None
        self._modified = False
        self._undo_stack.clear()
        self._refresh_card_list()
        self._load_current_card()
        self._update_paper_label()
        self.setWindowTitle("CardForge")

    # ------------------------------------------------------------------
    # Zuletzt verwendet
    # ------------------------------------------------------------------

    _MAX_RECENT = 10

    def _recent_paths(self) -> list[str]:
        s = QSettings("CardForge", "CardForge")
        val = s.value("recentFiles", [])
        if isinstance(val, list):
            return list(val)
        if isinstance(val, str) and val:
            return [val]
        return []

    def _add_recent_path(self, path: str):
        s = QSettings("CardForge", "CardForge")
        raw = s.value("recentFiles", [])
        paths: list[str] = list(raw) if isinstance(raw, list) else []
        path = os.path.abspath(path)
        if path in paths:
            paths.remove(path)
        paths.insert(0, path)
        paths = paths[: self._MAX_RECENT]
        s.setValue("recentFiles", paths)
        self._update_recent_menu()

    def _update_recent_menu(self):
        self._recent_menu.clear()
        paths = [p for p in self._recent_paths() if os.path.exists(p)]
        if not paths:
            act = self._recent_menu.addAction(self.tr("(none)"))
            act.setEnabled(False)
            return
        for p in paths:
            label = os.path.basename(p)
            act = self._recent_menu.addAction(label)
            act.setToolTip(p)
            act.setStatusTip(p)
            act.triggered.connect(lambda checked, fp=p: self._open_recent(fp))
        self._recent_menu.addSeparator()
        self._recent_menu.addAction(self.tr("Clear List")).triggered.connect(self._clear_recent)

    def _open_recent(self, path: str):
        if self._modified and not self._confirm_discard():
            return
        if not os.path.exists(path):
            QMessageBox.warning(
                self,
                self.tr("File Not Found"),
                self.tr("The file was not found:\n{path}").format(path=path),
            )
            self._update_recent_menu()
            return
        try:
            self._project = Project.load(path)
            self._project_path = path
            self._modified = False
            self._current_card_index = 0
            self._undo_stack.clear()
            self._refresh_card_list()
            self._load_current_card()
            self._update_paper_label()
            self.setWindowTitle(f"CardForge – {os.path.basename(path)}")
            self._add_recent_path(path)
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error Loading"), str(e))

    def _clear_recent(self):
        s = QSettings("CardForge", "CardForge")
        s.setValue("recentFiles", [])
        self._update_recent_menu()

    def _open_project(self):
        if self._modified and not self._confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Open Project"),
            "",
            self.tr("Business Card Project (*.vcproj)"),
        )
        if not path:
            return
        try:
            self._project = Project.load(path)
            self._project_path = path
            self._modified = False
            self._current_card_index = 0
            self._undo_stack.clear()
            self._refresh_card_list()
            self._load_current_card()
            self._update_paper_label()
            self.setWindowTitle(f"CardForge – {os.path.basename(path)}")
            self._add_recent_path(path)
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error Loading"), str(e))

    def _save_project(self):
        if not self._project_path:
            self._save_project_as()
            return
        self._do_save(self._project_path)

    def _save_project_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Save As"),
            "",
            self.tr("CardForge Project (*.vcproj)"),
        )
        if not path:
            return
        if not path.endswith(".vcproj"):
            path += ".vcproj"
        self._project_path = path
        self._do_save(path)

    def _do_save(self, path: str):
        try:
            self._project.save(path)
            self._modified = False
            self.setWindowTitle(f"CardForge – {os.path.basename(path)}")
            self._status.showMessage(self.tr("Saved: {path}").format(path=path))
            self._add_recent_path(path)
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error Saving"), str(e))

    def _export_template(self):
        """Exports the current card layout as a template (single card)."""
        if not self._project.cards:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Export as Template"),
            "",
            self.tr("CardForge Template (*.vctemplate)"),
        )
        if not path:
            return
        if not path.endswith(".vctemplate"):
            path += ".vctemplate"
        card = self._project.cards[self._current_card_index]
        data = {
            "type": "card_template",
            "paper": self._project.paper_template.to_dict(),
            "card": card.to_dict(),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self._status.showMessage(self.tr("Template exported: {path}").format(path=path))

    def _import_template(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Import Template"),
            "",
            self.tr("CardForge Template (*.vctemplate)"),
        )
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            card = CardLayout.from_dict(data["card"])
            import uuid

            card.id = str(uuid.uuid4())
            card.name = card.name + self.tr(" (imported)")
            self._project.cards.append(card)
            self._current_card_index = len(self._project.cards) - 1
            self._refresh_card_list()
            self._load_current_card()
            self._mark_modified()
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), str(e))

    # ------------------------------------------------------------------
    # Print / PDF
    # ------------------------------------------------------------------

    def _print_preview(self):
        from .print_preview import PrintPreviewDialog

        dlg = PrintPreviewDialog(self._project, self)
        dlg.exec()

    def _print_dialog(self):
        from .print_dialog import PrintExportDialog

        dlg = PrintExportDialog(self._project, self)
        dlg.exec()

    # ------------------------------------------------------------------
    # Schriftarten
    # ------------------------------------------------------------------

    def _add_font(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Select Font File"),
            "",
            self.tr("Font Files (*.ttf *.otf)"),
        )
        if not path:
            return
        from PySide6.QtGui import QFontDatabase

        fid = QFontDatabase.addApplicationFont(path)
        if fid < 0:
            QMessageBox.warning(self, self.tr("Error"), self.tr("Font could not be loaded."))
        else:
            families = QFontDatabase.applicationFontFamilies(fid)
            QMessageBox.information(
                self,
                self.tr("Font Loaded"),
                self.tr("Font(s) added:\n{families}").format(families=", ".join(families)),
            )

    # ------------------------------------------------------------------
    # Mail Merge
    # ------------------------------------------------------------------

    def _mail_merge(self):
        if not self._project.cards:
            return
        from .mail_merge import MailMergeDialog

        template = self._project.cards[self._current_card_index]
        dlg = MailMergeDialog(template, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._snapshot(self.tr("Mail Merge"))
            new_cards = dlg.result_layouts()
            self._project.cards.extend(new_cards)
            self._refresh_card_list()
            QMessageBox.information(
                self,
                self.tr("Done"),
                self.tr("{count} card(s) created from mail merge.").format(count=len(new_cards)),
            )

    # ------------------------------------------------------------------
    # Undo/Redo
    # ------------------------------------------------------------------

    def _snapshot(self, description: str):
        before = [c.to_dict() for c in self._project.cards]
        # after wird nach der Aktion gebildet – wir nutzen QUndoCommand direkt
        # Vereinfachung: before speichern, after nach nächstem event
        self._undo_before = before
        self._undo_desc = description

    def _push_snapshot(self):
        if hasattr(self, "_undo_before"):
            after = [c.to_dict() for c in self._project.cards]
            cmd = SnapshotCommand(
                self._project, self._undo_before, after, self._canvas, self, self._undo_desc
            )
            self._undo_stack.push(cmd)
            del self._undo_before
            self._mark_modified()
            self._canvas.invalidate_image_cache()
            self._canvas.invalidate_qr_cache()
            self._canvas.update()
            self._refresh_elem_list()

    # ------------------------------------------------------------------
    # Hilfsmethoden
    # ------------------------------------------------------------------

    def _mark_modified(self):
        self._modified = True
        title = self.windowTitle()
        if not title.endswith(" *"):
            self.setWindowTitle(title + " *")

    def _confirm_discard(self) -> bool:
        r = QMessageBox.question(
            self,
            self.tr("Discard Changes?"),
            self.tr("There are unsaved changes. Continue?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return r == QMessageBox.StandardButton.Yes

    def keyPressEvent(self, event):
        """Einzeltasten-Shortcuts nur wenn kein Texteingabe-Widget den Fokus hat."""
        fw = QApplication.focusWidget()
        if isinstance(fw, (QTextEdit, QLineEdit, QAbstractSpinBox)):
            super().keyPressEvent(event)
            return
        key = event.key()
        if key == Qt.Key.Key_T:
            self._insert_text()
        elif key == Qt.Key.Key_R:
            self._insert_rect()
        elif key == Qt.Key.Key_E:
            self._insert_ellipse()
        elif key == Qt.Key.Key_L:
            self._insert_line()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        if self._modified and not self._confirm_discard():
            event.ignore()
        else:
            event.accept()


# ---------------------------------------------------------------------------
# Eingebaute Papiervorlagen
# ---------------------------------------------------------------------------


def _builtin_paper_presets() -> list[PaperTemplate]:
    presets = []

    # Avery Zweckform C32010 (10 Karten auf A4)
    p = PaperTemplate()
    p.name = "Avery C32010 (10 Karten, A4)"
    p.paper_width = 210
    p.paper_height = 297
    p.card_width = 85.6
    p.card_height = 54.0
    p.margin_top = 13.5
    p.margin_bottom = 13.5
    p.margin_left = 8.0
    p.margin_right = 8.0
    p.gap_h = 17.8
    p.gap_v = 0.0
    p.cols = 2
    p.rows = 5
    presets.append(p)

    # Avery L4785 (8 Karten auf A4)
    p2 = PaperTemplate()
    p2.name = "Avery L4785 (8 Karten, A4)"
    p2.paper_width = 210
    p2.paper_height = 297
    p2.card_width = 85.0
    p2.card_height = 55.0
    p2.margin_top = 13.0
    p2.margin_bottom = 13.0
    p2.margin_left = 20.0
    p2.margin_right = 20.0
    p2.gap_h = 0.0
    p2.gap_v = 10.0
    p2.cols = 2
    p2.rows = 4
    presets.append(p2)

    # Sigel LP795 (20 Karten auf A4)
    p3 = PaperTemplate()
    p3.name = "Sigel LP795 (20 Karten, A4)"
    p3.paper_width = 210
    p3.paper_height = 297
    p3.card_width = 85.6
    p3.card_height = 54.0
    p3.margin_top = 10.0
    p3.margin_bottom = 10.0
    p3.margin_left = 7.2
    p3.margin_right = 7.2
    p3.gap_h = 14.0
    p3.gap_v = 0.0
    p3.cols = 2
    p3.rows = 10
    presets.append(p3)

    # Benutzerdefiniert (leere Vorlage)
    p4 = PaperTemplate()
    p4.name = "Benutzerdefiniert (leer)"
    presets.append(p4)

    return presets
