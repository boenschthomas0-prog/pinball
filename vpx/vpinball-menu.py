#!/usr/bin/env python3
"""
VPinball Vollbild-Menü — horizontaler Fisheye-Coverflow mit DMD-Infozeile.

Vollbild-Coverflow aus echten Tisch-Screenshots (zentral groß, zu den Seiten
gewölbt klein) auf unscharfem Tisch-Hintergrund, unten eine DMD-Style
Dot-Matrix-Zeile mit Name, Status und Genre. Kein App-Titel.
Wayland-tauglich (zwingt sich auf X11).

Screenshots/Vorschaubilder erzeugen:  python3 generate-previews.py
"""
import fcntl
import json
import math
import os
import random
import subprocess
import threading
import time
from pathlib import Path

# Menü zwingt sich auf X11 (auch unter Wayland) - sonst Fullscreen-Probleme
os.environ['GDK_BACKEND'] = 'x11'

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf, Pango, PangoCairo, Gst
import cairo

Gst.init(None)

VPX_DIR     = Path('/home/thomas/Applications/pinball/vpx')
TABLES_DIR  = VPX_DIR / 'tables'
MEDIA_DIR   = VPX_DIR / 'media'
LOG_FILE    = VPX_DIR / 'last-run.log'
STATUS_FILE = VPX_DIR / 'table-status.txt'
THEMES_DIR  = VPX_DIR / 'themes'        # Theme-Audio je Tisch (<tisch>.mp3/ogg/…)
CACHE_DIR   = Path.home() / '.vpinball' / 'Cache'
VPINBALL_INI = Path.home() / '.vpinball' / 'VPinballX.ini'
MENU_PREFS  = Path.home() / '.vpinball' / 'arcade-menu.json'   # Menü-Einstellungen

THEME_EXTS  = ('.mp3', '.ogg', '.opus', '.m4a', '.flac', '.wav')
THEME_VOLUME = 0.55                     # 0.0 – 1.0
THEME_DELAY  = 550                      # ms Wartezeit, bis das Theme startet

SCREEN_W, SCREEN_H = 1920, 1080

# ---- Layout-Regionen (px) -------------------------------------------------
# Vollbild-Coverflow + DMD ("Backbox"). Kein App-Titel mehr — das Rad zeigt
# die echten Tische selbst.
WHEEL  = (0, 34, 1920, 798)             # x, y, w, h  – horizontales Rad
DMD    = (260, 858, 1400, 150)
HINT       = (60, 1014, 1800, 56)       # x, y, w, h  – Dot-Matrix-Hinweiszeile
HINT_PITCH = 4                          # Punktabstand der Hinweiszeile, px
HINT_TEXT  = '◀ ▶  WÄHLEN      ENTER  STARTEN      M  MUSIK      9  ENDE'

# ---- Fisheye-Coverflow ----------------------------------------------------
# Screenshot-Karten auf einer horizontal gewölbten Linse: zentral groß &
# scharf, zu den Seiten gestaucht, verkleinert, abgedunkelt, sanft abgesenkt.
# Jede Karte zeigt den ECHTEN Tisch-Screenshot ungeschnitten — die Karte
# übernimmt das Seitenverhältnis des Bildes (auf sinnvolle Grenzen geklemmt).
WHEEL_SLOTS  = 7           # sichtbare Karten je Richtung (Rest wird geculled)
CARD_H       = 624         # Höhe der zentralen (größten) Karte, px
CARD_AR_MIN  = 0.72        # erlaubtes Seitenverhältnis (Breite/Höhe), min
CARD_AR_MAX  = 1.55        # ... max — Ausreißer werden cover-gecroppt
CARD_CACHE_H = 720         # Auflösungs-Cap der gecachten Karten-Bitmaps, px
CARD_S_EDGE  = 0.14        # minimaler Skalierungsfaktor ganz außen
FE_SPAN      = 820.0       # max. horizontale Auslenkung vom Rad-Zentrum, px
FE_TANH_K    = 0.62        # Stärke der Fisheye-Stauchung (höher = enger)
FE_SCALE_Q   = 0.74        # Breite der Größen-Glocke (höher = schneller klein)
FE_BOW       = 78.0        # vertikale Wölbung — Seitenkarten sinken ab, px
FE_ALPHA_P   = 0.46        # Transparenz-Abfall zum Rand
FE_ALPHA_MIN = 0.14        # minimale Deckkraft ganz außen

# ---- Anzeigenamen (mit Emoji) --------------------------------------------
DISPLAY_NAME = {
    'alien13.vpx':                                   '👽  Alien',
    'Alice Cooper Nightmare Castle (Ling Woo).vpx':  '🎸  Alice Cooper',
    'Attack from Mars (Bally 1995) g5k 1.3.11.vpx':  '👾  Attack from Mars',
    'Bart vs The Space Mutants.vpx':                 '🛸  Bart Simpson',
    'Fish Tales (Williams 1992).vpx':                '🎣  Fish Tales',
    'Futurama (Original 2024) v1.2.2.vpx':           '🤖  Futurama',
    'GOTG_2.1.0.vpx':                                '🚀  Guardians of the Galaxy',
    'Halloween (Granit 2020).vpx':                   '🎃  Halloween',
    'Houdini (Granit 2020).vpx':                     '🎩  Houdini',
    'Ramones (HauntFreaks 2021) v2.0.vpx':           '🎤  Ramones',
    'Stranger Things (Granit 2020).vpx':             '🔦  Stranger Things',
    'Watchmen (Wizball 2020).vpx':                   '🦸  Watchmen',
    'Yellow Submarine (Giantomasi 2020).vpx':        '🟡  Yellow Submarine',
}

