"""Equip and unequip accessory items on the avatar.

The ``.blend`` is the state of the system.  An equipped item is a visual object
parented to its slot's attach node, and the item id is written into the rig
root's custom properties (``equipped_Back``, ``equipped_Hand``).  Nothing is
cached in Python, so the file and the API cannot drift apart.
"""

import bpy
from mathutils import Euler

from . import assets, registry, rig, slots

#: Material given to the stand-in box that draws an item until real accessory
#: meshes exist.
VISUAL_MATERIAL = "MAT_Accessory"


def equipped_property(slot):
    """Name of the rig root property that records ``slot``'s item id."""
    return "equipped_{0}".format(slot)


def get_equipped():
    """``{slot: item id}`` for every occupied slot, read from the rig root."""
    root = rig.rig_root()
    if root is None:
        return {}
    equipped = {}
    for slot in slots.SLOTS:
        item_id = root.get(equipped_property(slot))
        if item_id:
            equipped[slot] = item_id
    return equipped


def equipped_item(slot):
    """The item worn in ``slot``, or ``None`` when the slot is empty."""
    item_id = get_equipped().get(slot)
    if item_id is None:
        return None
    return registry.get_item(item_id)


def equip(slot, item_id):
    """Wear the registered item ``item_id`` in ``slot``.

    Whatever is already in the slot is unequipped first.  Returns the visual
    object.  Raises ``KeyError`` for an unknown slot or an unregistered item,
    and ``ValueError`` when the item belongs in a different slot.
    """
    if not slots.is_slot(slot):
        raise KeyError("unknown accessory slot: {0!r}".format(slot))

    item = registry.get_item(item_id)
    if item is None:
        raise KeyError("no such registered item: {0!r}".format(item_id))
    if item.slot != slot:
        raise ValueError(
            "item {0!r} belongs in slot {1!r}, not {2!r}".format(item.id, item.slot, slot)
        )

    rig.ensure_attach()
    attach_name = slots.attach_name_for(slot)
    node = rig.attach_node(attach_name)
    if node is None:
        raise RuntimeError("rig has no {0} node: run build_avatar()".format(attach_name))
    root = rig.rig_root()
    if root is None:
        raise RuntimeError("no rig in the file: run build_avatar() first")

    worn = worn_visual(node)
    if worn is not None and worn.name == item.visual_name:
        return worn

    unequip(slot)
    visual = _obtain_visual(item)
    assets.move_to_collection(visual, assets.get_collection(assets.RIG_COLLECTION))
    assets.parent_in_local_space(visual, node)
    visual.location = item.local_position
    visual.rotation_euler = Euler(item.local_rotation)
    visual.scale = item.local_scale
    assets.set_hidden(visual, False)

    root[equipped_property(slot)] = item.id
    return visual


def unequip(slot):
    """Take off whatever is worn in ``slot``.  True when something came off."""
    if not slots.is_slot(slot):
        raise KeyError("unknown accessory slot: {0!r}".format(slot))

    removed = False
    node = rig.attach_node(slots.attach_name_for(slot))
    if node is not None:
        worn = worn_visual(node)
        if worn is not None:
            pool_visual(worn)
            removed = True

    root = rig.rig_root()
    if root is not None and root.get(equipped_property(slot)):
        del root[equipped_property(slot)]
        removed = True
    return removed


def worn_visual(node):
    """The mesh parented to the attach node ``node``, or ``None``."""
    for child in node.children:
        if child.type == "MESH":
            return child
    return None


def pool_visual(visual):
    """Park ``visual`` in the pool collection, unparented and hidden."""
    assets.unparent_preserving_transform(visual)
    assets.move_to_collection(visual, assets.get_collection(assets.POOL_COLLECTION))
    assets.set_hidden(visual, True)
    return visual


# --------------------------------------------------------------------------
# Internals
# --------------------------------------------------------------------------

def _obtain_visual(item):
    """The pooled visual already built for ``item``, or a freshly built one."""
    existing = bpy.data.objects.get(item.visual_name)
    if existing is not None and existing.type == "MESH":
        return existing

    visual = bpy.data.objects.new(item.visual_name, assets.unit_box_mesh(item.visual_name))
    visual.data.materials.append(assets.get_material(VISUAL_MATERIAL))
    return assets.link(visual, assets.get_collection(assets.POOL_COLLECTION))
