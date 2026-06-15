#!/usr/bin/env python3
"""Liest ctrl2key.json und schreibt die Keyboard-Scancodes in die VPinballX.ini.
Deaktiviert alle Joy*- und Achsen-Einstellungen — VPX sieht nur Tastendrücke."""
import json
import re
from pathlib import Path
from evdev import ecodes as e

CTRL2KEY = Path.home() / '.vpinball' / 'ctrl2key.json'
VPINBALL_INI = Path.home() / '.vpinball' / 'VPinballX.ini'

# Welche Joy*-Keys existieren (alle auf 0 setzen)
JOY_KEYS = [
    'JoyLFlipKey', 'JoyRFlipKey', 'JoyStagedLFlipKey', 'JoyStagedRFlipKey',
    'JoyPlungerKey', 'JoyAddCreditKey', 'JoyAddCredit2Key',
    'JoyLMagnaSave', 'JoyRMagnaSave', 'JoyStartGameKey', 'JoyExitGameKey',
    'JoyFrameCount', 'JoyVolumeUp', 'JoyVolumeDown',
    'JoyLTiltKey', 'JoyCTiltKey', 'JoyRTiltKey', 'JoyMechTiltKey',
    'JoyDebugKey', 'JoyDebuggerKey',
    'JoyLockbarKey', 'JoyTableRecenterKey', 'JoyTableUpKey', 'JoyTableDownKey',
    'JoyPauseKey', 'JoyTweakKey',
]

# Achsen leeren
AXIS_KEYS = ['LRAxis', 'UDAxis', 'PlungerAxis', 'LRAxisFlip', 'UDAxisFlip',
             'ReversePlungerAxis', 'DeadZone']

# Mapping: SDL-Button → VPX-Keyboard-Key-Name
SDL_TO_INI = {
    0: 'CTiltKey',      # A
    1: 'AddCreditKey2', # B
    2: 'AddCreditKey',  # X
    3: 'StartGameKey',  # Y
    4: 'LFlipKey',      # LB
    5: 'RFlipKey',      # RB
    6: 'LockbarKey',    # Select
    7: 'MechTilt',      # Start
    8: 'ExitGameKey',   # Home
    9: 'TableUpKey',    # L3
    10: 'PlungerKey',   # R3
}


def scancode(key_name):
    """KEY_LEFTSHIFT → 42"""
    return getattr(e, key_name, None)


def main():
    if not CTRL2KEY.exists():
        print(f'Fehler: {CTRL2KEY} nicht gefunden.')
        return

    mapping = json.loads(CTRL2KEY.read_text())
    ini = VPINBALL_INI.read_text()

    # 1) Joy* alle auf 0 setzen
    for key in JOY_KEYS:
        ini = re.sub(rf'^{re.escape(key)}\s*=.*$', f'{key} = 0', ini, flags=re.MULTILINE)

    # 2) Achsen leeren
    for key in AXIS_KEYS:
        ini = re.sub(rf'^{re.escape(key)}\s*=.*$', f'{key} = ', ini, flags=re.MULTILINE)

    # 3) Keyboard-Scancodes aus ctrl2key setzen
    for sdl_btn, key_name in mapping.items():
        sdl_btn = int(sdl_btn)
        ini_key = SDL_TO_INI.get(sdl_btn)
        if not ini_key:
            print(f'  ? SDL {sdl_btn} ({key_name}) — kein INI-Key definiert, übersprungen')
            continue
        code = scancode(key_name)
        if code is None:
            print(f'  ? {key_name} — unbekannter Scancode, übersprungen')
            continue
        ini = re.sub(rf'^{re.escape(ini_key)}\s*=.*$',
                     f'{ini_key} = {code}', ini, flags=re.MULTILINE)
        print(f'  SDL {sdl_btn:2d} → {key_name:15s} → {ini_key} = {code}')

    VPINBALL_INI.write_text(ini)
    print(f'\nGeschrieben: {VPINBALL_INI}')
    print('(Joy* = 0, Achsen leer — Controller läuft komplett über ctrl2key)')


if __name__ == '__main__':
    main()