# ---- Genre / Feature-Zeile für die DMD -----------------------------------
TABLE_INFO = {
    'alien13.vpx':                                   'SCI-FI HORROR',
    'Alice Cooper Nightmare Castle (Ling Woo).vpx':  'SHOCK-ROCK HORROR',
    'Attack from Mars (Bally 1995) g5k 1.3.11.vpx':  'BALLY 1995 - SCI-FI KLASSIKER',
    'Bart vs The Space Mutants.vpx':                 'THE SIMPSONS - RETRO',
    'Fish Tales (Williams 1992).vpx':                'WILLIAMS 1992 - ANGEL-KLASSIKER',
    'Futurama (Original 2024) v1.2.2.vpx':           'SCI-FI COMEDY',
    'GOTG_2.1.0.vpx':                                'MARVEL - ACTION',
    'Halloween (Granit 2020).vpx':                   'SLASHER-HORROR',
    'Houdini (Granit 2020).vpx':                     'MAGIE & ENTFESSELUNG',
    'Ramones (HauntFreaks 2021) v2.0.vpx':           'PUNK ROCK',
    'Stranger Things (Granit 2020).vpx':             '80ER MYSTERY-HORROR',
    'Watchmen (Wizball 2020).vpx':                   'SUPERHELDEN-NOIR',
    'Yellow Submarine (Giantomasi 2020).vpx':        'BEATLES - PSYCHEDELIC',
}

DEFAULT_STATUS = {
    'alien13.vpx':                                   'OK',
    'Futurama (Original 2024) v1.2.2.vpx':           '?',
    'GOTG_2.1.0.vpx':                                '?',
    'Ramones (HauntFreaks 2021) v2.0.vpx':           '?',
    'Fish Tales (Williams 1992).vpx':                'NEU',
    'Halloween (Granit 2020).vpx':                   'NEU',
    'Stranger Things (Granit 2020).vpx':             'NEU',
    'Houdini (Granit 2020).vpx':                     'NEU',
    'Alice Cooper Nightmare Castle (Ling Woo).vpx':  'KAPUTT',
    'Attack from Mars (Bally 1995) g5k 1.3.11.vpx':  'OK',
    'Yellow Submarine (Giantomasi 2020).vpx':        'NEU',
    'Watchmen (Wizball 2020).vpx':                   'NEU',
    'Bart vs The Space Mutants.vpx':                 'NEU',
}

STATUS_COLOR = {
    'OK':     (0.37, 1.00, 0.63),
    '?':      (1.00, 0.80, 0.40),
    'NEU':    (0.53, 0.80, 1.00),
    'TEST':   (0.73, 0.73, 0.73),
    'KAPUTT': (1.00, 0.33, 0.40),
}
STATUS_WORD = {
    'OK': 'LAEUFT', '?': 'UNGETESTET', 'NEU': 'NEU',
    'TEST': 'IM TEST', 'KAPUTT': 'DEFEKT',
}

ORANGE = (1.00, 0.42, 0.07)

# Tische mit Stehend/Sitzend-Perspektivwahl. Pro Modus die Desktop-POV-Werte,
# die das Menü vor dem Start nach [TableOverride] der VPinballX.ini schreibt.
# Mögliche Keys: LookAt (Neigung), FOV, Layback, PlayerX/Y/Z (Versatz/Zoom),
# ScaleX/Y/Z, Rotation — nicht gesetzte bleiben auf Tisch-Default.
# VPX rendert den ganzen Tisch mit EINER Kamera: Backbox/Hintergrund kippen
# zwangsläufig mit, daher die Winkel bewusst dezent halten.
# Startwerte zum gemeinsamen Feinjustieren (Tisch-Default: LookAt 45, Layback 0).
VIEW_MODES = {
    'Yellow Submarine (Giantomasi 2020).vpx': [
        ('STEHEND', {'LookAt': 53, 'Layback': 4}),
        ('SITZEND', {'LookAt': 38, 'Layback': 20}),
    ],
}


def load_status_overrides():
    s = {}
    if STATUS_FILE.exists():
        for line in STATUS_FILE.read_text().splitlines():
            if '|' in line:
                fn, st = line.split('|', 1)
                s[fn.strip()] = st.strip()
    return s


def save_status_override(fname, new_status):
    s = load_status_overrides()
    s[fname] = new_status
    STATUS_FILE.write_text('\n'.join(f'{k}|{v}' for k, v in s.items()) + '\n')


def load_prefs():
    """Menü-Einstellungen (z.B. Musik an/aus) aus arcade-menu.json lesen."""
    try:
        return json.loads(MENU_PREFS.read_text())
    except Exception:
        return {}


def save_prefs(prefs):
    """Menü-Einstellungen nach arcade-menu.json schreiben."""
    try:
        MENU_PREFS.write_text(json.dumps(prefs, indent=2) + '\n')
    except Exception:
        pass


# Desktop-POV-Keys, die das Menü in [TableOverride] verwalten kann.
VIEW_KEYS = ('LookAt', 'FOV', 'Layback', 'PlayerX', 'PlayerY', 'PlayerZ',
             'ScaleX', 'ScaleY', 'ScaleZ', 'Rotation')


def write_view_override(view):
    """Schreibt die Desktop-POV-Keys (ViewDT*) in [TableOverride] der VPX-INI.
    view = dict mit beliebigen VIEW_KEYS  ·  None/leer setzt ALLE zurück, damit
    der Tisch wieder seine eingebaute Perspektive (inkl. Hintergrund) nutzt.
    Nicht angegebene Keys werden geleert = Tisch-Default."""
    if not VPINBALL_INI.exists():
        return
    view = view or {}
    vals = {f'ViewDT{k}': view.get(k, '') for k in VIEW_KEYS}
    out, section = [], ''
    for line in VPINBALL_INI.read_text().splitlines():
        st = line.strip()
        if st.startswith('[') and st.endswith(']'):
            section = st
        if section == '[TableOverride]' and '=' in line:
            key = line.split('=', 1)[0].strip()
            if key in vals:
                out.append(f'{key} = {vals[key]}')
                continue
        out.append(line)
    VPINBALL_INI.write_text('\n'.join(out) + '\n')


def list_tables():
    overrides = load_status_overrides()
    items = [(p.name, overrides.get(p.name, DEFAULT_STATUS.get(p.name, '?')))
             for p in TABLES_DIR.glob('*.vpx')]
    items.sort(key=lambda t: DISPLAY_NAME.get(t[0], t[0])
               .split(maxsplit=1)[-1].lower())
    return items


