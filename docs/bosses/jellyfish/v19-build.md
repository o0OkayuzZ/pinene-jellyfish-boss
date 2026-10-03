# v19 central connection

The v18 in-game recording showed a gap between the central tissue and the
inside of the bell. This revision restores only that missing connection.
Three tapered tissue cuboids overlap the existing core and end on a rendered
inner bell face. The complete terminal cap fits inside that face in both LODs.
The connector, core and bell share the bell bone, including its pulse.

Existing shell and tentacle cuboids, pivots, animation data, textures and
behavior components are unchanged. The connector reuses the core texture tile.
Near: 529 cuboids / 3,308 triangles. Far: 177 / 1,132. The change adds three
cuboids and 36 triangles per LOD, with no additional bones, textures or layers.
BP/RP version: 0.1.4. Real-game appearance still requires user confirmation.

## Rebuild

Use the v18 near/far working blend files as inputs to attach_central_core.py,
then export_bedrock_geometry.py into jellyfish_boss_v19.geo.json and
jellyfish_boss_v19_far.geo.json. Keep v18_textures and the v17 animation file.
The complete build_flexible_rig.py also invokes this connection step after
assigning existing UV tiles. assemble_flexible_pack.py installs the results;
validate_pack.py and package_mcaddon.py validate and package v0.1.4.

audit_flexible_motion.py verifies the three overlaps, the whole terminal cap
against the exported inner north face, shared bell ownership, the existing
16 roots and 481 animation poses. It does not measure game FPS or shaders.
Preview from the exported JSON with preview_runtime.py using still/underside
or loop/underside. Animation and behavior cleanup remain the next stage.
