# Projekt-Status — Pinball-Studio

> **Lebende Datei.** Wird beim Session-Start automatisch in den Kontext geladen
> (SessionStart-Hook in `.claude/settings.json`). Sie beantwortet zwei Fragen:
> **Was ist erledigt?** und **Was ist noch offen?**
>
> **Claude:** Diese Datei am Ende jeder Session aktualisieren. Protokoll dazu
> steht in `CLAUDE.md` → Abschnitt "Session-Protokoll".

**Zuletzt aktualisiert:** 2026-06-15 (Tisch-Start-Test: blankTable OK, AFM/YS schwarzer Bildschirm)

---

## 🔧 Gerade in Arbeit

- _(nichts aktiv)_

## 📋 Offen / Backlog

### Arcade-Konsole (`arcade/`)
- [ ] **Spielstände / Statistiken — Design steht, Umsetzung offen.** Thomas hat
      die Konzept-Entscheidungen getroffen (Session 2026-05-21):
      - **Daten:** Highscores + Play-Tracking *kombiniert* — pro Tisch der echte
        Highscore & die Initialen aus `~/.vpinball/VPReg.ini` (PinMAME-Tische:
        NVRAM, best-effort), PLUS vom Menü geführt: Spiele gespielt, Gesamt-
        Spielzeit, zuletzt gespielt.
      - **Speicher:** `~/.vpinball/arcade-stats.json`, vom Menü geschrieben. Das
        Menü umschließt jeden Tischstart und kennt Start/Exit/Dauer exakt; nach
        dem Exit `VPReg.ini` diffen → neue/geänderte Section dem gestarteten
        Tisch zuordnen (Section-Namen ≠ Dateinamen, z.B. `gotg_2020`, `BTILC`).
      - **Menü-Anzeige:** „Backbox-Score-Panels" — dauerhaft sichtbare
        Dot-Matrix-Panels links/rechts neben der zentralen DMD (Highscore
        links, eigene Play-Stats rechts).
      - **In-Game:** kleines Always-on-Top-Overlay oben rechts, gleiche
        Dot-Matrix-Optik (`render_dots`), zeigt dieselben Tisch-Stats. Eigenes
        Skript, vom Menü beim Start gespawnt / beim Exit beendet. VPX läuft
        windowed (`-DisableTrueFullscreen`), Overlay daher machbar — Stacking
        über VPX mit QA testen. Live-Score ist NICHT von außen auslesbar
        (nur die Tisch-DMD hat ihn) → das Overlay zeigt statische Stats.
- [ ] **Theme-Musik pro Tisch** — aktuell teilen sich alle 13 Tische EIN
      zufälliges Menü-Theme (`themes/_menu-*.ogg`). Thomas möchte pro Tisch
      *unterschiedliche* Musik. → 13 passende lizenzfreie Tracks beschaffen
      (CC0/CC-BY) und als `themes/<Tischname>.<ext>` ablegen; das Menü zieht
      sie dann automatisch (Per-Tisch-Datei schlägt Menü-Theme).
- [ ] **Yellow Submarine — Stehend/Sitzend-POV feinjustieren**: die Werte in
      `VIEW_MODES` (`vpinball-menu.py`: `LookAt`/`Layback`) sind grob geschätzt
      und müssen mit dem Auge eingestellt werden. Mechanik bestätigt
      funktionierend ("passt im Prinzip"); Winkel zuletzt entschärft.
- [ ] **Watchmen & Futurama** — echte In-Game-Screenshots aufnehmen
      (`python3 shoot-tables.py watchmen futurama`). Beide haben im Fisheye-Rad
      aktuell nur eine flache Playfield-Textur statt eines echten Tisch-Bildes.
- [ ] Ungetestete Tische im **TEST-Modus** des Menüs durchchecken; Ergebnis landet
      in `~/Applications/pinball/vpx/table-status.txt` (per-Tisch-Tracker, OK/KAPUTT).
- [ ] `~/.vpinball/pinmame/roms/` aufräumen — dort liegen versehentlich `.vpx`-Tisch-
      Downloads statt echter PinMAME-ROMs.
