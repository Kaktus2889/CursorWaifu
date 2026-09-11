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
