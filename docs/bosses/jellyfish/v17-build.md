# v17 flexible tentacles

The user's real-game v16 recording confirms the updated appearance and moving
tentacles, and they report that it feels lighter. This is a subjective v16
observation, not an FPS measurement and not validation of v17 performance.

v17 targets stiff articulated arms. Catmull-Rom centerlines retain the archived
source-inspired anchors but give the arms continuous curves. Outer chains have
eight joints instead of four, and inner chains six instead of three. Two short,
overlapping cuboids follow each joint. Long rigid oral roots are shortened;
straight companion branches become gently offset secondary ribbons.

## Runtime budget

| Metric | v16 near | v17 near | v17 far |
| --- | ---: | ---: | ---: |
| Cuboids / panels | 526 | 526 | 174 |
| Drawn triangles | 3,272 | 3,272 | 1,096 |
| Unique skeleton bones | 58 | 114 | 98 |
| Geometry bone entries across active layers | 60 | 116 | 100 |
| Active animated bone channels | 57 | 113 | 1 |
| Render controller layers | 2 | 2 | 2 |

The GPU face budget and texture dimensions are unchanged. Bone transforms and
animation channels increase, so equivalent real-game frame time is not assumed.
Within that fixed total, shell triangles increase from 1,792 to 2,048 and
tissue triangles decrease from 1,480 to 1,224. The alpha-blended share is larger.
The far model still switches at 80 blocks and animates only the bell.

The tentacle wave travels from root to tip in a six-second loop. Small root
rotations and larger distal rotations avoid turning entire long spans together.
Forty-eight sampled intervals per cycle replace the former four intervals.
Each chain has a different phase. The four-second bell pulse runs separately,
so both animations loop without forcing a discontinuity. The preview covers
12 seconds, the common period of both loops; its 12 fps is an export setting.

The two source-baked 512x512 texture sets use revised atlas addresses for the
new cuboids. Shell/bell colors, normal convention and material roles retain the
v16 approach. The broad inner tissue uses alpha test; it is not yet a fully
translucent inner gel. The bell rim's visible panel joins remain a separate
visual refinement. This revision does not claim source-identical fidelity.

## Rebuild

Use Blender 5.1, the archived separated scene SOURCE.blend, the selected April
VISUAL.glb, and a writable WORK directory. Leave the original assets unchanged.

~~~powershell
blender -b SOURCE.blend --python-exit-code 1 --python tools/jellyfish_boss/build_flexible_rig.py -- WORK/near.blend WORK/placeholder.png VISUAL.glb near
blender -b SOURCE.blend --python-exit-code 1 --python tools/jellyfish_boss/build_flexible_rig.py -- WORK/far.blend WORK/placeholder-far.png VISUAL.glb far
blender -b WORK/near.blend --python-exit-code 1 --python tools/jellyfish_boss/export_bedrock_geometry.py -- docs/bosses/jellyfish/generated/jellyfish_boss_v17.geo.json
blender -b WORK/far.blend --python-exit-code 1 --python tools/jellyfish_boss/export_bedrock_geometry.py -- docs/bosses/jellyfish/generated/jellyfish_boss_v17_far.geo.json
blender -b WORK/near.blend --python-exit-code 1 --python tools/jellyfish_boss/bake_source_atlas.py -- docs/bosses/jellyfish/generated/v17_textures
py -3 tools/jellyfish_boss/export_flexible_animation.py docs/bosses/jellyfish/generated/jellyfish_boss_v17.animation.json
py -3 scripts/assemble_flexible_pack.py
py -3 scripts/validate_pack.py
blender -b WORK/near.blend --python-exit-code 1 --python tools/jellyfish_boss/audit_flexible_motion.py -- resource_pack/models/entity/jellyfish_boss.geo.json resource_pack/animations/jellyfish_boss.animation.json docs/bosses/jellyfish/generated/jellyfish_boss_v17_motion_audit.json
blender -b --python-exit-code 1 --python tools/jellyfish_boss/preview_runtime.py -- docs/bosses/jellyfish/generated/jellyfish_boss_v17.geo.json docs/bosses/jellyfish/generated/v17_textures docs/bosses/jellyfish/generated/jellyfish_boss_v17_runtime.png resource_pack/animations/jellyfish_boss.animation.json
blender -b --python-exit-code 1 --python tools/jellyfish_boss/preview_runtime.py -- docs/bosses/jellyfish/generated/jellyfish_boss_v17.geo.json docs/bosses/jellyfish/generated/v17_textures WORK/motion_frames resource_pack/animations/jellyfish_boss.animation.json loop
py -3 tools/jellyfish_boss/package_motion_preview.py WORK/motion_frames docs/bosses/jellyfish/generated/jellyfish_boss_v17_motion.gif
py -3 scripts/package_mcaddon.py
~~~

The motion audit samples 481 poses from actual exported bone pivots and
keyframes. It checks centerline joins, loop closure, seam velocity and bounds.
The geometry exporter independently checks every cuboid corner after rotation
conversion. These mathematical checks exclude engine-specific rendering,
alpha sorting and real-game performance.

## Real-game check

Reload the test world after replacing development packs. Look for disconnected
joins across at least two swimming cycles, compare movement and frame time with
v16 at the same camera position, then cross the 80-block LOD boundary. Recheck
the creative egg and content log. No world or graphics settings are edited.

Primary reference:
[Bedrock animation keyframes and interpolation](https://learn.microsoft.com/en-us/minecraft/creator/documents/animations/animationsoverview).
