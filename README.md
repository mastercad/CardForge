# CardForge

Professioneller Visitenkarten-Editor – portabel für Windows, macOS und Linux.

## Starten

```bash
# Einmalig:
python3 -m venv .venv
.venv/bin/python -m pip install -e .

# Starten:
.venv/bin/python main.py
```

## Features

| Feature | Beschreibung |
|---------|-------------|
| **Papiervorlagen** | Eingebaute Vorlagen (Avery, Sigel) + eigene anlegen |
| **Kartenlayouts** | Mehrere Karten pro Projekt, Vorder- und Rückseite |
| **Elemente** | Text, Bild, Rechteck, Ellipse, Linie, QR-Code |
| **Text** | Alle Systemschriften + eigene TTF/OTF laden |
| **Ausrichten** | An Karte oder Gruppe: links/rechts/oben/unten/mittig |
| **Skalierung** | Frei oder proportional (Bilder) |
| **Raster & Snap** | Einstellbares Raster, Snap-to-Grid |
| **Undo/Redo** | Vollständige Undo-Historie (100 Schritte) |
| **Farbpalette** | Eigene Palette speichern, direkt auf Elemente anwenden |
| **Mail Merge** | CSV/Excel einlesen, Platzhalter `{{Feldname}}` ersetzen |
| **PDF-Export** | Druckfertig mit Schnittmarken, ein- oder beidseitig |
| **Drucken** | Direkt über Systemdrucker |
| **Vorlagen** | Karten als `.vctemplate` exportieren/importieren |

## Dateiformat

- **Projekt:** `.vcproj` (JSON)
- **Vorlage:** `.vctemplate` (JSON)

## Mail Merge

1. In Text-Elemente Platzhalter eintragen: `{{Vorname}}`, `{{Nachname}}`, `{{Titel}}`
2. Extras → Seriendruck → CSV/Excel mit gleichen Spaltennamen laden
3. Karten werden automatisch generiert

## Portabilität / Distribution

Mit PyInstaller als Einzeldatei distribuierbar:

```bash
.venv/bin/python -m pip install pyinstaller
.venv/bin/python -m PyInstaller --onefile --windowed main.py
```
