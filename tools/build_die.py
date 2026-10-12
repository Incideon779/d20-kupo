#!/usr/bin/env python3
"""Numbered icosahedron, face textures, and the data the page rolls."""

import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
FACES = os.path.join(ASSETS, "faces")
SRC_DIE = os.path.expanduser("~/Downloads/d20kupo.jpg")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"

# Chessex-style tabletop layout. Opposites sum to 21.
# Around 20, viewed with 8 toward the camera: 2 on the left, 14 on the right.
# Sources: BoardGame.SE (Chessex/GameStop neighborhood of 20 is 2, 14, 8),
# Dice Maniacs' Club ("the d20 has an 8 below the 20"),
# and the Chessex-style adjacency used for the d20 maze on Puzzling.SE.
NEI = {
    1: (7, 19, 13),
    2: (20, 12, 18),
    3: (17, 16, 19),
    4: (14, 11, 18),
    5: (15, 13, 18),
    6: (16, 14, 9),
    7: (17, 15, 1),
    8: (20, 10, 16),
    9: (6, 19, 11),
    10: (8, 12, 17),
    11: (9, 13, 4),
    12: (2, 10, 15),
    13: (1, 5, 11),
    14: (20, 6, 4),
    15: (12, 7, 5),
    16: (8, 3, 6),
    17: (10, 3, 7),
    18: (2, 5, 4),
    19: (3, 1, 9),
    20: (2, 8, 14),
}

# Photo triangle around the clean face numbered 2. Pom-pom stays outside.
PHOTO_TRI = np.array([[592.0, 372.0], [438.0, 790.0], [768.0, 845.0]], dtype=np.float64)

S = 1024
SIDE = 860.0


def neigh_ok():
    for n, nbrs in NEI.items():
        assert len(nbrs) == 3 and len(set(nbrs)) == 3
        for m in nbrs:
            assert n in NEI[m]
            assert m != n
        opp = 21 - n
        assert sorted(21 - m for m in nbrs) == sorted(NEI[opp])


def icosahedron():
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    verts = []
    for i in (-1.0, 1.0):
        for j in (-1.0, 1.0):
            verts.append((0.0, i, j * phi))
            verts.append((i, j * phi, 0.0))
            verts.append((j * phi, 0.0, i))
    v = np.array(verts, dtype=np.float64)
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    # edges: closest pairs
    d = np.linalg.norm(v[:, None, :] - v[None, :, :], axis=2)
    np.fill_diagonal(d, 9)
    edge_len = d.min()
    adj = d < edge_len * 1.15
    faces = []
    for a in range(12):
        nbrs = np.where(adj[a])[0]
        for i, b in enumerate(nbrs):
            if b < a:
                continue
            for c in nbrs[i + 1 :]:
                if c > b and adj[b, c]:
                    faces.append((int(a), int(b), int(c)))
    assert len(faces) == 20, len(faces)
    out = []
    for a, b, c in faces:
        n = np.cross(v[b] - v[a], v[c] - v[a])
        if np.dot(n, v[a]) < 0:
            b, c = c, b
        out.append((a, b, c))
    return v, out, float(edge_len)


def face_neighbors(faces):
    edge_owner = {}
    neigh = [[] for _ in faces]
    for fi, (a, b, c) in enumerate(faces):
        for u, w in ((a, b), (b, c), (c, a)):
            key = (u, w) if u < w else (w, u)
            if key in edge_owner:
                oj = edge_owner[key]
                neigh[fi].append(oj)
                neigh[oj].append(fi)
            else:
                edge_owner[key] = fi
    for row in neigh:
        assert len(row) == 3
    return neigh, list(edge_owner.keys())


