"""gas_plant: a gas-fired combined-cycle power block, built so ten can stand in a row along X (footprint ~52 x 50 m).
Front (+Y): the turbine hall, 40 m (X) x 22 m (Y) x 16 m, corrugated cladding on a concrete plinth, roof-edge trim, clerestory
glazing, roller doors. On its roof two air-intake filter houses. Behind it (-Y): two heat-recovery boilers (HRSG) fed by
exhaust transition ducts, each venting into its own 55 m stack with red bands and red aviation lights. Pipe racks and
pipe runs between hall and boilers; three transformers on the +X side.
Parts: Plinth, Hall, Trim, Intake, HRSG, Pipes, Transformers, Stacks, StackBands, WarnLights.
Origin: base centre of the block; front faces +Y."""
import bpy, bmesh, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
from mathutils import Vector, Matrix

C.begin()
# runtime material: painted structural steel (boiler casing, transformer tanks, door frames)
C.MATS["TK_PaintSteel"] = {"tex": "Metal032", "tint": [0.55, 0.58, 0.56], "metal": 0.35, "rough": 0.55, "tile": 2.0}

C.root("gas_plant")
HX0, HX1, HY0, HY1, HH = -20.0, 20.0, 1.0, 23.0, 16.0      # turbine hall box
STX = (-10.0, 10.0)                                         # stack / boiler lines
STY = -21.5; STH = 55.0


def pipe(bm, p0, p1, r, segs=8, mi=0):
    p0 = Vector(p0); p1 = Vector(p1); d = p1 - p0
    vs = C.bm_cyl(bm, r, d.length, segs=segs, mat_index=mi)
    q = Vector((0, 0, 1)).rotation_difference(d.normalized())
    bmesh.ops.transform(bm, matrix=Matrix.Translation((p0 + p1) / 2) @ q.to_matrix().to_4x4(), verts=vs)


def box(bm, x0, x1, y0, y1, z0, z1, mi=0):
    return C.bm_box(bm, (x1 - x0, y1 - y0, z1 - z0), loc=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), mat_index=mi)


def tube(bm, r_in, r_out, z0, z1, cx=0, cy=0, segs=28, mi=0, r_out1=None, r_in1=None, inner=True):
    r_out1 = r_out if r_out1 is None else r_out1; r_in1 = r_in if r_in1 is None else r_in1
    ring = lambda r, z: [bm.verts.new((cx + r * math.cos(2 * math.pi * i / segs), cy + r * math.sin(2 * math.pi * i / segs), z)) for i in range(segs)]
    o0, o1, i0, i1 = ring(r_out, z0), ring(r_out1, z1), ring(r_in, z0), ring(r_in1, z1)
    for i in range(segs):
        j = (i + 1) % segs
        bm.faces.new((o0[i], o0[j], o1[j], o1[i])).material_index = mi
        if inner: bm.faces.new((i0[j], i0[i], i1[i], i1[j])).material_index = mi
        bm.faces.new((o1[i], o1[j], i1[j], i1[i])).material_index = mi
        bm.faces.new((o0[j], o0[i], i0[i], i0[j])).material_index = mi


# ------------------------------------------------------------------ plinth (TK_Concrete)
def plinth(bm):
    box(bm, -24, 30, -27, 26, -0.2, 0.0)                    # yard slab
    box(bm, HX0 - 1, HX1 + 1, HY0 - 1, HY1 + 1, 0.0, 0.9)    # hall plinth
    for sx in STX:
        box(bm, sx - 6, sx + 6, -19, 0, 0.0, 0.5)           # boiler pads
        C.bm_cyl(bm, 4.6, 0.8, loc=(sx, STY, 0.4), segs=20)  # stack foundations
    box(bm, 22.5, 29, 6, 22, 0.0, 0.6)                      # transformer bund
    for k in range(3):                                      # fire walls between transformers
        y = 6.3 + k * 5.2
        box(bm, 22.8, 28.6, y - 0.15, y + 0.15, 0.6, 6.0)
    box(bm, 22.8, 28.6, 21.4, 21.7, 0.6, 6.0)


