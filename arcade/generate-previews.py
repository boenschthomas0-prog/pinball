#!/usr/bin/env python3
"""
generate-previews.py — Vorschaubilder für das Pinball-Rad-Menü erzeugen.

Extrahiert aus jeder .vpx das eingebettete Playfield-Bild (via vpxtool) und
legt es als  vpx/media/<tisch>.png  ab. Kein Tisch-Start nötig — deterministisch,
schnell, ohne Bildschirm-Takeover und ohne Absturz-Risiko. Tische ohne
brauchbares Bild bekommen ein gestyltes Platzhalter-Bild — damit hat
GARANTIERT jeder Tisch eine Vorschau im Menü.

  python3 generate-previews.py                 # alle Tische
  python3 generate-previews.py alien hallow    # nur passende (Teilstring)
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

VPX_DIR    = Path('/home/thomas/Applications/pinball/vpx')
TABLES_DIR = VPX_DIR / 'tables'
MEDIA_DIR  = VPX_DIR / 'media'
VPXTOOL    = VPX_DIR / 'vpxtool'
TMP_DIR    = VPX_DIR / '.preview-extract'

OUT_MAX_H  = 1800           # px – Zielhöhe der gespeicherten Vorschau
RASTER_EXT = {'.png', '.webp', '.jpg', '.jpeg', '.bmp', '.tga', '.gif'}

FONT_CANDIDATES = [
    VPX_DIR / 'assets' / 'LiberationSans-Regular.ttf',
    Path('/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'),
    Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
]

# Saubere Anzeigenamen (ohne Emoji) für die Platzhalter-Karten
CLEAN_NAME = {
    'alien13':                                       'ALIEN',
    'Alice Cooper Nightmare Castle (Ling Woo)':      'ALICE COOPER',
    'Bart vs The Space Mutants':                     'BART SIMPSON',
    'Fish Tales (Williams 1992)':                    'FISH TALES',
    'Futurama (Original 2024) v1.2.2':               'FUTURAMA',
    'GOTG_2.1.0':                                    'GUARDIANS OF THE GALAXY',
    'Halloween (Granit 2020)':                       'HALLOWEEN',
    'Houdini (Granit 2020)':                         'HOUDINI',
    'Ramones (HauntFreaks 2021) v2.0':               'RAMONES',
    'Stranger Things (Granit 2020)':                 'STRANGER THINGS',
    'Watchmen (Wizball 2020)':                       'WATCHMEN',
    'Yellow Submarine (Giantomasi 2020)':            'YELLOW SUBMARINE',
}


def log(msg):
    print(msg, flush=True)


def find_font(size):
    for fp in FONT_CANDIDATES:
        if fp.exists():
            try:
                return ImageFont.truetype(str(fp), size)
            except Exception:
                pass
    return ImageFont.load_default()


def make_placeholder(stem, path):
    """Gestylte Platzhalter-Karte (hochkant) — damit JEDER Tisch eine hat."""
    name = CLEAN_NAME.get(stem, stem.upper())
    W, H = 860, 1640
    img = Image.new('RGB', (W, H), (10, 10, 14))
    d = ImageDraw.Draw(img)
    for y in range(-W, H, 56):                       # diagonale Streifen
        d.line([(0, y), (W, y + W)], fill=(20, 20, 27), width=20)
    d.rectangle([12, 12, W - 13, H - 13], outline=(255, 68, 0), width=6)
    big, small = find_font(78), find_font(36)
    lines, cur = [], ''
    for word in name.split():
        test = (cur + ' ' + word).strip()
        if cur and d.textlength(test, font=big) > W - 130:
            lines.append(cur)
            cur = word
        else:
            cur = test
    if cur:
        lines.append(cur)
    y = (H - len(lines) * 96) // 2 - 30
    for ln in lines:
        tw = d.textlength(ln, font=big)
        d.text(((W - tw) // 2, y), ln, font=big, fill=(245, 245, 245))
        y += 96
    sub = 'KEINE VORSCHAU'
    tw = d.textlength(sub, font=small)
    d.text(((W - tw) // 2, y + 14), sub, font=small, fill=(255, 110, 30))
    img.save(path, optimize=True)


def find_playfield(extract_dir):
    """Pfad zum Playfield-Bild ermitteln (gamedata 'image', sonst grösstes)."""
    images = extract_dir / 'images'
    if not images.is_dir():
        return None
    name = None
    gd = extract_dir / 'gamedata.json'
    if gd.exists():
        try:
            name = json.loads(gd.read_text()).get('image') or None
        except Exception:
            name = None
    if name:
        for f in images.iterdir():
            if f.stem == name and f.suffix.lower() in RASTER_EXT:
                return f
    # Fallback: grösstes Rasterbild (das Playfield ist meist die grösste Textur)
    cands = [f for f in images.iterdir()
             if f.is_file() and f.suffix.lower() in RASTER_EXT]
    return max(cands, key=lambda f: f.stat().st_size) if cands else None


def extract_playfield(table):
    """vpx extrahieren -> Playfield als PIL-Image (oder None)."""
    shutil.rmtree(TMP_DIR, ignore_errors=True)
    try:
        r = subprocess.run(
            [str(VPXTOOL), 'extract', '-f', '-o', str(TMP_DIR), str(table)],
            capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            log(f'  vpxtool-Fehler: {(r.stderr or r.stdout).strip()[:160]}')
            return None
        pf = find_playfield(TMP_DIR)
        if pf is None:
            log('  kein Playfield-Bild gefunden.')
            return None
        log(f'  Playfield: images/{pf.name}')
        img = Image.open(pf)
        img.load()
        return img.convert('RGB')
    except subprocess.TimeoutExpired:
        log('  vpxtool-Timeout (>300s).')
        return None
    except Exception as e:
        log(f'  Fehler: {e}')
        return None
    finally:
        shutil.rmtree(TMP_DIR, ignore_errors=True)


def save_preview(img, path):
    if img.height > OUT_MAX_H:
        nw = round(img.width * OUT_MAX_H / img.height)
        img = img.resize((nw, OUT_MAX_H), Image.LANCZOS)
    img.save(path, optimize=True)
    return img.size


def generate(table):
    stem = table.stem
    out = MEDIA_DIR / f'{stem}.png'
    log(f'\n=== {CLEAN_NAME.get(stem, stem)} ===')
    img = extract_playfield(table)
    if img is not None:
        size = save_preview(img, out)
        log(f'  ✓ Vorschau: media/{out.name}  ({size[0]}x{size[1]})')
        return 'ok'
    make_placeholder(stem, out)
    log(f'  ⚠ Platzhalter: media/{out.name}')
    return 'placeholder'


def main():
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    tables = sorted(TABLES_DIR.glob('*.vpx'))
    if len(sys.argv) > 1:
        filt = [a.lower() for a in sys.argv[1:]]
        tables = [t for t in tables
                  if any(f in t.name.lower() for f in filt)]
    if not tables:
        log('Keine passenden Tische gefunden.')
        return
    log(f'{len(tables)} Tisch(e) -> {MEDIA_DIR}')
    results = {}
    for t in tables:
        try:
            results[t.stem] = generate(t)
        except Exception as e:
            log(f'  Fehler bei {t.name}: {e}')
            make_placeholder(t.stem, MEDIA_DIR / f'{t.stem}.png')
            results[t.stem] = 'placeholder'
    shutil.rmtree(TMP_DIR, ignore_errors=True)
    ok = sum(1 for v in results.values() if v == 'ok')
    ph = sum(1 for v in results.values() if v == 'placeholder')
    log(f'\nFertig: {ok} echte Vorschau(en), {ph} Platzhalter — '
        f'alle {len(results)} Tische haben jetzt eine Vorschau.')


if __name__ == '__main__':
    main()
