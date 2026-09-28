# Jellyfish boss material plan

Status: v13 near-detail geometry exported as 801 Bedrock cuboids (9,612 maximum rendered triangles). Blender materials remain a visual target until the texture atlas and in-game render controllers are wired.

## Visual target

- Preserve the source model's dark navy/violet body, magenta tissue, cyan markings, and wet highlights.
- Read as dense jelly, not clear glass: the silhouette must remain visible in combat.
- Keep an irregular dark internal mass visible through the bell.
- Let only selected cyan and pink markings emit; the entire body must not glow uniformly.

## Bedrock render stack

| Pass | Geometry | Vanilla material | Target |
| --- | --- | --- | --- |
| Gel shell | Bell and outer tentacle skin | `entity_alphablend` | RGBA alpha 0.55-0.70; smooth wet surface |
| Inner tissue | Core and oral-arm mass | `entity_alphatest` | Alpha 0.88-1.00; prevents the boss from disappearing |
| Bioluminescence | Cyan stripes and sparse pink spots | `entity_emissive_alpha` | Separate TGA overlay and render controller |
| Edge breakup | Frill and narrow strand tips | `entity_alphatest` | Hard cutout details without excessive blend sorting |

## Vibrant Visuals texture set

- Use a 512x512 atlas and a matching RGBA MERS image.
- MERS channels: R metalness 0; G localized emission; B roughness 0.16-0.30; A subsurface 0.55-0.80 on gel.
- Add a normal map for shallow ripples only; no heavy bumps.
- Classic graphics fallback keeps alpha-blend and emissive overlays even when MERS is unavailable.

## Constraints

- Keep the 16 independently animated tentacles and the 58-bone rig.
- Use five overlapping tapered visual cubes per tentacle bone in the v13 near LOD to hide gaps.
- Avoid full-body low alpha: overlapping transparent tentacles can sort badly in Bedrock.
- Use v13 (801 cuboids) only as the near LOD; retain v12 (511) and v06 (398) as medium/far candidates.
- Keep the near model at or below the approved ~10,000 rendered-triangle ceiling.
- Validate in-game at 5, 10, 16, and 24 blocks with Vibrant Visuals both on and off before wiring LOD switches.
