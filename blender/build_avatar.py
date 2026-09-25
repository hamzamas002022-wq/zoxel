"""Rebuild the avatar and write both artifacts it feeds.

    blender --background --python blender/build_avatar.py

Writes:

* ``blender/zoxel_avatar.blend`` - the working file, with the rig regenerated
  from :mod:`zoxel_accessories.body`
* ``assets/models/zoxel_avatar.glb`` - the file the browser client loads

Run this after changing the proportions in ``body.py`` and the .blend, the
exported asset and the code all agree again.  If the .blend already exists it is
opened first, so the camera, the light and anything else in the file survive;
only the rig is replaced.
"""

import os
import sys

_BLENDER_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_DIR = os.path.dirname(_BLENDER_DIR)
if _BLENDER_DIR not in sys.path:
    sys.path.insert(0, _BLENDER_DIR)

import bpy

import zoxel_accessories as zx

#: The working file, and the asset the client picks up.
BLEND = os.path.join(_BLENDER_DIR, "zoxel_avatar.blend")
GLB = os.path.join(_REPO_DIR, "assets", "models", "zoxel_avatar.glb")


def select_tree(obj):
    """Select ``obj`` and everything parented under it."""
    obj.select_set(True)
    for child in obj.children:
        select_tree(child)
    return obj


def build(blend=BLEND, glb=GLB):
    """Rebuild the rig, save ``blend`` and export ``glb``.  Returns the root."""
    if os.path.isfile(blend):
        bpy.ops.wm.open_mainfile(filepath=blend)

    root = zx.build_avatar()

    # Selecting through the data API rather than an operator keeps this working
    # in background mode, where operators have no viewport context.
    for obj in bpy.data.objects:
        obj.select_set(False)
    select_tree(root)
    bpy.context.view_layer.objects.active = root

    bpy.ops.wm.save_as_mainfile(filepath=blend)
    print("wrote {0} ({1} bytes)".format(blend, os.path.getsize(blend)))

    os.makedirs(os.path.dirname(glb), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=glb,
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
    )
    print("wrote {0} ({1} bytes)".format(glb, os.path.getsize(glb)))
    return root


if __name__ == "__main__":
    build()