C.part("Plinth", plinth, [C.mat("TK_Concrete")])


# ------------------------------------------------------------------ hall (corrugated cladding, paint, glass, dark)
def hall(bm):
    z0 = 0.9
    box(bm, HX0, HX1, HY0, HY1, z0, HH, 0)                  # clad box
    # clerestory glazing band (glass slightly proud, dark backing behind it)
    for (x0, x1, y0, y1) in ((HX0 + 1, HX1 - 1, HY1, HY1 + 0.08), (HX0 - 0.08, HX0, HY0 + 1, HY1 - 1), (HX1, HX1 + 0.08, HY0 + 1, HY1 - 1)):
        box(bm, x0, x1, y0, y1, 12.0, 14.2, 3)
        if y1 - y0 < 1: box(bm, x0, x1, y1, y1 + 0.06, 12.0, 14.2, 2)
        else: box(bm, x0 - 0.06 if x0 < 0 else x1, x0 if x0 < 0 else x1 + 0.06, y0, y1, 12.0, 14.2, 2)
    # two roller doors on the front, with frames
    for dx in (-9.0, 9.0):
        box(bm, dx - 3.4, dx + 3.4, HY1, HY1 + 0.3, z0, z0 + 8.6, 1)          # frame
        box(bm, dx - 3.0, dx + 3.0, HY1 + 0.3, HY1 + 0.4, z0, z0 + 8.2, 0)    # door leaf (corrugated)
        box(bm, dx - 3.2, dx + 3.2, HY1 + 0.3, HY1 + 0.9, z0 + 8.2, z0 + 8.9, 1)  # roller box
    # personnel door + canopy, centre front
    box(bm, -1.1, 1.1, HY1, HY1 + 0.2, z0, z0 + 2.5, 1)
    box(bm, -0.8, 0.8, HY1 + 0.2, HY1 + 0.25, z0, z0 + 2.2, 3)
    box(bm, -1.8, 1.8, HY1, HY1 + 1.4, z0 + 2.7, z0 + 2.9, 1)
    # louvre panels low on the sides (ventilation)
    for y in (6, 12, 18):
        for (x0, x1) in ((HX0 - 0.25, HX0), (HX1, HX1 + 0.25)):
            box(bm, x0, x1, y - 1.5, y + 1.5, 3.0, 5.0, 3)
            for k in range(3): box(bm, min(x0, x1) - 0.05, max(x0, x1) + 0.05, y - 1.45, y + 1.45, 3.3 + k * 0.6, 3.45 + k * 0.6, 1)
    # roof: low monopitch-looking slab with ridge vents
    box(bm, HX0 + 0.3, HX1 - 0.3, HY0 + 0.3, HY1 - 0.3, HH, HH + 0.5, 0)
    for x in range(-15, 16, 6):
        box(bm, x - 1.2, x + 1.2, HY0 + 4, HY1 - 4, HH + 0.5, HH + 1.3, 1)
        box(bm, x - 1.5, x + 1.5, HY0 + 3.7, HY1 - 3.7, HH + 1.3, HH + 1.5, 1)


C.part("Hall", hall, [C.mat("TK_Corrugated"), C.mat("TK_PaintSteel"), C.mat("TK_Glass"), C.mat("TK_DarkPlastic")])