def clean_name(fname):
    """Anzeigename ohne Emoji, in Großbuchstaben (für die DMD)."""
    disp = DISPLAY_NAME.get(fname, fname.replace('.vpx', ''))
    parts = disp.split(maxsplit=1)
    return (parts[-1] if len(parts) > 1 else disp).upper()


def make_layout(cr, text, size, bold=True, width=None,
                align=Pango.Alignment.LEFT, ellipsize=False):
    layout = PangoCairo.create_layout(cr)
    desc = Pango.FontDescription()
    desc.set_family('Sans')
    desc.set_weight(Pango.Weight.BOLD if bold else Pango.Weight.NORMAL)
    desc.set_absolute_size(size * Pango.SCALE)
    layout.set_font_description(desc)
    if width is not None:
        layout.set_width(int(width * Pango.SCALE))
        layout.set_alignment(align)
    if ellipsize:
        layout.set_ellipsize(Pango.EllipsizeMode.END)
    layout.set_text(text, -1)
    return layout


def render_dots(specs, region_w, region_h, pitch, lit_rgb, unlit_rgb):
    """Rendert Textzeilen als Dot-Matrix-Display -> cairo.ImageSurface.
    specs: Liste von (text, fontsize_px, ypos_px) auf der Hi-Res-Fläche.
    unlit_rgb=None  ->  nur Leuchtpunkte, kein dunkles Raster dahinter."""
    cols, rows = region_w // pitch, region_h // pitch
    scale = 2

    # 1) Text scharf auf eine Hi-Res-Fläche rendern
    tw, th = cols * scale, rows * scale
    txt = cairo.ImageSurface(cairo.FORMAT_ARGB32, tw, th)
    tcr = cairo.Context(txt)
    tcr.set_source_rgba(1, 1, 1, 1)
    for text, fsize, ypos in specs:
        lay = make_layout(tcr, text, fsize, bold=True,
                          width=tw, align=Pango.Alignment.CENTER,
                          ellipsize=True)
        tcr.move_to(0, ypos)
        PangoCairo.show_layout(tcr, lay)
    txt.flush()
    buf = txt.get_data()
    stride = txt.get_stride()

    # 2) auf das Dot-Raster heruntersampeln
    out = cairo.ImageSurface(cairo.FORMAT_ARGB32, cols * pitch, rows * pitch)
    ocr = cairo.Context(out)
    for ry in range(rows):
        for rx in range(cols):
            acc = 0
            for dy in range(scale):
                row = (ry * scale + dy) * stride
                for dx in range(scale):
                    acc += buf[row + (rx * scale + dx) * 4 + 3]
            lit = acc / (scale * scale)
            cx = rx * pitch + pitch / 2
            cy = ry * pitch + pitch / 2
            if lit > 64:
                ocr.set_source_rgb(*lit_rgb)
                r = pitch * 0.44
            elif unlit_rgb is not None:
                ocr.set_source_rgb(*unlit_rgb)
                r = pitch * 0.30
            else:
                continue
            ocr.arc(cx, cy, r, 0, 6.2832)
            ocr.fill()
    out.flush()
    return out


