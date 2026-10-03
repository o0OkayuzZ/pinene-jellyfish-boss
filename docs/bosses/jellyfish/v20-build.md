# v20 upward-flaring connection

The user rejected the stair-like v19 connector and asked for a shape that
broadens upward. Only that connection is replaced. A curved membrane widens
from the existing core to a ring on the inner bell at height 0.895.
Near uses 32 sectors with three overlapping spans; far uses 16 with two.
Each terminal edge fits into a rendered inner bell face, with a 0.0008 inset.
The whole membrane, core and bell share the bell bone and its accepted pulse.

Only the two broad sides are drawn: 96 panels / 384 triangles near and
32 / 128 far. Full totals: 622 cuboids / 3,656 triangles near, 206 / 1,224 far.
The skeleton and two render layers are unchanged. BP/RP version is 0.1.5.
Old shell/tentacle cuboids and pivots, animation, behavior and every old atlas
pixel remain unchanged. New source-projected tissue tiles occupy slots 142-237
of the existing 512-square atlas; no texture or material layer is added.

## Rebuild and checks

Run attach_central_core.py on the v19 near/far working blends, then export
with export_bedrock_geometry.py into jellyfish_boss_v20.geo.json and
jellyfish_boss_v20_far.geo.json. Bake the near blend with bake_source_atlas.py
into v20_textures. The complete build_flexible_rig.py invokes the same helper.
Run assemble_flexible_pack.py, validate_pack.py and package_mcaddon.py.
The motion input remains jellyfish_boss_v17.animation.json.

audit_flexible_motion.py verifies all 32 inner-face contacts, 96 spans, 16
tentacle roots and 481 poses. Existing geometry and texture pixels were also
compared with v18, excluding only the newly allocated connector cells.
preview_runtime.py accepts still/connection for a close view of the junction.
Rendered previews approximate lighting; actual game appearance needs review.
Animation and behavior cleanup remain the next stage after shape acceptance.