# ------------------------------------------------------------------ trim: columns, roof edge capping, gutters, stairs
def trim(bm):
    z0 = 0.9
    for x in [HX0 + 5 * k for k in range(9)]:                       # pilasters on front and back
        for y in (HY1 + 0.15, HY0 - 0.15):
            if abs(x) < 13 and abs(abs(x) - 9) < 4 and y > 10: continue    # skip across doors
            box(bm, x - 0.25, x + 0.25, y - 0.15, y + 0.15, z0, HH, 0)
    for y in [HY0 + 5.5 * k for k in range(5)]:                     # pilasters on the sides
        for x in (HX0 - 0.15, HX1 + 0.15):
            box(bm, x - 0.15, x + 0.15, y - 0.25, y + 0.25, z0, HH, 0)
    # roof edge capping (parapet) all round
    e = 0.45
    box(bm, HX0 - e, HX1 + e, HY1 - 0.1, HY1 + e, HH - 0.1, HH + 0.9)
    box(bm, HX0 - e, HX1 + e, HY0 - e, HY0 + 0.1, HH - 0.1, HH + 0.9)
    box(bm, HX0 - e, HX0 + 0.1, HY0, HY1, HH - 0.1, HH + 0.9)
    box(bm, HX1 - 0.1, HX1 + e, HY0, HY1, HH - 0.1, HH + 0.9)
    # base kick plate
    box(bm, HX0 - 0.1, HX1 + 0.1, HY1, HY1 + 0.12, z0, z0 + 0.5)
    # downpipes at corners
    for (x, y) in ((HX0 - 0.35, HY1 + 0.35), (HX1 + 0.35, HY1 + 0.35), (HX0 - 0.35, HY0 - 0.35), (HX1 + 0.35, HY0 - 0.35)):
        pipe(bm, (x, y, z0), (x, y, HH), 0.12, 6)
    # roof guard rail along the front edge of the filter houses
    for x in (-16, 16):
        for y in (HY0 + 2, HY1 - 2):
            pipe(bm, (x, y, HH + 0.5), (x, y, HH + 1.6), 0.04, 4)
    # external stair tower on the -X end (zig-zag flights)
    sx = HX0 - 2.2
    for k in range(4):
        z = z0 + k * 3.8
        y0, y1 = (HY0 + 4, HY0 + 10) if k % 2 == 0 else (HY0 + 10, HY0 + 4)
        d = Vector((0, y1 - y0, 3.8))
        vs = C.bm_box(bm, (1.6, d.length, 0.12))
        a = math.atan2(3.8, y1 - y0)
        bmesh.ops.transform(bm, matrix=Matrix.Translation((sx, (y0 + y1) / 2, z + 1.9)) @ Matrix.Rotation(a, 4, "X"), verts=vs)
        box(bm, sx - 0.8, sx + 0.8, min(y0, y1) - 1.2 if k % 2 == 0 else max(y0, y1), min(y0, y1) if k % 2 == 0 else max(y0, y1) + 1.2, z + 3.7, z + 3.82)
    for (x, y) in ((sx - 0.9, HY0 + 2.8), (sx + 0.9, HY0 + 2.8), (sx - 0.9, HY0 + 11.2), (sx + 0.9, HY0 + 11.2)):
        box(bm, x - 0.1, x + 0.1, y - 0.1, y + 0.1, z0, HH + 1.0)


C.part("Trim", trim, [C.mat("TK_SteelRing")])


# ------------------------------------------------------------------ air intake filter houses on the roof
def intake(bm):
    for sx in STX:
        x0, x1, y0, y1, z0, z1 = sx - 5, sx + 5, 12.0, 21.0, HH + 0.5, HH + 7.5
        box(bm, x0, x1, y0, y1, z0 + 1.5, z1, 1)                         # filter house body
        for (a, b) in ((x0 + 0.5, x0 + 1.0), (x1 - 1.0, x1 - 0.5)):     # support legs
            for yy in (y0 + 0.6, y1 - 0.6): box(bm, a, b, yy - 0.25, yy + 0.25, z0, z0 + 1.5, 0)
        # weather hoods on the front face (+Y): 3 tiers of sloped hoods over louvred openings
        for k in range(3):
            zz = z0 + 2.0 + k * 1.8
            box(bm, x0 + 0.3, x1 - 0.3, y1, y1 + 0.05, zz, zz + 1.4, 2)   # louvre face (dark)
            vs = C.bm_box(bm, (x1 - x0 - 0.2, 1.1, 0.08))
            bmesh.ops.transform(bm, matrix=Matrix.Translation((sx, y1 + 0.45, zz + 1.45)) @ Matrix.Rotation(math.radians(-28), 4, "X"), verts=vs)
            for kk in range(1, 5): box(bm, x0 + kk * 2.0 - 0.04, x0 + kk * 2.0 + 0.04, y1, y1 + 0.9, zz, zz + 1.4, 0)
        box(bm, x0 - 0.2, x1 + 0.2, y0 - 0.2, y1 + 0.2, z1, z1 + 0.25, 0)  # roof cap
        # inlet duct down into the hall roof
        box(bm, sx - 2.0, sx + 2.0, y0 - 4.0, y0, z0, z0 + 4.5, 1)
        box(bm, sx - 2.2, sx + 2.2, y0 - 4.2, y0 - 3.8, z0, z0 + 4.7, 0)
        # silencer / vent stacks on the hall roof
        C.bm_cyl(bm, 0.7, 4.5, loc=(sx - 6.5, 6.0, HH + 2.75), segs=12, mat_index=1)
        C.bm_cyl(bm, 0.85, 0.3, loc=(sx - 6.5, 6.0, HH + 5.1), segs=12, mat_index=0)


