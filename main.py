"""
Einstiegspunkt von CardForge.
"""
import sys

from PySide6.QtWidgets import QApplication

from cardforge._app_icon import get_app_icon
from cardforge.main_window import MainWindow
from cardforge.theme import apply_theme, detect_system_theme, get_saved_theme
from cardforge.translations import install_translator, saved_language


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("CardForge")
    app.setOrganizationName("CardForge")
    app.setStyle("Fusion")
    app.setWindowIcon(get_app_icon())

    # i18n: Translator vor dem ersten Widget-Aufbau installieren
    install_translator(app, saved_language())

    detect_system_theme()           # Systemthema erfassen, bevor wir die Palette überschreiben
    apply_theme(app, get_saved_theme())

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
