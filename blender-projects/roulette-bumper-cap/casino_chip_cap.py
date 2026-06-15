"""
Casino-Chip-Bumper-Cap fuer Roulette-Tisch (VPX).

Headless-Workflow mit Blender 4.5 LTS. Refactored fuer Wiederverwendung:
der eigentliche Chip-Build steckt in build_chip(spec) - so kann
chip_set.py daraus 6 Chips in einer Szene bauen.

Aufruf:
    BLENDER=/home/thomas/Applications/pinball/blender/blender
    $BLENDER --background --python casino_chip_cap.py
"""

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple

import bpy
import bmesh
from mathutils import Vector


# --------------------------------------------------------------------------- #
# Geometrie-Konstanten - alle Masse in Metern.
# --------------------------------------------------------------------------- #

CAP_RADIUS       = 0.025
CAP_HEIGHT       = 0.012
SEGMENTS         = 128
EDGE_BEVEL_WIDTH = 0.0015
DOME_RISE        = 0.0020

INLAY_RADIUS = 0.017
INLAY_HEIGHT = 0.0008

# Goldener Aussen-Reifen (Mittelband)
BAND_HEIGHT  = 0.0022          # 2.2 mm dick
BAND_GROW    = 0.0010          # 1 mm Ueberstand - deutlich sichtbarer Reifen

# Edge-Spots
EDGE_SPOTS         = 8
EDGE_SPOT_WIDTH    = math.radians(12)
EDGE_SPOT_DEPTH    = 0.0005

# Konzentrische Top-Rillen
TOP_GROOVE_COUNT   = 4
TOP_GROOVE_INNER   = 0.0195    # gleich aussen vom Inlay
TOP_GROOVE_OUTER   = 0.0235    # gleich innen von der Aussenkante

HERE = Path(__file__).parent


# --------------------------------------------------------------------------- #
# ChipSpec - Farb-/Wert-Konfiguration
# --------------------------------------------------------------------------- #

RGBA = Tuple[float, float, float, float]


@dataclass
class ChipSpec:
    """Beschreibt einen Chip-Typ. Geometrie ist fuer alle gleich, nur Farben
    und der aufgedruckte Wert wechseln."""
    name:        str
    body_color:  RGBA
    edge_color:  RGBA = (0.92, 0.92, 0.90, 1.0)
    inlay_color: RGBA = (0.98, 0.97, 0.94, 1.0)
    band_color:  RGBA = (1.00, 0.78, 0.30, 1.0)
    text:        str  = "17"
    text_color:  RGBA = (0.05, 0.05, 0.06, 1.0)


# Klassische Roulette-Setzfarben (entspricht echten Casino-Werten)
ROULETTE_CHIPS = [
    ChipSpec("white",  body_color=(0.92, 0.92, 0.91, 1.0),
             text="1",   text_color=(0.05, 0.05, 0.06, 1.0)),
    ChipSpec("red",    body_color=(0.55, 0.04, 0.08, 1.0),
             text="5",   text_color=(0.98, 0.97, 0.94, 1.0)),
    ChipSpec("blue",   body_color=(0.04, 0.12, 0.45, 1.0),
             text="10",  text_color=(0.98, 0.97, 0.94, 1.0)),
    ChipSpec("green",  body_color=(0.04, 0.30, 0.12, 1.0),
             text="25",  text_color=(0.98, 0.97, 0.94, 1.0)),
    ChipSpec("black",  body_color=(0.03, 0.03, 0.04, 1.0),
             text="100", text_color=(1.00, 0.78, 0.20, 1.0),
             inlay_color=(0.18, 0.18, 0.20, 1.0)),
    ChipSpec("purple", body_color=(0.22, 0.05, 0.35, 1.0),
             text="500", text_color=(1.00, 0.78, 0.20, 1.0)),
]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for coll in (bpy.data.meshes, bpy.data.materials,
                 bpy.data.lights, bpy.data.cameras, bpy.data.curves):
        for item in list(coll):
            coll.remove(item)


