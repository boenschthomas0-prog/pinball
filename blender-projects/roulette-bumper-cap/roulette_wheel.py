"""
Europaeisches Roulette-Rad - das Kern-Asset fuer den geplanten VPX-Tisch.

37 Pockets in der korrekten Roulette-Wheel-Sequenz (0 + 1-36) mit den echten
Farben (rot/schwarz/gruen). Schmaler Holz-Aussenrand, polierter Stahlring,
Zahlen-Ring, Center-Cone, eine weisse Kugel in einer Pocket.

Geometrie ist auf Tisch-Skala (Durchmesser 22cm Wheel-Head, ungefaehre
Original-Proportionen 1:2). Fuer den VPX-Import kann man spaeter skalieren.

Aufruf:
    BLENDER=/home/thomas/Applications/pinball/blender/blender
    $BLENDER --background --python roulette_wheel.py
"""

import math
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector

import sys
sys.path.insert(0, str(Path(__file__).parent))
from casino_chip_cap import (                            # noqa: E402
    clear_scene, make_material, configure_world_background,
)


HERE = Path(__file__).parent
RENDER_PATH = HERE / "renders" / "wheel_preview.png"
OBJ_PATH    = HERE / "exports" / "wheel.obj"
BLEND_PATH  = HERE / "exports" / "wheel.blend"


# --------------------------------------------------------------------------- #
# Roulette-Konstanten - europaeisches Rad
# --------------------------------------------------------------------------- #

# Wheel-Sequenz im Uhrzeigersinn ab 0 (so liegen sie auf einem echten Rad)
WHEEL_SEQUENCE = [
    0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5,
    24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26,
]
assert len(WHEEL_SEQUENCE) == 37

RED_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}


def color_for(n):
    if n == 0:
        return "green"
    return "red" if n in RED_NUMBERS else "black"


# Maße in Metern - massstabsgetreu zu echtem Casino-Rad (~32cm Durchmesser)
RIM_OUTER     = 0.16
RIM_INNER     = 0.135
RIM_HEIGHT    = 0.022

POCKET_OUTER  = 0.132
POCKET_INNER  = 0.085
POCKET_DEPTH  = 0.012

NUMBERS_OUTER = 0.135
NUMBERS_INNER = 0.118

CENTER_RADIUS = 0.080
CENTER_HEIGHT = 0.025
TURRET_RADIUS = 0.025
TURRET_HEIGHT = 0.040

BALL_RADIUS   = 0.0066    # 13mm Durchmesser, etwas kleiner als Roulette real
BALL_POCKET   = 17        # in welcher Tasche liegt die Kugel (James Bond)


# --------------------------------------------------------------------------- #
# Helper - Mesh-Helfer
# --------------------------------------------------------------------------- #

def _new_mesh_obj(name):
    mesh = bpy.data.meshes.new(name + "Mesh")
    obj  = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj, mesh


def _cylinder(name, radius, height, segments=128, location=(0, 0, 0)):
    obj, mesh = _new_mesh_obj(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm, cap_ends=True, cap_tris=False, segments=segments,
        radius1=radius, radius2=radius, depth=height,
    )
    bm.to_mesh(mesh)
    bm.free()
    obj.location = Vector(location)
    obj.location.z += height / 2
    return obj


def _ring(name, r_outer, r_inner, height, segments=128, location=(0, 0, 0)):
    """Hohlzylinder = ein Ring. Manuell aus 4 Vertex-Loops."""
    obj, mesh = _new_mesh_obj(name)
    bm = bmesh.new()

    z_bot, z_top = -height / 2, height / 2
    # 4 Vertex-Loops: aussen-oben, aussen-unten, innen-oben, innen-unten
    outer_top = [bm.verts.new((r_outer * math.cos(2 * math.pi * i / segments),
                                r_outer * math.sin(2 * math.pi * i / segments),
                                z_top)) for i in range(segments)]
    outer_bot = [bm.verts.new((r_outer * math.cos(2 * math.pi * i / segments),
                                r_outer * math.sin(2 * math.pi * i / segments),
                                z_bot)) for i in range(segments)]
    inner_top = [bm.verts.new((r_inner * math.cos(2 * math.pi * i / segments),
                                r_inner * math.sin(2 * math.pi * i / segments),
                                z_top)) for i in range(segments)]
    inner_bot = [bm.verts.new((r_inner * math.cos(2 * math.pi * i / segments),
                                r_inner * math.sin(2 * math.pi * i / segments),
                                z_bot)) for i in range(segments)]
    # Faces: 4 Seiten (oben, unten, aussen, innen)
    for i in range(segments):
        j = (i + 1) % segments
        bm.faces.new([outer_top[i], outer_top[j], outer_bot[j], outer_bot[i]])
        bm.faces.new([inner_bot[i], inner_bot[j], inner_top[j], inner_top[i]])
        bm.faces.new([outer_top[j], outer_top[i], inner_top[i], inner_top[j]])
        bm.faces.new([inner_bot[i], outer_bot[i], outer_bot[j], inner_bot[j]])

    bm.to_mesh(mesh)
    bm.free()
    obj.location = Vector(location)
    obj.location.z += height / 2
    return obj