C.part("Intake", intake, [C.mat("TK_SteelRing"), C.mat("TK_PaintSteel"), C.mat("TK_DarkPlastic")])


# ------------------------------------------------------------------ heat-recovery boilers + transition ducts + breeching
def hrsg(bm):
    for sx in STX:
        x0, x1, y0, y1 = sx - 4.5, sx + 4.5, -17.0, -1.5
        box(bm, x0, x1, y0, y1, 0.5, 24.0, 0)                            # casing
        box(bm, x0 - 0.3, x1 + 0.3, y0 - 0.3, y1 + 0.3, 24.0, 24.5, 1)   # roof
        # steam drum on the roof, along Y, with saddles
        pipe(bm, (sx, y0 + 2, 26.0), (sx, y1 - 2, 26.0), 1.1, 14, 1)
        for yy in (y0 + 4, y1 - 4): box(bm, sx - 0.9, sx + 0.9, yy - 0.3, yy + 0.3, 24.5, 25.3, 1)
        # exhaust transition duct: from the hall back wall (gas turbine) widening into the boiler front
        # (a lofted box: small mouth at the hall, full height at the boiler)
        a = [Vector(v) for v in ((sx - 2.5, 1.0, 3.0), (sx + 2.5, 1.0, 3.0), (sx + 2.5, 1.0, 8.0), (sx - 2.5, 1.0, 8.0))]
        b = [Vector(v) for v in ((x0 + 0.3, -1.5, 1.5), (x1 - 0.3, -1.5, 1.5), (x1 - 0.3, -1.5, 18.0), (x0 + 0.3, -1.5, 18.0))]
        va = [bm.verts.new(v) for v in a]; vb = [bm.verts.new(v) for v in b]
        for i in range(4):
            j = (i + 1) % 4
            bm.faces.new((va[j], va[i], vb[i], vb[j])).material_index = 1
        # vertical frame columns + horizontal girts on the casing sides
        for yy in [y0 + k * 3.1 for k in range(6)]:
            for xx in (x0 - 0.15, x1 + 0.15): box(bm, xx - 0.15, xx + 0.15, yy - 0.2, yy + 0.2, 0.5, 24.0, 2)
        for zz in (6.0, 12.0, 18.0):
            for xx in (x0 - 0.2, x1 + 0.2): box(bm, xx - 0.12, xx + 0.12, y0, y1, zz - 0.15, zz + 0.15, 2)
            # access platforms (grating) on the outboard side
            xo = x1 if sx > 0 else x0
            s = 1 if sx > 0 else -1
            box(bm, min(xo, xo + s * 1.4), max(xo, xo + s * 1.4), y0, y1, zz - 0.05, zz + 0.05, 2)
            box(bm, min(xo + s * 1.35, xo + s * 1.45), max(xo + s * 1.35, xo + s * 1.45), y0, y1, zz + 1.0, zz + 1.08, 2)
        # breeching duct from the boiler back to the stack
        box(bm, sx - 2.6, sx + 2.6, STY + 2.0, y0, 14.0, 21.0, 1)
        box(bm, sx - 2.8, sx + 2.8, y0 - 0.4, y0, 13.8, 21.2, 2)


