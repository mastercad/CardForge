"""Tests für cardforge.paper_template_dialog."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QCoreApplication

from cardforge.models import PaperTemplate


class TestPaperTemplateDialog:
    def test_creates_without_crash(self, qapp):
        from cardforge.paper_template_dialog import PaperTemplateDialog

        tmpl = PaperTemplate()
        dlg = PaperTemplateDialog(tmpl)
        assert dlg is not None
        dlg.close()

    def test_get_template_returns_paper_template(self, qapp):
        from cardforge.paper_template_dialog import PaperTemplateDialog

        tmpl = PaperTemplate(name="TestVorlage")
        dlg = PaperTemplateDialog(tmpl)
        result = dlg.result_template()
        assert isinstance(result, PaperTemplate)
        dlg.close()

    def test_template_name_preserved(self, qapp):
        from cardforge.paper_template_dialog import PaperTemplateDialog

        tmpl = PaperTemplate(name="MeineVorlage")
        dlg = PaperTemplateDialog(tmpl)
        result = dlg.result_template()
        assert result.name == "MeineVorlage"
        dlg.close()

    def test_custom_dimensions(self, qapp):
        from cardforge.paper_template_dialog import PaperTemplateDialog

        tmpl = PaperTemplate(
            paper_width=148.0, paper_height=210.0, card_width=60.0, card_height=40.0
        )
        dlg = PaperTemplateDialog(tmpl)
        result = dlg.result_template()
        assert result.paper_width == pytest.approx(148.0)
        assert result.paper_height == pytest.approx(210.0)
        dlg.close()

    def test_preset_a4_portrait(self, qapp):
        from cardforge.paper_template_dialog import PaperTemplateDialog

        tmpl = PaperTemplate()
        dlg = PaperTemplateDialog(tmpl)
        # Kein Crash beim Öffnen mit Standard-A4
        assert dlg.windowTitle() != ""
        dlg.close()

    def test_accept_gathers_values(self, qapp):
        from cardforge.paper_template_dialog import PaperTemplateDialog

        tmpl = PaperTemplate(name="X")
        dlg = PaperTemplateDialog(tmpl)
        dlg._name.setText("Geändert")  # noqa: SLF001
        dlg._pw.setValue(200.0)  # noqa: SLF001
        dlg._accept()  # noqa: SLF001
        assert dlg.result_template().name == "Geändert"
        assert dlg.result_template().paper_width == pytest.approx(200.0)
        dlg.close()

    def test_on_preset_updates_dimensions(self, qapp):
        from cardforge.paper_template_dialog import _PAPER_SIZE_DIMS, PaperTemplateDialog

        tmpl = PaperTemplate()
        dlg = PaperTemplateDialog(tmpl)
        # A4 Portrait auswählen (key "a4_portrait")
        idx = dlg._paper_preset.findData("a4_portrait")  # noqa: SLF001
        dlg._paper_preset.setCurrentIndex(idx)  # noqa: SLF001
        dlg._on_preset(idx)  # noqa: SLF001
        assert dlg._pw.value() == pytest.approx(_PAPER_SIZE_DIMS["a4_portrait"][0])  # noqa: SLF001
        assert dlg._ph.value() == pytest.approx(_PAPER_SIZE_DIMS["a4_portrait"][1])  # noqa: SLF001
        dlg.close()

    def test_on_preset_unknown_name_noop(self, qapp):
        from cardforge.paper_template_dialog import PaperTemplateDialog

        tmpl = PaperTemplate(paper_width=100.0)
        dlg = PaperTemplateDialog(tmpl)
        # "custom" hat None-Abmessungen → keine Änderung
        idx = dlg._paper_preset.findData("custom")  # noqa: SLF001
        dlg._paper_preset.setCurrentIndex(idx)  # noqa: SLF001
        dlg._on_preset(idx)  # noqa: SLF001
        assert dlg._pw.value() == pytest.approx(100.0)  # noqa: SLF001
        dlg.close()

    def test_auto_calc_updates_cols_rows(self, qapp):
        from cardforge.paper_template_dialog import PaperTemplateDialog

        tmpl = PaperTemplate(
            paper_width=210.0,
            paper_height=297.0,
            card_width=85.6,
            card_height=54.0,
            margin_top=13.5,
            margin_bottom=13.5,
            margin_left=8.0,
            margin_right=8.0,
            gap_h=17.8,
            gap_v=0.0,
        )
        dlg = PaperTemplateDialog(tmpl)
        dlg._auto_calc()  # noqa: SLF001
        # Sollte cols und rows aktualisieren (kein Absturz)
        assert dlg._cols.value() >= 1  # noqa: SLF001
        assert dlg._rows.value() >= 1  # noqa: SLF001
        dlg.close()

    def test_gather_returns_template_with_values(self, qapp):
        from cardforge.paper_template_dialog import PaperTemplateDialog

        tmpl = PaperTemplate()
        dlg = PaperTemplateDialog(tmpl)
        dlg._name.setText("TestName")  # noqa: SLF001
        dlg._pw.setValue(150.0)  # noqa: SLF001
        t = dlg._gather()  # noqa: SLF001
        assert t.name == "TestName"
        assert t.paper_width == pytest.approx(150.0)
        dlg.close()

    def test_gather_empty_name_defaults(self, qapp):
        from cardforge.paper_template_dialog import PaperTemplateDialog

        tmpl = PaperTemplate()
        dlg = PaperTemplateDialog(tmpl)
        dlg._name.setText("")  # noqa: SLF001
        t = dlg._gather()  # noqa: SLF001
        assert t.name == "Template"  # fallback
        dlg.close()

    def test_creates_without_template_argument(self, qapp):
        from cardforge.paper_template_dialog import PaperTemplateDialog

        dlg = PaperTemplateDialog()  # template=None → neues PaperTemplate
        assert dlg.result_template() is not None
        dlg.close()


class TestPaperPreviewWidget:
    def test_preview_paints_without_crash(self, qapp):
        from cardforge.paper_template_dialog import _PaperPreview

        preview = _PaperPreview()
        preview.set_template(PaperTemplate())
        preview.resize(400, 500)
        preview.show()
        preview.repaint()
        QCoreApplication.processEvents()
        preview.close()

    def test_preview_set_template_triggers_update(self, qapp):
        from cardforge.paper_template_dialog import _PaperPreview

        preview = _PaperPreview()
        tmpl = PaperTemplate(paper_width=200.0, paper_height=300.0)
        preview.set_template(tmpl)
        assert preview._tmpl is tmpl  # noqa: SLF001
        preview.close()

    def test_preview_paints_with_zero_rows_cols(self, qapp):
        from cardforge.paper_template_dialog import _PaperPreview

        preview = _PaperPreview()
        tmpl = PaperTemplate(rows=0, cols=0)
        preview.set_template(tmpl)
        preview.resize(400, 500)
        preview.show()
        preview.repaint()
        QCoreApplication.processEvents()
        preview.close()

    def test_preview_paints_with_nonzero_rows_cols(self, qapp):
        from cardforge.paper_template_dialog import _PaperPreview

        preview = _PaperPreview()
        tmpl = PaperTemplate(rows=2, cols=2, card_width=85.6, card_height=54.0)
        preview.set_template(tmpl)
        preview.resize(600, 700)
        preview.show()
        preview.repaint()
        QCoreApplication.processEvents()
        preview.close()

    def test_preview_card_outside_boundary_false_branch(self, qapp):
        """Karten, die außerhalb des Papiers liegen, decken [126,123]-Zweig ab."""
        from PySide6.QtWidgets import QApplication

        from cardforge.paper_template_dialog import _PaperPreview

        preview = _PaperPreview()
        # Papier viel zu schmal für 2 Spalten → zweite Spalte liegt außerhalb
        tmpl = PaperTemplate(
            rows=1,
            cols=2,
            card_width=85.6,
            card_height=54.0,
            paper_width=90.0,  # zu schmal für 2x 85.6 mm
            paper_height=100.0,
            gap_h=2.0,
        )
        preview.set_template(tmpl)
        preview.resize(400, 400)
        preview.show()
        QApplication.processEvents()
        preview.repaint()
        preview.close()