def make_material(name, base_color, roughness=0.35, metallic=0.0,
                  clearcoat=0.0, specular=0.5):
    """Principled BSDF.

    - clearcoat:  zusaetzliche Lack-Schicht (0..1) - macht Plastik premium
    - specular:   Glanz-Staerke der Nicht-Metall-Reflexion
    """
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = base_color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    # Coat-Inputs heissen in Blender 4.x leicht anders je nach Version
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = clearcoat
        bsdf.inputs["Coat Roughness"].default_value = 0.05
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = specular
    return mat


# --------------------------------------------------------------------------- #
# Chip-Body mit Edge-Spots
# --------------------------------------------------------------------------- #

def _build_body_mesh(name):
    mesh = bpy.data.meshes.new(name + "Mesh")
    obj  = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm, cap_ends=True, cap_tris=False, segments=SEGMENTS,
        radius1=CAP_RADIUS, radius2=CAP_RADIUS, depth=CAP_HEIGHT,
    )
    bm.to_mesh(mesh)
    bm.free()
    obj.location.z = CAP_HEIGHT / 2
    return obj


def _dome_top(obj):
    """Sanfte Wölbung der Oberseite."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    top_face = max(bm.faces, key=lambda f: f.calc_center_median().z)
    bmesh.ops.inset_individual(bm, faces=[top_face], thickness=0.003)
    for v in bm.verts:
        if v.co.z > CAP_HEIGHT / 2 - 1e-5:
            r = math.hypot(v.co.x, v.co.y)
            if r < CAP_RADIUS:
                v.co.z += DOME_RISE * math.cos(r / CAP_RADIUS * math.pi / 2)
    bm.to_mesh(obj.data)
    bm.free()


def _carve_edge_spots(obj):
    """Druckt 8 weisse Edge-Marker in die Aussenkante."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    spot_centers = [2 * math.pi * i / EDGE_SPOTS for i in range(EDGE_SPOTS)]
    marker_idx = []
    for face in bm.faces:
        if abs(face.normal.z) > 0.3:
            continue
        c = face.calc_center_median()
        angle = math.atan2(c.y, c.x)
        for spot in spot_centers:
            diff = math.atan2(math.sin(angle - spot), math.cos(angle - spot))
            if abs(diff) < EDGE_SPOT_WIDTH / 2:
                inward = -face.normal * EDGE_SPOT_DEPTH
                for v in face.verts:
                    v.co += inward
                marker_idx.append(face.index)
                break
    bm.to_mesh(obj.data)
    bm.free()
    obj["marker_idx"] = marker_idx


def _carve_top_grooves(obj):
    """Konzentrische Vertiefungen auf der Oberseite (Guillochée-Look).

    Wir nutzen Loop-Subdivides der Top-Face und ziehen einzelne Vert-Ringe
    abwechselnd leicht nach unten. So entstehen feine Stufen-Rillen.
    """
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()

    z_top = max(v.co.z for v in bm.verts)
    # Top-Vertices sortiert nach Radius - jeder Kreis-Segment-Vert auf gleicher
    # Hoehe gehoert zu einem Ring.
    top_verts = [v for v in bm.verts if v.co.z > z_top - DOME_RISE - 1e-3]

    # Wir koennen hier keinen Loop-Cut machen, weil wir nur die n-gon Top haben.
    # Stattdessen: alle Top-Verts in Radius-Buckets gruppieren, jeden zweiten
    # Bucket abgesenkt - das gibt die Stufen-Optik.
    # In unserer Geometrie gibt es eh nur 2 Radius-Ringe (Aussen-Ring + Inset-
    # Ring) - das reicht fuer EINE Stufe. Mehr Rillen brauchten echte Loops.
    # Wir machen daher: den inneren Inset-Vert-Ring leicht absenken.
    if top_verts:
        rs = [math.hypot(v.co.x, v.co.y) for v in top_verts]
        rmax = max(rs)
        inner_verts = [v for v, r in zip(top_verts, rs) if r < rmax * 0.97]
        for v in inner_verts:
            v.co.z -= 0.00025      # 0.25 mm Stufe

    bm.to_mesh(obj.data)
    bm.free()


