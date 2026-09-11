# Animation expansion

Built-in image generation was used with the original sprite sheet as an identity
reference. Production asset: `assets/motion_v2.webp` (format-converted from the
generated PNG, alpha retained). Original sprites are preserved.

Prompt: preserve the original navy/teal chibi anime companion, cyan eyes, triangular
clip and halo, dark hoodie with cyan trim, skirt, opaque leggings and sneakers.
Create a transparent 4-by-4 atlas with consistent scale and baseline: first two
rows are eight sequential right-facing running poses with alternating leg contact,
compression, passing and airborne phases; third row is four overhead stretching
poses; fourth row is four happy dance poses. Smooth cel-shaded anime, full bodies,
padding, no text, grid lines, props or background.

Mapping: base frames 0–11; new running 12–19; stretching 20–23; dancing 24–27.
Breathing and hopping also use small runtime transforms.

## Idle repair v3

Built-in imagegen created sixteen new full-body idle poses in `idle_v3.webp`.
Prompt: preserve the original navy/teal chibi, hoodie, leggings, sneakers, halo
and clip; transparent 4x4 atlas with large empty margins. Poses: standing,
half-blink, blink, shy head tilt, curious up-left look, look blink, yawn, eye rub,
sitting, sitting blink, sway left/right, drowsy, curled sleep, waking, wave.
A second built-in background-extraction pass removed a baked checkerboard,
preserving poses. Format conversion retained alpha.

Unlike the old equal-height crop, v3 explicitly uses row boundaries
0, 355, 675, 955, 1254 (relative to source height 1254).
Runtime alpha bounds align each complete sprite inside a padded 270px frame,
using one shared scale so sitting characters are not enlarged.
Old idle IDs are remapped; full new atlas is also available at IDs 28–43.
