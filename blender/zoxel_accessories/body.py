"""Body proportions for the blocky Zoxel avatar.

Everything here is data: the rig is generated from these tables, so changing the
avatar's shape means editing numbers in this one file and re-running
``build_avatar()``.

Units are the same as the rest of the project - the avatar stands 1.02 units
tall, one box per body part.  A part that changes size along its length is
*tapered*, and a part whose far end swings sideways has *lean*, which together
give the avatar its "narrow on top, a little bigger at the bottom" silhouette:

* the torso is a clean block, a little narrower at the shoulders than at the hips,
* each arm is one straight block - the same width all the way down,
* each arm ends in a hand that **continues that block**, so the whole limb is a
  single clean column with no step anywhere in it,
* arm and hand both **lean outwards** as they go down, so their inner face follows
  the tapered side of the torso instead of leaving a gap at the shoulder.

Vertical landmarks, measured from the ground:

    TOP_Z      1.02  top of the head
    SHOULDER_Z 0.84  shoulders: top of the torso, bottom of the head, arm pivot
    HIP_Z      0.53  hips: top of the legs, bottom of the torso, hand end
    GROUND_Z   0.00  soles

Those three heights give the avatar its LEGO / Roblox read.  The hips sit above
the midpoint, so the legs are the biggest single thing on the body - 0.53 tall,
half the avatar - while the block above them (torso 0.31, head 0.18) is a
compact 0.49.  A short, wide upper body on long, thick legs is what makes a
blocky figure read as a minifigure rather than as a walking box.

The widths did not move at all, only where the hips are: the torso is the same
0.44 wide at the hips as it ever was, and each leg is still 0.22 across, so the
pair fills the hip width exactly the way a Roblox leg pair does.
"""

from collections import namedtuple

# --------------------------------------------------------------------------
# Vertical landmarks
# --------------------------------------------------------------------------

GROUND_Z = 0.0
HIP_Z = 0.53
SHOULDER_Z = 0.84
TOP_Z = 1.02

# --------------------------------------------------------------------------
# The torso, and the width of the side a limb has to sit against
# --------------------------------------------------------------------------

TORSO_HALF_HIP = (0.22, 0.12)           # wide end
TORSO_HALF_SHOULDER = (0.20, 0.11)      # narrow end
TORSO_HEIGHT = SHOULDER_Z - HIP_Z       # 0.31


def torso_half_x_at(z):
    """Half the torso's width at height ``z``, following its taper."""
    t = (z - HIP_Z) / TORSO_HEIGHT
    return TORSO_HALF_HIP[0] + t * (TORSO_HALF_SHOULDER[0] - TORSO_HALF_HIP[0])


# --------------------------------------------------------------------------
# The arm and hand
# --------------------------------------------------------------------------

#: How much of the limb is the hand, measured down from its end.  The arm makes
#: up the rest, so the whole limb is still 0.31 long - shoulder to hip, exactly
#: the height of the torso it hangs beside.
HAND_HEIGHT = 0.10

LEG_HEIGHT = HIP_Z - GROUND_Z           # 0.53
HEAD_HEIGHT = TOP_Z - SHOULDER_Z        # 0.18

#: Where the hand takes over from the arm.
WRIST_Z = HIP_Z + HAND_HEIGHT           # 0.63

#: Cross sections.  The arm is one straight block - the same width and depth at
#: the shoulder as at the wrist, like a Roblox arm - and the hand is the same
#: cross section again, so the limb is one clean column with no step in it.
ARM_HALF_SHOULDER = (0.09, 0.09)
ARM_HALF_WRIST = (0.09, 0.09)
HAND_HALF = ARM_HALF_WRIST

ARM_HEIGHT = SHOULDER_Z - WRIST_Z       # 0.21

#: How far a limb's inner face tucks into the torso.  The placement below is
#: derived from this, so the join holds at every height.
ARM_OVERLAP = 0.005


def _limb_centre_x(half, z):
    """Centre line for a limb of half width ``half`` sitting on the torso at ``z``."""
    return torso_half_x_at(z) + half[0] - ARM_OVERLAP


