"""Checks for the avatar rig and its proportions.

Runs inside Blender, because that is where ``bpy`` exists::

    blender --background --python blender/test/test_proportions.py

or from the Python console::

    import runpy
    runpy.run_path(r"<repo>\\blender\\test\\test_proportions.py", run_name="__main__")

Every check re-derives the expected geometry from
:mod:`zoxel_accessories.body` rather than from the built objects, so a check
only passes when the build actually matches the table.
"""

import os
import sys

_BLENDER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BLENDER_DIR not in sys.path:
    sys.path.insert(0, _BLENDER_DIR)

from mathutils import Vector

import bpy

import zoxel_accessories as zx
from zoxel_accessories import body, ops, registry, rig

#: Smallest difference that still counts as a real difference, in units.
TOLERANCE = 1e-6

_CHECKS = []


def check(fn):
    """Register ``fn`` as one check and return it."""
    _CHECKS.append(fn)
    return fn


# --------------------------------------------------------------------------
# Geometry helpers
# --------------------------------------------------------------------------

def world_bounds(obj):
    """World-space ``(low, high)`` corners of a mesh object's bounding box."""
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    low = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    high = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return low, high


def bounds_from_table(part):
    """The world bounds ``part`` should have, derived from its table entry.

    A part that leans is not symmetric about its pivot, so both end faces are
    measured and the extremes win.  The pivot face carries ``half_bottom`` when
    the part grows upwards from its pivot, and ``half_top`` when it grows down.
    """
    pivot_z = part.pivot[2]
    far_z = pivot_z + part.direction * part.height
    pivot_half = part.half_bottom if part.direction > 0 else part.half_top
    far_half = part.half_top if part.direction > 0 else part.half_bottom
    far_x = part.pivot[0] + part.lean[0]
    far_y = part.pivot[1] + part.lean[1]

    xs = (
        part.pivot[0] - pivot_half[0],
        part.pivot[0] + pivot_half[0],
        far_x - far_half[0],
        far_x + far_half[0],
    )
    ys = (
        part.pivot[1] - pivot_half[1],
        part.pivot[1] + pivot_half[1],
        far_y - far_half[1],
        far_y + far_half[1],
    )
    low = Vector((min(xs), min(ys), min(pivot_z, far_z)))
    high = Vector((max(xs), max(ys), max(pivot_z, far_z)))
    return low, high


def face_width(obj, top):
    """World X width of the box face at the top (or bottom) of ``obj``."""
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    target = max(p.z for p in points) if top else min(p.z for p in points)
    on_face = [p for p in points if abs(p.z - target) < TOLERANCE]
    return max(p.x for p in on_face) - min(p.x for p in on_face)


def inner_face_x(obj, top):
    """World X of the face nearest the avatar's centre line, top or bottom."""
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    target = max(p.z for p in points) if top else min(p.z for p in points)
    on_face = [p for p in points if abs(p.z - target) < TOLERANCE]
    return min(abs(p.x) for p in on_face)


def rig_bounds():
    """World bounds of every part of the rig together."""
    lows = []
    highs = []
    for name in body.part_names():
        low, high = world_bounds(bpy.data.objects[name])
        lows.append(low)
        highs.append(high)
    low = Vector((min(v.x for v in lows), min(v.y for v in lows), min(v.z for v in lows)))
    high = Vector((max(v.x for v in highs), max(v.y for v in highs), max(v.z for v in highs)))
    return low, high


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------

@check
def build_creates_every_part_and_the_attach_nodes():
    for name in body.part_names():
        assert bpy.data.objects.get(name) is not None, "missing part {0}".format(name)
    duplicates = [n for n in body.part_names() if bpy.data.objects.get(n + ".001")]
    assert not duplicates, "duplicated parts: {0}".format(duplicates)
    for attach in body.ATTACHES:
        assert rig.attach_node(attach.name) is not None, "missing {0}".format(attach.name)
    assert rig.rig_root() is not None, "no rig root"


