#!/usr/bin/env python3
"""Controller → Tastatur: übersetzt Gamepad-Buttons in Tastendrücke."""
import json
import os
import signal
import sys
import time
from pathlib import Path

from evdev import InputDevice, UInput, ecodes as e, list_devices

CONFIG = Path(os.environ.get('CTRL2KEY_CFG',
              str(Path.home() / '.vpinball' / 'ctrl2key.json')))

DEFAULT_MAP = {
    "4":  "KEY_LEFTSHIFT",    # LB  → linker Flipper
    "5":  "KEY_RIGHTSHIFT",   # RB  → rechter Flipper
    "2":  "KEY_5",            # X   → Coin
    "3":  "KEY_1",            # Y   → Start
    "10": "KEY_ENTER",        # R3  → Plunger
    "1":  "KEY_4",            # B   → Credit 2
    "8":  "KEY_9",            # Home → Exit
    "0":  "KEY_SPACE",        # A   → Aktion
    "6":  "KEY_LEFT",         # Select → links
    "7":  "KEY_RIGHT",        # Start → rechts
}

KEY_NAMES = {k: v for k, v in vars(e).items() if k.startswith('KEY_')}
KEY_REV = {v: k for k, v in KEY_NAMES.items()}


def load_map():
    if CONFIG.exists():
        raw = json.loads(CONFIG.read_text())
        return {int(k): KEY_NAMES.get(v, getattr(e, v, e.KEY_SPACE))
                for k, v in raw.items()}
    return {int(k): KEY_NAMES[v] for k, v in DEFAULT_MAP.items()}


def save_defaults():
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(DEFAULT_MAP, indent=2) + '\n')
    print(f'Config saved: {CONFIG}')


def find_ctrl():
    for p in sorted(Path('/dev/input/by-id').glob('*-event-joystick')):
        try:
            return InputDevice(str(p))
        except Exception:
            continue
    try:
        return InputDevice('/dev/input/js0')
    except Exception:
        return None


def main():
    keymap = load_map()

    ctrl = find_ctrl()
    if not ctrl:
        print('Kein Controller gefunden.')
        sys.exit(1)

    print(f'Controller: {ctrl.name}')
    print(f'Mapping ({len(keymap)} Tasten):')
    for btn, keycode in sorted(keymap.items()):
        kname = KEY_REV.get(keycode, hex(keycode))
        print(f'  SDL {btn:2d} → {kname}')

    ui = UInput({e.EV_KEY: list(keymap.values())},
                name='ctrl2key-virtual-kbd',
                bustype=e.BUS_VIRTUAL)

    running = True
    def stop():
        nonlocal running
        running = False
    signal.signal(signal.SIGINT, lambda *_: stop())
    signal.signal(signal.SIGTERM, lambda *_: stop())

    print('\nLäuft … (Ctrl+C zum Beenden)')

    try:
        ctrl.grab()
        for event in ctrl.read_loop():
            if not running:
                break
            if event.type == e.EV_KEY:
                keycode = keymap.get(event.code)
                if keycode:
                    ui.write(e.EV_KEY, keycode, event.value)
                    ui.syn()
    except OSError:
        pass
    finally:
        ui.close()
        print('Beendet.')


if __name__ == '__main__':
    if '--save-defaults' in sys.argv:
        save_defaults()
    else:
        main()