# --------------------------------------------------------------------------- #
# Pockets - 37 Sektoren mit Farben
# --------------------------------------------------------------------------- #

def _build_pocket_disc(z_base):
    """Erzeugt die Sektor-Scheibe: ein flacher Cylinder mit 37 keilfoermigen
    Top-Faces. Jeder Sektor bekommt sein eigenes Material (rot/schwarz/gruen).
    """
    obj, mesh = _new_mesh_obj("Pockets")
    bm = bmesh.new()

    n = 37
    z_top, z_bot = POCKET_DEPTH, 0.0
    sector_angle = 2 * math.pi / n
    # Sequenz beginnt traditionell bei "12 Uhr" (positive Y-Achse)
    angle_offset = math.pi / 2

    # Center-Vertex oben + unten - dann Speichen-Geometrie zum Rand
    center_top = bm.verts.new((0, 0, z_top))
    center_bot = bm.verts.new((0, 0, z_bot))

    rim_top = []
    rim_bot = []
    for i in range(n):
        a = angle_offset - i * sector_angle    # im Uhrzeigersinn
        x = POCKET_OUTER * math.cos(a)
        y = POCKET_OUTER * math.sin(a)
        rim_top.append(bm.verts.new((x, y, z_top)))
        rim_bot.append(bm.verts.new((x, y, z_bot)))

    # BMFaces direkt referenzieren - bm.faces.new() laesst .index auf -1
    # bis bm.faces.index_update() gerufen wird.
    top_faces_bm  = []
    side_faces_bm = []

    # Oben: 37 Dreiecks-Sektoren vom Zentrum, in WHEEL_SEQUENCE-Reihenfolge
    for i in range(n):
        j = (i + 1) % n
        top_faces_bm.append(
            bm.faces.new([center_top, rim_top[i], rim_top[j]])
        )

    # Unten: 37 Dreiecke (umgekehrte Reihenfolge fuer Outward Normals)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([center_bot, rim_bot[j], rim_bot[i]])

    # Mantel: 37 Quads (Sektor-Trennwaende werden hier zum Silbermantel)
    for i in range(n):
        j = (i + 1) % n
        side_faces_bm.append(
            bm.faces.new([rim_top[i], rim_bot[i], rim_bot[j], rim_top[j]])
        )

    bm.faces.index_update()
    sector_face_index = {WHEEL_SEQUENCE[i]: top_faces_bm[i].index
                          for i in range(n)}
    side_face_indices = [f.index for f in side_faces_bm]

    bm.to_mesh(mesh)
    bm.free()

    obj.location.z = z_base

    # 3 Materialien: rot, schwarz, gruen
    red   = make_material("PocketRed",   (0.42, 0.02, 0.04, 1.0),
                          roughness=0.55, specular=0.4)
    black = make_material("PocketBlack", (0.025, 0.025, 0.03, 1.0),
                          roughness=0.6, specular=0.4)
    green = make_material("PocketGreen", (0.02, 0.32, 0.10, 1.0),
                          roughness=0.55, specular=0.4)
    silver = make_material("PocketDivider", (0.85, 0.85, 0.87, 1.0),
                           roughness=0.25, metallic=1.0)
    obj.data.materials.append(red)      # Slot 0
    obj.data.materials.append(black)    # Slot 1
    obj.data.materials.append(green)    # Slot 2
    obj.data.materials.append(silver)   # Slot 3

    color_to_slot = {"red": 0, "black": 1, "green": 2}
    for number, idx in sector_face_index.items():
        obj.data.polygons[idx].material_index = color_to_slot[color_for(number)]
    # Seitenflaechen (Mantel) silber
    for idx in side_face_indices:
        obj.data.polygons[idx].material_index = 3

    for poly in obj.data.polygons:
        poly.use_smooth = False        # harte Sektorenkanten - keine Smoothing

    return obj


# --------------------------------------------------------------------------- #
# Nummern als 3D-Text-Ring
# --------------------------------------------------------------------------- #

