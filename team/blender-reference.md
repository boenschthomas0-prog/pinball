# Blender-Referenz — VPX-Pinball-Studio

> **Zweck.** Kuratiertes Nachschlagewerk für die Agenten (`pinball-artwork`,
> `vpx-developer`), die 3D-Geometrie für Visual-Pinball-Tische bauen. Bei Bedarf
> lesen — nicht auswendig. Beantwortet: *Welche Doku ist maßgeblich?* und
> *Wie steuert ein Agent Blender überhaupt?*
>
> **Zuletzt aktualisiert:** 2026-05-22

---

## Status — WICHTIG zuerst lesen

- **Blender ist installiert** (2026-05-22): `blender/blender` im Projekt-Ordner
  — **4.5.10 LTS**, gebündeltes Python **3.11.11**, `bpy` headless verifiziert.
  Voller Pfad: `/home/thomas/Applications/pinball/blender/blender`.
- **Nicht im `PATH`** — wie `vpxtool` immer mit vollem Pfad aufrufen.
- **Version 4.5 LTS** ist bewusst gewählt: stabil, langlebig, von Add-ons
  unterstützt. `latest` (5.x) ist Bleeding-Edge — nicht dafür bauen.
- Gebündeltes Python für `pip`: `blender/4.5/python/bin/python3.11`.

## Das Kern-Prinzip für Agenten

Agenten klicken **nicht** in Blenders GUI. Sie steuern Blender **headless** über
die Python-API `bpy`:

```bash
BLENDER=/home/thomas/Applications/pinball/blender/blender
$BLENDER --background --python skript.py        # Skript ausführen, ohne Fenster
$BLENDER --background datei.blend --python s.py # auf bestehender Datei arbeiten
$BLENDER --background --python-expr "import bpy; print(bpy.app.version_string)"
```

Daraus folgt die Prioritäten-Reihenfolge der Doku unten:
**Python-API vor GUI-Handbuch.** Das Handbuch erklärt *Konzepte* (Was ist eine
UV-Map? Was macht Baking?), die Python-API erklärt das *Tun*.

---

## 1. VPX-spezifisch — hier anfangen

Das ist der De-facto-Standard für Blender↔VPX. Wer Tisch-Geometrie baut, liest
das zuerst.

| Resource | Was | Link |
|---|---|---|
| **vpx_lightmapper** | Blender-Add-on: importiert `.vpx` direkt, bäckt Lightmaps/Bakemaps automatisch, exportiert spielbare `.vpx` mit neuer Geometrie + Textur + Script-Helfern. Die README dokumentiert den **gesamten** Bake-Workflow. | <https://github.com/vbousquet/vpx_lightmapper> |
| **pinball-parts** | Blender-Bibliothek fertiger Pinball-Teile (Posts, Schrauben, Bats…) — als Assets nutzbar UND als Beispiel für korrekt skalierte VPX-Geometrie. | <https://github.com/vbousquet/pinball-parts> |
| **VPForums-Guide #166** | Praktiker-Workflow „3d animations VPX/Blender". | <https://www.vpforums.org/index.php?app=tutorials&article=166> |
| **VPE „Realistic Playfield"** | Saubere Schritt-für-Schritt-Blender-Anleitung fürs Playfield-Modeling. Zielt auf das Unity-basierte VPE, aber Modeling/UV/Bake übertragen sich 1:1 auf VPX. | <https://docs.visualpinball.org/creators-guide/tutorials/realistic-playfield/index.html> |

> **`vpx_lightmapper` — getestet 2026-05-22 (Blender 4.5, headless): läuft auf
> Linux NICHT.** Das Add-on aktiviert sich nur im Warn-Modus, weil die
> Abhängigkeit **`win32crypt`** (Teil von `pywin32`) fehlt — ein
> **Windows-only**-Paket, auf Linux gar nicht installierbar.
> - **Import** (`vlm_import.py`) ist portabel: nur `olefile` + `Pillow` —
>   beide wurden in Blenders Python installiert (`olefile 0.47`, `Pillow 12.2`).
> - **Export** (`vlm_export.py`) ist hart Windows-gebunden: nutzt die Windows-
>   CryptoAPI (`win32crypt`/`win32cryptcon`, MD2-Hash der `.vpx`) und Windows-
>   OLE-Storage (`win32com.storagecon`), um die `.vpx` zu schreiben.
> - Das ist ein **OS-Problem, kein Blender-Versions-Problem.** Blender 3.6 LTS
>   würde auf Linux genauso scheitern — der „Fallback 3.6" entfällt.
>
> **Fazit:** Die fertige Lightmapper-Pipeline ist auf diesem Linux-Setup nicht
> einsetzbar. Zwei Wege bleiben:
> 1. **OBJ-Weg** (unten) — Modeling + Baking mit Blender 4.5 funktionieren
>    sofort und vollständig. Empfohlener Standard.
> 2. **`vlm_export.py` portieren** — den `.vpx`-Export auf Linux umbauen
>    (z.B. Geometrie/Texturen exportieren und mit dem vorhandenen
>    `vpxtool assemble` zusammenbauen statt Windows-OLE). Echtes Projekt;
>    Entscheidung offen, siehe `STATUS.md`.