#: Where the arm's centre line runs.  Derived from the torso rather than
#: hardcoded, so retuning the taper keeps the arm welded to it: the arm's inner
#: face ends up ARM_OVERLAP inside the torso at the shoulder and at the wrist.
ARM_X = _limb_centre_x(ARM_HALF_SHOULDER, SHOULDER_Z)     # 0.285
WRIST_X = _limb_centre_x(ARM_HALF_WRIST, WRIST_Z)         # 0.299

#: The arm's inner face at the wrist.  The hand keeps this line, so the limb
#: stays a straight column and never sinks into the hip.
WRIST_INNER_X = WRIST_X - ARM_HALF_WRIST[0]                # 0.209

HAND_X = WRIST_INNER_X + HAND_HALF[0]                     # 0.299, hand centre at the wrist
HAND_END_X = _limb_centre_x(HAND_HALF, HIP_Z)             # 0.305, hand centre at the hip

ARM_LEAN = WRIST_X - ARM_X                                # 0.014
HAND_LEAN = HAND_END_X - HAND_X                           # 0.006

# --------------------------------------------------------------------------
# Everything else
# --------------------------------------------------------------------------

# Distance of a limb's centre line from the avatar's centre line.
LEG_X = 0.115

# Half extents, as (x, y).  A negative Y is the avatar's front.  The leg is a
# little deeper than it is wide, which is what stops a long leg reading as a
# flat plank when you look at it from the side.
LEG_HALF = (0.11, 0.12)
HEAD_HALF = (0.16, 0.09)

# --------------------------------------------------------------------------
# The rig
# --------------------------------------------------------------------------

#: One box part.  ``direction`` is +1 when the part grows upwards from its pivot
#: (the pivot sits at the part's bottom, e.g. the torso at the hips) and -1 when
#: it grows downwards (the pivot sits at the part's top, e.g. the arm at the
#: shoulder).  ``half_bottom``/``half_top`` are the geometric bottom and top of
#: the box in both cases, so a tapered limb reads the same either way round.
#: ``lean`` slides the far end - the end away from the pivot - sideways in X and
#: Y, which is how an arm is angled out to meet the torso.
Part = namedtuple(
    "Part",
    "name parent pivot half_bottom half_top height direction material lean",
    defaults=((0.0, 0.0),),
)

#: One empty that an accessory visual is parented to.  ``offset`` is measured in
#: the anchor part's local space, from that part's pivot.
Attach = namedtuple("Attach", "name parent offset")

PARTS = (
    Part(
        name="Torso",
        parent="CHAR_Root",
        pivot=(0.0, 0.0, HIP_Z),
        half_bottom=TORSO_HALF_HIP,
        half_top=TORSO_HALF_SHOULDER,
        height=TORSO_HEIGHT,
        direction=1,
        material="MAT_Shirt",
    ),
    Part(
        name="Head",
        parent="Torso",
        pivot=(0.0, 0.0, SHOULDER_Z),
        half_bottom=HEAD_HALF,
        half_top=HEAD_HALF,
        height=HEAD_HEIGHT,
        direction=1,
        material="MAT_Skin",
    ),
    Part(
        name="Arm_L",
        parent="Torso",
        pivot=(-ARM_X, 0.0, SHOULDER_Z),
        half_bottom=ARM_HALF_WRIST,
        half_top=ARM_HALF_SHOULDER,
        height=ARM_HEIGHT,
        direction=-1,
        material="MAT_Skin",
        lean=(-ARM_LEAN, 0.0),
    ),
    Part(
        name="Arm_R",
        parent="Torso",
        pivot=(ARM_X, 0.0, SHOULDER_Z),
        half_bottom=ARM_HALF_WRIST,
        half_top=ARM_HALF_SHOULDER,
        height=ARM_HEIGHT,
        direction=-1,
        material="MAT_Skin",
        lean=(ARM_LEAN, 0.0),
    ),
    Part(
        name="Hand_L",
        parent="Arm_L",
        pivot=(-HAND_X, 0.0, WRIST_Z),
        half_bottom=HAND_HALF,
        half_top=HAND_HALF,
        height=HAND_HEIGHT,
        direction=-1,
        material="MAT_Skin",
        lean=(-HAND_LEAN, 0.0),
    ),
    Part(
        name="Hand_R",
        parent="Arm_R",
        pivot=(HAND_X, 0.0, WRIST_Z),
        half_bottom=HAND_HALF,
        half_top=HAND_HALF,
        height=HAND_HEIGHT,
        direction=-1,
        material="MAT_Skin",
        lean=(HAND_LEAN, 0.0),
    ),
    Part(
        name="Leg_L",
        parent="CHAR_Root",
        pivot=(-LEG_X, 0.0, HIP_Z),
        half_bottom=LEG_HALF,
        half_top=LEG_HALF,
        height=LEG_HEIGHT,
        direction=-1,
        material="MAT_Pants",
    ),
    Part(
        name="Leg_R",
        parent="CHAR_Root",
        pivot=(LEG_X, 0.0, HIP_Z),
        half_bottom=LEG_HALF,
        half_top=LEG_HALF,
        height=LEG_HEIGHT,
        direction=-1,
        material="MAT_Pants",
    ),
)

