"""
Roulette-Chip-Set: 6 klassische Setzfarben in einer Reihe.

Nutzt build_chip() aus casino_chip_cap.py - so muss die Geometrie nur an
einer Stelle gepflegt werden.

Render-Engine: Eevee (Real-Time-Rasterizer). Fuer 6 Chips waere Cycles
~30 Minuten. Eevee macht das in unter einer Minute, und fuer Plastik mit
Clearcoat sieht's nahezu gleich aus.

Aufruf:
    BLENDER=/home/thomas/Applications/pinball/blender/blender
    $BLENDER --background --python chip_set.py
"""

import math
from pathlib import Path

import bpy
from mathutils import Vector

# Wir importieren aus dem Geschwister-Skript. __file__ ist der absolute Pfad.
import sys
sys.path.insert(0, str(Path(__file__).parent))
from casino_chip_cap import (                          # noqa: E402
    ROULETTE_CHIPS, build_chip, clear_scene, make_material,
    configure_world_background, CAP_RADIUS, CAP_HEIGHT,
)


HERE = Path(__file__).parent
RENDER_PATH = HERE / "renders" / "chip_set.png"


def setup_set_camera_and_lights(set_width):
    """Wide-Shot fuer 6 Chips in einer Reihe.

    Kamera weiter weg, Lens etwas breiter (50mm statt 100mm), Track-To auf
    die Mitte der Reihe.
    """
    target = bpy.data.objects.new("CamTarget", None)
    target.location = (0, 0, CAP_HEIGHT * 0.6)
    bpy.context.collection.objects.link(target)

    cam_data = bpy.data.cameras.new("Cam")
    cam_data.lens = 40
    cam = bpy.data.objects.new("Cam", cam_data)
    # Naeher (Distanz 1.0x Set-Breite) und hoeher (0.6x = ~30 Grad downview)
    # zeigt Top + Body + Goldring, lasst aber Padding um die Reihe.
    cam.location = (0.0, -set_width * 1.0, set_width * 0.60)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam

    track = cam.constraints.new(type="TRACK_TO")
    track.target = target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"

    # Eine grosse Soft-Box als Hauptlicht ueber dem Set
    def add_area(name, energy, loc, size, rot=(0, 0, 0), color=(1, 1, 1)):
        d = bpy.data.lights.new(name, type="AREA")
        d.energy = energy
        d.size = size
        d.color = color
        o = bpy.data.objects.new(name, d)
        o.location = loc
        o.rotation_euler = rot
        bpy.context.collection.objects.link(o)
        return o

    add_area("KeySoft", 5.0, (0.0, -set_width * 0.25, set_width * 0.50),
             size=set_width * 0.7,
             rot=(math.radians(20), 0, 0),
             color=(1.0, 0.97, 0.92))
    add_area("FillL",   1.5, (-set_width * 0.7, -set_width * 0.10,
                              set_width * 0.20),
             size=0.30, color=(0.85, 0.92, 1.0))
    add_area("FillR",   1.5, ( set_width * 0.7, -set_width * 0.10,
                              set_width * 0.20),
             size=0.30, color=(1.00, 0.92, 0.85))
    add_area("Rim",     3.0, (0.0, set_width * 0.4, set_width * 0.15),
             size=0.40, color=(1.0, 0.80, 0.65))

    # Felt-Boden im Casino-Gruen
    bpy.ops.mesh.primitive_plane_add(size=set_width * 4,
                                     location=(0, 0, 0))
    plane = bpy.context.object
    plane.name = "Floor"
    plane.data.materials.append(
        make_material("Floor", (0.04, 0.18, 0.08, 1.0),
                      roughness=0.95, specular=0.1)
    )


def configure_eevee_render(filepath, resolution=(1920, 720)):
    """Eevee statt Cycles - schnell genug fuer 6 Objekte und gut genug
    fuer Plastik mit Clearcoat.
    """
    scene = bpy.context.scene
    # Blender 4.5: Engine heisst 'BLENDER_EEVEE_NEXT'
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    # Eevee-spezifische Quality-Settings: mehr Samples fuer weniger Noise
    scene.eevee.taa_render_samples = 128
    scene.eevee.use_raytracing = True            # echte Reflexionen am Gold
    scene.render.resolution_x = resolution[0]
    scene.render.resolution_y = resolution[1]
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(filepath)
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Punchy"
    scene.view_settings.exposure = 0.5     # Belichtung hoch fuer kraeftige Farben


def main():
    print("=" * 60)
    print("Roulette-Chip-Set (6 Chips)")
    print("=" * 60)

    clear_scene()

    # Chips in einer Reihe auslegen. Abstand etwas mehr als Durchmesser
    # damit es nicht eng wirkt.
    spacing = CAP_RADIUS * 2.4
    n = len(ROULETTE_CHIPS)
    total_width = spacing * (n - 1)

    for i, spec in enumerate(ROULETTE_CHIPS):
        x = -total_width / 2 + i * spacing
        print(f"  Chip {i+1}/{n}: {spec.name} '{spec.text}' @ x={x*1000:.0f}mm")
        build_chip(spec, location=(x, 0, 0))

    setup_set_camera_and_lights(set_width=total_width + 2 * CAP_RADIUS)
    configure_world_background()
    configure_eevee_render(RENDER_PATH)

    print("Rendere ->", RENDER_PATH)
    bpy.ops.render.render(write_still=True)
    print("Fertig.")


if __name__ == "__main__":
    main()