@check
def rebuilding_does_not_leave_duplicates():
    before = len(bpy.data.objects)
    zx.build_avatar()
    zx.build_avatar()
    assert len(bpy.data.objects) == before, "object count drifted {0} -> {1}".format(
        before, len(bpy.data.objects)
    )
    for name in body.part_names() + body.attach_names():
        assert bpy.data.objects.get(name + ".001") is None, "duplicated {0}".format(name)


@check
def every_part_sits_where_the_table_says():
    for part in body.PARTS:
        obj = bpy.data.objects[part.name]
        assert (Vector(obj.location) - Vector(part.pivot)).length < TOLERANCE, (
            "{0} origin is {1}, table says {2}".format(part.name, tuple(obj.location), part.pivot)
        )
        low, high = world_bounds(obj)
        expected_low, expected_high = bounds_from_table(part)
        assert (low - expected_low).length < TOLERANCE, (
            "{0} starts at {1}, table says {2}".format(part.name, tuple(low), tuple(expected_low))
        )
        assert (high - expected_high).length < TOLERANCE, (
            "{0} ends at {1}, table says {2}".format(part.name, tuple(high), tuple(expected_high))
        )


@check
def the_torso_is_narrow_on_top_and_big_at_the_bottom():
    torso = bpy.data.objects["Torso"]
    top = face_width(torso, top=True)
    bottom = face_width(torso, top=False)
    assert top < bottom, "torso is not tapered: top {0}, bottom {1}".format(top, bottom)
    assert abs(top - 2 * body.TORSO_HALF_SHOULDER[0]) < TOLERANCE
    assert abs(bottom - 2 * body.TORSO_HALF_HIP[0]) < TOLERANCE


@check
def the_head_is_narrower_than_the_shoulders():
    head = bpy.data.objects["Head"]
    top = face_width(head, top=True)
    assert top < 2 * body.TORSO_HALF_HIP[0], "the head is not the narrow end"
    assert top <= 2 * body.TORSO_HALF_SHOULDER[0] + TOLERANCE, "the head overhangs the shoulders"


@check
def the_arm_is_one_straight_block():
    """The arm must be the same width top and bottom - a straight Roblox arm."""
    for side in ("L", "R"):
        arm = bpy.data.objects["Arm_{0}".format(side)]
        shoulder = face_width(arm, top=True)
        wrist = face_width(arm, top=False)
        assert abs(shoulder - wrist) < TOLERANCE, (
            "arm_{0} is not straight: {1:.4f} at the shoulder, {2:.4f} at the wrist".format(
                side, shoulder, wrist
            )
        )
        assert abs(shoulder - 2 * body.ARM_HALF_SHOULDER[0]) < TOLERANCE, (
            "arm_{0} is {1:.4f} wide, the table says {2:.4f}".format(
                side, shoulder, 2 * body.ARM_HALF_SHOULDER[0]
            )
        )


@check
def both_arms_end_in_a_normal_hand():
    """Two normal hands: the arm's own width, and not tall.

    The hand continues the arm's column - no step in width, no step sideways -
    and stays flatter than it is wide, so it reads as a hand rather than a block.
    """
    for side, arm_name in (("L", "Arm_L"), ("R", "Arm_R")):
        arm = bpy.data.objects[arm_name]
        hand = bpy.data.objects.get("Hand_{0}".format(side))
        assert hand is not None, "missing Hand_{0}".format(side)
        assert hand.parent is not None and hand.parent.name == arm_name, (
            "Hand_{0} hangs on {1}".format(side, hand.parent)
        )

        arm_low = world_bounds(arm)[0]
        hand_bounds = world_bounds(hand)
        assert abs(hand_bounds[1].z - arm_low.z) < 1e-4, "the hand does not meet the wrist"

        arm_wrist = face_width(arm, top=False)
        hand_top = face_width(hand, top=True)
        assert abs(hand_top - arm_wrist) < 1e-4, (
            "hand {0} is {1:.4f} wide where the arm is {2:.4f}: there is a step".format(
                side, hand_top, arm_wrist
            )
        )

        hand_tall = hand_bounds[1].z - hand_bounds[0].z
        assert hand_tall < hand_top, (
            "hand {0} is {1:.3f} tall and {2:.3f} wide: too tall".format(side, hand_tall, hand_top)
        )
        assert abs(inner_face_x(arm, False) - inner_face_x(hand, True)) < 1e-4, (
            "the hand steps sideways off the arm's line"
        )


