"""Slot ids, attach-node names and the rig part each attach node hangs on.

A slot is a place an item can be worn.  Each one owns an attach node - an empty
parented to a rig part - and an item's visual is parented to that empty, so the
visual follows the part it is welded to with no constraint or animation setup.
"""

SLOT_BACK = "Back"
SLOT_HAND = "Hand"

#: Every slot, in the order the sidebar panel lists them.
SLOTS = (SLOT_BACK, SLOT_HAND)

#: slot id -> name of the empty a visual is parented to.  These names must match
#: the attach nodes declared in :mod:`zoxel_accessories.body`.
ATTACH_NODES = {
    SLOT_BACK: "BackAttach",
    SLOT_HAND: "HandAttach",
}

#: slot id -> name of the rig part the attach node hangs on.  Informational:
#: :func:`zoxel_accessories.rig.build_avatar` is what actually places them.
ANCHOR_PARTS = {
    SLOT_BACK: "Torso",
    SLOT_HAND: "Hand_R",
}


def is_slot(slot):
    """True when ``slot`` is one of :data:`SLOTS`."""
    return slot in ATTACH_NODES


def attach_name_for(slot):
    """Name of the attach empty that a visual in ``slot`` is parented to.

    Raises ``KeyError`` for an unknown slot.
    """
    try:
        return ATTACH_NODES[slot]
    except KeyError:
        raise KeyError("unknown accessory slot: {0!r}".format(slot))


def anchor_part_for(slot):
    """Name of the rig part that holds ``slot``'s attach node.

    Raises ``KeyError`` for an unknown slot.
    """
    try:
        return ANCHOR_PARTS[slot]
    except KeyError:
        raise KeyError("unknown accessory slot: {0!r}".format(slot))