## 2. Blender-Python-API — das echte Agenten-Interface

| Seite | Wofür | Link |
|---|---|---|
| API-Referenz | Einstiegsportal (`current` = neueste Version) | <https://docs.blender.org/api/current/index.html> |
| Quickstart | **Zuerst lesen** | <https://docs.blender.org/api/current/info_quickstart.html> |
| API Overview | `bpy.data`, `bpy.context`, `bpy.ops` erklärt — **zuerst lesen** | <https://docs.blender.org/api/current/info_overview.html> |
| `bpy.types` | Typ-Referenz (Objekte, Meshes, Materialien) | <https://docs.blender.org/api/current/bpy.types.html> |
| `bpy.ops` | Operatoren (Aktionen) | <https://docs.blender.org/api/current/bpy.ops.html> |
| Best Practice | Konventionen für saubere Skripte | <https://docs.blender.org/api/current/info_best_practice.html> |

## 3. Blender-Konzepte — offizielles Handbuch

Agenten an die **4.5-LTS**-Version pinnen, nicht an `latest`.

| Thema | Link |
|---|---|
| Handbuch 4.5 LTS (Startseite) | <https://docs.blender.org/manual/en/4.5/> |
| Render-Baking (Cycles) | <https://docs.blender.org/manual/en/4.5/render/cycles/baking.html> |
| UV-Mapping / Editing | <https://docs.blender.org/manual/en/4.5/modeling/meshes/uv/editing.html> |
| Modeling | <https://docs.blender.org/manual/en/4.5/modeling/index.html> |

---

## Blender↔VPX-Workflow (laut vpx_lightmapper)

1. Tisch in VPX erstellen & speichern.
2. Tisch in Blender importieren (oder bestehende Szene aktualisieren).
3. Bake-Einstellungen konfigurieren (Licht-Gruppen, Objekt-Gruppen, Bake-Modi).
4. Materialien & Licht in Blender verfeinern.
5. Texturen baken (automatisierter Batch-Prozess).
6. Ergebnis im Rendered-Viewport prüfen.
7. Aktualisierte `.vpx` exportieren (neue Geometrie + Texturen).
8. Tisch-Script mit den generierten Helfern anpassen.
9. In VPX testen, iterieren.

**Alternativer, leichtgewichtiger Weg ohne das Add-on:** VPX kann Geometrie als
`.obj` exportieren → in Blender importieren, bearbeiten → zurück. Kein Alpha-VPX
nötig, aber kein automatisches Lightmap-Baking.

## Headless-`bpy`-Spickzettel

```python
import bpy

# Szene leeren
bpy.ops.wm.read_factory_settings(use_empty=True)

# OBJ importieren / exportieren (Blender 4.x: neue Operator-Namen)
bpy.ops.wm.obj_import(filepath="tisch.obj")
bpy.ops.wm.obj_export(filepath="out.obj")

# Über Daten iterieren statt über die GUI
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        ...

# Baken braucht: Mesh mit UV-Map + aktiver Image-Texture-Node als Bake-Ziel
bpy.context.scene.render.engine = 'CYCLES'
bpy.ops.object.bake(type='DIFFUSE')
```

Regeln: **Daten-API (`bpy.data`) vor Operatoren (`bpy.ops`)** bevorzugen —
Operatoren hängen am GUI-Kontext und brechen headless leicht. Baking verlangt
immer eine UV-Map und ein explizites Bake-Ziel (Image-Texture-Node).

## Bezug zum Team

- **`pinball-artwork`** entwirft, was baubar ist — kennt jetzt zusätzlich die
  Blender-Geometrie-Pipeline.
- **`vpx-developer`** führt die Headless-Skripte aus und integriert die
  exportierte `.vpx`.
- Größere Architektur-Entscheidungen (Lightmapper-Pipeline ja/nein) trifft der
  **Producer** mit Thomas — siehe `STATUS.md`.