- [ ] Dracula (falls wieder eingespielt): ROM `drac_l1.zip`/`drac_l2.zip` beschaffen.
- [ ] F-14: PinMAME-Pfad-Fix verifizieren (`[Plugin.PinMAME] PinMAMEPath=...`).

### Studio / Agenten-Team
- [ ] Externe Bild-API für AI-Artwork-Generierung anbinden (DALL·E / Stable Diffusion)
- [ ] Optional: Slash-Command, der einen kompletten Feature-Zyklus orchestriert
- [ ] Entscheiden: ein Mono-Repo oder getrennte Repos pro Tisch
- [ ] **Entscheidung: `vpx_lightmapper` auf Linux portieren — ja/nein?**
      Getestet 2026-05-22 (Blender 4.5, headless): das Add-on läuft auf Linux
      **nicht** — harte Windows-Abhängigkeit `win32crypt`/`pywin32`. Der
      Import-Teil ist portabel (`olefile`+`Pillow`), nur der `.vpx`-**Export**
      ist Windows-gebunden (Windows-CryptoAPI + OLE-Storage). Kein Blender-
      Versions-, sondern ein OS-Problem. Optionen: **A)** beim OBJ-Weg bleiben
      (Modeling/Bake mit Blender 4.5 gehen sofort); **B)** `vlm_export.py`
      portieren (Export über `vpxtool assemble`). Details:
      `team/blender-reference.md`.

## ✅ Erledigt

- **2026-05-27** — **Erste eigene Blender-Assets für Roulette-Tisch (Headless-Pipeline).**
  Neuer Projekt-Ordner `blender-projects/roulette-bumper-cap/` mit drei Skripten und
  Renders/OBJ-Exporten:
  - `casino_chip_cap.py` — modularer Builder (ChipSpec-Dataclass, build_chip()),
    erzeugt einen "edlen" Casino-Chip-Bumper-Cap: 50mm-Body mit Dome-Top, 8 Edge-Spots,
    goldener Außenring auf halber Höhe, helles Inlay mit aufgepresster 3D-Wertzahl
    ("17"). Cycles-Render + OBJ/MTL/.blend-Export. ~300 Zeilen, ausführlich
    deutsch kommentiert für Lern-Workflow.
  - `chip_set.py` — importiert build_chip() und rendert 6 Roulette-Chips
    (weiß/rot/blau/grün/schwarz/lila, Werte 1/5/10/25/100/500) in einer Reihe
    auf Casino-Felt. Eevee statt Cycles (Faktor ~30 schneller).
  - `roulette_wheel.py` — europäisches Roulette-Rad: 37 Pockets in echter
    Wheel-Sequenz (0 + 1-36) mit korrekter Rot/Schwarz/Grün-Farbverteilung,
    Holz-Außenrand, polierter Stahlring, 37 Zahlen als 3D-Text-Ring (jede
    tangential zur Wheel-Achse rotiert), Center-Cone+Turret+Topper, Spielkugel
    in Pocket 17.
  - **Offen für nächste Session**: Wheel-Render ist erkennbar aber Sektor-Farben
    vermischen sich durch Anti-Aliasing (Sektoren nur ~9px breit) → höhere
    Auflösung oder dunklere Materials nötig. Chip-Set hat durch AgX-Tonemapping
    noch pastellige Farben — Material-Sättigung erhöhen oder Standard-Transform
    mit Belichtungs-Anpassung probieren. Roulette-Tisch selbst (Playfield,
    Bumper-Layout, Wheel-Integration) ist neues Backlog-Thema.