def _build_numbers(z_base):
    """Zahlen 0-36 in der Wheel-Sequenz, jeweils im Sektor-Mittelpunkt.

    Jede Zahl ist ein eigenes Text-Objekt (Curve) - so kann sie individuell
    rotiert werden (Tangential zur Wheel-Achse: jeder Text zeigt nach aussen).
    """
    n = 37
    sector_angle = 2 * math.pi / n
    angle_offset = math.pi / 2
    r_text = (NUMBERS_OUTER + NUMBERS_INNER) / 2

    text_objects = []
    for i, number in enumerate(WHEEL_SEQUENCE):
        a = angle_offset - i * sector_angle - sector_angle / 2

        curve = bpy.data.curves.new(f"Num{number}", type="FONT")
        curve.body = str(number)
        curve.size = 0.013
        curve.align_x = "CENTER"
        curve.align_y = "CENTER"
        curve.extrude = 0.0004

        obj = bpy.data.objects.new(f"Num_{number:02d}", curve)
        bpy.context.collection.objects.link(obj)
        obj.location = (r_text * math.cos(a), r_text * math.sin(a),
                        z_base + POCKET_DEPTH + 0.0005)
        # Text-Up zeigt zum Wheel-Center => Z-Rotation = a - pi/2
        obj.rotation_euler = (0, 0, a - math.pi / 2)
        text_objects.append(obj)

    mat = make_material("NumberWhite", (0.96, 0.96, 0.93, 1.0),
                        roughness=0.35, clearcoat=0.5)
    for o in text_objects:
        o.data.materials.append(mat)
    return text_objects


# --------------------------------------------------------------------------- #
# Aussenrand (Holz) + polierter Ring
# --------------------------------------------------------------------------- #

def _build_outer_rim():
    """Holzfarbener Outer-Rim mit poliertem Innen-Trennring."""
    rim = _ring("OuterRim", RIM_OUTER, RIM_INNER, RIM_HEIGHT)
    wood = make_material("Wood", (0.18, 0.07, 0.03, 1.0),
                         roughness=0.55, specular=0.4, clearcoat=0.6)
    rim.data.materials.append(wood)
    for poly in rim.data.polygons:
        poly.use_smooth = True

    # Schmaler chromfarbener Trennring innen am Pocket-Bereich
    chrome_ring = _ring("ChromeRing", RIM_INNER, POCKET_OUTER,
                        RIM_HEIGHT * 0.4)
    chrome = make_material("Chrome", (0.92, 0.92, 0.95, 1.0),
                           roughness=0.12, metallic=1.0)
    chrome_ring.data.materials.append(chrome)
    for poly in chrome_ring.data.polygons:
        poly.use_smooth = True

    return [rim, chrome_ring]


# --------------------------------------------------------------------------- #
# Center: Cone + Turret
# --------------------------------------------------------------------------- #

def _build_center(z_base):
    """Konische Mitte mit Turm - typischer Roulette-Center."""
    # Flacher Cone als breite Basis
    cone_mesh = bpy.data.meshes.new("CenterConeMesh")
    cone_obj  = bpy.data.objects.new("CenterCone", cone_mesh)
    bpy.context.collection.objects.link(cone_obj)
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm, cap_ends=True, cap_tris=False, segments=96,
        radius1=CENTER_RADIUS, radius2=TURRET_RADIUS * 1.2,
        depth=CENTER_HEIGHT,
    )
    bm.to_mesh(cone_mesh)
    bm.free()
    cone_obj.location.z = z_base + POCKET_DEPTH + CENTER_HEIGHT / 2

    # Turret: schmaler Cylinder oben drauf
    turret = _cylinder("Turret", TURRET_RADIUS, TURRET_HEIGHT, segments=64,
                       location=(0, 0,
                                 z_base + POCKET_DEPTH + CENTER_HEIGHT))
    # Spitzer Kegel als Topper
    topper_mesh = bpy.data.meshes.new("TopperMesh")
    topper_obj  = bpy.data.objects.new("Topper", topper_mesh)
    bpy.context.collection.objects.link(topper_obj)
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm, cap_ends=True, cap_tris=False, segments=64,
        radius1=TURRET_RADIUS, radius2=0.0, depth=0.012,
    )
    bm.to_mesh(topper_mesh)
    bm.free()
    topper_obj.location.z = (z_base + POCKET_DEPTH + CENTER_HEIGHT
                              + TURRET_HEIGHT + 0.006)

    gold  = make_material("CenterGold", (0.98, 0.78, 0.28, 1.0),
                          roughness=0.18, metallic=1.0)
    brass = make_material("CenterBrass", (0.85, 0.62, 0.20, 1.0),
                          roughness=0.30, metallic=1.0)
    cone_obj.data.materials.append(brass)
    turret.data.materials.append(gold)
    topper_obj.data.materials.append(gold)

    for o in (cone_obj, turret, topper_obj):
        for poly in o.data.polygons:
            poly.use_smooth = True
    return [cone_obj, turret, topper_obj]


