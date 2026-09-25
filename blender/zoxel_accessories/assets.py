"""Meshes, materials and collections for the Zoxel avatar.

The avatar is made of boxes.  A box whose two ends have different half extents
is tapered, which is how the torso and the arms get their shape; see
:mod:`zoxel_accessories.body` for the numbers.
"""

import bpy
from mathutils import Matrix

RIG_COLLECTION = "ZoxelRig"
POOL_COLLECTION = "AccessoryPool"

#: Colours used only when a material of that name does not exist yet.  A
#: material already in the .blend is always reused untouched, so rebuilding the
#: rig never discards colours that were authored by hand.
DEFAULT_MATERIALS = {
    "MAT_Shirt": (0.04, 0.18, 0.18, 1.0),
    "MAT_Pants": (0.10, 0.10, 0.14, 1.0),
    "MAT_Skin": (0.72, 0.55, 0.38, 1.0),
    "MAT_Face": (0.05, 0.04, 0.04, 1.0),
    "MAT_Accessory": (0.55, 0.42, 0.12, 1.0),
}

#: Used for a material name that is not listed above.
FALLBACK_MATERIAL_COLOR = (0.8, 0.8, 0.8, 1.0)

#: Winding order of the six faces of a box built by :func:`box_mesh`, so the
#: normals point outwards.
_BOX_FACES = (
    (0, 3, 2, 1),   # -Z
    (4, 5, 6, 7),   # +Z
    (0, 1, 5, 4),   # -Y
    (1, 2, 6, 5),   # +X
    (2, 3, 7, 6),   # +Y
    (3, 0, 4, 7),   # -X
)


# --------------------------------------------------------------------------
# Collections and objects
# --------------------------------------------------------------------------

def get_collection(name, parent=None):
    """Return the collection ``name``, creating and linking it when missing."""
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(collection)
    return collection


def link(obj, collection):
    """Link ``obj`` into ``collection`` and return it."""
    collection.objects.link(obj)
    return obj


def move_to_collection(obj, collection):
    """Link ``obj`` into ``collection`` and unlink it from every other one."""
    for existing in list(obj.users_collection):
        if existing is not collection:
            existing.objects.unlink(obj)
    if obj not in collection.objects.values():
        collection.objects.link(obj)
    return obj


def remove_object(obj):
    """Delete ``obj`` from the file, and its mesh if nothing else uses it."""
    mesh = obj.data if obj.type == "MESH" else None
    bpy.data.objects.remove(obj, do_unlink=True)
    if mesh is not None and mesh.users == 0:
        bpy.data.meshes.remove(mesh)
    return None


def new_empty(name, location, display_size=0.06):
    """Create a plain-axes empty at ``location``, not yet linked."""
    empty = bpy.data.objects.new(name, None)
    empty.empty_display_type = "PLAIN_AXES"
    empty.empty_display_size = display_size
    empty.location = location
    return empty


def parent_with_keep_transform(obj, parent):
    """Parent ``obj`` to ``parent`` without moving it in world space.

    This is what a rig part wants: each one is authored at an absolute position,
    and parenting records the offset instead of snapping it to the parent.
    """
    obj.parent = parent
    obj.matrix_parent_inverse = parent.matrix_world.inverted()
    return obj


def parent_in_local_space(obj, parent):
    """Parent ``obj`` so its own transform is measured in ``parent``'s space.

    This is what an accessory visual wants: ``local_position``,
    ``local_rotation`` and ``local_scale`` are relative to the attach node the
    item hangs on, so the visual follows that part with no constraint.
    """
    obj.parent = parent
    obj.matrix_parent_inverse = Matrix.Identity(4)
    return obj


def unparent_preserving_transform(obj):
    """Detach ``obj`` from its parent without moving it in world space."""
    world = obj.matrix_world.copy()
    obj.parent = None
    obj.matrix_parent_inverse = Matrix.Identity(4)
    obj.matrix_world = world
    return obj


def set_hidden(obj, hidden=True):
    """Hide or show ``obj`` in both the viewport and renders."""
    obj.hide_viewport = hidden
    obj.hide_render = hidden
    obj.hide_set(hidden)
    return obj


# --------------------------------------------------------------------------
# Materials
# --------------------------------------------------------------------------

def get_material(name):
    """Return the material ``name``, creating it from :data:`DEFAULT_MATERIALS`.

    An existing material is returned as-is, so the colours already in a .blend
    survive a rebuild of the rig.
    """
    material = bpy.data.materials.get(name)
    if material is not None:
        return material

    color = DEFAULT_MATERIALS.get(name, FALLBACK_MATERIAL_COLOR)
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    node = principled_node(material)
    if node is not None:
        node.inputs["Base Color"].default_value = color
    return material


def principled_node(material):
    """The Principled BSDF node of ``material``, or ``None`` if it has none."""
    if not material.use_nodes or material.node_tree is None:
        return None
    for node in material.node_tree.nodes:
        if node.type == "BSDF_PRINCIPLED":
            return node
    return None


# --------------------------------------------------------------------------
# Meshes
# --------------------------------------------------------------------------

def box_mesh(name, half_bottom, half_top, z_bottom, z_top, centre_bottom=(0.0, 0.0),
             centre_top=(0.0, 0.0)):
    """Build a box mesh whose two ends differ in size, and can be offset.

    ``half_bottom`` and ``half_top`` are ``(x, y)`` half extents, applied at
    ``z_bottom`` and ``z_top`` respectively, so passing the same pair twice
    gives a plain box.  ``centre_bottom`` and ``centre_top`` slide each face in X
    and Y, so the two ends can sit offset from one another: that is what leans a
    box over instead of keeping it upright.
    """
    bx, by = half_bottom
    bcx, bcy = centre_bottom
    tx, ty = half_top
    tcx, tcy = centre_top
    verts = [
        (bcx - bx, bcy - by, z_bottom),
        (bcx + bx, bcy - by, z_bottom),
        (bcx + bx, bcy + by, z_bottom),
        (bcx - bx, bcy + by, z_bottom),
        (tcx - tx, tcy - ty, z_top),
        (tcx + tx, tcy - ty, z_top),
        (tcx + tx, tcy + ty, z_top),
        (tcx - tx, tcy + ty, z_top),
    ]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], _BOX_FACES)
    mesh.update()
    return mesh


def tapered_box_mesh(name, half_bottom, half_top, height, direction=1, lean=(0.0, 0.0)):
    """Build a box mesh that runs from the origin out to its far end.

    With ``direction`` +1 the mesh occupies ``0..height`` in local Z, so the
    object's origin is the part's bottom; with -1 it occupies ``-height..0``, so
    the origin is the part's top.  ``half_bottom`` is the geometric bottom in
    both cases.

    ``lean`` slides the far end - the end away from the origin - in X and Y, so a
    limb can be angled away from the joint it hangs on.
    """
    if direction > 0:
        z_bottom, z_top = 0.0, float(height)
        centre_bottom, centre_top = (0.0, 0.0), lean
    else:
        z_bottom, z_top = -float(height), 0.0
        centre_bottom, centre_top = lean, (0.0, 0.0)
    return box_mesh(name, half_bottom, half_top, z_bottom, z_top, centre_bottom, centre_top)


def unit_box_mesh(name="AccessoryBox"):
    """A 1x1x1 box centred on the origin.

    There are no accessory meshes in the project yet, so an equipped visual is
    this box scaled by the item's ``local_scale``.
    """
    return box_mesh(name, (0.5, 0.5), (0.5, 0.5), -0.5, 0.5)