def label_faces(neigh):
    """Map geometric face index -> number, matching NEI."""
    sets = {i: set(NEI[i]) for i in range(1, 21)}
    order = []
    seen = set()
    stack = [0]
    seen.add(0)
    while stack:
        i = stack.pop()
        order.append(i)
        for j in neigh[i]:
            if j not in seen:
                seen.add(j)
                stack.append(j)
    assign = [0] * 20
    used = set()

    def bt(k):
        if k == 20:
            return True
        fi = order[k]
        for n in range(1, 21):
            if n in used:
                continue
            good = True
            for j in neigh[fi]:
                m = assign[j]
                if m and (m not in sets[n]):
                    good = False
                    break
            if not good:
                continue
            for j in range(20):
                m = assign[j]
                if not m or j in neigh[fi]:
                    continue
                if m in sets[n]:
                    good = False
                    break
            if not good:
                continue
            assign[fi] = n
            used.add(n)
            if bt(k + 1):
                return True
            used.remove(n)
            assign[fi] = 0
        return False

    assert bt(0), "no embedding of the Chessex map"
    return assign


def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )


def qrot(q, v):
    x, y, z, w = q
    tx = 2 * (y * v[2] - z * v[1])
    ty = 2 * (z * v[0] - x * v[2])
    tz = 2 * (x * v[1] - y * v[0])
    cx = y * tz - z * ty
    cy = z * tx - x * tz
    cz = x * ty - y * tx
    return (v[0] + w * tx + cx, v[1] + w * ty + cy, v[2] + w * tz + cz)


def qnorm(q):
    n = math.sqrt(sum(c * c for c in q))
    return tuple(c / n for c in q)


def from_unit(a, b):
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    d = float(np.dot(a, b))
    if d > 0.999999:
        return (0.0, 0.0, 0.0, 1.0)
    if d < -0.999999:
        axis = np.cross(a, (1.0, 0.0, 0.0))
        if np.linalg.norm(axis) < 1e-6:
            axis = np.cross(a, (0.0, 1.0, 0.0))
        axis = axis / np.linalg.norm(axis)
        s = math.sin(math.pi / 2)
        return (axis[0] * s, axis[1] * s, axis[2] * s, math.cos(math.pi / 2))
    c = np.cross(a, b)
    return qnorm((c[0], c[1], c[2], 1.0 + d))


def qaxis(axis, ang):
    axis = np.asarray(axis, dtype=np.float64)
    axis = axis / np.linalg.norm(axis)
    s = math.sin(ang / 2.0)
    return (axis[0] * s, axis[1] * s, axis[2] * s, math.cos(ang / 2.0))


def apply_q(verts, q):
    return np.array([qrot(q, p) for p in verts], dtype=np.float64)


def normals_of(verts, faces):
    out = []
    for a, b, c in faces:
        n = np.cross(verts[b] - verts[a], verts[c] - verts[a])
        n = n / np.linalg.norm(n)
        out.append(n)
    return out


def centroids(verts, faces):
    return np.array([verts[list(f)].mean(axis=0) for f in faces])


def orient_quat(verts, faces, numbers):
    """20 to +Y, then yaw so 8 sits toward +Z."""
    ns = normals_of(verts, faces)
    i20 = numbers.index(20)
    i8 = numbers.index(8)
    q1 = from_unit(ns[i20], (0.0, 1.0, 0.0))
    c8 = qrot(q1, centroids(verts, faces)[i8])
    yaw = math.atan2(c8[0], c8[2])
    q2 = qaxis((0.0, 1.0, 0.0), -yaw)
    return qmul(q2, q1)


def settle_quat(normal, glyph):
    """Rotate this face to +Y and its glyph-up to -Z. Three.js xyzw."""
    q1 = from_unit(normal, (0.0, 1.0, 0.0))
    g2 = np.array(qrot(q1, glyph))
    g2[1] = 0.0
    q2 = from_unit(g2, (0.0, 0.0, -1.0))
    return qmul(q2, q1)


def texture_triangle():
    h = SIDE * math.sqrt(3.0) / 2.0
    cx = S / 2.0
    top_y = 36.0
    cy = top_y + 2.0 * h / 3.0
    top = np.array([cx, top_y])
    bl = np.array([cx - SIDE / 2.0, cy + h / 3.0])
    br = np.array([cx + SIDE / 2.0, cy + h / 3.0])
    return top, bl, br, np.array([cx, cy])


