# Pinball-Studio — Projekt-Kontext

## Was ist dieses Projekt?

`~/Applications/pinball/` ist Thomas' **Pinball-Studio** — alles an einem Ort:
ein Linux-Flipperautomat auf Basis von Visual Pinball X (`VPinballX_GL`) plus ein
Claude-Code-gemanagtes Agenten-Team, das eigene Tische baut. Dieser Ordner ist
die **Projekt-Wurzel** — hier liegen Kontext, Status und das Agenten-Team.
Claude Code wird hier geöffnet.

## Aufbau

| Eintrag | Rolle | Git? |
|---|---|---|
| `CLAUDE.md` · `STATUS.md` · `AGENTS.md` | Projekt-Kontext, Status, Agenten-Doku | — |
| `team/` | Agenten-Definitionen (`agents/`, deployt nach `~/.claude/agents/`) + Studio-Doku (`blender-reference.md`) | — |
| `arcade/` | Konsolen-Quellcode: Vollbild-Menü, Launcher, VPX-Settings, Tisch-Patches | ✅ |
| `vpx/` | VPX-Installation: Binary `VPinballX_GL`, `tables/`, libs, `vpxtool` | ❌ |
| `blender/` | Blender 4.5 LTS — headless 3D-Toolchain für Tisch-Geometrie (`bpy`) | ❌ |
| `backups/` | Snapshots / Sicherungen | ❌ |
| `runtime/` | Verknüpfung → `~/.vpinball/` (VPX-Laufzeit: Settings, ROMs, Cache) | — |

Die VPX-Laufzeit liegt physisch unter `~/.vpinball/` — die Engine liest sie von
dort, der Pfad lässt sich nicht verschieben. `runtime/` ist die Verknüpfung
dorthin. Editiert wird im Git-Ordner `arcade/`; nach `vpx/`
bzw. `~/.vpinball/` wird **deployt** (kopiert).

## Session-Protokoll — WICHTIG

So bleibt Claude über Sessions hinweg informiert:

1. **Beim Session-Start:** `STATUS.md` wird automatisch geladen (SessionStart-Hook
   in `.claude/settings.json`). Sie zeigt *erledigt* und *offen*. Wenn der Hook
   mal nicht greift: `STATUS.md` zuerst selbst lesen.
2. **Während der Arbeit:** Größere Aufgaben in `STATUS.md` unter "Gerade in Arbeit"
   führen.
3. **Am Session-Ende — `STATUS.md` aktualisieren:**
   - Fertiges von "Offen" nach "✅ Erledigt" verschieben (mit Datum).
   - Neu Aufgetauchtes unter "Offen / Backlog" ergänzen.
   - `Zuletzt aktualisiert`-Datum setzen.
   - Im "Session-Log" einen kurzen datierten Block anhängen.
   - Datum verlässlich beziehen: `date +%F`.

So weiß jede neue Session sofort, was lief und was noch aussteht.

## Das Agenten-Team — Claude-Code-gemanagtes Studio

Thomas' Studio baut Visual-Pinball-Tische als **Claude-Code-gemanagtes
Agenten-Team**. Die Haupt-Claude-Session ist der **Producer** und ruft drei
Spezial-Agenten auf:

- **`pinball-artwork`** — Playfields, Backglass, Plastics, Bumper-Caps, Promo-Bilder
- **`vpx-developer`** — `script.vbs`-Logik, Gameitems, Build via `vpxtool`
- **`vpx-qa`** — Tische starten, screenshotten, Crash-Logs prüfen, validieren

Rollen, Workflow und Deploy: siehe **`AGENTS.md`**. Agenten-Quelle liegt in
`team/agents/` und wird nach `~/.claude/agents/` deployt.

## Wichtige Dateien

**Projekt-Wurzel (`pinball/`):**

| Datei | Wofür |
|---|---|
| `CLAUDE.md` | dieser Projekt-Kontext (lädt jede Session) |
| `STATUS.md` | lebender Done/Offen-Tracker |
| `AGENTS.md` | Agenten-Team: Rollen, Workflow, Deploy |
| `team/agents/*.md` | Agenten-Definitionen |
| `team/blender-reference.md` | Blender-für-VPX: Doku-Links, Workflow, `bpy`-Spickzettel |
| `.claude/settings.json` | SessionStart-Hook (lädt `STATUS.md`) |

**Konsolen-Quellcode (`arcade/`):**

| Datei | Wofür |
|---|---|
| `vpinball-menu.py` | Vollbild-Menü: horizontaler Fisheye-Coverflow (echte Tisch-Screenshots) |
| `vpinball-menu.sh` | alte zenity-Fallback-Version |
| `generate-previews.py` | Playfield-Bilder aus den `.vpx` für die Menü-Vorschau ziehen |
| `shoot-tables.py` | echte In-Game-Screenshots fürs Coverflow-Menü aufnehmen |
| `VPinballX.ini` | VPX-Settings-Vorlage für `~/.vpinball/` |
| `VPinball.desktop` | Desktop-Launcher |
| `icon.svg` | Kabinett-Icon |
| `table-patches/*.vbs` | Linux-Patches für Tische (PUP rausnehmen etc.) |
| `README.md` / `README-de.md` | Setup-Anleitung (DE) / User-Anleitung |

## Deploy-Workflow

```bash
cp arcade/vpinball-menu.py arcade/icon.svg ~/Applications/pinball/vpx/
cp arcade/VPinballX.ini ~/.vpinball/
cp arcade/VPinball.desktop ~/Desktop/
cp arcade/table-patches/*.vbs ~/Applications/pinball/vpx/tables/
```

Einen Tisch direkt starten (umgeht das Menü):

```bash
cd ~/Applications/pinball/vpx
DISPLAY=:0 SDL_VIDEODRIVER=x11 ./VPinballX_GL -Primary -DisableTrueFullscreen \
    -Play "tables/<tisch>.vpx"
```

## Linux-/Wayland-Fallstricke (hart erkauft)

- Menü braucht `GDK_BACKEND=x11`, VPX braucht `SDL_VIDEODRIVER=x11` — sonst kein
  echter Vollbildmodus unter Mutter/Wayland.
- VPX-Standalone crasht beim Shutdown mancher Tische (`free(): invalid size`,
  Exit 134) — Engine-Bug, nicht der Tisch.
- PinUp Player (PUP) ist Windows-only → betroffene Tische über VBScript-Dummy
  patchen (`arcade/table-patches/`).
- Echte Maschinen-Recreations (Williams, Bally…) brauchen PinMAME-ROMs in
  `~/.vpinball/pinmame/roms/`. Original-Tische brauchen keine ROMs.
- Nach jedem Tisch-Edit den Cache löschen: `rm -rf ~/.vpinball/Cache/<tischname>`.

## Verwandte Skills & Slash-Commands

Global verfügbar (`~/.claude/`):

- `/vpx-crash-log` — letzten VPX-Crash aus `last-run.log` analysieren
- `/vpx-menu-restart` — Pinball-Menü sauber neu starten
- `/vpx-screenshot` — Screenshot des VPinball-Fensters

## Tastenbelegung (Referenz)

| Taste | Aktion |
|---|---|
| 1 | Spiel starten · 5 Münze · Leertaste Plunger |
| L-/R-Shift | linker / rechter Flipper |
| 9 oder ESC | Tisch beenden → zurück ins Menü · P Pause |
