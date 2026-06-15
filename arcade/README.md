# Thomas Arcade - VPinball Setup

Pinball-Spielkonsole auf Linux mit Visual Pinball X Standalone (VPinballX_GL 10.8.1).

## Was ist drin

- **vpinball-menu.py** - Vollbild-Menü: horizontaler Fisheye-Coverflow aus echten Tisch-Screenshots
- **vpinball-menu.sh** - Alte zenity-Fallback-Version
- **generate-previews.py** - zieht aus jeder `.vpx` das Playfield-Bild als Menü-Vorschau
- **shoot-tables.py** - nimmt echte In-Game-Screenshots für das Coverflow-Menü auf
- **icon.svg** - Pinball-Kabinett-Icon
- **VPinballX.ini** - VPX-Settings (Tasten 1=Start, 5=Coin, Space=Plunger, 9=Exit, etc.)
- **VPinball.desktop** - Desktop-Launcher
- **table-patches/** - Linux-Patches für Tische (z.B. BTILC ohne PinUp Player)
- **README-de.md** - Deutsche User-Anleitung

## Installation

```bash
sudo apt install python3-gi gir1.2-gtk-3.0 wmctrl unzip
# VPinballX_GL nach ~/Applications/pinball/vpx/ entpacken
git clone <this-repo> ~/vpx-arcade
cd ~/vpx-arcade
cp vpinball-menu.py icon.svg ~/Applications/pinball/vpx/
cp VPinballX.ini ~/.vpinball/
cp VPinball.desktop ~/Desktop/
cp table-patches/*.vbs ~/Applications/pinball/vpx/tables/
chmod +x ~/Applications/pinball/vpx/vpinball-menu.py ~/Desktop/VPinball.desktop
```

## Gelernte Wayland-/Linux-Fallstricke

- VPX braucht `SDL_VIDEODRIVER=x11` und das Menü `GDK_BACKEND=x11`
- GTK fullscreen() unter Mutter+Wayland: manuell mit wmctrl nachhelfen
- VPinball-Standalone crasht beim Shutdown mancher Tische (`free(): invalid size`, Exit 134) - bekannter Engine-Bug, NICHT der Tisch
- xrandr-Rotation: auf manchen Setups durch GPU/Treiber blockiert
- PUP (PinUp Player) ist Windows-only - betroffene Tische über VBScript-Dummy patchen

## Menü-Steuerung (Coverflow)

| Taste | Aktion |
|---|---|
| ◀ / ▶  ·  L-/R-Shift | Tisch wählen |
| Enter / Leertaste | gewählten Tisch starten |
| F5 / F8 | Tisch als LÄUFT / DEFEKT markieren |
| 9 | Menü beenden |

## Tasten im Spiel

| Taste | Aktion |
|---|---|
| 1 | Spiel starten |
| 5 | Münze einwerfen |
| Leertaste | Plunger / Kugel schießen |
| L-Shift / R-Shift | Linker / Rechter Flipper |
| 9 oder ESC | Tisch beenden → zurück ins Menü |
| P | Pause |