- **2026-05-27** — **Attack from Mars (Bally 1995, g5k 1.3.11) integriert + spielbar.**
  Tisch + ROM + Sample-Pack + factory-reset NVRAM installiert. Vier Sidecar-`.vbs`-Patches gegen
  Wine-VBScript-Inkompatibilitäten: (1) `Table1_KeyDown`/`KeyUp`-Aliase weil VPX-Standalone das
  Element „AFM" nicht zuverlässig an `AFM_KeyDown` bindet, (2) `LinearEnvelope`-Safety-Guards
  gegen Empty-xInput → negativer Array-Index → Type-Mismatch (`dictionary_Invoke dispId=7
  hres=-2146795477`), (3) `On Error Resume Next` Wraps um alle nFozzy-Dampener-Aufrufe
  (PolarityCorrect, RubbersD/SleevesD.dampen, FlippersD.Dampenf), (4) Pricing-Reset via
  `Settings.Value()` (1-Coin-1-Credit). TDD-Test `arcade/tests/test_afm.sh` schreibt
  Smoke-Test (xdotool Maus-Click + Tasten → 45s Run → Log-Pattern-Grep). Baseline 2-3
  Type-Mismatches → nach Patches **3× hintereinander 0 Errors**. Menü-Status auf OK.
  Patch-Backup in `arcade/table-patches/`. Memory um vier neue Refs (vpinball-programming,
  vpinball-standalone-linux, vpinball-debugging-playbook, vpinball-resources) und
  AFM-Status (afm-current-state) erweitert.
- **2026-05-22** — **Blender-Toolchain ins Studio aufgenommen.** Blender
  **4.5.10 LTS** als Tarball nach `blender/` installiert (kein Root, eigener
  Ordner wie `vpx/`), `bpy` headless verifiziert (gebündeltes Python 3.11.11).
  Neues Referenz-Dokument `team/blender-reference.md`: priorisierte Doku-Links
  (vpx_lightmapper, Blender-Python-API, Handbuch 4.5 LTS), Blender↔VPX-Workflow,
  Headless-`bpy`-Spickzettel. Agenten `pinball-artwork` + `vpx-developer` um
  Blender-Wissen erweitert und neu deployt; `CLAUDE.md` + `AGENTS.md` ergänzt.
- **2026-05-22** — **`vpx_lightmapper` headless getestet → Linux-inkompatibel.**
  Add-on v0.0.7 in Blender 4.5 geladen: registriert nur im Warn-Modus, harte
  Windows-Abhängigkeit `win32crypt`/`pywin32`. Import-Code portabel, aber der
  `.vpx`-Export nutzt Windows-CryptoAPI + OLE — auf Linux nicht lauffähig.
  Konsequenz im Backlog: Entscheidung OBJ-Weg vs. Export-Portierung.
- **2026-05-21** — **Menü-Musik standardmäßig aus + `M`-Toggle.** Die Theme-Musik
  spielt nicht mehr automatisch beim Blättern. Taste `M` schaltet sie an/aus
  (Toast `♪ MUSIK AN/AUS`), die Hinweiszeile zeigt jetzt `M  MUSIK`. Die Wahl
  wird in `~/.vpinball/arcade-menu.json` (`{"music": …}`) gemerkt. Der
  GStreamer-Code bleibt intakt — nur hinter den Toggle gehängt. Nach `vpx/`
  deployt.
- **2026-05-21** — **Theme-Musik im Menü.** GStreamer-Audio im Coverflow:
  markierst du einen Tisch, spielt sein Theme (Endlosschleife, entprellt,
  stoppt beim Spielstart). Quelle = `vpx/themes/<Tischname>.<ext>`; ohne eigene
  Datei läuft ein zufälliges Menü-Theme. 5 lizenzfreie Synthwave-Loops geladen
  (`themes/_menu-1..5.ogg`, "Retro Synthwave Loops", Tomasz Kucza, CC-BY 4.0 —
  siehe `themes/CREDITS.txt`). Playback per GStreamer-Test bestätigt.
- **2026-05-21** — **Yellow Submarine: Perspektivwahl Stehend/Sitzend.** Beim
  Start von YS zeigt das Menü eine Dot-Matrix-Abfrage (STEHEND/SITZEND, Wahl mit
  ◀/▶). Die Wahl schreibt den Desktop-POV (`ViewDTLookAt/FOV/Layback`) nach
  `[TableOverride]` der `VPinballX.ini`; alle anderen Tische setzen den Override
  zurück. Mechanik + Picker-UI fertig, POV-Werte noch grob (Feinjustage offen).
