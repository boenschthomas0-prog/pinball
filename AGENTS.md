# AGENTS.md — Das VPX-Pinball-Studio

`~/Applications/pinball/` ist Thomas' Pinball-Studio und die Projekt-Wurzel.
Dieses Dokument beschreibt das Claude-Code-gemanagte Agenten-Team, das die
Visual-Pinball-Tische baut.

## Rollen

| Agent | Abteilung | Macht |
|---|---|---|
| `pinball-artwork` | Artwork & Design | Playfields, Backglass, Plastics, Bumper-Caps, Promo — plus Physik-/Engine-Verständnis |
| `vpx-developer` | Entwicklung | `script.vbs`-Logik, Gameitems-JSON, Build mit `vpxtool` |
| `vpx-qa` | QA | Tisch starten, Screenshot, Crash-Log, OK/KAPUTT-Urteil |

Die **Haupt-Claude-Session ist der Producer/Manager**: sie nimmt deine Wünsche
auf, zerlegt sie und ruft die Agenten über das Agent-Tool auf.

## Standard-Workflow für ein Tisch-Feature

1. **Producer** (Haupt-Session) zerlegt den Wunsch in Artwork- und Code-Teile.
2. **pinball-artwork** und/oder **vpx-developer** arbeiten am `exampleTable/`-Source.
3. **vpx-developer** baut den Tisch (`vpxtool assemble`) und deployt.
4. **vpx-qa** startet, screenshottet, prüft Logs → OK/KAPUTT.
5. **Producer** berichtet dem User und aktualisiert `STATUS.md`.

Artwork und Developer können parallel laufen (unabhängige Dateien); QA kommt
immer nach dem Build.

## Wo die Agenten leben

Die Agenten-Definitionen werden **hier im Projekt-Root gepflegt**
(`team/agents/*.md`, versioniert) und nach `~/.claude/agents/` **deployt**, damit
sie in allen Projekten verfügbar sind:

```bash
cp team/agents/*.md ~/.claude/agents/
```

Dasselbe "hier editieren, dorthin deployen"-Muster wie beim Menü-Skript.

## Agenten aufrufen

- **Automatisch:** beschreibe der Haupt-Session eine Aufgabe ("mach das Backglass
  schöner", "fix den Multiball-Bug", "test alle Tische") — sie wählt den Agenten.
- **Direkt:** die Haupt-Session nutzt das Agent-Tool mit
  `subagent_type: pinball-artwork` (bzw. `vpx-developer`, `vpx-qa`).

## Blender-Toolchain

Tisch-**Geometrie** (Meshes, Ramps, Lightmaps) entsteht in **Blender 4.5 LTS**,
installiert unter `blender/` (headless, via `bpy`-API gesteuert — keine GUI).

- `vpx-developer` führt die Headless-Skripte aus, `pinball-artwork` liefert die
  gestalterische Vorgabe.
- Kuratiertes Nachschlagewerk — Doku-Links, Workflow, `bpy`-Spickzettel:
  **`team/blender-reference.md`**. Vor jeder Blender-Arbeit lesen.

## Noch offen (siehe `STATUS.md`)

- Externe Bild-API für echte AI-Artwork-Generierung anbinden.
- Optional: Slash-Command, der einen kompletten Feature-Zyklus orchestriert.