def render_dmd(lines):
    """Tisch-Name (Zeile 1) + Status/Genre (Zeile 2) als orange Dot-Matrix."""
    th = (DMD[3] // 5) * 2
    specs = [(lines[0], th * 0.34, th * 0.06),
             (lines[1], th * 0.22, th * 0.56)]
    return render_dots(specs, DMD[2], DMD[3], 5, ORANGE, (0.16, 0.07, 0.01))


def render_hint(text):
    """Steuer-Hinweis als schmale, dezente Dot-Matrix-Zeile (nur Leuchtpunkte)."""
    th = (HINT[3] // HINT_PITCH) * 2
    specs = [(text, th * 0.62, th * 0.17)]
    return render_dots(specs, HINT[2], HINT[3], HINT_PITCH,
                       (0.62, 0.37, 0.12), None)


class ArcadeMenu(Gtk.Window):
    def __init__(self):
        super().__init__(title='Thomas Arcade')
        self.set_decorated(False)
        self.set_app_paintable(True)
        self.set_resizable(False)
        self.set_default_size(SCREEN_W, SCREEN_H)
        geo = Gdk.Geometry()
        geo.min_width = geo.max_width = SCREEN_W
        geo.min_height = geo.max_height = SCREEN_H
        self.set_geometry_hints(None, geo,
            Gdk.WindowHints.MIN_SIZE | Gdk.WindowHints.MAX_SIZE)

        self.tables = list_tables()
        self.index = 0
        self.anim = 0.0                 # animierter Rad-Offset
        self.anim_id = None
        self.toast_text = ''
        self.toast_id = None
        self.pixbuf_cache = {}
        self.thumb_cache = {}           # tisch -> Karten-Bitmap (voller Screenshot)
        self.bg_cache = {}              # tisch -> Mini-Bitmap für unscharfen BG
        self.dmd_cache = {}             # (tisch, status) -> Dot-Matrix-Surface
        self.dmd_surface = None
        self.hint_surface = render_hint(HINT_TEXT)   # statische Dot-Matrix-Zeile
        self.picker = None              # None = aus; sonst Index des Modus
        self.view_choice = {}           # tisch -> zuletzt gewählter Modus-Index
        self.picker_cache = {}          # text -> Dot-Matrix-Surface (Picker)

        # Theme-Audio: spielt das Spiel-Theme des markierten Tisches.
        # Standardmäßig AUS — per 'M' umschaltbar, die Wahl wird gemerkt.
        self.music_on = bool(load_prefs().get('music', False))
        self.theme_player = Gst.ElementFactory.make('playbin', None)
        self.theme_timer = None         # ausstehender (entprellter) Theme-Start
        self.theme_cur = None           # gerade laufende Theme-Datei (str)
        self.menu_theme = self._pick_menu_theme()   # Standard-Attract-Theme
        if self.theme_player:
            self.theme_player.set_property('volume', THEME_VOLUME)
            bus = self.theme_player.get_bus()
            bus.add_signal_watch()
            bus.connect('message', self._on_theme_message)

        self.da = Gtk.DrawingArea()
        self.add(self.da)
        self.da.connect('draw', self.on_draw)
        self.connect('key-press-event', self.on_key)
        self.connect('destroy', Gtk.main_quit)
        self.connect('realize', lambda *_: (self.fullscreen(), self.present()))

        self._update_selection()

    # ---- Daten / Auswahl --------------------------------------------------
    def _current(self):
        return self.tables[self.index] if self.tables else (None, None)

    def _load_pixbuf(self, fname):
        stem = fname[:-4] if fname.endswith('.vpx') else fname
        if stem in self.pixbuf_cache:
            return self.pixbuf_cache[stem]
        path = MEDIA_DIR / f'{stem}.png'
        pb = None
        if path.exists():
            try:
                pb = GdkPixbuf.Pixbuf.new_from_file(str(path))
            except Exception:
                pb = None
        self.pixbuf_cache[stem] = pb
        return pb

    def _thumb(self, fname):
        """Karten-Bitmap — voller Screenshot, Seitenverhältnis auf Grenzen
        geklemmt. Echte Tisch-Shots (~quadratisch) bleiben ungeschnitten;
        nur Ausreißer (hochkant-Texturen) werden cover-gecroppt."""
        stem = fname[:-4] if fname.endswith('.vpx') else fname
        if stem in self.thumb_cache:
            return self.thumb_cache[stem]
        pb = self._load_pixbuf(fname)
        thumb = None
        if pb:
            sw, sh = pb.get_width(), pb.get_height()
            ar = min(CARD_AR_MAX, max(CARD_AR_MIN, sw / sh))
            if sw / sh > ar:                       # zu breit -> Breite croppen
                cw, ch = int(round(sh * ar)), sh
            else:                                  # zu hoch  -> Höhe croppen
                cw, ch = sw, int(round(sw / ar))
            if (cw, ch) != (sw, sh):
                pb = pb.new_subpixbuf((sw - cw) // 2, (sh - ch) // 2, cw, ch)
            if ch > CARD_CACHE_H:
                sc = CARD_CACHE_H / ch
                pb = pb.scale_simple(max(1, round(cw * sc)), CARD_CACHE_H,
                                     GdkPixbuf.InterpType.BILINEAR)
            thumb = pb
        self.thumb_cache[stem] = thumb
        return thumb

    def _bg_pixbuf(self, fname):
        """Stark verkleinertes Bild für den unscharfen Rad-Hintergrund."""
        stem = fname[:-4] if fname.endswith('.vpx') else fname
        if stem in self.bg_cache:
            return self.bg_cache[stem]
        pb = self._load_pixbuf(fname)
        small = None
        if pb and pb.get_width() > 0:
            bw = 64
            bh = max(1, round(bw * pb.get_height() / pb.get_width()))
            small = pb.scale_simple(bw, bh, GdkPixbuf.InterpType.BILINEAR)
        self.bg_cache[stem] = small
        return small

    def _update_selection(self):
        """DMD-Infozeile neu bauen + Spiel-Theme nachziehen (bei Auswahlwechsel)."""
        fn, status = self._current()
        if fn is None:
            self.dmd_surface = None
            return
        # DMD: Zeile 1 = Name, Zeile 2 = Status + Genre (gecacht je Tisch+Status)
        key = (fn, status)
        if key not in self.dmd_cache:
            info = TABLE_INFO.get(fn, 'PINBALL')
            word = STATUS_WORD.get(status, status)
            self.dmd_cache[key] = render_dmd(
                [clean_name(fn), f'{word}  -  {info}'])
        self.dmd_surface = self.dmd_cache[key]
        self._schedule_theme()

    # ---- Spiel-Theme (Audio) ---------------------------------------------
    def _pick_menu_theme(self):
        """Wählt zufällig eines der _menu-*-Stücke als Standard-Attract-Theme."""
        if not THEMES_DIR.is_dir():
            return None
        cands = sorted(p for p in THEMES_DIR.iterdir()
                       if p.stem.startswith('_menu')
                       and p.suffix.lower() in THEME_EXTS)
        return random.choice(cands) if cands else None

    def _theme_path(self, fn):
        """Theme-Audiodatei eines Tisches; sonst das Standard-Menü-Theme."""
        stem = fn[:-4] if fn.endswith('.vpx') else fn
        for ext in THEME_EXTS:
            p = THEMES_DIR / f'{stem}{ext}'
            if p.exists():
                return p
        return self.menu_theme

    def _schedule_theme(self):
        """Theme-Start entprellt anstoßen — beim schnellen Blättern nicht spammen.
        Bei ausgeschalteter Musik (Standard) passiert nichts."""
        if not self.music_on:
            return
        if self.theme_timer:
            GLib.source_remove(self.theme_timer)
        self.theme_timer = GLib.timeout_add(THEME_DELAY, self._fire_theme)

    def _fire_theme(self):
        self.theme_timer = None
        fn = self._current()[0]
        self._play_theme(self._theme_path(fn) if fn else None)
        return False

    def _play_theme(self, path):
        """Theme wechseln/stoppen. path=None stoppt die Wiedergabe."""
        if not self.theme_player:
            return
        target = str(path) if path else None
        if target == self.theme_cur:
            return
        self.theme_player.set_state(Gst.State.NULL)
        self.theme_cur = None
        if target:
            self.theme_player.set_property('uri', Gst.filename_to_uri(target))
            self.theme_player.set_state(Gst.State.PLAYING)
            self.theme_cur = target

    def _on_theme_message(self, _bus, msg):
        # Theme in Endlosschleife — bei Dateiende zurück an den Anfang
        if msg.type == Gst.MessageType.EOS and self.theme_cur:
            self.theme_player.seek_simple(
                Gst.Format.TIME, Gst.SeekFlags.FLUSH, 0)
        elif msg.type == Gst.MessageType.ERROR:
            self.theme_player.set_state(Gst.State.NULL)
            self.theme_cur = None

    def _toggle_music(self):
        """Menü-Musik an/aus schalten — die Wahl wird in arcade-menu.json gemerkt."""
        self.music_on = not self.music_on
        prefs = load_prefs()
        prefs['music'] = self.music_on
        save_prefs(prefs)
        if self.music_on:
            self._schedule_theme()              # Theme des aktuellen Tisches starten
            self._toast('♪  MUSIK  AN')
        else:
            if self.theme_timer:
                GLib.source_remove(self.theme_timer)
                self.theme_timer = None
            self._play_theme(None)              # laufendes Theme stoppen
            self._toast('♪  MUSIK  AUS')

    # ---- Navigation -------------------------------------------------------
    def _move(self, direction):
        if not self.tables:
            return
        self.index = (self.index + direction) % len(self.tables)
        self.anim += direction
        self._update_selection()
        if self.anim_id is None:
            self.anim_id = GLib.timeout_add(16, self._anim_tick)

    def _jump(self, new_index):
        if not self.tables:
            return
        self.index = new_index % len(self.tables)
        self.anim = 0.0
        self._update_selection()
        self.da.queue_draw()

    def _anim_tick(self):
        self.anim *= 0.60
        if abs(self.anim) < 0.03:
            self.anim = 0.0
            self.anim_id = None
            self.da.queue_draw()
            return False
        self.da.queue_draw()
        return True

    # ---- Zeichnen ---------------------------------------------------------
    def on_draw(self, _w, cr):
        # Hintergrund
        bg = cairo.LinearGradient(0, 0, 0, SCREEN_H)
        bg.add_color_stop_rgb(0.0, 0.05, 0.05, 0.07)
        bg.add_color_stop_rgb(0.5, 0.02, 0.02, 0.03)
        bg.add_color_stop_rgb(1.0, 0.06, 0.04, 0.02)
        cr.set_source(bg)
        cr.paint()

        self._draw_wheel(cr)
        self._draw_dmd(cr)
        self._draw_hint(cr)
        self._draw_toast(cr)
        self._draw_picker(cr)

    def _draw_hint(self, cr):
        s = self.hint_surface
        if s:
            cr.set_source_surface(
                s, round((SCREEN_W - s.get_width()) / 2), HINT[1])
            cr.paint()

    def _rounded(self, cr, x, y, w, h, r):
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -1.5708, 0)
        cr.arc(x + w - r, y + h - r, r, 0, 1.5708)
        cr.arc(x + r, y + h - r, r, 1.5708, 3.1416)
        cr.arc(x + r, y + r, r, 3.1416, 4.7124)
        cr.close_path()

    def _fisheye(self, t):
        """Slot-Offset t -> (x-Versatz, y-Versatz, Skala, Alpha) auf der Linse.
        Horizontaler Coverflow: x staucht per tanh, y ist die sanfte Wölbung."""
        bell = 1.0 / (1.0 + (t * FE_SCALE_Q) ** 2)
        dx = FE_SPAN * math.tanh(t * FE_TANH_K)
        dy = FE_BOW * (1.0 - bell)              # Seitenkarten sinken leicht ab
        scale = CARD_S_EDGE + (1.0 - CARD_S_EDGE) * bell
        alpha = max(FE_ALPHA_MIN, 1.0 / (1.0 + (t * FE_ALPHA_P) ** 2))
        return dx, dy, scale, alpha

    def _draw_wheel_bg(self, cr, x, y, w, h):
        """Unscharfer Hintergrund aus dem aktuell gewählten Tisch-Screenshot."""
        fn = self.tables[self.index][0] if self.tables else None
        bg = self._bg_pixbuf(fn) if fn else None
        if bg:
            bw, bh = bg.get_width(), bg.get_height()
            sc = max(w / bw, h / bh)            # cover-fit, hochskaliert = weich
            cr.save()
            cr.rectangle(x, y, w, h)
            cr.clip()
            cr.translate(x + (w - bw * sc) / 2, y + (h - bh * sc) / 2)
            cr.scale(sc, sc)
            Gdk.cairo_set_source_pixbuf(cr, bg, 0, 0)
            cr.get_source().set_filter(cairo.FILTER_GOOD)
            cr.paint_with_alpha(0.32)
            cr.restore()
        # abdunkelnder Verlauf, damit die Karten klar darüber stehen
        veil = cairo.LinearGradient(0, y, 0, y + h)
        veil.add_color_stop_rgba(0.0, 0.03, 0.03, 0.05, 0.84)
        veil.add_color_stop_rgba(0.5, 0.03, 0.03, 0.05, 0.60)
        veil.add_color_stop_rgba(1.0, 0.03, 0.03, 0.05, 0.84)
        cr.set_source(veil)
        cr.rectangle(x, y, w, h)
        cr.fill()

    def _draw_wheel(self, cr):
        x, y, w, h = WHEEL
        cx, cy = x + w / 2, y + h / 2
        n = len(self.tables)

        cr.save()
        cr.rectangle(x, y, w, h)
        cr.clip()
        self._draw_wheel_bg(cr, x, y, w, h)
        if n:
            # Karten geometrisch erfassen, dann fern -> nah zeichnen, damit
            # die zentrale Karte oben auf dem Stapel liegt.
            cards = []
            for k in range(-WHEEL_SLOTS, WHEEL_SLOTS + 1):
                t = k + self.anim
                dx, dy, scale, alpha = self._fisheye(t)
                fn, status = self.tables[(self.index + k) % n]
                thumb = self._thumb(fn)
                ar = thumb.get_width() / thumb.get_height() if thumb else 1.0
                ch = CARD_H * scale
                cw = ch * ar                   # Karte folgt dem Bild-Format
                ccx, ccy = cx + dx, cy + dy
                if ccx + cw / 2 < x or ccx - cw / 2 > x + w:
                    continue
                cards.append((abs(t), fn, status, ccx, ccy, cw, ch,
                              alpha, scale, thumb))
            cards.sort(key=lambda c: c[0], reverse=True)
            for dist, fn, status, ccx, ccy, cw, ch, alpha, scale, thumb in cards:
                # < 0.5001: garantiert auch bei exakt halbem Offset Auswahl
                self._draw_card(cr, fn, status, ccx, ccy, cw, ch,
                                alpha, scale, thumb, dist < 0.5001)
        cr.restore()

    def _draw_card(self, cr, fname, status, ccx, ccy, cw, ch,
                   alpha, scale, thumb, is_center):
        """Eine Screenshot-Karte des Coverflows zeichnen."""
        x0, y0 = ccx - cw / 2, ccy - ch / 2
        rad = max(6.0, 16.0 * scale)
        border = max(2.0, 5.0 * scale)
        ix, iy = x0 + border, y0 + border
        iw, ih = cw - 2 * border, ch - 2 * border
        irad = max(3.0, rad - border)

        # Spiegelung unter der Karte — Coverflow-Signatur
        if thumb:
            cr.save()
            rtop = y0 + ch + 2
            cr.rectangle(x0, rtop, cw, ih * 0.5)
            cr.clip()
            cr.translate(0, 2 * rtop)            # an rtop vertikal spiegeln
            cr.scale(1, -1)
            cr.translate(ix, iy)
            cr.scale(iw / thumb.get_width(), ih / thumb.get_height())
            Gdk.cairo_set_source_pixbuf(cr, thumb, 0, 0)
            cr.get_source().set_filter(cairo.FILTER_GOOD)
            g = cairo.LinearGradient(0, 0, 0, thumb.get_height())
            near = (0.32 if is_center else 0.17) * alpha
            g.add_color_stop_rgba(0, 0, 0, 0, 0.0)      # tief unten -> aus
            g.add_color_stop_rgba(1, 0, 0, 0, near)     # nahe Karte -> sichtbar
            cr.mask(g)
            cr.restore()

        # Orange-Schein hinter der zentralen Karte (gestufter Fake-Glow)
        if is_center:
            for gi, ga in ((22, 0.06), (13, 0.10), (6, 0.16)):
                self._rounded(cr, x0 - gi, y0 - gi,
                              cw + 2 * gi, ch + 2 * gi, rad + gi)
                cr.set_source_rgba(*ORANGE, ga)
                cr.fill()

        # Schlagschatten — verkauft die Tiefe der gestapelten Karten
        self._rounded(cr, x0 + 6 * scale, y0 + 8 * scale, cw, ch, rad)
        cr.set_source_rgba(0, 0, 0, 0.5 * alpha)
        cr.fill()

        # Karten-Korpus (dunkler Rahmen rund um den Screenshot)
        self._rounded(cr, x0, y0, cw, ch, rad)
        cr.set_source_rgba(0.06, 0.06, 0.08, alpha)
        cr.fill()

        # Screenshot einpassen — der Thumb füllt die Karte exakt aus
        cr.save()
        self._rounded(cr, ix, iy, iw, ih, irad)
        cr.clip()
        if thumb:
            cr.translate(ix, iy)
            cr.scale(iw / thumb.get_width(), ih / thumb.get_height())
            Gdk.cairo_set_source_pixbuf(cr, thumb, 0, 0)
            cr.get_source().set_filter(cairo.FILTER_GOOD)
            cr.paint_with_alpha(alpha)
        else:
            cr.set_source_rgba(0.1, 0.1, 0.13, alpha)
            cr.paint()
            lay = make_layout(cr, clean_name(fname), max(8.0, 26 * scale),
                              bold=True, width=iw,
                              align=Pango.Alignment.CENTER, ellipsize=True)
            _, th = lay.get_pixel_size()
            cr.set_source_rgba(0.62, 0.62, 0.68, alpha)
            cr.move_to(ix, iy + (ih - th) / 2)
            PangoCairo.show_layout(cr, lay)
        cr.restore()

        # Nicht-zentrale Karten abdunkeln -> die Auswahl sticht hervor
        if not is_center:
            self._rounded(cr, ix, iy, iw, ih, irad)
            cr.set_source_rgba(0, 0, 0, 0.16 + 0.34 * (1.0 - scale))
            cr.fill()

        # Rahmen — zentrale Karte kräftig orange, der Rest dezent grau
        self._rounded(cr, x0, y0, cw, ch, rad)
        if is_center:
            cr.set_source_rgba(*ORANGE, 1.0)
            cr.set_line_width(max(3.0, 5.0 * scale))
        else:
            cr.set_source_rgba(0.52, 0.52, 0.58, 0.55 * alpha)
            cr.set_line_width(max(1.5, 2.5 * scale))
        cr.stroke()

        # Status-Punkt oben links auf der Karte
        col = STATUS_COLOR.get(status, (0.7, 0.7, 0.7))
        dotr = max(4.0, 9.0 * scale)
        dcx = x0 + border + dotr + 5
        dcy = y0 + border + dotr + 5
        cr.set_source_rgba(0, 0, 0, 0.6 * alpha)
        cr.arc(dcx, dcy, dotr + 3, 0, 6.2832)
        cr.fill()
        cr.set_source_rgba(col[0], col[1], col[2], alpha)
        cr.arc(dcx, dcy, dotr, 0, 6.2832)
        cr.fill()

    def _draw_dmd(self, cr):
        x, y, w, h = DMD
        self._rounded(cr, x, y, w, h, 14)
        cr.set_source_rgb(0.015, 0.015, 0.02)
        cr.fill()
        self._rounded(cr, x, y, w, h, 14)
        cr.set_source_rgba(ORANGE[0], ORANGE[1], ORANGE[2], 0.45)
        cr.set_line_width(2)
        cr.stroke()
        if self.dmd_surface:
            sw = self.dmd_surface.get_width()
            sh = self.dmd_surface.get_height()
            cr.set_source_surface(self.dmd_surface,
                                  x + (w - sw) / 2, y + (h - sh) / 2)
            cr.paint()

    def _draw_toast(self, cr):
        if not self.toast_text:
            return
        lay = make_layout(cr, self.toast_text, 22, bold=True)
        tw, th = lay.get_pixel_size()
        bx = (SCREEN_W - tw) / 2 - 30
        by = DMD[1] - 70
        self._rounded(cr, bx, by, tw + 60, th + 22, 11)
        cr.set_source_rgba(0, 0, 0, 0.85)
        cr.fill()
        cr.set_source_rgb(1.0, 0.8, 0.0)
        cr.move_to(bx + 30, by + 11)
        PangoCairo.show_layout(cr, lay)

    def _toast(self, msg):
        self.toast_text = msg
        if self.toast_id:
            GLib.source_remove(self.toast_id)
        self.toast_id = GLib.timeout_add(2600, self._clear_toast)
        self.da.queue_draw()

    def _clear_toast(self):
        self.toast_text = ''
        self.toast_id = None
        self.da.queue_draw()
        return False

    # ---- Perspektive-Abfrage ---------------------------------------------
    def _picker_dots(self, text, w, h, pitch):
        """Gecachte Dot-Matrix-Surface für einen Picker-Text."""
        key = (text, w, h, pitch)
        if key not in self.picker_cache:
            thh = (h // pitch) * 2
            self.picker_cache[key] = render_dots(
                [(text, thh * 0.66, thh * 0.15)], w, h, pitch, ORANGE, None)
        return self.picker_cache[key]

    def _draw_picker(self, cr):
        if self.picker is None:
            return
        fn = self._current()[0]
        modes = VIEW_MODES.get(fn, [])
        if not modes:
            self.picker = None
            return

        # abgedunkelter Hintergrund
        cr.set_source_rgba(0, 0, 0, 0.74)
        cr.rectangle(0, 0, SCREEN_W, SCREEN_H)
        cr.fill()

        # Panel
        pw, ph = 1040, 446
        px, py = (SCREEN_W - pw) / 2, (SCREEN_H - ph) / 2
        self._rounded(cr, px, py, pw, ph, 22)
        cr.set_source_rgb(0.05, 0.05, 0.07)
        cr.fill()
        self._rounded(cr, px, py, pw, ph, 22)
        cr.set_source_rgb(*ORANGE)
        cr.set_line_width(3)
        cr.stroke()

        # Titel
        title = self._picker_dots('PERSPEKTIVE  WÄHLEN', 780, 64, 5)
        cr.set_source_surface(title, px + (pw - title.get_width()) / 2, py + 40)
        cr.paint()

        # Modus-Karten nebeneinander
        ow, oh, gap = 392, 156, 56
        total = len(modes) * ow + (len(modes) - 1) * gap
        ox = px + (pw - total) / 2
        oy = py + 138
        for i, (label, _) in enumerate(modes):
            bx = ox + i * (ow + gap)
            sel = (i == self.picker)
            self._rounded(cr, bx, oy, ow, oh, 14)
            if sel:
                cr.set_source_rgba(*ORANGE, 0.16)
                cr.fill()
                self._rounded(cr, bx, oy, ow, oh, 14)
                cr.set_source_rgb(*ORANGE)
                cr.set_line_width(3)
            else:
                cr.set_source_rgba(0.5, 0.5, 0.56, 0.45)
                cr.set_line_width(2)
            cr.stroke()
            surf = self._picker_dots(label, ow - 48, oh - 52, 5)
            cr.set_source_surface(surf, bx + (ow - surf.get_width()) / 2,
                                  oy + (oh - surf.get_height()) / 2)
            cr.paint_with_alpha(1.0 if sel else 0.34)

        # Hinweis
        hint = self._picker_dots('◀ ▶  WÄHLEN      ENTER  STARTET      9  ZURÜCK',
                                 960, 40, 4)
        cr.set_source_surface(hint, px + (pw - hint.get_width()) / 2,
                              py + ph - 64)
        cr.paint()

    # ---- Eingabe ----------------------------------------------------------
    def on_key(self, _w, event):
        kn = Gdk.keyval_name(event.keyval)
        if self.picker is not None:
            return self._picker_key(kn)
        if kn in ('Left', 'Up', 'Shift_L'):
            self._move(-1); return True
        if kn in ('Right', 'Down', 'Shift_R'):
            self._move(1); return True
        if kn == 'Page_Up':
            self._jump(self.index - 5); return True
        if kn == 'Page_Down':
            self._jump(self.index + 5); return True
        if kn == 'Home':
            self._jump(0); return True
        if kn == 'End':
            self._jump(len(self.tables) - 1); return True
        if kn in ('Return', 'KP_Enter', 'space'):
            self.launch_selected(); return True
        if kn in ('9', 'KP_9'):
            Gtk.main_quit(); return True
        if kn == 'F5':
            self._mark('OK'); return True
        if kn == 'F8':
            self._mark('KAPUTT'); return True
        if kn in ('m', 'M'):
            self._toggle_music(); return True
        return False

    def _picker_key(self, kn):
        """Tasten während der Perspektive-Abfrage (Stehend/Sitzend)."""
        fn = self._current()[0]
        modes = VIEW_MODES.get(fn, [])
        if not modes:
            self.picker = None
        elif kn in ('Left', 'Up', 'Shift_L'):
            self.picker = (self.picker - 1) % len(modes)
            self.da.queue_draw()
        elif kn in ('Right', 'Down', 'Shift_R'):
            self.picker = (self.picker + 1) % len(modes)
            self.da.queue_draw()
        elif kn in ('Return', 'KP_Enter', 'space'):
            self.launch_selected()
        elif kn in ('9', 'KP_9', 'Escape'):
            self.picker = None
            self.da.queue_draw()
        return True

    def _mark(self, new_status):
        if not self.tables:
            return
        fn, _ = self.tables[self.index]
        save_status_override(fn, new_status)
        self.tables = list_tables()
        # Index auf denselben Tisch nachziehen
        for i, (f, _s) in enumerate(self.tables):
            if f == fn:
                self.index = i
                break
        self._update_selection()
        self._toast(f'{clean_name(fn)}  →  {STATUS_WORD.get(new_status, new_status)}')

    # ---- Tisch starten ----------------------------------------------------
    def launch_selected(self):
        if not self.tables:
            return
        fn, _ = self.tables[self.index]
        modes = VIEW_MODES.get(fn)
        if modes and self.picker is None:
            # Tisch hat Perspektiv-Modi -> erst die Abfrage öffnen
            self.picker = self.view_choice.get(fn, 0)
            self.da.queue_draw()
            return
        view = None
        if modes:
            idx = self.picker if self.picker is not None else 0
            self.view_choice[fn] = idx
            self.picker = None
            view = modes[idx][1]
        self._launch(fn, view)

    def _capture_preview_async(self, fn):
        """Wenn noch kein media/<stem>.png existiert, in 30s einen Screenshot
        vom VPinball-Fenster ziehen und speichern. Daemon-Thread, fail-silent."""
        stem = fn[:-4] if fn.endswith('.vpx') else fn
        preview_path = MEDIA_DIR / f'{stem}.png'
        if preview_path.exists():
            return

        def _worker():
            time.sleep(30)
            tmp_xwd = f'/tmp/auto-preview-{os.getpid()}.xwd'
            try:
                from PIL import Image
                res = subprocess.run(
                    ['wmctrl', '-l'], capture_output=True, text=True,
                    env={**os.environ, 'DISPLAY': ':0'}, timeout=5)
                wid = None
                for line in res.stdout.splitlines():
                    if 'Visual Pinball' in line or 'VPinballX' in line:
                        wid = line.split()[0]
                        break
                if not wid:
                    return
                subprocess.run(
                    ['xwd', '-id', wid, '-out', tmp_xwd],
                    env={**os.environ, 'DISPLAY': ':0'}, check=True, timeout=10)
                from PIL import ImageFilter
                img = Image.open(tmp_xwd).convert('RGB')
                sm = img.resize((64, 36))
                avg = sum(r + g + b for r, g, b in sm.getdata()) \
                    / (sm.width * sm.height * 3)
                if avg < 14:
                    return  # zu dunkel — nächster Spielstart versucht's nochmal

                # Tisch-Crop: Maske vom Tisch erzeugen, dann fünf 5x5-Erosionen
                # — das löst isolierte helle Spots (Statustext, DMD-Punkte) auf,
                # weil sie klein genug sind, der zusammenhängende Tisch nicht.
                w, h = img.size
                gray = img.convert('L')
                mask = gray.point(lambda p: 255 if p > 30 else 0)
                for _ in range(5):
                    mask = mask.filter(ImageFilter.MinFilter(5))
                cols = list(mask.resize((w, 1), Image.BOX).getdata())
                rows = list(mask.resize((1, h), Image.BOX).getdata())
                T = 5
                x_lo = next((i for i, v in enumerate(cols) if v > T), 0)
                x_hi = next((w - 1 - i for i, v in enumerate(reversed(cols))
                             if v > T), w - 1)
                y_lo = next((i for i, v in enumerate(rows) if v > T), 0)
                y_hi = next((h - 1 - i for i, v in enumerate(reversed(rows))
                             if v > T), h - 1)
                if x_hi > x_lo and y_hi > y_lo:
                    pad = 8
                    img = img.crop((max(0, x_lo - pad),
                                    max(0, y_lo - pad),
                                    min(w, x_hi + 1 + pad),
                                    min(h, y_hi + 1 + pad)))

                if img.width > 1280:
                    h = round(img.height * 1280 / img.width)
                    img = img.resize((1280, h), Image.LANCZOS)
                img.save(preview_path, optimize=True)
            except Exception:
                pass
            finally:
                try:
                    os.remove(tmp_xwd)
                except OSError:
                    pass

        threading.Thread(target=_worker, daemon=True).start()

    def _launch(self, fn, view):
        self._toast(f'Laedt:  {clean_name(fn)}  …')
        while Gtk.events_pending():
            Gtk.main_iteration()

        # Theme stoppen — der Tisch übernimmt jetzt den Ton
        if self.theme_timer:
            GLib.source_remove(self.theme_timer)
            self.theme_timer = None
        self._play_theme(None)

        write_view_override(view)        # Perspektive setzen / zurücksetzen
        cache = CACHE_DIR / fn.replace('.vpx', '')
        if cache.exists():
            subprocess.run(['rm', '-rf', str(cache)], check=False)
        subprocess.run(['pkill', '-9', '-f', 'VPinballX_GL'], check=False)
        time.sleep(0.4)

        with open(LOG_FILE, 'a') as logf:
            logf.write(f'==== {time.strftime("%F %T")} - Starting: {fn} ====\n')
            proc = subprocess.Popen(
                ['./VPinballX_GL', '-Primary', '-DisableTrueFullscreen',
                 '-Play', f'tables/{fn}'],
                cwd=str(VPX_DIR),
                stdout=logf, stderr=subprocess.STDOUT,
                env={**os.environ, 'SDL_VIDEODRIVER': 'x11'})

        self._capture_preview_async(fn)

        while proc.poll() is None:
            while Gtk.events_pending():
                Gtk.main_iteration()
            time.sleep(0.1)

        rc = proc.returncode
        with open(LOG_FILE, 'a') as logf:
            logf.write(f'==== {time.strftime("%F %T")} - Exit Code: {rc} ====\n')

        self.tables = list_tables()
        self.index = max(0, min(self.index, len(self.tables) - 1))
        self._update_selection()
        self.present()
        self.fullscreen()
        self.da.queue_draw()

        # 0/1 = sauber, 134 = bekannter VPX-Shutdown-Bug, 137/143 = gekillt
        if rc not in (0, 1, 134, 137, 143):
            self._toast(f'⚠  Tisch beendet mit Code {rc}')
        else:
            self._clear_toast()


def main():
    lock_fd = open('/tmp/vpinball-menu.lock', 'w')
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return

    subprocess.run(['pkill', '-9', '-f', 'VPinballX_GL'], check=False)

    win = ArcadeMenu()
    win.show_all()
    win.fullscreen()
    win.present()

    def kick_fullscreen():
        win.fullscreen()
        win.move(0, 0)
        win.present()
        return False
    GLib.timeout_add(250, kick_fullscreen)
    GLib.timeout_add(1000, kick_fullscreen)

    def force_via_wmctrl():
        subprocess.run(['wmctrl', '-r', 'Thomas Arcade', '-b', 'add,fullscreen'],
                       check=False)
        return False
    GLib.timeout_add(500, force_via_wmctrl)
    GLib.timeout_add(1500, force_via_wmctrl)

    Gtk.main()


if __name__ == '__main__':
    main()
