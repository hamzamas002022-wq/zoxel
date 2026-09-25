# Zoxel avatar (Blender)

The blocky avatar rig, and the wearable accessory system built on top of it.

The rig is **generated from code**, not hand-modelled: `build_avatar()` rebuilds
the whole thing from the proportions table in `zoxel_accessories/body.py`. Change
a number there, run the build again, and the avatar comes back different but
consistent - parts on their joints, attach nodes re-welded, materials reused.

## The avatar

One box per body part, 1.02 units tall, standing on `z = 0`. The silhouette is
deliberately **narrow on top and a little bigger at the bottom**:

| Part | Pivot (the joint) | Bottom | Top | Height |
|---|---|---|---|---|
| `Torso` | hips, `z = 0.44` | 0.44 wide (hips) | 0.40 wide (shoulders) | 0.40 |
| `Head` | neck, `z = 0.84` | 0.32 wide | 0.32 wide | 0.18 |
| `Arm_L` / `Arm_R` | shoulder, `x = ±0.285`, `z = 0.84` | 0.18 | 0.18 (straight) | 0.30 |
| `Hand_L` / `Hand_R` | wrist, `x = ±0.430`, `z = 0.54` | 0.44 (as wide as the torso) | 0.44 (as wide as the torso) | 0.10 |
| `Leg_L` / `Leg_R` | hip, `z = 0.44` | 0.22 wide | 0.22 wide | 0.44 |

So the torso is tapered from the shoulders down to the hips, and each arm is one
**straight block** - the same width at the shoulder as at the wrist, like a Roblox
arm - ending in a **full-size hand**, as wide and deep as the torso itself. That
hand keeps the arm's inner line, so all of its extra size grows outwards, away from
the hip, and never sinks into the body. `Hand_L` and `Hand_R` are children of their
arms, so a hand follows its arm.

The limbs also **lean outwards as they go down**, so their inner face follows the
torso's tapered side instead of leaving a wedge of daylight at the shoulder. That
placement is *derived*, not typed in: `ARM_X`, `WRIST_X` and `HAND_X` come from
`torso_half_x_at()` plus `ARM_OVERLAP`, and the two leans fall out of the same
three numbers. Retune the torso and the limb follows it, still welded.

Every part's origin sits on its **joint** rather than at its centre - the torso
at the hips, the arms at the shoulders, the legs at the hips, the hands at the
wrists - so rotating a part swings it the way an animator expects.

Parts hang off `CHAR_Root` as `Leg_L/R` and `Torso`, with `Head`, `Arm_L/R` under
`Torso` and `Hand_L/R` under their arm.

| Material | Used by |
|---|---|
| `MAT_Shirt` | torso |
| `MAT_Skin` | head, arms, hands |
| `MAT_Pants` | legs |
| `MAT_Face` | unused, reserved |
| `MAT_Accessory` | stand-in boxes for equipped items |

Existing materials are reused exactly as they are, so rebuilding the rig never
discards colours that were authored by hand.

## Accessories

One item on the back, one item in the hand.

| Slot | Attach node | Hangs on |
|---|---|---|
| `Back` | `BackAttach` | `Torso` |
| `Hand` | `HandAttach` | `Hand_R` |

A visual is a child object of its attach node, so it follows the part it is
welded to with no constraint or animation setup.

No items are registered yet, because the project has no accessory meshes:
`registry.py` ships empty. Add one with `register_item` (see "Adding an item"),
and it becomes available to `equip` and to the sidebar panel.

## Load it in Blender

Open `zoxel_avatar.blend`, then the Python console (or a Text datablock):

    import sys
    sys.path.append(r"<repo>\blender")
    import zoxel_accessories as accessories

Importing registers a **Zoxel** tab in the 3D viewport sidebar (`N`), which drives
the same API from buttons: build the avatar, pick an item per slot, equip it, take
it off again. If the panel does not appear, run `accessories.register()`.

Blender keeps imported modules alive for the whole session, so after editing a
file in this package an already-running Blender is still executing the old code.
Run `accessories.reload()` to replace it and re-register the panel against the
new one.

## API

    accessories.build_avatar()                     # base rig + attach points
    accessories.ensure_attach()                    # re-weld missing attach nodes
    accessories.register_item(my_item)             # see "Adding an item" below
    accessories.equip(accessories.SLOT_HAND, my_item.id)
    accessories.get_equipped()                     # {"Back": ..., "Hand": ...}
    accessories.unequip(accessories.SLOT_BACK)
    accessories.reload()                           # after editing any of these files