# --------------------------------------------------------------------------- #
# Kugel
# --------------------------------------------------------------------------- #

def _build_ball(z_base):
    """Weisse Roulette-Kugel in Pocket BALL_POCKET."""
    n = 37
    sector_angle = 2 * math.pi / n
    angle_offset = math.pi / 2
    idx = WHEEL_SEQUENCE.index(BALL_POCKET)
    a = angle_offset - idx * sector_angle - sector_angle / 2

    # Pocket-Center: zwischen Outer-Pocket und Inner-Pocket-Edge
    r_pocket_center = (POCKET_OUTER + POCKET_INNER) / 2

    mesh = bpy.data.meshes.new("BallMesh")
    obj  = bpy.data.objects.new("Ball", mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(
        bm, u_segments=48, v_segments=24, radius=BALL_RADIUS,
    )
    bm.to_mesh(mesh)
    bm.free()
    obj.location = (r_pocket_center * math.cos(a),
                     r_pocket_center * math.sin(a),
                     z_base + POCKET_DEPTH + BALL_RADIUS)

    ivory = make_material("Ball", (0.95, 0.93, 0.86, 1.0),
                          roughness=0.20, clearcoat=0.7, specular=0.6)
    obj.data.materials.append(ivory)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


# --------------------------------------------------------------------------- #
# Szene
# --------------------------------------------------------------------------- #

def setup_camera_and_lights():
    target = bpy.data.objects.new("CamTarget", None)
    target.location = (0, 0, 0.020)
    bpy.context.collection.objects.link(target)

    cam_data = bpy.data.cameras.new("Cam")
    # 35mm Weitwinkel + groessere Distance: das volle Wheel (32cm Durchmesser)
    # passt ins Frame, der Center dominiert nicht mehr.
    cam_data.lens = 35
    cam = bpy.data.objects.new("Cam", cam_data)
    cam.location = (0.30, -0.38, 0.32)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam

    track = cam.constraints.new(type="TRACK_TO")
    track.target = target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"

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

    add_area("KeyTop",  60, (0.10, -0.10, 0.40), size=0.35,
             rot=(math.radians(20), math.radians(10), 0),
             color=(1.0, 0.96, 0.90))
    add_area("FillL",   15, (-0.25, -0.05, 0.20), size=0.30,
             color=(0.85, 0.92, 1.0))
    add_area("Rim",     30, (0.0, 0.30, 0.18), size=0.30,
             color=(1.0, 0.85, 0.65))
    add_area("BounceUp", 8, (0.0, 0.0, 0.12), size=0.50,
             color=(1.0, 1.0, 1.0))

    bpy.ops.mesh.primitive_plane_add(size=1.2, location=(0, 0, 0))
    plane = bpy.context.object
    plane.name = "Floor"
    plane.data.materials.append(
        make_material("Floor", (0.04, 0.18, 0.08, 1.0),
                      roughness=0.95, specular=0.1)
    )


def configure_eevee(filepath):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.eevee.taa_render_samples = 256
    scene.eevee.use_raytracing = True
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 1280
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(filepath)
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Very High Contrast"
    scene.view_settings.exposure = -0.2


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #

def main():
    print("=" * 60)
    print("Roulette-Rad (europaeisch, 37 Pockets)")
    print("=" * 60)

    clear_scene()

    z_pocket_base = 0
    outer = _build_outer_rim()
    pockets = _build_pocket_disc(z_pocket_base)
    numbers = _build_numbers(z_pocket_base)
    center = _build_center(z_pocket_base)
    ball = _build_ball(z_pocket_base)

    n_objs = len(outer) + 1 + len(numbers) + len(center) + 1
    n_verts = sum(len(o.data.vertices)
                  for o in bpy.data.objects
                  if o.type == "MESH")
    print(f"Objekte: {n_objs}, Mesh-Verts: {n_verts}")
    print(f"Kugel in Tasche: {BALL_POCKET}")

    setup_camera_and_lights()
    configure_world_background()
    configure_eevee(RENDER_PATH)

    print("Rendere ->", RENDER_PATH)
    bpy.ops.render.render(write_still=True)

    print("Speichere .blend ->", BLEND_PATH)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))

    print("Fertig.")


if __name__ == "__main__":
    main()
