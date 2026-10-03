# v21 blended connection

The v20 game screenshot showed a narrow neck and a color boundary where
the central membrane met the oral-arm bundle. The lower foot is now buried
in the existing core, with eight shallow folds and a wider, earlier flare.
The upper shoulder and 32 inset inner-bell contacts retain their v20 shape.
Connector colors project the archived oral tissue over the new membrane,
compressing source height continuously to avoid unrelated upper bell colors.

Near remains 32 sectors x three spans: 96 panels / 384 triangles.
Far remains 16 sectors x two spans: 32 panels / 128 triangles.
Totals remain 622 cuboids / 3,656 triangles near, 206 / 1,224 far.
The 114-bone skeleton, accepted v17 motion, two render layers and two
512-square color/normal/MERS sets are unchanged. BP/RP version is 0.1.6.
Only connector geometry and its existing tissue UV slots 142-237 change.
All pre-connector geometry, pivots and atlas pixels are preserved.

## Rebuild and checks

Run attach_central_core.py on the v20 near/far working blends, then export
with export_bedrock_geometry.py to jellyfish_boss_v21.geo.json and
jellyfish_boss_v21_far.geo.json. Bake the near blend with bake_source_atlas.py
into v21_textures. build_flexible_rig.py invokes the same helper.
Run assemble_flexible_pack.py, validate_pack.py and package_mcaddon.py.
The motion input remains jellyfish_boss_v17.animation.json.

audit_flexible_motion.py verifies 96 spans, all 32 terminal contacts, 16
tentacle roots and 481 poses. Scope checks compare old geometry and atlas
pixels with v18, allowing only the connector geometry and UV cells.
Previews use exported JSON and installed atlas data with approximate lighting.
Actual game appearance, transparency, LOD and FPS still need review.
Animation and behavior cleanup follow the user's acceptance of the model.
