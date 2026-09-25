"""Operators and the sidebar panel.

``register()`` puts a **Zoxel** tab in the 3D viewport sidebar (``N``), which
drives the same API as the Python console: build the rig, pick an item per slot,
equip it, take it off again.
"""

import bpy

from . import body, equip, registry, rig, slots

#: bl_idname of the sidebar panel, used to tell whether the addon is registered.
PANEL_IDNAME = "ZOXEL_PT_accessories"


def _slot_enum():
    """Enum items for a slot property, one entry per slot."""
    return [(slot, slot, "Slot {0}".format(slot)) for slot in slots.SLOTS]


def _item_enum(self, _context):
    """Enum items for an item property: whatever is registered for ``self.slot``."""
    registered = registry.items_for_slot(getattr(self, "slot", slots.SLOTS[0]))
    if not registered:
        return [("", "nothing registered", "Register an ItemDef first")]
    return [(item.id, item.id, "{0} ({1})".format(item.id, item.mesh)) for item in registered]


class ZOXEL_OT_build_avatar(bpy.types.Operator):
    """Rebuild the avatar rig from the proportions table."""

    bl_idname = "zoxel.build_avatar"
    bl_label = "Build Avatar"
    bl_description = "Rebuild the rig, the hand blocks and the attach nodes"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, _context):
        rig.build_avatar()
        self.report(
            {"INFO"},
            "Zoxel avatar rebuilt: {0} parts".format(len(body.part_names())),
        )
        return {"FINISHED"}


class ZOXEL_OT_equip(bpy.types.Operator):
    """Wear a registered item in a slot."""

    bl_idname = "zoxel.equip"
    bl_label = "Equip"
    bl_description = "Wear this item in the slot"
    bl_options = {"REGISTER", "UNDO"}

    slot: bpy.props.EnumProperty(name="Slot", items=_slot_enum())
    item: bpy.props.EnumProperty(name="Item", items=_item_enum)

    def execute(self, _context):
        try:
            equip.equip(self.slot, self.item)
        except (KeyError, ValueError, RuntimeError) as error:
            # Reported rather than raised: an operator that raises only prints a
            # traceback, and the user needs the message in the UI.
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        self.report({"INFO"}, "Equipped {0} in {1}".format(self.item, self.slot))
        return {"FINISHED"}


class ZOXEL_OT_unequip(bpy.types.Operator):
    """Take off whatever is worn in a slot."""

    bl_idname = "zoxel.unequip"
    bl_label = "Unequip"
    bl_description = "Take off the item in this slot"
    bl_options = {"REGISTER", "UNDO"}

    slot: bpy.props.EnumProperty(name="Slot", items=_slot_enum())

    def execute(self, _context):
        try:
            equip.unequip(self.slot)
        except (KeyError, ValueError, RuntimeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        self.report({"INFO"}, "Unequipped {0}".format(self.slot))
        return {"FINISHED"}


class ZOXEL_PT_accessories(bpy.types.Panel):
    """The Zoxel tab: one row per slot, plus the rebuild button."""

    bl_idname = PANEL_IDNAME
    bl_label = "Zoxel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Zoxel"

    def draw(self, _context):
        layout = self.layout
        layout.operator("zoxel.build_avatar", icon="MESH_CUBE")

        if rig.rig_root() is None:
            layout.label(text="No rig: press Build Avatar", icon="INFO")
            return

        equipped = equip.get_equipped()
        for slot in slots.SLOTS:
            layout.separator()
            column = layout.column(align=True)
            column.label(text="{0}: {1}".format(slot, equipped.get(slot) or "empty"))

            row = column.row(align=True)
            equipping = row.operator("zoxel.equip", text="Equip")
            equipping.slot = slot
            row.prop(equipping, "item", text="")
            row.operator("zoxel.unequip", text="", icon="X").slot = slot


_CLASSES = (
    ZOXEL_OT_build_avatar,
    ZOXEL_OT_equip,
    ZOXEL_OT_unequip,
    ZOXEL_PT_accessories,
)


def register():
    """Register the panel and its operators.  Calling it twice is a no-op."""
    if hasattr(bpy.types, PANEL_IDNAME):
        return
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    """Unregister the panel and its operators."""
    for cls in reversed(_CLASSES):
        if hasattr(bpy.types, cls.__name__):
            bpy.utils.unregister_class(cls)