C.part("HRSG", hrsg, [C.mat("TK_Corrugated"), C.mat("TK_PaintSteel"), C.mat("TK_SteelRing")])


# ------------------------------------------------------------------ pipes: racks between hall and boilers, risers
def pipes(bm):
    # main pipe rack running along X at y -0.2 between the hall and the boilers (bents every 6 m)
    for x in range(-16, 17, 8):
        box(bm, x - 0.15, x + 0.15, -0.6, -0.3, 0.5, 7.0, 0)
        box(bm, x - 0.15, x + 0.15, 0.3, 0.6, 0.5, 7.0, 0)
        box(bm, x - 0.2, x + 0.2, -0.7, 0.7, 6.8, 7.1, 0)
        box(bm, x - 0.2, x + 0.2, -0.7, 0.7, 4.8, 5.0, 0)
    for k, (y, z, r) in enumerate(((-0.4, 7.45, 0.35), (0.35, 7.4, 0.3), (0.0, 7.35, 0.25), (-0.35, 5.3, 0.3), (0.3, 5.25, 0.25))):
        pipe(bm, (-19.5, y, z), (19.5, y, z), r, 8, 1 if k % 2 else 0)
    # risers from the rack up the boiler fronts to the drums
    for sx in STX:
        for dx in (-3.2, 3.2):
            pipe(bm, (sx + dx, -0.4, 7.45), (sx + dx, -1.2, 7.45), 0.3, 8)
            pipe(bm, (sx + dx, -1.2, 7.45), (sx + dx, -1.2, 25.5), 0.3, 8)
            pipe(bm, (sx + dx, -1.2, 25.5), (sx + dx * 0.25, -3.5, 26.0), 0.28, 8)
        # feedwater line on the outboard side, down to grade
        s = 1 if sx > 0 else -1
        pipe(bm, (sx + s * 5.2, -2.5, 0.5), (sx + s * 5.2, -2.5, 23.0), 0.25, 8, 1)
        pipe(bm, (sx + s * 5.2, -2.5, 23.0), (sx + s * 5.2, -12.0, 23.0), 0.25, 8, 1)
    # pipes leaving the hall to the transformers' side (cooling water)
    pipe(bm, (HX1, 4.0, 2.5), (HX1 + 3.0, 4.0, 2.5), 0.4, 8, 1)
    pipe(bm, (HX1 + 3.0, 4.0, 2.5), (HX1 + 3.0, -10.0, 2.5), 0.4, 8, 1)
    pipe(bm, (HX1 + 3.0, -10.0, 2.5), (HX1 + 3.0, -10.0, 0.0), 0.4, 8, 1)


C.part("Pipes", pipes, [C.mat("TK_SteelRing"), C.mat("TK_PaintSteel")])


# ------------------------------------------------------------------ transformers
def transformers(bm):
    for k in range(3):
        cy = 8.9 + k * 5.2
        cx = 25.6
        box(bm, cx - 1.6, cx + 1.6, cy - 1.7, cy + 1.7, 0.6, 4.4, 0)        # main tank
        box(bm, cx - 1.75, cx + 1.75, cy - 1.85, cy + 1.85, 4.4, 4.6, 0)   # lid
        pipe(bm, (cx - 0.6, cy, 4.6), (cx - 0.6, cy, 5.2), 0.35, 8)        # conservator support
        pipe(bm, (cx - 0.6, cy - 1.4, 5.6), (cx - 0.6, cy + 1.4, 5.6), 0.4, 8)  # conservator tank
        for i in range(6):                                                 # radiator fins on the +X face
            y = cy - 1.3 + i * 0.52
            box(bm, cx + 1.6, cx + 2.6, y - 0.04, y + 0.04, 1.0, 4.0, 0)
        box(bm, cx + 1.6, cx + 2.7, cy - 1.5, cy + 1.5, 4.0, 4.15, 0)
        for j, yy in enumerate((cy - 0.9, cy, cy + 0.9)):                  # HV bushings (porcelain)
            C.bm_cyl(bm, 0.16, 1.6, loc=(cx - 1.0, yy, 5.4), segs=6, mat_index=1, r2=0.1)
            for s in range(2): C.bm_cyl(bm, 0.26, 0.08, loc=(cx - 1.0, yy, 5.0 + s * 0.5), segs=6, mat_index=1)
        # cable trunking back to the hall
        box(bm, HX1 + 0.2, cx - 1.6, cy - 0.3, cy + 0.3, 3.2, 3.8, 0)