def warp_master(src_rgb):
    """Equilateral face from the photo, exterior filled so mips do not go black."""
    top, bl, br, cent = texture_triangle()
    dst = np.stack([top, bl, br])
    # Pull the photo corners in so the pom-pom and the outer frame stay out.
    photo = PHOTO_TRI.copy()
    photo = photo.mean(axis=0) + (photo - photo.mean(axis=0)) * 0.90
    H, W = src_rgb.shape[:2]
    out = np.zeros((S, S, 3), np.float64)
    minx = int(max(0, np.floor(dst[:, 0].min())))
    maxx = int(min(S - 1, np.ceil(dst[:, 0].max())))
    miny = int(max(0, np.floor(dst[:, 1].min())))
    maxy = int(min(S - 1, np.ceil(dst[:, 1].max())))
    yy, xx = np.mgrid[miny : maxy + 1, minx : maxx + 1]
    P = np.stack([xx, yy], -1).astype(np.float64)
    A, B, C = dst
    v0, v1 = B - A, C - A
    den = v0[0] * v1[1] - v1[0] * v0[1]
    v2 = P - A
    v = (v2[..., 0] * v1[1] - v1[0] * v2[..., 1]) / den
    w = (v0[0] * v2[..., 1] - v2[..., 0] * v0[1]) / den
    u = 1.0 - v - w
    mask = (u >= -0.002) & (v >= -0.002) & (w >= -0.002)
    srcp = u[..., None] * photo[0] + v[..., None] * photo[1] + w[..., None] * photo[2]
    sx = np.clip(srcp[..., 0], 0, W - 1.001)
    sy = np.clip(srcp[..., 1], 0, H - 1.001)
    x0 = np.floor(sx).astype(np.int32)
    y0 = np.floor(sy).astype(np.int32)
    x1 = np.clip(x0 + 1, 0, W - 1)
    y1 = np.clip(y0 + 1, 0, H - 1)
    fx = (sx - x0)[..., None]
    fy = (sy - y0)[..., None]
    samp = (
        src_rgb[y0, x0] * (1 - fx) * (1 - fy)
        + src_rgb[y0, x1] * fx * (1 - fy)
        + src_rgb[y1, x0] * (1 - fx) * fy
        + src_rgb[y1, x1] * fx * fy
    )
    block = out[miny : maxy + 1, minx : maxx + 1]
    block[:] = np.where(mask[..., None], samp, block)
    out[miny : maxy + 1, minx : maxx + 1] = block
    # Spread edge color into the margin so filtering does not pick up black.
    known = np.zeros((S, S), dtype=bool)
    known[miny : maxy + 1, minx : maxx + 1] = mask
    color = out.copy()
    for _ in range(28):
        acc = np.zeros_like(color)
        wgt = np.zeros((S, S))
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            sh = np.roll(np.roll(color, dy, 0), dx, 1)
            sm = np.roll(np.roll(known, dy, 0), dx, 1)
            acc += sh * sm[..., None]
            wgt += sm
        fill = (~known) & (wgt > 0)
        color[fill] = acc[fill] / wgt[fill, None]
        known |= fill
        if known.all():
            break
    return color, known


