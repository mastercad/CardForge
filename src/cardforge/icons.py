"""
Visitenkarten-Icons via qtawesome (FontAwesome 5 + Brands).

Mapping: interner Name -> qtawesome-Icon-ID
Skalierung und Farbe werden zur Laufzeit gesetzt.
"""

from __future__ import annotations

import qtawesome as qta
from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QPixmap

# ---------------------------------------------------------------------------
# Icon-Mapping: interner Name → qtawesome-ID
# ---------------------------------------------------------------------------

ICONS: dict[str, str] = {
    # Communication
    "phone": "fa5s.phone",
    "mobile": "fa5s.mobile-alt",
    "fax": "fa5s.fax",
    "email": "fa5s.envelope",
    # Internet / Location / Person
    "web": "fa5s.globe",
    "location": "fa5s.map-marker-alt",
    "person": "fa5s.user",
    "company": "fa5s.building",
    "clock": "fa5s.clock",
    # Social networks (Brands)
    "linkedin": "fa5b.linkedin",
    "xing": "fa5b.xing",
    "instagram": "fa5b.instagram",
    "facebook": "fa5b.facebook-square",
    "twitter": "fa5b.twitter",
    "youtube": "fa5b.youtube",
    # Other useful icons
    "print": "fa5s.print",
    "link": "fa5s.link",
    "at": "fa5s.at",
}


def get_icon_label(name: str) -> str:
    """Gibt den übersetzten Anzeigenamen für ein Icon zurück.

    Muss zur Laufzeit aufgerufen werden (nach Translator-Installation),
    damit QCoreApplication.translate() die aktive Übersetzung liefert.
    """
    tr = lambda s: QCoreApplication.translate("Icons", s)  # noqa: E731
    labels: dict[str, str] = {
        "phone": tr("Phone"),
        "mobile": tr("Mobile"),
        "fax": tr("Fax"),
        "email": tr("E-Mail"),
        "web": tr("Website"),
        "location": tr("Location"),
        "person": tr("Person"),
        "company": tr("Company"),
        "clock": tr("Time"),
        "linkedin": "LinkedIn",
        "xing": "Xing",
        "instagram": "Instagram",
        "facebook": "Facebook",
        "twitter": "Twitter / X",
        "youtube": "YouTube",
        "print": tr("Printer"),
        "link": tr("Link"),
        "at": tr("@ (E-Mail)"),
    }
    return labels.get(name, name)


def get_icon_pixmap(icon_name: str, color: str, size: int) -> QPixmap | None:
    """Gibt ein QPixmap des Icons in der gewünschten Farbe und Größe zurück."""
    fa_name = ICONS.get(icon_name)
    if fa_name is None:
        return None
    try:
        icon = qta.icon(fa_name, color=color)
        pm = icon.pixmap(size, size)
        return pm if not pm.isNull() else None
    except Exception:
        return None