C.part("Transformers", transformers, [C.mat("TK_PaintSteel"), C.mat("TK_DarkPlastic")])


# ------------------------------------------------------------------ stacks: tapered concrete shells with platforms
def stacks(bm):
    for sx in STX:
        tube(bm, 2.5, 3.1, 0.8, STH, sx, STY, 24, r_out1=2.55, r_in1=2.1)
        # inner flue liner visible at the top
        tube(bm, 1.7, 1.9, STH - 3.0, STH + 0.6, sx, STY, 16)


C.part("Stacks", stacks, [C.mat("TK_Stack")], smooth=True)


def stack_r(z): return 3.1 + (2.55 - 3.1) * (z - 0.8) / (STH - 0.8)


def bands(bm):
    for sx in STX:
        for (z0, z1) in ((STH - 9.5, STH - 6.5), (STH - 3.0, STH)):
            tube(bm, stack_r(z1) - 0.05, stack_r(z0) + 0.04, z0, z1, sx, STY, 24, r_out1=stack_r(z1) + 0.04, inner=False)


C.part("StackBands", bands, [C.mat("TK_StackBand")], smooth=True)


def platforms(bm):
    for sx in STX:
        for z in (STH - 11.0, 30.0):
            r = stack_r(z)
            tube(bm, r, r + 1.3, z - 0.1, z + 0.1, sx, STY, 14, inner=False)                    # grating
            tube(bm, r + 1.22, r + 1.3, z + 1.0, z + 1.08, sx, STY, 14, inner=False)          # handrail
            for i in range(6):
                a = 2 * math.pi * i / 6
                p = Vector((sx + (r + 1.26) * math.cos(a), STY + (r + 1.26) * math.sin(a), z))
                pipe(bm, p, p + Vector((0, 0, 1.05)), 0.03, 4)
        # caged ladder up the back of the stack
        r0 = 3.25
        for dx in (-0.25, 0.25):
            pipe(bm, (sx + dx, STY - r0, 0.8), (sx + dx, STY - stack_r(STH) - 0.15, STH - 0.5), 0.03, 4)


# platforms go into Trim? Keep stack steel with the pipes' material in its own object for clarity.
C.part("StackSteel", platforms, [C.mat("TK_SteelRing")])


def warn(bm):
    for sx in STX:
        for z in (STH + 0.05, 30.0 + 1.2):
            r = stack_r(min(z, STH)) + (0.25 if z > STH else 1.3)
            for i in range(4):
                a = math.pi / 4 + i * math.pi / 2
                x, y = sx + (r - 0.1) * math.cos(a), STY + (r - 0.1) * math.sin(a)
                C.bm_cyl(bm, 0.22, 0.3, loc=(x, y, z + 0.15), segs=6)              # lamp body
                C.bm_cyl(bm, 0.22, 0.2, loc=(x, y, z + 0.4), segs=6, r2=0.06)       # domed lens


C.part("WarnLights", warn, [C.mat("TK_WarnLight")], smooth=True)

# re-centre: the origin is the centre of the yard slab's footprint (base centre of the block)
mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
for o in C.ROOT.children:
    for v in o.data.vertices: mn = Vector(map(min, mn, v.co)); mx = Vector(map(max, mx, v.co))
shift = Vector((-(mn.x + mx.x) / 2, -(mn.y + mx.y) / 2, 0))
for o in C.ROOT.children: o.data.transform(Matrix.Translation(shift))
print("[gas_plant] footprint", mx.x - mn.x, mx.y - mn.y, "shift", tuple(shift))

C.finish("gas_plant", note="hall 40x22x16, 2 HRSG + 2 stacks 55 m, footprint X -24..30 / Y -27..26; ten in a row at >= 56 m pitch")