@check
def the_limbs_sit_where_the_table_says():
    """Every arm and hand mesh must sit on the centre line the table derives."""
    for side in ("L", "R"):
        for name in body.LIMB_PARTS[side]:
            limb = body.part(name)
            obj = bpy.data.objects[name]
            far_z = limb.pivot[2] + limb.direction * limb.height
            for top, z in ((True, limb.pivot[2]), (False, far_z)):
                measured = inner_face_x(obj, top)
                expected = body.part_centre_x_at(limb, z) - body.part_half_x_at(limb, z)
                assert abs(measured - expected) < 1e-4, (
                    "{0} inner face at z={1} is {2:.4f}, the table says {3:.4f}".format(
                        name, z, measured, expected
                    )
                )


@check
def the_limbs_stay_welded_to_the_torso():
    """No gap between a limb and the torso's tapered side, at any height.

    This is what stops the dark wedge opening up at the shoulder.  It covers the
    whole limb, hand included: the inner face has to sit inside the torso from the
    shoulder to the hand's end, and not so deep that the limb disappears into it.
    """
    for side in ("L", "R"):
        for step in range(11):
            z = body.HIP_Z + (body.SHOULDER_Z - body.HIP_Z) * step / 10.0
            torso = body.torso_half_x_at(z)
            limb_inner = body.limb_inner_x_at(side, z)
            assert limb_inner <= torso + TOLERANCE, (
                "limb {0} leaves a gap at z={1:.2f}: inner face {2:.4f}, torso {3:.4f}".format(
                    side, z, limb_inner, torso
                )
            )
            assert limb_inner >= torso - 0.02, (
                "limb {0} is buried at z={1:.2f}: inner face {2:.4f}, torso {3:.4f}".format(
                    side, z, limb_inner, torso
                )
            )


@check
def the_avatar_stands_on_the_ground():
    low, high = rig_bounds()
    assert abs(low.z - body.GROUND_Z) < 1e-4, "lowest point is {0}".format(low.z)
    assert abs(high.z - body.TOP_Z) < 1e-4, "highest point is {0}".format(high.z)


@check
def the_parts_hinge_on_their_joints():
    joints = {
        "Torso": body.HIP_Z,
        "Arm_L": body.SHOULDER_Z,
        "Arm_R": body.SHOULDER_Z,
        "Hand_L": body.WRIST_Z,
        "Hand_R": body.WRIST_Z,
        "Leg_L": body.HIP_Z,
        "Leg_R": body.HIP_Z,
    }
    for name, joint_z in joints.items():
        obj = bpy.data.objects[name]
        assert abs(obj.location.z - joint_z) < TOLERANCE, (
            "{0} hinges at {1}, expected {2}".format(name, obj.location.z, joint_z)
        )


@check
def the_attach_nodes_are_where_the_table_says():
    for attach in body.ATTACHES:
        node = rig.attach_node(attach.name)
        expected = rig.attach_world_location(attach)
        assert (Vector(node.location) - Vector(expected)).length < TOLERANCE, (
            "{0} is at {1}, table says {2}".format(attach.name, tuple(node.location), expected)
        )
        assert node.parent is not None and node.parent.name == attach.parent


@check
def the_hand_attach_node_is_on_a_hand():
    assert body.attach("HandAttach").parent == zx.slots.ANCHOR_PARTS[zx.SLOT_HAND]
    assert zx.slots.attach_name_for(zx.SLOT_HAND) == "HandAttach"


