"""The base avatar rig: body parts, their pivots, and the attach nodes.

``build_avatar()`` is the entry point.  It rebuilds the whole rig from the
tables in :mod:`zoxel_accessories.body`, so the avatar is always generated from
code instead of being repaired by hand.

Every part's origin sits on its joint rather than at its centre - the torso at
the hips, the arms at the shoulders, the legs at the hips, the hands at the
wrists - so rotating a part swings it the way an animator expects.
"""

import bpy

from . import assets, body
from .body import BUILD_ORDER

#: The rig's root empty.  Every part is a descendant of it.
RIG_ROOT = "CHAR_Root"


def rig_root():
    """The rig's root empty, or ``None`` when the file has no rig."""
    root = bpy.data.objects.get(RIG_ROOT)
    if root is None or root.type != "EMPTY":
        return None
    return root


def part_object(name):
    """The rig object called ``name``, or ``None``."""
    return bpy.data.objects.get(name)


def attach_node(name):
    """The attach empty called ``name``, or ``None`` when it is not an empty."""
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "EMPTY":
        return None
    return obj


def attach_world_location(attach):
    """World position of an attach node: its anchor part's pivot plus ``offset``.

    The rig checks in ``blender/tests/test_proportions.py`` compare this with
    where :func:`_parent_attach` actually puts the empty.
    """
    anchor = body.part(attach.parent)
    return tuple(pivot + offset for pivot, offset in zip(anchor.pivot, attach.offset))


def build_avatar():
    """Rebuild the whole avatar from :mod:`zoxel_accessories.body`.

    Any existing rig is removed first, so this is safe to run repeatedly and is
    how a change to the proportions is picked up.  Accessories are not carried
    over: the visuals hang off attach nodes that are recreated here.

    Returns the root object.
    """
    remove_rig()

    collection = assets.get_collection(assets.RIG_COLLECTION)
    root = assets.link(
        assets.new_empty(RIG_ROOT, (0.0, 0.0, 0.0), display_size=0.12), collection
    )

    parts = {RIG_ROOT: root}
    for name in BUILD_ORDER:
        if name == RIG_ROOT:
            continue
        parts[name] = _build_part(body.part(name), collection)

    # Parenting reads world matrices, and setting an object's location does not
    # refresh them on its own.
    bpy.context.view_layer.update()
    _parent_parts(parts)
    for attach in body.ATTACHES:
        _parent_attach(attach, parts)

    bpy.context.view_layer.update()
    return root


def ensure_attach(root=None):
    """Add back any attach node that is missing from the rig.

    Returns the names of the nodes it created.  Raises ``RuntimeError`` when the
    file has no rig, or when an anchor part is missing too - in that case
    ``build_avatar()`` is what is needed, not a repair.
    """
    root = root or rig_root()
    if root is None:
        raise RuntimeError("no rig in the file: run build_avatar() first")

    missing = [a for a in body.ATTACHES if attach_node(a.name) is None]
    absent = sorted({a.parent for a in missing if part_object(a.parent) is None})
    if absent:
        raise RuntimeError(
            "cannot attach to missing rig part(s): {0} - run build_avatar()".format(
                ", ".join(absent)
            )
        )
    if not missing:
        return ()

    bpy.context.view_layer.update()
    for attach in missing:
        _parent_attach(attach, None)
    bpy.context.view_layer.update()
    return tuple(a.name for a in missing)


def remove_rig():
    """Delete the rig root, every part under it, and any pooled accessory visual.

    ``build_avatar()`` owns the names in :mod:`zoxel_accessories.body`, so an
    object holding one of those names is removed here even if it has lost its
    parent.
    """
    for name in body.part_names() + body.attach_names():
        obj = bpy.data.objects.get(name)
        if obj is not None:
            assets.remove_object(obj)

    root = rig_root()
    if root is not None:
        for obj in _descendants(root):
            assets.remove_object(obj)

    pool = bpy.data.collections.get(assets.POOL_COLLECTION)
    if pool is not None:
        for obj in list(pool.objects):
            assets.remove_object(obj)
    bpy.context.view_layer.update()


# --------------------------------------------------------------------------
# Internals
# --------------------------------------------------------------------------

def _build_part(part, collection):
    """Create ``part`` as a mesh object at its pivot, not yet parented."""
    mesh = assets.tapered_box_mesh(
        part.name,
        part.half_bottom,
        part.half_top,
        part.height,
        part.direction,
        part.lean,
    )
    obj = assets.link(bpy.data.objects.new(part.name, mesh), collection)
    obj.location = part.pivot
    obj.data.materials.append(assets.get_material(part.material))
    return obj


def _parent_parts(parts):
    """Parent every part to the part named by its table entry, without moving it."""
    for name in BUILD_ORDER:
        if name == RIG_ROOT:
            continue
        assets.parent_with_keep_transform(parts[name], parts[body.part(name).parent])


def _parent_attach(attach, parts):
    """Create ``attach`` as an empty welded to its anchor part.

    ``parts`` is the object table from a build in progress; when it is ``None``
    the anchor is looked up in the file instead.
    """
    parent = parts[attach.parent] if parts else part_object(attach.parent)
    collection = _collection_of(parent)
    empty = assets.link(
        assets.new_empty(attach.name, attach_world_location(attach)), collection
    )
    return assets.parent_with_keep_transform(empty, parent)


def _collection_of(obj):
    """The first collection ``obj`` is linked to, or the rig collection."""
    if obj.users_collection:
        return obj.users_collection[0]
    return assets.get_collection(assets.RIG_COLLECTION)


def _descendants(obj):
    """``obj`` and everything parented under it, deepest first."""
    found = []
    for child in obj.children:
        found.extend(_descendants(child))
    found.append(obj)
    return found