- **2026-05-21** — Hinweiszeile unten auf Dot-Matrix umgestellt (gemeinsamer
  Renderer `render_dots` für DMD + Hinweiszeile).
- **2026-05-21** — Konsolen-Menü auf **horizontalen Fisheye-Coverflow** umgebaut
  (`arcade/vpinball-menu.py`): App-Titel „Thomas Arcade" entfernt, linke Vorschau
  weg, Vollbild-Coverflow aus echten Tisch-Screenshots (zentral groß, zu den
  Seiten gewölbt klein), mit Spiegelungen, Orange-Glow auf der Auswahl und
  unscharfem Tisch-Hintergrund. Karten zeigen die Tische ungeschnitten (Karte
  folgt dem Bild-Format). Steuerung ◀/▶ bzw. Flipper. Nach `vpx/` deployt.
  `table-status.txt`-Datenfehler bei Alice Cooper bereinigt (Status war ein
  ganzer Satz statt `KAPUTT`).
- **2026-05-21** — Projekt-Kontext (`CLAUDE.md`, `STATUS.md`, `AGENTS.md`,
  `.claude/`, `team/`) auf die Wurzel `~/Applications/pinball/` gezogen — Claude
  Code läuft jetzt direkt im Studio-Ordner.
- **2026-05-21** — Alles in **einen** Ordner zusammengelegt: `~/Applications/pinball/`
  mit `arcade/`, `vpx/`, `backups/` und `runtime/`-Verknüpfung. Alle
  fest verdrahteten Pfade angepasst (Launcher, Menü, Agenten, Commands, Doku).
- **2026-05-21** — Agenten-Team aufgebaut: `pinball-artwork`, `vpx-developer`,
  `vpx-qa`. Quelle in `team/agents/`, deployt nach `~/.claude/agents/`, HQ-Doku in
  `AGENTS.md`. `pinball-artwork` um Physik-/Programmier-Kompetenz erweitert.
- **2026-05-21** — Projekt als Claude-Code-Projekt initialisiert: `CLAUDE.md`,
  `STATUS.md` und SessionStart-Hook angelegt.
- **2026-05-20** — Arcade-Setup als Git-Repo committet: GTK-Vollbild-Menü,
  Desktop-Launcher, `VPinballX.ini`, Table-Patches, Doku.
- alien13 und BTILC als spielbar bestätigt.

## 🐛 Bekannte Probleme

- VPinball-Standalone crasht beim Shutdown mancher Tische (`free(): invalid size`,
  Exit 134) — bekannter Engine-Bug, **nicht** der Tisch.
- Wayland: Menü braucht `GDK_BACKEND=x11`, VPX braucht `SDL_VIDEODRIVER=x11`.
- Alice Cooper Nightmare Castle: in `table-status.txt` als KAPUTT markiert.

---

## 🗒️ Session-Log

Neueste Einträge oben. Pro Session ein kurzer Block: Datum, was gemacht, was offen blieb.

### 2026-06-15 — Tisch-Start getestet: blankTable OK, AFM/YS schwarzer Bildschirm
- Thomas wollte AFM starten → schwarzer Vollbildschirm, obwohl VPX-Log fehlerfrei.
- `blankTable.vpx` (minimal) rendert korrekt — VPX-Engine und OpenGL funktionieren.
- AFM und Yellow Submarine laden vollständig (`Startup done`, `Static PreRender done`)
  aber zeigen nur Schwarz. Mögliche Ursache: Attract Mode rendert leer, oder
  PinMAME-Initialisierung hängt.
- `PlayfieldFullScreen` kurz auf 0 gesetzt und zurückgesetzt — liegt nicht daran.
- YS: fehlende Sound-Dateien (`YS1.mp3`, `Bell2`) spammen das Log.
- **Offen:** AFM-Schwarz-Bug eingenzen (Münze/Start simulieren? PinMAME-Log?
  Anderen PinMAME-Tisch testen?)

