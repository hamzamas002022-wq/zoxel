"""Zoxel avatar accessories.

Importing this package registers a **Zoxel** tab in the 3D viewport sidebar and
exposes the API the tab drives::

    import sys
    sys.path.append(r"<repo>\\blender")
    import zoxel_accessories as accessories

    accessories.build_avatar()
    accessories.register_item(my_item)
    accessories.equip(accessories.SLOT_HAND, my_item.id)
    accessories.get_equipped()

See ``blender/README.md`` for the slot table and how to add an item.
"""

from . import assets, body, ops, registry, rig, slots
from . import equip as _equip_module
from .item_def import ItemDef
from .registry import all_items, get_item, items_for_slot, register_item
from .slots import SLOT_BACK, SLOT_HAND, SLOTS

#: Rebuild the rig, and repair missing attach nodes on the rig that is there.
build_avatar = rig.build_avatar
ensure_attach = rig.ensure_attach

#: Wear an item, take it off, and see what is worn.
equip = _equip_module.equip
unequip = _equip_module.unequip
get_equipped = _equip_module.get_equipped

#: Register or unregister the sidebar panel.
register = ops.register
unregister = ops.unregister

__all__ = [
    "SLOT_BACK",
    "SLOT_HAND",
    "SLOTS",
    "ItemDef",
    "register_item",
    "get_item",
    "all_items",
    "items_for_slot",
    "build_avatar",
    "ensure_attach",
    "equip",
    "unequip",
    "get_equipped",
    "register",
    "unregister",
    "reload",
    "assets",
    "body",
    "registry",
    "rig",
    "slots",
]


def reload():
    """Re-import this package so edits to its modules take effect.

    Blender keeps imported modules alive for the whole session, so after editing
    a file in this package a running Blender is still executing the old code.
    This replaces the package and re-registers the panel against the new one.

    Returns the freshly imported package.
    """
    import importlib
    import sys

    unregister()
    for name in list(sys.modules):
        if name == __name__ or name.startswith(__name__ + "."):
            del sys.modules[name]
    return importlib.import_module(__name__)


# Importing the package is what puts the panel in the sidebar.
register()
