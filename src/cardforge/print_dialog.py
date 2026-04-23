"""
Druck-Dialog: Auswahl Karten, Seiten, ein-/beidseitig.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from .models import Project


class PrintExportDialog(QDialog):
    def __init__(self, project: Project, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Print / PDF Export"))
        self.setMinimumWidth(420)
        self._project = project
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)

        # Card selection
        grp_cards = QGroupBox(self.tr("Cards"))
        vl = QVBoxLayout(grp_cards)
        self._rb_all = QRadioButton(self.tr("All cards"))
        self._rb_all.setChecked(True)
        self._rb_sel = QRadioButton(self.tr("Selected cards:"))
        vl.addWidget(self._rb_all)
        vl.addWidget(self._rb_sel)

        self._card_list = QListWidget()
        self._card_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        for card in self._project.cards:
            item = QListWidgetItem(card.name)
            self._card_list.addItem(item)
        self._card_list.setEnabled(False)
        vl.addWidget(self._card_list)

        self._rb_all.toggled.connect(lambda checked: self._card_list.setEnabled(not checked))
        self._rb_sel.toggled.connect(lambda checked: self._card_list.setEnabled(checked))
        root.addWidget(grp_cards)

        # Side selection
        grp_side = QGroupBox(self.tr("Sides"))
        bg = QButtonGroup(self)
        vl2 = QVBoxLayout(grp_side)
        self._rb_both = QRadioButton(self.tr("Duplex (front & back)"))
        self._rb_both.setChecked(True)
        self._rb_front = QRadioButton(self.tr("Single-sided – front"))
        self._rb_back = QRadioButton(self.tr("Single-sided – back"))
        for rb in (self._rb_both, self._rb_front, self._rb_back):
            bg.addButton(rb)
            vl2.addWidget(rb)

        # Binding edge (relevant for duplex only)
        flip_row = QHBoxLayout()
        flip_lbl = QLabel(self.tr("  Binding edge:"))
        self._flip_combo = QComboBox()
        self._flip_combo.addItem(self.tr("Long edge (portrait, default)"), "long-edge")
        self._flip_combo.addItem(self.tr("Short edge (landscape)"), "short-edge")
        flip_row.addWidget(flip_lbl)
        flip_row.addWidget(self._flip_combo)
        flip_row.addStretch()
        vl2.addLayout(flip_row)

        def _update_flip_enabled():
            self._flip_combo.setEnabled(self._rb_both.isChecked())
            flip_lbl.setEnabled(self._rb_both.isChecked())

        self._rb_both.toggled.connect(_update_flip_enabled)
        self._rb_front.toggled.connect(_update_flip_enabled)
        self._rb_back.toggled.connect(_update_flip_enabled)
        root.addWidget(grp_side)

        # Options
        grp_opt = QGroupBox(self.tr("Options"))
        fl = QFormLayout(grp_opt)
        self._cut_marks = QCheckBox(self.tr("Draw cut marks"))
        self._cut_marks.setChecked(True)
        fl.addRow("", self._cut_marks)
        root.addWidget(grp_opt)

        # Buttons
        btn_row = QHBoxLayout()
        btn_preview = QPushButton(self.tr("Preview…"))
        btn_preview.clicked.connect(self._show_preview)
        btn_pdf = QPushButton(self.tr("Export as PDF…"))
        btn_pdf.clicked.connect(self._export_pdf)
        btn_print = QPushButton(self.tr("Print…"))
        btn_print.clicked.connect(self._print)
        btn_cancel = QPushButton(self.tr("Cancel"))
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_preview)
        btn_row.addWidget(btn_pdf)
        btn_row.addWidget(btn_print)
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        root.addLayout(btn_row)

    def _selected_indices(self) -> list[int]:
        if self._rb_all.isChecked():
            return list(range(len(self._project.cards)))
        sel = []
        for i in range(self._card_list.count()):
            if self._card_list.item(i).isSelected():
                sel.append(i)
        return sel if sel else list(range(len(self._project.cards)))

    def _side(self) -> str:
        if self._rb_front.isChecked():
            return "front"
        if self._rb_back.isChecked():
            return "back"
        return "both"

    def _duplex_flip(self) -> str:
        return self._flip_combo.currentData()

    def _show_preview(self):
        from print_preview import PrintPreviewDialog

        # Seite im Vorschau-Dialog vorwählen
        side = self._side()
        dlg = PrintPreviewDialog(self._project, self)
        if side == "back":
            dlg._rb_back.setChecked(True)
        dlg._chk_marks.setChecked(self._cut_marks.isChecked())
        dlg._refresh()
        dlg.exec()

    def _export_pdf(self):
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save PDF"), "", self.tr("PDF files (*.pdf)")
        )
        if not path:
            return
        if not path.endswith(".pdf"):
            path += ".pdf"
        from .pdf_export import export_pdf

        try:
            export_pdf(
                self._project,
                path,
                self._selected_indices(),
                side=self._side(),
                cut_marks=self._cut_marks.isChecked(),
                duplex_flip=self._duplex_flip(),
            )
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.information(
                self, self.tr("Done"), self.tr("PDF saved:\n{path}").format(path=path)
            )
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.critical(self, self.tr("Error"), str(e))

    def _print(self):
        """Druckt über das System-Druckersystem (via temporäres PDF)."""
        import os
        import subprocess
        import sys
        import tempfile

        from PySide6.QtPrintSupport import QPrintDialog, QPrinter

        from .pdf_export import export_pdf

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            tmp = f.name
        try:
            export_pdf(
                self._project,
                tmp,
                self._selected_indices(),
                side=self._side(),
                cut_marks=self._cut_marks.isChecked(),
                duplex_flip=self._duplex_flip(),
            )
            if sys.platform == "win32":
                os.startfile(tmp, "print")
            else:
                printer = QPrinter(QPrinter.PrinterMode.HighResolution)
                dlg = QPrintDialog(printer, self)
                if dlg.exec() != QPrintDialog.DialogCode.Accepted:
                    return
                printer_name = printer.printerName()
                # print-scaling=none verhindert, dass CUPS das PDF
                # auf den bedruckbaren Bereich skaliert (1:1 exakt)
                scale_opt = ["-o", "print-scaling=none"]
                # Duplex-Option aus eigenem Dialog an lpr weitergeben
                if self._side() == "both":
                    flip = self._duplex_flip()
                    sides_val = (
                        "two-sided-long-edge" if flip == "long-edge" else "two-sided-short-edge"
                    )
                else:
                    sides_val = "one-sided"
                duplex_opt = ["-o", f"sides={sides_val}"]
                if printer_name:
                    cmd = ["lpr", "-P", printer_name] + scale_opt + duplex_opt + [tmp]
                else:
                    cmd = ["lpr"] + scale_opt + duplex_opt + [tmp]
                result = subprocess.call(cmd)
                if result != 0:
                    from PySide6.QtWidgets import QMessageBox

                    QMessageBox.critical(
                        self, "Druckfehler", f"lpr schlug fehl (Exit-Code {result})."
                    )
                    return
            self.accept()
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.critical(self, "Fehler", str(e))
        finally:
            # Kurz warten, dann löschen
            import threading

            def _cleanup():
                import time

                time.sleep(5)
                import contextlib

                with contextlib.suppress(Exception):
                    os.unlink(tmp)

            threading.Thread(target=_cleanup, daemon=True).start()