### 2026-05-27 — Erste Blender-Assets für eigenen Roulette-Tisch
- Thomas wollte Blender ausprobieren mit Blick auf einen eigenen
  Roulette-Themed-Pinball-Tisch. Headless-Workflow gewählt (per Python-Skript,
  keine GUI-Klickerei).
- Drei Assets aufgebaut in `blender-projects/roulette-bumper-cap/`:
  einzelner Casino-Chip-Bumper-Cap → Set von 6 Roulette-Chips → komplettes
  Roulette-Rad. Pipeline: bmesh-Geometrie + Principled-BSDF-Materials +
  Cycles/Eevee-Rendering + OBJ-Export.
- Lern-Erkenntnisse durch Bug-Hunt: Catmull-Clark-Subsurf verformt n-gon-Caps
  zu Kuppeln (Subsurf weglassen, mit höheren Segment-Zahlen kompensieren);
  `bm.faces.new()` setzt `.index` erst nach `bm.faces.index_update()` (sonst
  alle face.index = -1 → falsche Material-Slots); AgX-Tonemap entsättigt
  Casino-Farben (Standard zu aggressiv, AgX High-Contrast als Mittelweg);
  id-properties an Objekten brauchen String-Keys, keine ints.
- Offen: Sektor-Farbe im Wheel deutlicher machen (mehr Auflösung oder satter),
  Roulette-Tisch-Konzept (Playfield-Layout, Bumper-Platzierung) ist eigene
  Folge-Aufgabe.

### 2026-05-22 — Bello's Big Walk aus dem Projekt entfernt
- Auf Wunsch von Thomas den Eigenbau-Tisch „Bello's Big Walk" komplett aus dem
  Projekt genommen: Backlog-Sektion *Tisch-Entwicklung* + Erledigt-/Log-Einträge
  in `STATUS.md`, Menü- und Vorschau-Einträge (`vpinball-menu.py`,
  `generate-previews.py`), den Theme-Eintrag (`vpx/themes/README.txt`) und alle
  `tabledev/`-Verweise (`README.md`, `AGENTS.md`, Agenten-Doku).
- Agenten-Doku nach `~/.claude/agents/` neu deployt. `arcade/`-Repo committet
  (die übrigen Dateien liegen außerhalb von Git).
- Hinweis: Es gab keinen `tabledev/bellos-walk/`-Ordner mehr auf der Platte —
  nur noch Verweise. Damit ist `tabledev/` projektweit ungenutzt.

### 2026-05-22 — Blender-Toolchain + Referenz-Doku
- Recherche „beste Blender-Doku" → kuratiertes Nachschlagewerk
  `team/blender-reference.md` angelegt (Doku-Links, Blender↔VPX-Workflow,
  Headless-`bpy`-Spickzettel). Kern-Erkenntnis: Agenten steuern Blender
  headless via `bpy`, nicht über die GUI.
- **Blender 4.5.10 LTS installiert** als Tarball nach `blender/` (kein Root,
  1,2 GB; `bpy` headless verifiziert, Python 3.11.11).
- Agenten `pinball-artwork` (3D-Vorgabe) + `vpx-developer` (führt `bpy`-Skripte
  aus) um Blender-Abschnitte erweitert, neu nach `~/.claude/agents/` deployt.
