"""The item registry.

Empty by default, on purpose: the project has no accessory meshes yet.  Register
an item here and it becomes available to :func:`zoxel_accessories.equip` and to
the sidebar panel.
"""

_ITEMS = {}


def register_item(item):
    """Add ``item`` to the registry and return it.

    Raises ``ValueError`` when the id is already taken, so a copy/paste mistake
    is reported instead of silently replacing an item.
    """
    if item.id in _ITEMS:
        raise ValueError("item id already registered: {0}".format(item.id))
    _ITEMS[item.id] = item
    return item


def unregister_item(item_id):
    """Remove ``item_id``; True when something was removed."""
    return _ITEMS.pop(item_id, None) is not None


def get_item(item_id):
    """The item called ``item_id``, or ``None``."""
    return _ITEMS.get(item_id)


def all_items():
    """Every registered item, ordered by id."""
    return tuple(_ITEMS[key] for key in sorted(_ITEMS))


def items_for_slot(slot):
    """Every registered item that goes in ``slot``, ordered by id."""
    return tuple(item for item in all_items() if item.slot == slot)


def clear():
    """Forget every registered item."""
    _ITEMS.clear()