def _assign_body_materials(obj, spec: ChipSpec):
    body  = make_material(f"Body_{spec.name}",  spec.body_color,
                          roughness=0.25, clearcoat=0.7, specular=0.6)
    edge  = make_material(f"Edge_{spec.name}",  spec.edge_color,
                          roughness=0.35, clearcoat=0.5)
    obj.data.materials.append(body)
    obj.data.materials.append(edge)
    marker_idx = set(obj.get("marker_idx", []))
    for poly in obj.data.polygons:
        poly.material_index = 1 if poly.index in marker_idx else 0


def _add_bevel(obj):
    bevel = obj.modifiers.new("EdgeBevel", "BEVEL")
    bevel.width = EDGE_BEVEL_WIDTH
    bevel.segments = 4
    bevel.limit_method = "ANGLE"
    bevel.angle_limit = math.radians(30)
    for poly in obj.data.polygons:
        poly.use_smooth = True


# --------------------------------------------------------------------------- #
# Gold-Band (Aussenring um den Body)
# --------------------------------------------------------------------------- #

def _build_band(name_suffix, spec: ChipSpec, parent_location):
    """Schmaler goldener Ring auf halber Chip-Hoehe - Premium-Detail."""
    mesh = bpy.data.meshes.new(f"Band{name_suffix}")
    obj  = bpy.data.objects.new(f"Band_{spec.name}", mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm, cap_ends=True, cap_tris=False, segments=SEGMENTS,
        radius1=CAP_RADIUS + BAND_GROW,
        radius2=CAP_RADIUS + BAND_GROW,
        depth=BAND_HEIGHT,
    )
    bm.to_mesh(mesh)
    bm.free()
    obj.location = parent_location.copy()
    # Auf halber Chip-Hoehe zentriert (Mitte des Bodys liegt bei CAP_HEIGHT/2,
    # parent_location.z bringt uns dorthin)
    mat = make_material(f"Gold_{spec.name}", spec.band_color,
                        roughness=0.18, metallic=1.0)
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    # Bevel fuer weiche Kanten
    bevel = obj.modifiers.new("BandBevel", "BEVEL")
    bevel.width = 0.0003
    bevel.segments = 3
    return obj


# --------------------------------------------------------------------------- #
# Inlay (helle Druckscheibe in der Mitte)
# --------------------------------------------------------------------------- #

def _build_inlay(spec: ChipSpec, parent_location):
    mesh = bpy.data.meshes.new(f"Inlay_{spec.name}")
    obj  = bpy.data.objects.new(f"Inlay_{spec.name}", mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm, cap_ends=True, cap_tris=False, segments=96,
        radius1=INLAY_RADIUS, radius2=INLAY_RADIUS, depth=INLAY_HEIGHT,
    )
    bm.to_mesh(mesh)
    bm.free()
    # parent_location ist der Origin am Boden des Chips. Body geht von z=0
    # bis z=CAP_HEIGHT, plus Dome-Rise in der Mitte. Inlay sitzt darauf.
    obj.location = parent_location.copy()
    obj.location.z += CAP_HEIGHT + DOME_RISE + INLAY_HEIGHT / 2
    mat = make_material(f"Inlay_{spec.name}", spec.inlay_color,
                        roughness=0.30, clearcoat=0.9, specular=0.7)
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    # Subtiler Bevel an der Inlay-Kante
    bevel = obj.modifiers.new("InlayBevel", "BEVEL")
    bevel.width = 0.0005
    bevel.segments = 3
    return obj


