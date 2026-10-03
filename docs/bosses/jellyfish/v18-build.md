# v18 root attachments

The user approved the overall v17 appearance and requested corrected attachment
positions before proceeding to animation and behavior cleanup. Their latest
recording includes underside views. The unchanged April GLB was inspected from
the same direction before this edit.

Outer anchors now lie inside the actual lowest bell panel, whose profile comes
from the original GLB. Inner anchors lie inside the rotated central tissue
volume. Only the root and the next source control point change; distal curves
retain the accepted v17 design. Twelve floating skirt blocks become eight
rim-root collars and four central collars at the real anchor positions.

Low horizontal rays could miss the uneven source bell lip and hit interior tissue.
The lower bell profile and its atlas now fall back to the nearby outer lip
when that occurs, preventing the inward panels seen in the v17 recording.


The runtime remains 526 cuboids / 3,272 triangles near, and 174 / 1,096 far,
with two layers and 113 active animated bones near. Versions are BP/RP 0.1.3.
The accepted v17 animation data and behavior components are carried forward.
No combat or animation timing is changed in this modeling revision.

The motion audit samples 481 poses and also checks all 16 root anchors against
the actual exported support cuboid and the exported bone pivot. Its report
contains before/after anchor positions and the support object for each root.
These checks validate export math, not real-game performance or alpha sorting.

## Rebuild

Follow the Blender 5.1 commands in v17-build.md, using WORK/near-v18.blend,
WORK/far-v18.blend, jellyfish_boss_v18.geo.json, jellyfish_boss_v18_far.geo.json
and v18_textures for the new outputs. The animation input remains the committed
jellyfish_boss_v17.animation.json. Run assemble_flexible_pack.py and
validate_pack.py, then audit_flexible_motion.py, preview_runtime.py and
package_mcaddon.py. The underside renderer accepts these final arguments:

~~~powershell
blender -b --python-exit-code 1 --python tools/jellyfish_boss/preview_runtime.py -- docs/bosses/jellyfish/generated/jellyfish_boss_v18.geo.json docs/bosses/jellyfish/generated/v18_textures docs/bosses/jellyfish/generated/jellyfish_boss_v18_underside.png docs/bosses/jellyfish/generated/jellyfish_boss_v17.animation.json still underside
~~~

## Next stage

Current stage: model attachment review in the test world.
Next stage: organize idle, swimming, attack, hurt and death animations together
with their behavior triggers. This modeling revision does not introduce those
states or change attacks. Confirm the root appearance from below and from the
side, then proceed to that cleanup after the shape is accepted.
