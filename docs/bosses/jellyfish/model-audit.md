# Jellyfish boss model audit

Audited on 2026-09-28 from the archived April 2026 source files. This document records provenance and conversion constraints only; the final boss name and gameplay identifier are intentionally not frozen yet.

## Visual identity

The source is a floating neon jellyfish with a dark near-black bell, cyan luminous streaks and dots, and purple-pink organic tentacles. Its silhouette is distinct from Pinene and remains readable as a large hovering boss.

## Source ranking

1. **Primary visual source:** `Meshy_AI_Neon_Jellyfish_in_the_0405163425_texture.glb`
   - 17,854,848 bytes
   - SHA-256 `9DA58B10A8E6BBCDABAA2AACD72A1C802D567A744FFD98E9AEC5718A1F7BC9EE`
   - 1 mesh, 11,460 vertices, 11,020 triangles
   - one UV set and three packed 2048x2048 maps
   - no armature and no animation
2. **Editable segmentation reference:** `3.blend`
   - 14,752,009 bytes
   - SHA-256 `E4BDFDA620BF48D7F21DA570718CCAE24F555033838DF2F9E24490F900531311`
   - separate bell and tentacle objects, but no armature
   - tentacles: about 18.6k triangles plus a Geometry Nodes modifier
   - bell: about 52.4k triangles
3. **Separated export reference:** `jelly.glb`
   - 15,682,752 bytes
   - SHA-256 `DD1CB803E9F2E39F189B4EA1B97CCF65EB6D808FD6DD1D69CEDC90E755D0C47B`
   - 2 meshes and about 73.2k triangles total
   - preserves the intended color maps but is much heavier than the primary source
4. **Tentacle-only reference:** `jellysayokusyu.glb`
   - 11,004,020 bytes
   - SHA-256 `8A7EC261B8BE8EEB74CB6D0BE506F5D20727DF6AE3DC08F1F646D59571E49ED1`
   - 1 mesh, 18,640 triangles, no armature

The loose `jelly.obj` and `kurageexp.obj` exports point to MTL files with no diffuse texture map and therefore render white. They are not suitable as the visual source. The original loose Meshy OBJ is approximately 260 MB and is retained only as an archive.

## Bedrock decision

Do not ship the arbitrary triangle mesh or a restricted `poly_mesh`. Rebuild the runtime model as supported Bedrock cuboid geometry, using the primary GLB for silhouette and color reference and the separated files only for part boundaries.

Draft runtime targets:

- freeze bone names and pivots before attack animation work
- separate bell, core, major tentacle chains, and optional short inner tendrils
- use a 256x256 or 512x512 atlas
- reproduce cyan markings with an emissive layer already supported by the repository
- prioritize the 5-15 block combat silhouette over tiny surface detail
- keep the source binaries outside Git until a final, intentionally selected working asset exists

## Next gates

1. Confirm encounter scale and the boss's final name.
2. Choose the number of independently animated major tentacles.
3. Build a cuboid greybox and validate it in Bedrock before final texturing.
4. Lock the skeleton, then implement idle, swim, telegraphs, attacks, stagger, and death.
5. Tune gameplay only after real-device animation timing is known.

## Topology finding and rebuild decision

The April editable scene confirms that the visible damage is structural rather than a simple export glitch:

- the source tentacle object contains 21 disconnected components
- its dominant component merges most tentacles through the central mass, so clean per-tentacle weighting is not recoverable automatically
- the bell object contains 25,429 disconnected components, including many microscopic surface fragments
- retaining the archived model as visual reference while rebuilding supported runtime geometry is therefore mandatory

## Confirmed rig direction

The boss is an airborne encounter. Greybox v03 replaces the damaged lower mesh with 16 continuous, independently controlled tentacles:

- 8 long outer tentacles, 4 joints each
- 8 shorter inner oral arms, 3 joints each
- 56 tentacle bones plus `root` and `bell`
- overlapping segments hide all joint gaps
- unique phase offsets prevent synchronized mechanical motion
- an 80-frame idle loop and bell pulse are included in the Blender working copy

The current dome is still the archived visual reference and the new tentacles are untextured greybox geometry. Final Bedrock cuboids and the texture atlas remain separate approval gates.

### Reproducible greybox build

Run Blender with the archived separated scene as the input:

`blender SOURCE.blend --background --python tools/jellyfish_boss/build_clean_tentacle_rig.py -- OUTPUT.blend PREVIEW.png`

The builder requires source objects `Meshy_Mesh_0` and `Meshy_Mesh_0.008`, hides the damaged tentacle mesh, preserves the bell as a visual reference, and creates the clean rig without modifying the source file.