# --------------------------------------------------------------------------- #
# Wert-Text (extrudierte 3D-Zahl)
# --------------------------------------------------------------------------- #

def _build_text(spec: ChipSpec, parent_location):
    """3D-Text aus einer Curve, extrudiert, zentriert auf Inlay.

    Blender hat eingebauten Font-Support ueber bpy.data.curves vom Typ 'FONT'.
    Default-Font ist Bfont (gebuendelt mit Blender) - keine externe Datei noetig.
    """
    curve = bpy.data.curves.new(f"Text_{spec.name}", type="FONT")
    curve.body = spec.text
    curve.size = 0.014                # Schrifthoehe ~14mm
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.extrude = 0.0006             # 0.6mm 3D-Tiefe
    curve.bevel_depth = 0.00015        # winzige Fasung an Text-Kanten

    obj = bpy.data.objects.new(f"Text_{spec.name}", curve)
    bpy.context.collection.objects.link(obj)
    obj.location = parent_location.copy()
    # Text auf Inlay-Oberseite (= Body-Top + Dome + Inlay-Hoehe), plus halbe
    # Extrude-Tiefe um den Text in seiner Mitte zu platzieren, plus 0.1mm
    # Anti-Z-Fight-Offset
    obj.location.z += (CAP_HEIGHT + DOME_RISE + INLAY_HEIGHT
                       + curve.extrude / 2 + 0.0001)

    mat = make_material(f"Text_{spec.name}", spec.text_color,
                        roughness=0.22, metallic=0.0, clearcoat=0.8)
    obj.data.materials.append(mat)
    return obj


# --------------------------------------------------------------------------- #
# Oeffentliche Build-Funktion
# --------------------------------------------------------------------------- #

def build_chip(spec: ChipSpec, location=(0, 0, 0)):
    """Baut einen kompletten Chip an der angegebenen Position.

    Returns: list of all created objects (body, band, inlay, text)
    """
    loc = Vector(location)

    body = _build_body_mesh(f"Body_{spec.name}")
    body.location = loc + Vector((0, 0, CAP_HEIGHT / 2))
    _dome_top(body)
    _carve_edge_spots(body)
    _carve_top_grooves(body)
    _assign_body_materials(body, spec)
    _add_bevel(body)

    # Band-Position = Body-Position (zentriert um halbe Hoehe)
    band_loc = loc + Vector((0, 0, CAP_HEIGHT / 2))
    band = _build_band(spec.name, spec, band_loc)

    inlay = _build_inlay(spec, loc)
    text  = _build_text(spec, loc)

    return [body, band, inlay, text]


# --------------------------------------------------------------------------- #
# Szene (Studio-Setup)
# --------------------------------------------------------------------------- #

def setup_camera_and_lights(target_pos=(0, 0, 0.008)):
    target = bpy.data.objects.new("CamTarget", None)
    target.location = target_pos
    bpy.context.collection.objects.link(target)

    cam_data = bpy.data.cameras.new("Cam")
    cam_data.lens = 90
    cam = bpy.data.objects.new("Cam", cam_data)
    # Hoeher fuer mehr Top-Down-Sicht: 18cm hoch bei 18cm Distance = ~45 Grad
    cam.location = (0.14, -0.18, 0.18)
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

    # Studio-Setup: grosse Soft-Box als Hauptlicht, kuehle Fill von links,
    # warmer Rim aus Hintergrund, Backdrop-Bouncer von oben.
    add_area("KeyBox",  6.0, ( 0.20, -0.15, 0.25), size=0.20,
             rot=(math.radians(45), math.radians(15), 0),
             color=(1.0, 0.96, 0.90))
    add_area("FillBox", 2.0, (-0.18, -0.05, 0.18), size=0.25,
             color=(0.85, 0.92, 1.0))
    add_area("RimBox",  4.0, ( 0.05,  0.18, 0.12), size=0.15,
             color=(1.0, 0.85, 0.70))
    add_area("Top",     1.5, ( 0.00,  0.00, 0.30), size=0.40,
             color=(1.0, 1.0, 1.0))

    # Casino-Felt-Boden mit leichter Stoff-Rauheit
    bpy.ops.mesh.primitive_plane_add(size=0.8, location=(0, 0, 0))
    plane = bpy.context.object
    plane.name = "Floor"
    floor_mat = make_material("Floor", (0.04, 0.18, 0.08, 1.0),
                              roughness=0.95, specular=0.1)
    plane.data.materials.append(floor_mat)