def erase_old_numeral(img):
    """Hide the photo's 2 with the face's own crimson, and leave the gold scrolls."""
    img = img.copy()
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    sat = img.max(axis=-1) - img.min(axis=-1)
    yy, xx = np.mgrid[0:S, 0:S]
    # Yellow metal of the filigree. Pearl (the old numeral) has blue close to green.
    gold = (g > b + 28) & (r > 110) & (g > 80) & (lum > 70)
    enamel = (r > 30) & (r > g + 18) & (g < 55) & (b < 48) & (lum < 110) & (lum > 6)
    box = (yy > 280) & (yy < 720) & (xx > 320) & (xx < 800)
    seed = box & (lum > 130) & (sat < 100) & (b > 80) & ~gold
    lab, _n = ndimage.label(seed)
    sizes = np.bincount(lab.ravel())
    sizes[0] = 0
    glyph = lab == int(np.argmax(sizes))
    mask = glyph.copy()
    for _ in range(40):
        grown = ndimage.binary_dilation(mask)
        expand = grown & ~mask & ~enamel & ~gold & box
        if int(expand.sum()) < 3:
            break
        mask |= expand
    mask = ndimage.binary_closing(mask, iterations=4)
    ys, xs = np.where(mask)
    cx, cy = float(xs.mean()), float(ys.mean())
    rx = (int(xs.max()) - int(xs.min())) / 2.0 + 48.0
    ry = (int(ys.max()) - int(ys.min())) / 2.0 + 44.0
    ell = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1.0
    # Keep a gold scroll that reaches outside the field. Cover scraps of the numeral.
    cover = ell.copy()
    glab, _gn = ndimage.label(gold)
    gsizes = np.bincount(glab.ravel())
    for gid in range(1, len(gsizes)):
        comp = glab == gid
        if comp.any() and (~ell & comp).any():
            cover &= ~comp
    ring = enamel & ~ell & (((xx - cx) / (rx + 70)) ** 2 + ((yy - cy) / (ry + 70)) ** 2 <= 1.0)
    if int(ring.sum()) < 50:
        ring = enamel & ~ell
    col = np.median(img[ring].reshape(-1, 3), axis=0)
    rng = np.random.default_rng(4)
    n1 = ndimage.gaussian_filter(rng.normal(0, 1, (S, S)), 0.7)
    n2 = ndimage.gaussian_filter(rng.normal(0, 1, (S, S)), 2.4)
    grain = n1 * 7.5 + n2 * 4.0
    rad = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    rad = np.clip(rad, 0, 1)
    scale = (1.0 + 0.12 * (1.0 - rad) ** 1.6)[..., None]
    filled = np.clip(col.reshape(1, 1, 3) * scale, 0, 255)
    filled = filled.copy()
    filled[..., 0] = np.clip(filled[..., 0] + grain * 1.15, 0, 255)
    filled[..., 1] = np.clip(filled[..., 1] + grain * 0.28, 0, 255)
    filled[..., 2] = np.clip(filled[..., 2] + grain * 0.22, 0, 255)
    dist = ndimage.distance_transform_edt(cover)
    alpha = np.clip(dist / 26.0, 0, 1) * cover
    print(
        "enamel field",
        round(cx),
        round(cy),
        "cover",
        int(cover.sum()),
        "color",
        [round(float(v)) for v in col],
    )
    return np.clip(img * (1.0 - alpha[..., None]) + filled * alpha[..., None], 0, 255)


