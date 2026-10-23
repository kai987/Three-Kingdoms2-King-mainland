# Terrain edit prompt

Tool: built-in `image_gen.imagegen`, existing-image edit, opaque background.

Input: `edit-reference.png` — nearest-neighbor 5× crop of the immutable
`before-map.png`, native rectangle `(150,325,160,200)`.

Output retained as `generated-edit.png`. Only the two bounded mountain masks
are composited into the game asset; the rest of the generated image is unused.

Exact prompt:

> Use case: precise-object-edit. This is an actual cropped NES strategy-game terrain asset, 800x1000 reference pixels representing a 160x200 native-pixel patch. Edit this exact image in place with identical crop, framing and proportions; no city labels, no text, no annotations. Make ONLY TWO tiny terrain edits. (1) At reference coordinates roughly x225..430, y215..320, immediately below and right of the upper-left large orange-red mountain and immediately left/above the white castle centered near (500,390), the residual small green/brown foothill looks like a pasted green patch. Repaint this SAME little foothill as coherent reddish-brown/orange rock connected to the neighboring orange-red mountain slope. Use exactly the adjacent mountain's black crevices, red-brown shading, warm orange/yellow ridges and dithered pixel texture. Remove the small green rock patch without painting surrounding grass brown. Keep the existing larger mountain and its silhouette intact. (2) Add ONE small GREEN mountain in the clear grass INSIDE reference rectangle x265..435, y475..590, centered around x340,y545, with peak near (335,480) and base no lower than y590. This is the empty wedge above the near-horizontal tan road at y610 and left of the diagonal road, between the upper white castle and the bottom-center white castle. The new green mountain must match the existing small green peak near (160,840): black shadow face, bright green ridge, dark green foot, native pixel/dither style. Fit completely in that rectangle, leaving a grass gap to every road. This is a small mountain, not a large range or extra hills. Invariants: every white castle, black castle outline, tan road, bridge, blue river, existing green mountain elsewhere, all other orange mountains, and the grass texture outside these two tiny areas must retain their exact positions and geometry. Keep the source's pixel resolution character. Do not smooth, blur, modernize, redraw the entire map, alter paths, introduce roads or additional rivers. Return the same image extent, ideally 800x1000, no margins or borders.