def configure_world_background():
    """Subtle Gradient als Welt-Hintergrund - vermeidet sterilen Schwarz-/
    Einfarbig-Look und gibt schoene Spiegelungen am Goldring."""
    scene = bpy.context.scene
    world = scene.world
    world.use_nodes = True
    nt = world.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)

    bg     = nt.nodes.new("ShaderNodeBackground")
    grad   = nt.nodes.new("ShaderNodeTexGradient")
    mapp   = nt.nodes.new("ShaderNodeMapping")
    coord  = nt.nodes.new("ShaderNodeTexCoord")
    ramp   = nt.nodes.new("ShaderNodeValToRGB")
    output = nt.nodes.new("ShaderNodeOutputWorld")

    grad.gradient_type = "EASING"
    # Color-Ramp: oben dunkles Petrol, unten warmes Braun
    ramp.color_ramp.elements[0].color = (0.025, 0.04, 0.06, 1.0)
    ramp.color_ramp.elements[1].color = (0.10,  0.07, 0.04, 1.0)

    nt.links.new(coord.outputs["Generated"], mapp.inputs["Vector"])
    nt.links.new(mapp.outputs["Vector"],     grad.inputs["Vector"])
    nt.links.new(grad.outputs["Fac"],        ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"],      bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"],   output.inputs["Surface"])


def configure_render(filepath, samples=192, resolution=1024):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(filepath)
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"


# --------------------------------------------------------------------------- #
# Export
# --------------------------------------------------------------------------- #

def export_obj(objects, filepath):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        # Text-Objekte (Curve) muessen vor dem OBJ-Export konvertiert sein.
        # apply_modifiers=True erledigt das nicht fuer Curves, also explicit.
        if obj.type == "FONT":
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.convert(target="MESH")
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.wm.obj_export(
        filepath=str(filepath),
        export_selected_objects=True,
        apply_modifiers=True,
        export_materials=True,
        forward_axis="Y", up_axis="Z",
    )


# --------------------------------------------------------------------------- #
# Pipeline fuer Einzel-Chip
# --------------------------------------------------------------------------- #

def main():
    print("=" * 60)
    print("Casino-Chip-Bumper-Cap (edle Variante)")
    print("=" * 60)

    clear_scene()

    # Bond-Spec: rot mit 17 (James Bonds Glückszahl bei Roulette)
    spec = ChipSpec(
        name="bond",
        body_color=(0.55, 0.04, 0.08, 1.0),
        text="17",
        text_color=(1.00, 0.78, 0.20, 1.0),  # Gold
    )

    objects = build_chip(spec)
    setup_camera_and_lights()
    configure_world_background()

    render_path = HERE / "renders" / "chip_preview.png"
    configure_render(render_path)

    total_verts = sum(len(o.data.vertices) for o in objects if hasattr(o.data, "vertices"))
    print(f"Objekte: {[o.name for o in objects]}")
    print(f"Verts gesamt: {total_verts}")

    print("Rendere ->", render_path)
    bpy.ops.render.render(write_still=True)

    obj_path = HERE / "exports" / "chip.obj"
    print("Exportiere OBJ ->", obj_path)
    export_obj(objects, obj_path)

    blend_path = HERE / "exports" / "chip.blend"
    print("Speichere .blend ->", blend_path)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    print("Fertig.")


if __name__ == "__main__":
    main()
