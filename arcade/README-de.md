# VPinball - Anleitung

Kurze Anleitung, wie du VPinball auf diesem Rechner startest und Tische verwaltest.

## So startest du das Spiel

### Variante 1: Per Doppelklick (einfachster Weg)

1. Doppelklick auf **VPinball.desktop** auf dem Desktop.
2. Beim ersten Mal fragt Linux evtl. "Vertrauen und ausführen" - bestätigen.
3. Es erscheint der **Coverflow** - alle Tische als Screenshot-Karten nebeneinander,
   der gewählte in der Mitte groß.
4. Mit **◀ / ▶** (oder den Flipper-Tasten) den Tisch wählen, **Enter** startet ihn.
5. Nach dem Beenden (ESC oder 9 im Spiel) bist du zurück im Coverflow.

### Variante 2: Per Terminal

```bash
/home/thomas/Applications/pinball/vpx/vpinball-menu.py
```

### Variante 3: Direkt einen bestimmten Tisch starten

```bash
cd /home/thomas/Applications/pinball/vpx
./VPinballX_GL -Primary -DisableTrueFullscreen -Play "tables/alien13.vpx"
```

## Tasten im Spiel

| Taste | Funktion |
|---|---|
| **Linke Shift** | Linker Flipper |
| **Rechte Shift** | Rechter Flipper |
| **Leertaste (SPACE)** | Plunger (Kugel abschießen) |
| **1** | Spiel starten (Start) |
| **5** | Münze einwerfen / Credit (Coin 1) |
| **4** | zweite Münze (Coin 2, falls Tisch's anbietet) |
| **P** | Spiel pausieren / fortsetzen |
| **ESC** | Spiel beenden → zurück ins Menü |
| **9** | Spiel beenden → zurück ins Menü (alternativ) |

**Typischer Spielablauf:**
1. Im Menü Tisch wählen → Enter
2. Im Spiel **5** drücken (Münze)
3. **1** drücken (Spiel starten)
4. **Leertaste** halten → Kugel schießt mit Stärke
5. Spielen mit **Shift links/rechts** für Flipper
6. **9** oder **ESC** wenn fertig → zurück ins Menü

## Aktuell installierte Tische (12 Spiel-Tische + 3 Test-Tische)

Status nach dem Setup vom 2026-05-20:

| # | Tisch | Status | Anmerkung |
|---|---|---|---|
| 1 | **alien13.vpx** | **OK** | bestätigt, läuft sauber |
| 2 | **BTILC_2026_Original_1.0.0.vpx** | **OK** | bestätigt, läuft |
| 3 | F-14 Tomcat (Williams 1987) 1.6.vpx | **? testen** | PinMAME-Pfad gefixt - sollte jetzt mit Sound laufen |
| 4 | Futurama (Original 2024) v1.2.2.vpx | **? testen** | Original, kein ROM nötig |
| 5 | GOTG_2.1.0.vpx | **? testen** | Guardians of the Galaxy |
| 6 | Ramones (HauntFreaks 2021) v2.0.vpx | **? testen** | hat Standalone-.vbs daneben |
| 7 | Halloween (Granit 2020).vpx | **NEU** | von archive.org geladen, ungetestet |
| 8 | Stranger Things (Granit 2020).vpx | **NEU** | von archive.org, ungetestet |
| 9 | Houdini (Granit 2020).vpx | **NEU** | von archive.org, ungetestet |
| 10 | Alice Cooper Nightmare Castle (Ling Woo).vpx | **NEU** | von archive.org, ungetestet |
| 11 | Yellow Submarine (Giantomasi 2020).vpx | **NEU** | von archive.org, ungetestet |
| 12 | Bram Stokers Dracula (Williams 1993) | **KAPUTT** | PinMAME-ROM `drac_l1.zip` fehlt. Nicht spielbar bis ROM beschafft. |
| - | JP's VPX7 Rev3 Elasticity_Test | TEST | nur Physik-Kalibrierung |
| - | Nudge Test and Calibration | TEST | nur Tilt-Kalibrierung |
| - | Screen Size Calibration | TEST | nur Bildschirm-Setup |

**Ziel von 10 funktionierenden Tischen:**
- 2 bestätigt OK (alien13, BTILC)
- 5 ungetestet aber sehr wahrscheinlich OK (F-14 mit Sound-Fix, Futurama, GOTG, Ramones + die 5 neuen Granit/Ling Woo Tische)
- 1 fix nötig (Dracula braucht ROM)

→ **Du musst die 5+5 ungetesteten Tische durchchecken** - dafür gibt's jetzt den **Test-Modus** im Menü.

## Tische als OK / DEFEKT markieren

Jede Karte im Coverflow hat oben links einen Status-Punkt: grün = läuft,
rot = defekt, blau = neu, gelb = ungetestet. Den Status setzt du direkt im
Menü, ohne extra Test-Modus:

- Tisch in die Mitte stellen, dann **F5** drücken → markiert als **LÄUFT**
- **F8** drücken → markiert als **DEFEKT**

Der Status wird in `~/Applications/pinball/vpx/table-status.txt` gespeichert
und beim nächsten Menü-Start wieder angezeigt.

**Plan:** Geh einmal durch alle Tische, starte jeden kurz an, und markier mit
F5/F8 was läuft - dann hast du eine saubere Liste der spielbaren Tische.

## Warum funktionieren einige nicht?

**Dracula und F-14** sind Nachbauten echter Flipperautomaten (Williams 1987/1993). Die brauchen die original ROMs (kleine `.zip`-Dateien mit z.B. `f14_u19.l1` drin), legal nur erhältlich wenn man die echte Maschine besitzt - oder über vpforums.org für Bildungs-/Backup-Zwecke.

Im Verzeichnis `~/.vpinball/pinmame/roms/` liegen aktuell **falsche** Dateien: dort sind die kompletten Tisch-Downloads gelandet (.vpx-Dateien drin), statt echter PinMAME-ROMs. Nur `f14_l1.zip` ist ein echtes ROM-Paket.

**Fix für F-14**: Die PinMAME-Plugin-Konfiguration ist leer. In `~/.vpinball/VPinballX.ini` unter `[Plugin.PinMAME]` muss `PinMAMEPath = /home/thomas/.vpinball/pinmame` gesetzt werden (steht aktuell unter `[Player]`, aber das Plugin liest aus der eigenen Sektion).

**Fix für Dracula**: ROM `drac_l1.zip` (oder `drac_l2.zip`) besorgen und nach `~/.vpinball/pinmame/roms/` legen.

## Neue Tische hinzufügen

1. Tisch (`.vpx` Datei) nach `/home/thomas/Applications/pinball/vpx/tables/` kopieren.
2. Vorschaubild erzeugen, damit der Tisch eine Karte im Coverflow bekommt:
   `cd ~/Applications/pinball/arcade && python3 generate-previews.py`
   (zieht das Playfield-Bild) — oder `python3 shoot-tables.py` für einen echten
   In-Game-Screenshot.
3. Menü neu starten - der Tisch erscheint im Coverflow.
4. Falls der Tisch eine echte alte Maschine emuliert (Williams, Bally, Gottlieb...):
   - PinMAME-ROM (z.B. `drac_l1.zip`) nach `/home/thomas/.vpinball/pinmame/roms/` legen.

### Wo gute Tische herkommen

- **vpforums.org** - größte Sammlung, kostenlose Registrierung
- **vpuniverse.com** - viele moderne Originals und Recreations
- **monsterbashers.com / pinballnirvana.com** - kuratierte Listen

Tipp: Such nach "VPX 10.8" - das passt zur installierten Version.
Recommended für stabiles Spielen ohne Probleme:
- **Original-Tische** (z.B. die schon installierten "Futurama", "Ramones", "BTILC") - brauchen keine ROMs.
- Recreations von **VPW (Visual Pinball Workshop)** - sehr hohe Qualität.

## Wenn ein Tisch nicht startet

1. **Log ansehen:** `/home/thomas/Applications/pinball/vpx/last-run.log` - dort steht warum.
2. **Cache des Tisches löschen:** `rm -rf ~/.vpinball/Cache/<tischname>`
3. **Fehlende ROM?** Log zeigt z.B. "ROM not found: drac_l1" - dann ROM nach `~/.vpinball/pinmame/roms/` legen.
4. **Komplettreset der Einstellungen** (letzte Option):
   ```bash
   pkill -f VPinballX_GL
   mv ~/.vpinball ~/.vpinball.broken
   cp -r ~/.vpinball.STABLE ~/.vpinball
   ```
   `.vpinball.STABLE` ist eine bestehende Sicherung von früher.

## Wichtige Pfade

| Was | Wo |
|---|---|
| VPinball Programm | `/home/thomas/Applications/pinball/vpx/VPinballX_GL` |
| Tisch-Dateien | `/home/thomas/Applications/pinball/vpx/tables/` |
| Menü-Skript | `/home/thomas/Applications/pinball/vpx/vpinball-menu.py` |
| Einstellungen | `/home/thomas/.vpinball/VPinballX.ini` |
| PinMAME ROMs | `/home/thomas/.vpinball/pinmame/roms/` |
| Log | `/home/thomas/Applications/pinball/vpx/last-run.log` |
| Backup-Einstellungen | `/home/thomas/.vpinball.STABLE/` |
