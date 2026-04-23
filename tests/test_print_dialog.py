"""Tests für cardforge.print_dialog."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from cardforge.models import CardLayout, Project


def _project_with_cards(n: int = 2) -> Project:
    p = Project(name="Drucktest")
    for i in range(n):
        p.cards.append(CardLayout(name=f"Karte {i + 1}"))
    return p


class TestPrintExportDialog:
    def test_creates_without_crash(self, qapp):
        from cardforge.print_dialog import PrintExportDialog

        p = _project_with_cards(2)
        dlg = PrintExportDialog(p)
        assert dlg is not None
        dlg.close()

    def test_window_title(self, qapp):
        from cardforge.print_dialog import PrintExportDialog

        p = _project_with_cards()
        dlg = PrintExportDialog(p)
        assert "Druck" in dlg.windowTitle() or "PDF" in dlg.windowTitle()
        dlg.close()

    def test_default_selects_all_cards(self, qapp):
        from cardforge.print_dialog import PrintExportDialog

        p = _project_with_cards(3)
        dlg = PrintExportDialog(p)
        # Standard: Alle Karten
        assert dlg._rb_all.isChecked()  # noqa: SLF001
        dlg.close()

    def test_default_side_is_both(self, qapp):
        from cardforge.print_dialog import PrintExportDialog

        p = _project_with_cards()
        dlg = PrintExportDialog(p)
        assert dlg._rb_both.isChecked()  # noqa: SLF001
        dlg.close()

    def test_selected_indices_all(self, qapp):
        from cardforge.print_dialog import PrintExportDialog

        p = _project_with_cards(3)
        dlg = PrintExportDialog(p)
        indices = dlg._selected_indices()  # noqa: SLF001
        assert indices == [0, 1, 2]
        dlg.close()

    def test_side_selection_front(self, qapp):
        from cardforge.print_dialog import PrintExportDialog

        p = _project_with_cards()
        dlg = PrintExportDialog(p)
        dlg._rb_front.setChecked(True)  # noqa: SLF001
        assert dlg._side() == "front"  # noqa: SLF001
        dlg.close()

    def test_side_selection_back(self, qapp):
        from cardforge.print_dialog import PrintExportDialog

        p = _project_with_cards()
        dlg = PrintExportDialog(p)
        dlg._rb_back.setChecked(True)  # noqa: SLF001
        assert dlg._side() == "back"  # noqa: SLF001
        dlg.close()

    def test_side_selection_both(self, qapp):
        from cardforge.print_dialog import PrintExportDialog

        p = _project_with_cards()
        dlg = PrintExportDialog(p)
        dlg._rb_both.setChecked(True)  # noqa: SLF001
        assert dlg._side() == "both"  # noqa: SLF001
        dlg.close()

    def test_project_stored(self, qapp):
        from cardforge.print_dialog import PrintExportDialog

        p = _project_with_cards(2)
        dlg = PrintExportDialog(p)
        assert dlg._project is p  # noqa: SLF001
        dlg.close()

    def test_selected_indices_with_sel_mode_some_selected(self, qapp):
        from cardforge.print_dialog import PrintExportDialog

        p = _project_with_cards(3)
        dlg = PrintExportDialog(p)
        dlg._rb_sel.setChecked(True)  # noqa: SLF001
        # Karte 0 und 2 auswählen
        dlg._card_list.item(0).setSelected(True)  # noqa: SLF001
        dlg._card_list.item(2).setSelected(True)  # noqa: SLF001
        indices = dlg._selected_indices()  # noqa: SLF001
        assert indices == [0, 2]
        dlg.close()

    def test_selected_indices_with_sel_mode_none_selected_fallback(self, qapp):
        from cardforge.print_dialog import PrintExportDialog

        p = _project_with_cards(3)
        dlg = PrintExportDialog(p)
        dlg._rb_sel.setChecked(True)  # noqa: SLF001
        # Nichts auswählen → alle als Fallback
        indices = dlg._selected_indices()  # noqa: SLF001
        assert indices == [0, 1, 2]
        dlg.close()

    def test_duplex_flip_returns_current_data(self, qapp):
        from cardforge.print_dialog import PrintExportDialog

        p = _project_with_cards()
        dlg = PrintExportDialog(p)
        # Standard: "long-edge"
        assert dlg._duplex_flip() == "long-edge"  # noqa: SLF001
        dlg._flip_combo.setCurrentIndex(1)  # noqa: SLF001
        assert dlg._duplex_flip() == "short-edge"  # noqa: SLF001
        dlg.close()

    def test_export_pdf_cancelled(self, qapp):
        from cardforge.print_dialog import PrintExportDialog

        p = _project_with_cards()
        dlg = PrintExportDialog(p)
        with patch("cardforge.print_dialog.QFileDialog.getSaveFileName", return_value=("", "")):
            dlg._export_pdf()  # noqa: SLF001
        # Kein Absturz, kein PDF geschrieben
        dlg.close()

    def test_export_pdf_appends_extension(self, qapp, tmp_path):
        from cardforge.print_dialog import PrintExportDialog

        p = _project_with_cards()
        dlg = PrintExportDialog(p)
        out = str(tmp_path / "output")
        with (
            patch("cardforge.print_dialog.QFileDialog.getSaveFileName", return_value=(out, "")),
            patch("cardforge.pdf_export.export_pdf") as mock_exp,
            patch("PySide6.QtWidgets.QMessageBox.information"),
        ):
            dlg._export_pdf()  # noqa: SLF001
            # Pfad sollte .pdf angehängt bekommen
            call_path = mock_exp.call_args[0][1]
            assert call_path.endswith(".pdf")
        dlg.close()

    def test_export_pdf_success(self, qapp, tmp_path):
        from cardforge.print_dialog import PrintExportDialog

        p = _project_with_cards()
        dlg = PrintExportDialog(p)
        out = str(tmp_path / "output.pdf")
        with (
            patch("cardforge.print_dialog.QFileDialog.getSaveFileName", return_value=(out, "")),
            patch("cardforge.pdf_export.export_pdf") as mock_exp,
            patch("PySide6.QtWidgets.QMessageBox.information") as mock_info,
        ):
            dlg._export_pdf()  # noqa: SLF001
            mock_exp.assert_called_once()
            mock_info.assert_called_once()
        dlg.close()

    def test_export_pdf_error_shows_critical(self, qapp, tmp_path):
        from cardforge.print_dialog import PrintExportDialog

        p = _project_with_cards()
        dlg = PrintExportDialog(p)
        out = str(tmp_path / "output.pdf")
        with (
            patch("cardforge.print_dialog.QFileDialog.getSaveFileName", return_value=(out, "")),
            patch("cardforge.pdf_export.export_pdf", side_effect=RuntimeError("export failed")),
            patch("PySide6.QtWidgets.QMessageBox.critical") as mock_crit,
        ):
            dlg._export_pdf()  # noqa: SLF001
            mock_crit.assert_called_once()
        dlg.close()

    def test_print_cancelled_at_dialog(self, qapp):
        """QPrintDialog abgelehnt → kein accept(), kein crash."""
        from cardforge.print_dialog import PrintExportDialog

        p = _project_with_cards()
        dlg = PrintExportDialog(p)
        with (
            patch("cardforge.pdf_export.export_pdf"),
            patch("PySide6.QtPrintSupport.QPrintDialog") as MockQPD,
            patch("PySide6.QtPrintSupport.QPrinter"),
            patch.object(dlg, "accept") as mock_accept,
        ):
            mock_dlg_inst = MagicMock()
            MockQPD.return_value = mock_dlg_inst
            # exec() returns something that is NOT MockQPD.DialogCode.Accepted
            mock_dlg_inst.exec.return_value = MagicMock()
            dlg._print()  # noqa: SLF001
            mock_accept.assert_not_called()
        dlg.close()

    def test_print_lpr_failure_shows_error(self, qapp):
        """lpr-Fehler → QMessageBox.critical."""
        from cardforge.print_dialog import PrintExportDialog

        p = _project_with_cards()
        dlg = PrintExportDialog(p)
        mock_printer = MagicMock()
        mock_printer.printerName.return_value = "TestPrinter"
        with (
            patch("cardforge.pdf_export.export_pdf"),
            patch("PySide6.QtPrintSupport.QPrintDialog") as MockQPD,
            patch("PySide6.QtPrintSupport.QPrinter", return_value=mock_printer),
            patch("subprocess.call", return_value=1),
            patch("PySide6.QtWidgets.QMessageBox.critical") as mock_crit,
        ):
            mock_dlg_inst = MagicMock()
            MockQPD.return_value = mock_dlg_inst
            mock_dlg_inst.exec.return_value = MockQPD.DialogCode.Accepted
            dlg._print()  # noqa: SLF001
            mock_crit.assert_called()
        dlg.close()

    def test_print_lpr_success(self, qapp):
        """lpr erfolgreich → accept() aufgerufen."""
        from cardforge.print_dialog import PrintExportDialog

        p = _project_with_cards()
        dlg = PrintExportDialog(p)
        mock_printer = MagicMock()
        mock_printer.printerName.return_value = ""
        with (
            patch("cardforge.pdf_export.export_pdf"),
            patch("PySide6.QtPrintSupport.QPrintDialog") as MockQPD,
            patch("PySide6.QtPrintSupport.QPrinter", return_value=mock_printer),
            patch("subprocess.call", return_value=0),
            patch.object(dlg, "accept") as mock_accept,
        ):
            mock_dlg_inst = MagicMock()
            MockQPD.return_value = mock_dlg_inst
            mock_dlg_inst.exec.return_value = MockQPD.DialogCode.Accepted
            dlg._print()  # noqa: SLF001
            mock_accept.assert_called_once()
        dlg.close()

    def test_print_export_error_shows_critical(self, qapp):
        """export_pdf wirft Fehler → critical-Box."""
        from cardforge.print_dialog import PrintExportDialog

        p = _project_with_cards()
        dlg = PrintExportDialog(p)
        with (
            patch("cardforge.pdf_export.export_pdf", side_effect=RuntimeError("fail")),
            patch("PySide6.QtWidgets.QMessageBox.critical") as mock_crit,
        ):
            dlg._print()  # noqa: SLF001
            mock_crit.assert_called_once()
        dlg.close()


# ---------------------------------------------------------------------------
# _show_preview – importiert print_preview per bare import
# ---------------------------------------------------------------------------


class TestShowPreview:
    def test_show_preview_front_side(self, qapp):
        """_show_preview mit front-Seite öffnet PreviewDialog."""
        import sys

        from cardforge.print_dialog import PrintExportDialog

        p = _project_with_cards(2)
        dlg = PrintExportDialog(p)
        mock_preview = MagicMock()
        mock_module = MagicMock()
        mock_module.PrintPreviewDialog.return_value = mock_preview
        with patch.dict(sys.modules, {"print_preview": mock_module}):
            dlg._show_preview()  # noqa: SLF001
        mock_preview.exec.assert_called_once()
        dlg.close()

    def test_show_preview_back_side_sets_rb_back(self, qapp):
        """_show_preview mit Rückseite wählt _rb_back vor."""
        import sys

        from cardforge.print_dialog import PrintExportDialog

        p = _project_with_cards(2)
        dlg = PrintExportDialog(p)
        dlg._rb_back.setChecked(True)  # noqa: SLF001
        mock_preview = MagicMock()
        mock_module = MagicMock()
        mock_module.PrintPreviewDialog.return_value = mock_preview
        with patch.dict(sys.modules, {"print_preview": mock_module}):
            dlg._show_preview()  # noqa: SLF001
        mock_preview._rb_back.setChecked.assert_called_with(True)
        dlg.close()
