# Jellyfish boss material plan

Status: v15 optimized near-detail geometry exported as 1,136 Bedrock cuboids but only 9,176 rendered triangles after join-face culling. Three 512x512 color/normal/MERS texture sets are generated and the 40x11 bell UV grid is wired; pack integration remains staged.

## Visual target

- Preserve the source model's dark navy/violet body, magenta tissue, cyan markings, and wet highlights.
- Read as dense jelly, not clear glass: the silhouette must remain visible in combat.
- Keep an irregular dark internal mass visible through the bell.
- Let only selected cyan and pink markings emit; the entire body must not glow uniformly.
- Paint cyan rays continuously across adjacent panel UVs and use dark mottling to disguise cuboid boundaries.
- Keep shell-edge alpha high enough that background-colored seams do not appear between panels.

## Bedrock render stack

| Pass | Geometry | Vanilla material | Target |
| --- | --- | --- | --- |
| Gel shell | Bell and outer tentacle skin | `entity_alphablend` | RGBA alpha 0.55-0.70; smooth wet surface |
| Inner tissue | Core and oral-arm mass | `entity_alphatest` | Alpha 0.88-1.00; prevents the boss from disappearing |
| Bioluminescence | Cyan stripes and sparse pink spots | `entity_emissive_alpha` | Separate TGA overlay and render controller |
| Edge breakup | Frill and narrow strand tips | `entity_alphatest` | Hard cutout details without excessive blend sorting |

## Vibrant Visuals texture set

- Generated separate 512x512 shell, tissue, and glow color maps with matching RGBA MERS and normal maps.
- The bell uses a 40x11 atlas grid with 12x44-pixel cells, so adjacent dome panels sample neighboring texture regions instead of repeating one pixel.
- MERS channels: R metalness 0; G localized emission; B roughness; A subsurface scattering.
- Shell: low roughness, near-zero emission, high subsurface. Tissue: moderate roughness and localized pink emission. Glow: full emissive green channel.
- Normal maps use shallow organic ripples only; no heavy bumps.
- Classic graphics fallback keeps the color alpha-blend and emissive overlay passes when PBR maps are unavailable.
- Before copying these files into the integrated resource pack, raise its minimum engine version to 1.21.120 and add the `pbr` capability; do not silently change the shared manifest during model staging.

## Constraints

- Keep the 16 independently animated tentacles and the 58-bone rig.
- Use seven open-ended tapered visual cuboids per tentacle bone in the v15 near LOD.
- Back the translucent bell with 40 dark inner ribs so shell seams do not reveal the background.
- Omit the two hidden join faces on bell and tentacle cuboids; v15 removes 2,228 faces / 4,456 triangles.
- Avoid full-body low alpha: overlapping transparent tentacles can sort badly in Bedrock.
- Use v15 (1,136 cuboids / 9,176 rendered triangles) only as the near LOD; retain v12 (511) and v06 (398) as medium/far candidates.
- Keep the near model at or below the approved ~10,000 rendered-triangle ceiling.
- Validate in-game at 5, 10, 16, and 24 blocks with Vibrant Visuals both on and off before wiring LOD switches.
