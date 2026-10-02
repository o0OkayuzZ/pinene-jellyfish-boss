# v16 surface reconstruction

The selected April GLB remains the source of silhouette and color. Original
binaries are unchanged and kept outside Git. This revision is not a new AI
beauty illustration: the preview renderer consumes exported geometry and atlases.

## Structural changes

| Metric | v15 | v16 near | v16 far |
| --- | ---: | ---: | ---: |
| Cuboids / panels | 1,136 | 526 | 174 |
| Drawn triangles | 9,176 | 3,272 | 1,096 |
| Render controller layers | 3 | 2 | 2 |
| Geometry bone entries | 174 | 60 | 60 |
| Active animated bone channels | 57 | 57 | 1 |
| Independently controlled chains | 16 | 16 | 16 (rest pose) |

The layers contain different geometry; v15 did **not** draw all 1,136 cuboids
three times. GPU transparency overdraw and collision work are candidates for
the reported lag, not measured causes. No before/after FPS is available yet.

The bell uses two-face, thin panels (32 sectors x 8 tiers), a profile sampled
from the original GLB, and a continuous 512x360 color panorama. Cyan rays and
dots come from the original texture and MERS emission, not raised cubes.
Outer filaments and inner ribbons have three overlapping cubes per bone.
Far LOD uses 16 sectors x 6 tiers and one cube per bone at camera distances
over 80 blocks. The two layers prune bones without geometry or descendants.

The coordinate conversion previously treated Bedrock rotation values like
right-handed XYZ angles. The corrected export is checked against Blockbench's
mirror-X / negate-X,Y import convention on every cuboid corner. It also fixes
an over-escaped bell-name regex that sent coherent bell UVs to hashed cells.

Visual scale 9.5 is baked into geometry and pivots, while BP scale is 1.0.
The intended 10.5x8 physical box remains explicit. This avoids relying on
whether visual scale also affects collision and keeps culling bounds explicit.
The source bake preserves near-black navy, cyan and varied magenta; only the
outer shell blends alpha, with an opaque alpha-tested inner mass.

## Rebuild

Use Blender 5.1 with the separated source scene and the selected visual GLB.
Replace SOURCE, VISUAL and WORK with actual paths. Never overwrite the sources.

```powershell
blender -b SOURCE.blend --python tools/jellyfish_boss/build_surface_rig.py -- WORK/near.blend PREVIEW.png VISUAL.glb near
blender -b SOURCE.blend --python tools/jellyfish_boss/build_surface_rig.py -- WORK/far.blend PREVIEW.png VISUAL.glb far
blender -b WORK/near.blend --python tools/jellyfish_boss/bake_source_atlas.py -- docs/bosses/jellyfish/generated/v16_textures
blender -b WORK/near.blend --python tools/jellyfish_boss/export_bedrock_geometry.py -- docs/bosses/jellyfish/generated/jellyfish_boss_v16.geo.json
blender -b WORK/far.blend --python tools/jellyfish_boss/export_bedrock_geometry.py -- docs/bosses/jellyfish/generated/jellyfish_boss_v16_far.geo.json
py -3 scripts/assemble_surface_pack.py
py -3 scripts/validate_pack.py
blender -b --python tools/jellyfish_boss/preview_runtime.py -- docs/bosses/jellyfish/generated/jellyfish_boss_v16.geo.json docs/bosses/jellyfish/generated/v16_textures docs/bosses/jellyfish/generated/jellyfish_boss_v16_runtime.png resource_pack/animations/jellyfish_boss.animation.json
py -3 scripts/package_mcaddon.py
```

## Real-game gates

- Use a duplicate test world; do not change graphics settings between variants.
- Spawn exactly one jellyfish, with other bosses absent for the baseline.
- Compare frame time with no jellyfish, v15, and v16, at identical camera views.
- Inspect bell seams, cyan paint, alpha sorting, tentacle joins during the loop.
- Move across 80 blocks and confirm geometry and animation switch correctly.
- Confirm the existing creative spawn egg still places the boss.
- Check the content log; mathematical validation is not runtime schema validation.

Primary references: [geometry / face omission](https://learn.microsoft.com/en-us/minecraft/creator/reference/content/visualreference/geometry.v1.12.0),
[distance query](https://learn.microsoft.com/en-us/minecraft/creator/reference/content/molangreference/examples/molangconcepts/queryfunctions),
[Molang geometry selection](https://learn.microsoft.com/en-us/minecraft/creator/documents/molang/practical-molang),
[Blockbench parser](https://github.com/JannisX11/blockbench/blob/master/js/formats/bedrock/bedrock.js).