`build_avatar()` removes any existing rig first, so it is safe to run repeatedly
and is how a change to the proportions is picked up. It returns the root object.

`equip` rejects an item whose `slot` does not match, unequips the current
occupant first, parents the visual to the slot's attach node, and writes the id
into the rig root's custom properties (`equipped_Back`, `equipped_Hand`).
`unequip` unparents the visual into the `AccessoryPool` collection, hidden, ready
to be reused on the next equip.

The `.blend` is the state: an equipped item is a visual on its attach node plus a
property on the rig root. Nothing is cached in Python, so the file and the API
cannot drift apart.

## Where things live

| File | Contents |
|---|---|
| `zoxel_accessories/body.py` | the proportions table: parts, pivots, extents, attach nodes |
| `zoxel_accessories/slots.py` | slot ids, attach-node names, anchor parts |
| `zoxel_accessories/item_def.py` | `ItemDef` |
| `zoxel_accessories/registry.py` | the item registry - empty by default, add items here |
| `zoxel_accessories/assets.py` | box meshes, materials, collections, parenting helpers |
| `zoxel_accessories/rig.py` | base rig, build/remove, attach-point resolution |
| `zoxel_accessories/equip.py` | equip / unequip / get_equipped, the visual pool |
| `zoxel_accessories/ops.py` | operators and the sidebar panel |
| `test/test_proportions.py` | checks for the rig and its proportions |
| `build_avatar.py` | rebuilds the rig, saves the `.blend` and writes the GLB |

## Adding an item

Register one `ItemDef` in `registry.py`. `local_position` / `local_rotation` /
`local_scale` are applied in the attach node's local space, which is what makes
an item sit correctly on this rig:

    register_item(ItemDef(
        id="my_item",
        slot=SLOT_HAND,
        mesh="my_asset_id",
        local_position=(0.0, -0.06, -0.18),
        local_rotation=(0.35, 0.0, 0.0),
        local_scale=(0.12, 0.12, 0.44),
    ))

`mesh` names the asset to draw. There are no accessory meshes in the project yet,
so the only thing that has been used here is a unit box scaled by `local_scale`;
this field is where a real asset id goes once one exists.

## Changing the avatar

Edit the tables in `zoxel_accessories/body.py` and run `build_avatar()` again.
`PARTS` is ordered so a parent is always built before its children, and
`BUILD_ORDER` is the order `build_avatar()` walks; a part's `direction` is +1
when it grows upwards from its pivot (the torso) and -1 when it grows downwards
(the arms, hands and legs). `half_bottom` is always the geometric bottom, so a
tapered limb reads the same either way round, and `lean` slides the far end of a
part sideways, which is how the arms are angled out to stay on the torso.

`body.py` also carries the helpers the join checks use - `torso_half_x_at`,
`part_half_x_at`, `part_centre_x_at` and `limb_inner_x_at` - so the width and the
inner face of the torso or of a limb at any height are one call away. If you
retune the taper or the lean, those checks will tell you when a limb has stopped
meeting the body.

## Checks

    blender --background --python blender/test/test_proportions.py

18 checks, run inside Blender because that is where `bpy` exists. They rebuild
the avatar and re-derive the expected geometry from `body.py` rather than from
the built objects, so they only pass when the build matches the table: the taper
of the torso, the straight limbs, both hands, joint pivots, ground contact, attach
node positions, and the equip/unequip round trip.

Three of them guard the two places the avatar can look broken. Two cover the
limb/torso join - each limb's lean is compared against the derived centre line,
and its inner face has to stay inside the torso at eleven heights, hand included -
and the third covers the limb itself: the arm has to be the same width top and
bottom, and each hand has to be as wide as the torso and to grow outwards off the
arm's inner line.

## Rebuilding and exporting

The rig, attach points and equipped state all live in the `.blend`. If they are
removed, `build_avatar()` recreates the rig and `ensure_attach()` adds the attach
nodes back onto any rig it finds, so nothing has to be re-authored by hand.

`build_avatar.py` is the one command that brings the artefacts back in step with
the code: it rebuilds the rig, saves it into the `.blend` and writes the GLB.

    blender --background --python blender/build_avatar.py

It opens `zoxel_avatar.blend` first when that file exists, so the camera, the
light and anything else in the file survive and only the rig is replaced, and it
exports `CHAR_Root` and its children only, so nothing else leaks into the GLB.
Run it after editing `body.py`.

glTF is Y-up, so the avatar's height arrives on the glTF Y axis: the GLB is 1.02
units tall, the feet are on `y = 0` and the hands sit at `y = 0.44..0.54`.
