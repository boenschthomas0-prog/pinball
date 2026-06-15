#!/usr/bin/env python3
"""
shoot-tables.py — Echte In-Game-Screenshots für das Pinball-Rad aufnehmen.

Startet der Reihe nach jeden Tisch im Vollbild. Pro Tisch macht DER NUTZER
einen Screenshot mit der Druck-Taste (PrintScreen) und beendet den Tisch dann
mit Taste 9. Das Skript holt den neuen Screenshot automatisch aus
~/Pictures/Screenshots/ und legt ihn als vpx/media/<tisch>.png ab.

Ablauf pro Tisch:
  1. Tisch erscheint im Vollbild — kurz warten bis er fertig gerendert ist.
  2. [Druck]/[PrintScreen] drücken  ->  ggf. oben "Bildschirm" wählen  ->  [Enter].
  3. Tisch mit Taste [9] beenden  ->  der nächste Tisch startet automatisch.

Tische die du nicht screenshottest (oder die crashen) behalten ihr bisheriges
Bild als Fallback — so bleibt kein Tisch ohne Vorschau.

  python3 shoot-tables.py                # alle Tische
  python3 shoot-tables.py alien hallow   # nur passende (Teilstring)
"""
import os
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image

os.environ.setdefault('DISPLAY', ':0')

VPX_DIR    = Path('/home/thomas/Applications/pinball/vpx')
TABLES_DIR = VPX_DIR / 'tables'
MEDIA_DIR  = VPX_DIR / 'media'
SHOTS_DIR  = Path.home() / 'Pictures' / 'Screenshots'
OUT_MAX_W  = 1280
START_DELAY = 15        # s – Vorlauf, damit du die Anleitung lesen kannst
GAP        = 3          # s – Pause zwischen den Tischen


def log(msg):
    print(msg, flush=True)


def shots_set():
    if not SHOTS_DIR.is_dir():
        return set()
    return {p for p in SHOTS_DIR.iterdir()
            if p.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp')}


def kill_vpx():
    subprocess.run(['pkill', '-9', 'VPinballX_GL'], check=False)
    time.sleep(0.5)


def is_blank(img):
    s = img.resize((64, 36))
    px = list(s.getdata())
    return sum(r + g + b for r, g, b in px) / (len(px) * 3) < 14


def process(src, dst):
    """GNOME-Screenshot -> verkleinern -> media/<tisch>.png. False wenn schwarz."""
    try:
        img = Image.open(src)
        img.load()
        img = img.convert('RGB')
    except Exception as e:
        log(f'  Bild-Fehler: {e}')
        return False
    if is_blank(img):
        return False
    if img.width > OUT_MAX_W:
        h = round(img.height * OUT_MAX_W / img.width)
        img = img.resize((OUT_MAX_W, h), Image.LANCZOS)
    img.save(dst, optimize=True)
    return True


def shoot(table, idx, total):
    stem = table.stem
    log(f'\n=== [{idx}/{total}] {stem} ===')
    before = shots_set()
    kill_vpx()
    proc = subprocess.Popen(
        ['./VPinballX_GL', '-Primary', '-DisableTrueFullscreen',
         '-Play', f'tables/{table.name}'],
        cwd=str(VPX_DIR),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env={**os.environ, 'SDL_VIDEODRIVER': 'x11'})
    log('  Tisch laeuft  ->  [Druck] Screenshot, dann [9] zum Beenden …')

    t0 = time.time()
    while proc.poll() is None:
        time.sleep(0.5)
    dur = time.time() - t0
    kill_vpx()

    new = sorted(shots_set() - before, key=lambda p: p.stat().st_mtime)
    if new:
        src = new[-1]
        if process(src, MEDIA_DIR / f'{stem}.png'):
            log(f'  ✓ Screenshot uebernommen: {src.name}')
            return 'ok'
        log('  ⚠ Screenshot war schwarz — bisheriges Bild bleibt.')
        return 'blank'
    log(f'  ⚠ kein neuer Screenshot (Tisch lief {dur:.0f}s) — '
        f'bisheriges Bild bleibt.')
    return 'none'


def main():
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(['pkill', '-9', '-f', 'vpinball-menu.py'], check=False)
    tables = sorted(TABLES_DIR.glob('*.vpx'))
    if len(sys.argv) > 1:
        filt = [a.lower() for a in sys.argv[1:]]
        tables = [t for t in tables
                  if any(f in t.name.lower() for f in filt)]
    if not tables:
        log('Keine passenden Tische gefunden.')
        return

    log(f'In-Game-Screenshots für {len(tables)} Tisch(e).')
    log(f'Pro Tisch:  [Druck] -> [Enter]  fuer den Screenshot, '
        f'dann [9] zum Beenden.')
    for s in range(START_DELAY, 0, -1):
        log(f'  Erster Tisch startet in {s}s …')
        time.sleep(1)

    results = {}
    for i, t in enumerate(tables, 1):
        try:
            results[t.stem] = shoot(t, i, len(tables))
        except Exception as e:
            log(f'  Fehler: {e}')
            results[t.stem] = 'error'
        time.sleep(GAP)

    kill_vpx()
    ok = sum(1 for v in results.values() if v == 'ok')
    miss = [k for k, v in results.items() if v != 'ok']
    log(f'\nFertig: {ok}/{len(results)} Tische mit echtem In-Game-Screenshot.')
    if miss:
        log('Ohne neuen Screenshot (Fallback-Bild bleibt):')
        for m in miss:
            log(f'  - {m}')
        log('Diese gezielt nachholen:  python3 shoot-tables.py '
            '"<teil-des-namens>"')


if __name__ == '__main__':
    main()