def paint_faces(blank):
    os.makedirs(FACES, exist_ok=True)
    font = ImageFont.truetype(FONT, 300)
    top, bl, br, cent = texture_triangle()
    sheet = Image.new("RGB", (5 * 180, 4 * 180), (20, 8, 8))
    for n in range(1, 21):
        face = Image.fromarray(blank.astype(np.uint8), "RGB")
        label = str(n)
        # Measure at a draft size, then scale the mask so every numeral has the same cap height.
        probe = ImageFont.truetype(FONT, 240)
        bb = probe.getbbox(label)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        target_h = 214
        size = int(240 * target_h / th)
        # Two-digit numerals stay inside the enamel field, clear of the scrolls.
        font_n = ImageFont.truetype(FONT, size)
        bb = font_n.getbbox(label)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        if tw > 308:
            font_n = ImageFont.truetype(FONT, int(size * 308 / tw))
            bb = font_n.getbbox(label)
            tw, th = bb[2] - bb[0], bb[3] - bb[1]
        mask = Image.new("L", (S, S), 0)
        md = ImageDraw.Draw(mask)
        x = int(cent[0] - tw / 2 - bb[0])
        y = int(cent[1] - th / 2 - bb[1])
        md.text((x, y), label, font=font_n, fill=255)
        if n in (6, 9):
            bar_w = int(tw * 0.66)
            bar_h = max(8, size // 18)
            bx0 = int(cent[0] - bar_w / 2)
            by0 = int(y + bb[3] + size * 0.04)
            md.rounded_rectangle((bx0, by0, bx0 + bar_w, by0 + bar_h), radius=4, fill=255)
        # Raised pearl: dark offset, body, top highlight.
        alpha = mask.filter(ImageFilter.GaussianBlur(0.6))
        a = np.array(alpha).astype(np.float64) / 255.0
        shade = np.array(mask.filter(ImageFilter.GaussianBlur(1.4))).astype(np.float64) / 255.0
        # shift shade down-right for the cast
        cast = np.zeros_like(shade)
        cast[6:, 5:] = shade[:-6, :-5] * 0.55
        base = np.array(face).astype(np.float64)
        base *= 1.0 - cast[..., None] * 0.45
        # body
        body = np.array([236.0, 230.0, 221.0])
        highlight = np.array([255.0, 252.0, 246.0])
        # vertical gradient across the glyph
        yy = np.linspace(0, 1, S)[:, None]
        grad = highlight * (1 - yy) + body * yy
        base = base * (1 - a[..., None]) + grad * a[..., None]
        # cool rim on the lower edge of the glyph so it reads as inlay
        edge = a - np.array(mask.filter(ImageFilter.MinFilter(3))).astype(np.float64) / 255.0
        edge = np.clip(edge, 0, 1)
        rim = np.array([92.0, 78.0, 64.0])
        base = base * (1 - edge[..., None] * 0.85) + rim * edge[..., None] * 0.85
        face = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")
        face.save(os.path.join(FACES, f"{n:02d}.jpg"), quality=92)
        thumb = face.resize((180, 180), Image.Resampling.LANCZOS)
        sheet.paste(thumb, (((n - 1) % 5) * 180, ((n - 1) // 5) * 180))
    sheet.save("/tmp/d20work/faces.jpg", quality=90)


def wood_texture():
    src = Image.open(SRC_DIE).convert("RGB")
    # Left of the die: one run of grain, no mirrored diamond.
    crop = src.crop((0, 740, 420, 1120))
    tile = crop.resize((1600, 1000), Image.Resampling.LANCZOS)
    # Pull it a little darker so the die stays the bright object.
    arr = np.array(tile).astype(np.float64)
    arr = arr * 0.78 + np.array([18, 8, 4])
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(
        os.path.join(ASSETS, "wood.jpg"), quality=90
    )


def plane_uv(verts, normal, glyph, idx):
    """UVs in Three.js convention: v is up, origin at the bottom left of the image."""
    top, bl, br, cent = texture_triangle()
    tri = np.stack([top, bl, br])
    tc = tri.mean(axis=0)
    # Texture vertex radius in pixels (top vertex).
    rt = float(np.linalg.norm(top - tc))
    c = verts[list(idx)].mean(axis=0)
    right = np.cross(glyph, normal)
    right = right / np.linalg.norm(right)
    r3 = float(np.linalg.norm(verts[idx[0]] - c))
    uvs = []
    for i in idx:
        d = verts[i] - c
        du = float(np.dot(d, right))
        dv = float(np.dot(d, glyph))
        px = tc[0] + (du / r3) * rt
        py = tc[1] - (dv / r3) * rt
        uvs.append([px / S, 1.0 - py / S])
    return uvs


def main():
    os.makedirs("/tmp/d20work", exist_ok=True)
    neigh_ok()
    verts, faces, edge_len = icosahedron()
    neigh, edges = face_neighbors(faces)
    numbers = label_faces(neigh)
    # Chirality: 2 on the viewer's left, 14 on the right, 8 toward the camera.
    q = orient_quat(verts, faces, numbers)
    turned = apply_q(verts, q)
    cens = centroids(turned, faces)
    x2 = float(cens[numbers.index(2)][0])
    x14 = float(cens[numbers.index(14)][0])
    mirrored = False
    if x2 > x14:
        verts = verts.copy()
        verts[:, 0] *= -1
        faces = [(a, c, b) for a, b, c in faces]
        mirrored = True
        q = orient_quat(verts, faces, numbers)
    verts = apply_q(verts, q)
    ns = normals_of(verts, faces)
    # Scale so the top face sits 1 unit from the origin.
    i20 = numbers.index(20)
    radius = abs(float(np.dot(ns[i20], verts[faces[i20][0]])))
    verts = verts / radius
    ns = normals_of(verts, faces)
    # Glyph up. Face 20 is horizontal, so -Z lies in the face and points away from the camera.
    glyphs = []
    for nrm in ns:
        g = np.array([0.0, 0.0, -1.0])
        g = g - nrm * float(np.dot(g, nrm))
        if np.linalg.norm(g) < 0.2:
            g = np.array([0.0, 1.0, 0.0])
            g = g - nrm * float(np.dot(g, nrm))
        glyphs.append(g / np.linalg.norm(g))
    # Face 20 must read upright: glyph up is exactly -Z.
    glyphs[i20] = np.array([0.0, 0.0, -1.0])

    report = []
    face_out = []
    for fi, (a, b, c) in enumerate(faces):
        num = numbers[fi]
        quat = settle_quat(ns[fi], glyphs[fi])
        n2 = qrot(quat, ns[fi])
        g2 = qrot(quat, glyphs[fi])
        assert n2[1] > 0.999, (num, n2)
        assert g2[2] < -0.999, (num, g2)
        # The face that is up is this one.
        ups = [qrot(quat, ns[j])[1] for j in range(20)]
        winner = int(np.argmax(ups))
        assert winner == fi, (num, numbers[winner])
        uvs = plane_uv(verts, ns[fi], glyphs[fi], (a, b, c))
        face_out.append(
            {
                "n": num,
                "idx": [a, b, c],
                "normal": [round(float(x), 6) for x in ns[fi]],
                "uv": [[round(u, 6), round(v, 6)] for u, v in uvs],
                "quat": [round(float(x), 6) for x in quat],
            }
        )
        report.append(num)
    # Opposites and the front neighbor.
    by_n = {f["n"]: f for f in face_out}
    for n in range(1, 21):
        nrm = np.array(by_n[n]["normal"])
        opp = by_n[21 - n]["normal"]
        assert float(np.dot(nrm, opp)) < -0.99, n
    assert abs(by_n[20]["normal"][1] - 1) < 1e-6
    assert by_n[1]["normal"][1] < -0.99
    # 8 is the front neighbor: its centroid has the greatest +Z among 20's neighbors.
    cens = centroids(verts, faces)
    i20 = numbers.index(20)
    front = max(neigh[i20], key=lambda j: cens[j][2])
    assert numbers[front] == 8, numbers[front]
    # 2 left, 14 right.
    assert cens[numbers.index(2)][0] < 0
    assert cens[numbers.index(14)][0] > 0

    data = {
        "positions": [[round(float(x), 6) for x in p] for p in verts],
        "faces": sorted(face_out, key=lambda f: f["n"]),
        "edges": edges,
        "neighbors": {str(n): list(NEI[n]) for n in range(1, 21)},
    }
    js = "window.DIE = " + json.dumps(data, separators=(",", ":")) + ";\n"
    with open(os.path.join(ROOT, "js", "die-data.js"), "w", encoding="utf-8") as f:
        os.makedirs(os.path.join(ROOT, "js"), exist_ok=True)
        f.write(js)
    with open(os.path.join(ASSETS, "die.json"), "w", encoding="utf-8") as f:
        json.dump(data, f)

    src = np.asarray(Image.open(SRC_DIE).convert("RGB"), dtype=np.float64)
    master, _known = warp_master(src)
    blank = erase_old_numeral(master)
    Image.fromarray(np.clip(master, 0, 255).astype(np.uint8)).save("/tmp/d20work/master.jpg", quality=90)
    Image.fromarray(np.clip(blank, 0, 255).astype(np.uint8)).save("/tmp/d20work/blank.jpg", quality=90)
    paint_faces(blank)
    wood_texture()

    ccw = []
    a, b, c = faces[i20]
    # Neighbor across each CCW edge.
    def across(u, w):
        for j in neigh[i20]:
            if u in faces[j] and w in faces[j]:
                return numbers[j]
        raise RuntimeError("edge")

    ccw = [across(a, b), across(b, c), across(c, a)]
    print("faces", len(faces), "verts", len(verts), "mirrored", mirrored)
    print("20 CCW from outside", ccw)
    print("2.x", round(float(cens[numbers.index(2)][0]), 3), "14.x", round(float(cens[numbers.index(14)][0]), 3))
    print("8.z", round(float(cens[numbers.index(8)][2]), 3))
    print("edge", round(edge_len, 4), "settle ok 1..20")
    print("wrote", os.path.join(ROOT, "js", "die-data.js"))


if __name__ == "__main__":
    main()
