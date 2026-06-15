#!/usr/bin/env python3
"""Drück einen Button → zeigt die SDL-Button-Nummer (für VPinballX.ini)."""
from evdev import InputDevice, ecodes
from pathlib import Path

# Controller finden
dev = None
for p in sorted(Path('/dev/input/by-id').glob('*-event-joystick')):
    try:
        dev = InputDevice(str(p))
        break
    except Exception:
        continue
if not dev:
    print("Kein Controller gefunden.")
    exit(1)

print(f"Controller: {dev.name}")
print("Drück die Tasten nacheinander:")
print("  A / B / X / Y / LB / RB / Select / Start / Home / L3 / R3")
print("  (Strg+C zum Beenden)")
print()

BTN_NAMES = {
    304: 'A', 305: 'B', 307: 'X', 308: 'Y',
    310: 'LB (linke Schulter)', 311: 'RB (rechte Schulter)',
    314: 'Select/Minus', 315: 'Start/Plus',
    316: 'Home/Guide', 317: 'L3 (linker Stick)', 318: 'R3 (rechter Stick)',
}

# SDL Button = Index in der HID-Reihenfolge
EVDEV_TO_SDL = {c: i for i, c in enumerate(sorted(dev.capabilities()[ecodes.EV_KEY]))}
SDL_ORDER = sorted(dev.capabilities()[ecodes.EV_KEY])

print(f"SDL-Button → evdev-Code   (Name)")
print("-" * 40)
for sdl_idx, ev_code in enumerate(SDL_ORDER):
    name = BTN_NAMES.get(ev_code, f'?')
    print(f"  {sdl_idx:2d}        → {ev_code}       ({name})")

print()
print("Jetzt live testen (Button drücken):")

dev.grab()
try:
    for event in dev.read_loop():
        if event.type == ecodes.EV_KEY and event.value == 1:
            evcode = event.code
            sdl_idx = SDL_ORDER.index(evcode)
            name = BTN_NAMES.get(evcode, f'Button {evcode}')
            print(f"  SDL {sdl_idx:2d}  ←  {name}")
except KeyboardInterrupt:
    pass
except OSError:
    print("Controller entfernt.")
