"""The definition of a wearable item."""

from dataclasses import dataclass

from . import slots


@dataclass(frozen=True)
class ItemDef:
    """One wearable item.

    ``local_position``, ``local_rotation`` and ``local_scale`` are applied in the
    attach node's local space, which is what makes an item sit correctly on this
    rig rather than somewhere near it.

    ``mesh`` names the asset to draw.  There are no accessory meshes in the
    project yet, so a visual is currently a unit box multiplied by
    ``local_scale``; this field is where a real asset id goes once one exists.
    """

    id: str
    slot: str
    mesh: str
    local_position: tuple = (0.0, 0.0, 0.0)
    local_rotation: tuple = (0.0, 0.0, 0.0)
    local_scale: tuple = (1.0, 1.0, 1.0)

    def __post_init__(self):
        if not self.id:
            raise ValueError("ItemDef.id must not be empty")
        if not slots.is_slot(self.slot):
            raise ValueError(
                "ItemDef.slot must be one of {0}, got {1!r}".format(
                    ", ".join(slots.SLOTS), self.slot
                )
            )

    @property
    def visual_name(self):
        """Name of the object that draws this item, on the rig or in the pool."""
        return "{0}_visual".format(self.id)
