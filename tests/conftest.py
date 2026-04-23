"""
Gemeinsame pytest-Fixtures für alle Tests.
Der Qt-QPA-Platform-Offscreen-Mode wird über die Umgebungsvariable
QT_QPA_PLATFORM=offscreen gesetzt (in pyproject.toml oder CI).
"""

from __future__ import annotations

import os
import sys

import pytest

# Sicherstellen, dass kein echtes Display benötigt wird
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


# ---------------------------------------------------------------------------
# QSettings-Isolation: Tests schreiben nie in die echten CardForge-Settings
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True, scope="session")
def _isolate_qsettings(tmp_path_factory):
    """Leitet QSettings auf ein temporäres Verzeichnis um, damit Tests nie in
    die echten Benutzer-Settings (recentFiles usw.) schreiben.

    Auf Linux liest Qt QSettings-Pfade aus XDG_CONFIG_HOME – daher wird diese
    Umgebungsvariable auf ein temporäres Verzeichnis gesetzt. Zusätzlich wird
    QSettings.setPath gesetzt, um auch explizit konfigurierte Instanzen
    abzufangen.
    """
    from PySide6.QtCore import QSettings

    tmp = tmp_path_factory.mktemp("qsettings")

    # Primäre Absicherung: XDG_CONFIG_HOME auf tmp setzen (Linux)
    original_xdg = os.environ.get("XDG_CONFIG_HOME")
    os.environ["XDG_CONFIG_HOME"] = str(tmp)

    # Sekundäre Absicherung: Qt-interne Pfadumleitung
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp))
    QSettings.setPath(QSettings.Format.NativeFormat, QSettings.Scope.UserScope, str(tmp))

    yield

    # Umgebungsvariable wiederherstellen
    if original_xdg is None:
        os.environ.pop("XDG_CONFIG_HOME", None)
    else:
        os.environ["XDG_CONFIG_HOME"] = original_xdg


# ---------------------------------------------------------------------------
# QApplication – einmalig pro Test-Session
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def qapp():
    """Liefert eine QApplication-Instanz für die gesamte Test-Session."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv[:1])
    # Verhindert, dass Qt die Anwendung beendet, wenn das letzte Fenster geschlossen wird.
    # Ohne diesen Aufruf könnten Tests nach dem Schließen aller Fenster fehlschlagen.
    app.setQuitOnLastWindowClosed(False)
    yield app


@pytest.fixture(autouse=True)
def _drain_qt_events():
    """Zerstört nach jedem Test alle via WA_DeleteOnClose geschlossenen Widgets.

    Qt verarbeitet DeferredDelete-Events (von deleteLater/WA_DeleteOnClose) erst
    beim nächsten Event-Loop-Durchlauf.  sendPostedEvents(DeferredDelete) erzwingt
    diesen Schritt explizit, ohne einen laufenden Event-Loop zu benötigen.  So
    akkumulieren keine Zombie-Widgets über Tests hinweg, die sonst z. B.
    app.setStyleSheet() massiv verlangsamen würden.
    """
    yield
    import gc

    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is not None:
        gc.collect()  # Python-Referenzzyklen auflösen
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


# ---------------------------------------------------------------------------
# Modell-Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def card_element():
    """Einfaches CardElement mit Standardwerten."""
    from cardforge.models import CardElement

    return CardElement()


@pytest.fixture()
def text_element():
    """Text-CardElement mit gesetztem Text."""
    from cardforge.models import ELEMENT_TEXT, CardElement

    e = CardElement(type=ELEMENT_TEXT, text="Max Mustermann", x=5.0, y=5.0, width=40.0, height=10.0)
    return e


@pytest.fixture()
def card_layout(text_element):
    """CardLayout mit einem Text-Element auf der Vorderseite."""
    from cardforge.models import CardLayout

    layout = CardLayout(name="Testkarte")
    layout.front_elements.append(text_element)
    return layout


@pytest.fixture()
def paper_template():
    """Standard-Papiervorlage (A4)."""
    from cardforge.models import PaperTemplate

    return PaperTemplate()


@pytest.fixture()
def project(card_layout, paper_template):
    """Vollständiges Projekt mit einer Karte."""
    from cardforge.models import Project

    p = Project(name="Testprojekt")
    p.paper_template = paper_template
    p.cards.append(card_layout)
    return p