@check
def ensure_attach_restores_a_deleted_node():
    node = rig.attach_node("HandAttach")
    parent = node.parent
    bpy.data.objects.remove(node, do_unlink=True)
    created = zx.ensure_attach()
    assert "HandAttach" in created, "ensure_attach did not report the rebuild"
    restored = rig.attach_node("HandAttach")
    assert restored is not None and restored.parent == parent


@check
def the_sidebar_panel_is_registered():
    assert hasattr(bpy.types, ops.PANEL_IDNAME), "the Zoxel panel is not registered"


@check
def an_item_can_be_equipped_and_removed():
    for slot in zx.SLOTS:
        zx.unequip(slot)

    item = zx.ItemDef(
        id="check_item",
        slot=zx.SLOT_HAND,
        mesh="unit_box",
        local_position=(0.0, -0.06, -0.18),
        local_scale=(0.12, 0.12, 0.44),
    )
    zx.register_item(item)
    try:
        visual = zx.equip(zx.SLOT_HAND, item.id)
        assert visual.parent is not None and visual.parent.name == "HandAttach"
        assert zx.get_equipped().get(zx.SLOT_HAND) == item.id
        for actual, expected in zip(visual.scale, item.local_scale):
            assert abs(actual - expected) < 1e-5, (
                "the visual was scaled {0}, the item asks for {1}".format(
                    tuple(visual.scale), item.local_scale
                )
            )

        bpy.context.view_layer.update()
        node = rig.attach_node("HandAttach")
        expected = (node.matrix_world @ Vector(item.local_position)).z
        assert abs(visual.matrix_world.translation.z - expected) < 1e-4, (
            "the visual is at {0}, the attach offset puts it at {1}".format(
                visual.matrix_world.translation.z, expected
            )
        )

        assert zx.unequip(zx.SLOT_HAND) is True
        assert zx.get_equipped() == {}, "the slot is still marked as occupied"
        assert visual.parent is None, "the visual is still on the rig"
        assert visual.hide_viewport is True, "the pooled visual is still visible"
    finally:
        zx.unequip(zx.SLOT_HAND)
        registry.clear()


@check
def a_slot_rejects_an_item_from_another_slot():
    item = zx.ItemDef(id="check_back_item", slot=zx.SLOT_BACK, mesh="unit_box")
    zx.register_item(item)
    try:
        zx.equip(zx.SLOT_BACK, item.id)
        try:
            zx.equip(zx.SLOT_HAND, item.id)
        except ValueError:
            pass
        else:
            raise AssertionError("equipping a Back item in the Hand slot was allowed")
    finally:
        zx.unequip(zx.SLOT_BACK)
        registry.clear()


@check
def reload_replaces_the_package():
    """``reload()`` must swap in fresh modules and leave the panel registered."""
    global zx
    before = zx
    after = zx.reload()
    assert after is not before, "reload returned the same module object"
    assert after.build_avatar is not before.build_avatar, "the old functions came back"
    assert hasattr(after, "SLOT_HAND"), "the fresh package is missing the public API"
    assert hasattr(bpy.types, ops.PANEL_IDNAME), "the panel went missing after a reload"
    zx = after


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------

def run():
    """Build the avatar, run every check, and report.  Raises on failure."""
    zx.build_avatar()
    print("built the avatar from the proportions table")
    failures = []
    for fn in _CHECKS:
        bpy.context.view_layer.update()
        try:
            fn()
        except Exception as error:
            # Reported, never swallowed: run() raises once every check has run.
            failures.append(fn.__name__)
            print("FAIL {0}: {1}: {2}".format(fn.__name__, type(error).__name__, error))
        else:
            print("PASS {0}".format(fn.__name__))

    passed = len(_CHECKS) - len(failures)
    print("{0}/{1} checks passed".format(passed, len(_CHECKS)))
    if failures:
        raise AssertionError("failed: {0}".format(", ".join(failures)))
    return passed


if __name__ == "__main__":
    run()
