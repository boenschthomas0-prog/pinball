# AGENT.md — VPinball Arcade

## Project Overview
Pinball arcade cabinet on Linux using Visual Pinball X Standalone (VPinballX_GL 10.8.1). Full-screen GTK3 coverflow menu with fisheye effect, DMD info line, and per-table theme music.

## Directory Structure
- `vpinball-menu.py` — Main menu (GTK3, Cairo, fullscreen coverflow)
- `generate-previews.py` — Extracts playfield images from `.vpx` files via `vpxtool`
- `shoot-tables.py` — Interactive in-game screenshot capture
- `tools/patch_afm_nvram.py` — PinMAME NVRAM patcher (WPC checksums)
- `tests/test_afm.sh` — Bash integration test for AFM table bugs
- `table-patches/` — VBScript patches for Linux-compatible tables
- `VPinballX.ini` — VPX keybindings (1=Start, 5=Coin, Space=Plunger, 9=Exit)

## Coding Conventions
- **Python 3.10+** with type annotations (`from __future__ import annotations`)
- **GTK3** via PyGObject (`gi.repository`) — Cairo for custom drawing
- No classes where plain functions suffice (menu is function-oriented)
- Paths: `VPX_DIR = Path('/home/thomas/Applications/pinball/vpx')` — hardcoded, do NOT change
- Error handling: return codes, no bare `except`, log to `last-run.log`
- Comments/docstrings: German for user-facing, English for technical
- Constants in `UPPER_CASE`, functions in `snake_case`

## Key Patterns
- **X11 requirement**: `os.environ['GDK_BACKEND'] = 'x11'` must be set before `gi.import`
- **VPX lifecycle**: subprocess with `Popen`, track PID, kill via SIGTERM, wait, then SIGKILL
- **Status file**: `table-status.txt` — pipe-delimited: `name|status|genre|year|manufacturer`
- **Theme audio**: `Gst` playback, per-table `.mp3`/`.ogg` in `themes/` dir
- **DMD display**: PangoCairo dot-matrix-style rendering at bottom of screen
- **Coverflow**: cairo transforms for fisheye perspective, off-screen surface for blur

## Testing
- `tests/test_afm.sh` — standalone bash test, outputs KEY=value format with PASS/FAIL/INCONCLUSIVE
- Run: `bash tests/test_afm.sh [--quick]`

## Important Gotchas
- VPX crashes on shutdown (`free(): invalid size`, exit 134) — known engine bug, not table fault
- Wayland: force X11 via `GDK_BACKEND=x11` + `SDL_VIDEODRIVER=x11`
- Mouse input: `xdotool` click 1 to wake SDL2 input before key sends
- Never guess NVRAM offsets — must be verified from ROM disassembly or trusted map
- NVRAM files are 12334 bytes (12288 WPC-12K + 46-byte PinMAME footer)
