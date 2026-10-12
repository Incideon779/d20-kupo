# How the die is numbered

A real twenty-sided die: 20 faces, opposites add to 21, and 20 is not next to 19 (that layout is a spindown).

This one follows the Chessex-style table. Around 20, with 8 toward the camera: 2 is on the viewer's left, 14 is on the right. From outside the 20 face, the neighbors go 8, then 14, then 2.

Sources for that neighborhood: the Chessex / GameStop diagram discussed on BoardGame.SE (2, 14, and 8 around 20), Dice Maniacs' Club ("the d20 has an 8 below the 20"), and the Chessex-style adjacency used for the d20 maze on Puzzling.SE. The full neighbor list is `NEI` in `tools/build_die.py`.

`tools/build_die.py` checks, every time it writes `js/die-data.js`:

- opposites add to 21 and their normals point opposite ways
- settling on each face from 1 to 20 actually puts that face up, with the top of the numeral pointing away from a camera on +z
- 8 is the neighbor of 20 closest to the camera
- 2 is on the left of 20, 14 is on the right

The solid is a regular icosahedron (12 vertices, 20 flat triangles), scaled so the top face sits 1 unit from the center. It is not a UV sphere.