- `CLAUDE.md` (Aufbau- + Datei-Tabelle) und `AGENTS.md` (neuer Abschnitt
  „Blender-Toolchain") ergänzt.
- **`vpx_lightmapper` headless getestet:** läuft auf Linux nicht — harte
  Windows-Dependency `win32crypt`. Import-Teil portabel, `.vpx`-Export
  Windows-gebunden. OS-Problem, kein Versions-Problem.
- **Offen:** Entscheidung OBJ-Weg vs. `vlm_export.py`-Portierung — siehe Backlog.

### 2026-05-21 — Menü-Musik-Toggle + Score-Feature geplant
- **Menü-Musik standardmäßig aus**: spielt nicht mehr automatisch beim Blättern.
  Neue Taste `M` schaltet an/aus, Wahl gemerkt in `~/.vpinball/arcade-menu.json`.
  Hinweiszeile um `M  MUSIK` ergänzt. GStreamer-Code bleibt, nur hinter Toggle
  gehängt. Nach `vpx/` deployt — Menü lief nicht, greift beim nächsten Start.
- **Score-/Statistik-Feature geplant**: Wunsch „Scores die persistieren +
  Statistiken im Menü + In-Game-Overlay oben rechts in Retro-Pixel-Optik".
  Design mit Thomas geklärt (Highscores + Play-Tracking kombiniert,
  Backbox-Score-Panels) — Details im Backlog-Eintrag oben. Umsetzung steht noch
  aus, nächste Session.
- **Offen:** Score-Feature umsetzen; pro-Tisch-Musik; YS-POV feinjustieren;
  Watchmen/Futurama-Screenshots.

### 2026-05-21 — Menü-Politur: Perspektive + Theme-Musik
- Hinweiszeile unten auf **Dot-Matrix** umgestellt (gemeinsamer Renderer
  `render_dots` für DMD + Hinweiszeile).
- **Yellow Submarine Stehend/Sitzend**: Dot-Matrix-Abfrage beim Start, schreibt
  Desktop-POV nach `[TableOverride]` der `VPinballX.ini`. Mechanik bestätigt;
  Winkel auf Wunsch entschärft (LookAt 53/38, Layback 4/20). Feinjustage offen.
- **Theme-Musik**: GStreamer-Player im Menü, spielt `themes/<Tisch>.<ext>` beim
  Markieren (Loop, entprellt, stoppt beim Start). 5 lizenzfreie Synthwave-Loops
  als Menü-Theme geladen (CC-BY, `themes/CREDITS.txt`).
- Stand auf Wunsch gesichert (STATUS.md + Commit) — Thomas wechselt das Thema.
- **Offen:** pro Tisch eigene Musik (13 Tracks); Spielstand-Persistenz-Konzept;
  YS-POV feinjustieren; Watchmen/Futurama-Screenshots.

### 2026-05-21 — Coverflow-Menü
- Menü-Rad von Text-Liste → vertikales Fisheye-Rad → schließlich **horizontaler
  Fisheye-Coverflow**: Karten auf horizontal gewölbter Linse (tanh-Stauchung,
  Größen-Glocke, sanfte vertikale Wölbung), Orange-Glow auf der Auswahl,
  abgedunkelte Nebenkarten, **Spiegelungen** unter den Karten.
- App-Titel „Thomas Arcade" entfernt (war kein DMD-Pixelstil); linke Vorschau
  ganz weg — Vollbild-Coverflow, dahinter unscharfer Tisch-Hintergrund.
- Karten zeigen den **echten Tisch ungeschnitten** (Seitenverhältnis folgt dem
  Bild, auf Grenzen geklemmt); früherer 16:9-Crop verworfen.
- Steuerung auf ◀/▶ umgestellt (plus Flipper-Tasten, Up/Down weiter gültig).
- `table-status.txt` repariert (Alice-Cooper-Status war fehlerhaft befüllt).
- Menü nach `vpx/` deployt und neu gestartet — läuft.
- Offen: Watchmen & Futurama haben noch keinen echten In-Game-Screenshot —
  Thomas nimmt sie selbst auf (`shoot-tables.py watchmen futurama`).

### 2026-05-21
- Projekt-Initialisierung: `CLAUDE.md` + `STATUS.md` + SessionStart-Hook.
- Agenten-Team aufgebaut (`pinball-artwork`, `vpx-developer`, `vpx-qa`) + `AGENTS.md`;
  `pinball-artwork` um Physik-/Programmier-Kompetenz erweitert.
- **Großer Umzug:** vier verstreute Ordner → ein `~/Applications/pinball/` mit
  Unterordnern; alle Pfade in Skripten, Configs und Doku angepasst.
- Projekt-Kontext auf die `pinball/`-Wurzel hochgezogen — `claude` läuft jetzt
  direkt im Studio-Ordner.
- Offen geblieben: alles unter "Offen / Backlog" oben.
- ⚠️ Claude Code in `~/Applications/pinball/` öffnen.
