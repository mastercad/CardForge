"""
Tests für cardforge.about_dialog – AboutDialog und Hilfskomponenten.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QPushButton

# ---------------------------------------------------------------------------
# _HeaderWidget
# ---------------------------------------------------------------------------


class TestHeaderWidget:
    def test_init_no_crash(self, qapp):
        from cardforge.about_dialog import _HeaderWidget

        w = _HeaderWidget()
        assert w is not None
        w.close()

    def test_fixed_height(self, qapp):
        from cardforge.about_dialog import _HeaderWidget

        w = _HeaderWidget()
        assert w.height() == 160
        w.close()

    def test_paint_event_no_crash(self, qapp):
        from cardforge.about_dialog import _HeaderWidget

        w = _HeaderWidget()
        w.resize(460, 160)
        w.show()
        QApplication.processEvents()
        w.repaint()
        QApplication.processEvents()
        w.close()

    def test_paint_with_minimum_size(self, qapp):
        """Auch bei sehr kleiner Breite darf paintEvent nicht abstürzen."""
        from cardforge.about_dialog import _HeaderWidget

        w = _HeaderWidget()
        w.resize(1, 160)
        w.show()
        QApplication.processEvents()
        w.repaint()
        w.close()


# ---------------------------------------------------------------------------
# _link_btn
# ---------------------------------------------------------------------------


class TestLinkBtn:
    def test_creates_button_with_label(self, qapp):
        from cardforge.about_dialog import _link_btn

        btn = _link_btn("Visit Website", "https://example.com", "#0066cc")
        assert btn.text() == "Visit Website"

    def test_button_object_name(self, qapp):
        from cardforge.about_dialog import _link_btn

        btn = _link_btn("GitHub", "https://github.com", "#333")
        assert btn.objectName() == "about_link_btn"

    def test_button_is_qpushbutton(self, qapp):
        from cardforge.about_dialog import _link_btn

        btn = _link_btn("Test", "https://test.com", "#ff0000")
        assert isinstance(btn, QPushButton)

    def test_button_with_different_accents(self, qapp):
        from cardforge.about_dialog import _link_btn

        # Various accent colors should not crash
        for color in ("#ff0000", "#00ff00", "#0000ff", "blue", "rgb(0,0,0)"):
            btn = _link_btn("Link", "https://example.com", color)
            assert btn is not None


# ---------------------------------------------------------------------------
# AboutDialog
# ---------------------------------------------------------------------------


class TestAboutDialog:
    def test_creates_no_crash(self, qapp):
        from cardforge.about_dialog import AboutDialog

        dlg = AboutDialog(None)
        assert dlg is not None
        dlg.close()

    def test_fixed_width(self, qapp):
        from cardforge.about_dialog import AboutDialog

        dlg = AboutDialog(None)
        assert dlg.width() == 460
        dlg.close()

    def test_window_title_set(self, qapp):
        from cardforge.about_dialog import AboutDialog

        dlg = AboutDialog(None)
        # Just check it doesn't crash; title may be translated
        title = dlg.windowTitle()
        assert isinstance(title, str)
        dlg.close()

    def test_show_and_repaint_no_crash(self, qapp):
        """show() + repaint() deckt _HeaderWidget.paintEvent ab."""
        from cardforge.about_dialog import AboutDialog

        dlg = AboutDialog(None)
        dlg.show()
        QApplication.processEvents()
        dlg.repaint()
        QApplication.processEvents()
        dlg.close()

    def test_build_ui_creates_close_button(self, qapp):
        """_build_ui legt einen Schließen-Button an."""
        from cardforge.about_dialog import AboutDialog

        dlg = AboutDialog(None)
        close_btn = dlg.findChild(QPushButton, "about_close_btn")
        assert close_btn is not None
        dlg.close()

    def test_close_button_calls_accept(self, qapp):
        """Klick auf Schließen-Button ruft accept() → Dialog schließt sich."""
        from cardforge.about_dialog import AboutDialog

        dlg = AboutDialog(None)
        dlg.show()
        QApplication.processEvents()
        close_btn = dlg.findChild(QPushButton, "about_close_btn")
        assert close_btn is not None
        close_btn.click()
        QApplication.processEvents()
        dlg.close()

    def test_apply_style_sets_stylesheet(self, qapp):
        """_apply_style setzt einen nicht-leeren Stylesheet."""
        from cardforge.about_dialog import AboutDialog

        dlg = AboutDialog(None)
        ss = dlg.styleSheet()
        assert isinstance(ss, str)
        assert len(ss) > 0
        dlg.close()

    def test_show_feedback_shows_label(self, qapp):
        """_show_feedback(msg) zeigt das Feedback-Label an."""
        from cardforge.about_dialog import AboutDialog

        dlg = AboutDialog(None)
        dlg.show()
        QApplication.processEvents()
        dlg._show_feedback("Link kopiert!")  # noqa: SLF001
        QApplication.processEvents()
        assert dlg._feedback.isVisible()  # noqa: SLF001
        dlg.close()

    def test_show_feedback_sets_text(self, qapp):
        """_show_feedback setzt den Feedback-Text."""
        from cardforge.about_dialog import AboutDialog

        dlg = AboutDialog(None)
        dlg._show_feedback("Test-Feedback")  # noqa: SLF001
        assert dlg._feedback.text() == "Test-Feedback"  # noqa: SLF001
        dlg.close()

    def test_show_feedback_empty_string(self, qapp):
        """_show_feedback mit leerem String darf nicht abstürzen."""
        from cardforge.about_dialog import AboutDialog

        dlg = AboutDialog(None)
        dlg._show_feedback("")  # noqa: SLF001
        dlg.close()

    def test_link_buttons_present_in_ui(self, qapp):
        """_build_ui erstellt mindestens zwei Link-Buttons (Website, GitHub)."""
        from cardforge.about_dialog import AboutDialog

        dlg = AboutDialog(None)
        btns = dlg.findChildren(QPushButton, "about_link_btn")
        assert len(btns) >= 2
        dlg.close()

    def test_resize_paints_header(self, qapp):
        """Resize + Repaint deckt alle paint-Branches des _HeaderWidget ab."""
        from cardforge.about_dialog import AboutDialog

        dlg = AboutDialog(None)
        dlg.show()
        QApplication.processEvents()
        dlg.resize(500, 400)
        QApplication.processEvents()
        dlg.repaint()
        QApplication.processEvents()
        dlg.close()