#: Upper back of the torso - a little outside the back face so an item hangs on
#: the surface rather than inside the body.
BACK_ATTACH_OFFSET = (0.0, 0.12, 0.30)

#: Palm of the right hand - the bottom face of the hand block.
HAND_ATTACH_OFFSET = (0.0, 0.0, -HAND_HEIGHT)

ATTACHES = (
    Attach(name="BackAttach", parent="Torso", offset=BACK_ATTACH_OFFSET),
    Attach(name="HandAttach", parent="Hand_R", offset=HAND_ATTACH_OFFSET),
)

#: Order parts are built in, so a parent always exists before its children.
BUILD_ORDER = (
    "CHAR_Root",
    "Torso",
    "Head",
    "Arm_L",
    "Arm_R",
    "Hand_L",
    "Hand_R",
    "Leg_L",
    "Leg_R",
)

#: The two parts that make up one limb, from the shoulder down.
LIMB_PARTS = {"L": ("Arm_L", "Hand_L"), "R": ("Arm_R", "Hand_R")}


def part(name):
    """Return the :class:`Part` called ``name``.

    Raises ``KeyError`` when the rig has no such part.
    """
    for candidate in PARTS:
        if candidate.name == name:
            return candidate
    raise KeyError("no such rig part: {0}".format(name))


def attach(name):
    """Return the :class:`Attach` called ``name``.

    Raises ``KeyError`` when the rig has no such attach node.
    """
    for candidate in ATTACHES:
        if candidate.name == name:
            return candidate
    raise KeyError("no such attach node: {0}".format(name))


def part_names():
    """Names of every box part in the rig."""
    return tuple(p.name for p in PARTS)


def attach_names():
    """Names of every attach node in the rig."""
    return tuple(a.name for a in ATTACHES)


def _far_end_t(part_, z):
    """How far along ``part_`` ``z`` sits: 0 at its pivot, 1 at its far end."""
    return (z - part_.pivot[2]) / (part_.direction * part_.height)


def part_half_x_at(part_, z):
    """Half the width of ``part_`` at height ``z``, following its taper."""
    t = _far_end_t(part_, z)
    if part_.direction > 0:
        near, far = part_.half_bottom, part_.half_top
    else:
        near, far = part_.half_top, part_.half_bottom
    return near[0] + (far[0] - near[0]) * t


def part_centre_x_at(part_, z):
    """``part_``'s centre line at height ``z``, following its lean."""
    t = _far_end_t(part_, z)
    return abs(part_.pivot[0]) + abs(part_.lean[0]) * t


def limb_inner_x_at(side, z):
    """``side``'s arm-or-hand inner face at ``z``: the line that stays in the torso."""
    arm_name, hand_name = LIMB_PARTS[side]
    name = arm_name if z > WRIST_Z else hand_name
    limb = part(name)
    return part_centre_x_at(limb, z) - part_half_x_at(limb, z)
