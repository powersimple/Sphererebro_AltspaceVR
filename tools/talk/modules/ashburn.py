"""Module "ashburn": from space down to Ashburn, Virginia (Data Center Alley), in 3D. One element, one cue.

Switched on by talk_show.json:  "modules": [{"name": "ashburn", "after": "5B"}]   (delete that entry to remove the
module from the show; nothing else in the talk refers to it). choreo.py calls build(g, opts) with its own namespace.

What plays (about 42 s):
  0 - 2.5 s   a black bubble (29 m, centred on the audience) fades in: the hall, racks and screen are gone
  1.5 - 9.5   the Earth arrives, 10 m across, 18 m in front and above the equator, turning until Virginia faces the seats
  10 - 40     one continuous zoom about Ashburn (the globe grows 16,000 x): six imagery layers take over from each
              other, the ground tips from a wall into a raked floor below the seats, and the buildings rise
  hold        2.4 km of Data Center Alley, 20 m across, its lower edge at the equator: data centres amber, others grey
Everything is unlit and baked (no lights, no video, no scripts): the motion is one Unity AnimationClip.

Hierarchy (Unity axes; Pivot unit = the Earth's radius, so Pivot's scale IS the globe's radius in metres):
  Space, SpaceFade                the bubble (opaque once faded in, so anything outside it is hidden)
  Pivot                           at the focus on the Earth's surface: position, tilt and scale are animated
    Centre/Spin/GlobeW, GlobeE    the globe, spun about the Earth's axis
    L1, L2                        5,000 km and 1,000 km layers (radius-1 caps)
    Site (scale 1 / Earth radius) metres from here down
      L3 .. L6                    200 km, 40 km, 8 km, 2.4 km
      Blocks/DC, Blocks/Other     buildings
Data and images: tools/geo/ashburn_fetch.py; meshes: tools/blender/ashburn_zoom.py; materials: talk_materials_ashburn.json.
"""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))


def build(g, opts):
    element, one_shot, EASE, EYE = g["element"], g["one_shot"], g["EASE"], g["EYE"]
    smooth, in_out, out3 = EASE["smooth"], EASE["inout"], EASE["out"]
    data = json.load(open(os.path.join(REPO, "tools", "geo", "ashburn_data.json")))
    lat = data["focus"]["lat"]; R_M = data["earthRadiusKm"] * 1000.0
    AX, AZ = EYE[0], EYE[2]

    # ---- the plan -------------------------------------------------------------------------------------------------
    # Ben, 2026-11-10: "it's too low, all the content should be seen above the equator of the sphere" (y = 0). So the
    # globe hangs above the equator, the map ends as a steep raked wall whose lower edge is at the equator, and a black
    # floor just under the stage hides whatever of the ground runs on below it.
    BUB_R = 29.0                                  # the curved screen stands at 30 m: the bubble stays inside it
    # Ben, 2026-11-10 (after seeing it): the Earth "lower, larger and closer". Was radius 5, centre 7 up and 18 ahead. Then "too close, move it back": 16 -> 22 m ahead.
    S0, S1 = 7.5, 53000.0                         # globe radius (m): 15 m Earth -> 1 km = 8.3 m (2.4 km of Ashburn = 20 m)
    C0 = [0.0, 8.0, AZ + 22.0]                    # the globe's centre while it is a globe: its underside 0.5 m above the equator
    RX0, RX1 = -75.0, -60.0                       # Pivot tilt: the ground's normal stays mostly toward the seats
    P1 = [0.0, 9.2, AZ + 17.0]                    # where Ashburn ends up: 10 m above eye level, 17 m ahead
    FLOOR_Y = -3.2                                # the black floor: under the stage (y -2.65), over the white hall's floor
    T_ARR0, T_ARR1 = 1.5, 5.0                     # arrival
    T_SPIN1 = 9.5
    T_Z0, T_Z1 = 10.0, 40.0                       # the zoom
    POSE_BY = 0.55                                # the tilt and the move finish this far through the zoom
    T_END = 42.0

    def nrm(rx):                                  # Unity: Rx(rx) takes +Y to (0, cos, sin)
        a = math.radians(rx); return [0.0, math.cos(a), math.sin(a)]
    P0 = [c + S0 * n for c, n in zip(C0, nrm(RX0))]

    def S_at(t):
        if t <= T_ARR0: return 0.25
        if t < T_ARR1: return 0.25 + (S0 - 0.25) * out3((t - T_ARR0) / (T_ARR1 - T_ARR0))
        if t <= T_Z0: return S0
        if t >= T_Z1: return S1
        return math.exp(math.log(S0) + (math.log(S1) - math.log(S0)) * smooth((t - T_Z0) / (T_Z1 - T_Z0)))

    def pose_at(t):
        """Pivot position, tilt, scale at time t."""
        S = S_at(t)
        if t <= T_Z0: return [c + S * n for c, n in zip(C0, nrm(RX0))], RX0, S
        w = smooth(min(1.0, (t - T_Z0) / ((T_Z1 - T_Z0) * POSE_BY)))
        return [a + (b - a) * w for a, b in zip(P0, P1)], RX0 + (RX1 - RX0) * w, S

    def t_of(S):                                  # when the zoom reaches radius S (bisection)
        lo, hi = T_Z0, T_Z1
        for _ in range(50):
            mid = (lo + hi) / 2
            if S_at(mid) < S: lo = mid
            else: hi = mid
        return round(lo, 3)

    el = element("ashburn", "module: from space to Ashburn, Virginia. A black bubble, the Earth, one 16,000 x zoom through six "
                            "imagery layers to 2.4 km of Data Center Alley with its buildings as blocks (data centres amber)")
    A = "ashburn_zoom"

    # ---- the bubble -----------------------------------------------------------------------------------------------
    eye = [AX, EYE[1], AZ]
    el.node("SpaceFade", {"special": "envsphere", "radius": BUB_R + 0.3, "mat": "TK_AshSpaceFade", "segments": 48}, p=eye, a=0)
    el.node("Space", {"special": "envsphere", "radius": BUB_R, "mat": "TK_AshSpace", "segments": 48}, p=eye, on=0)
    for holder, mat in (("SpaceFade", "TK_AshSpaceFade"), ("Space", "TK_AshSpace")):
        el.node(holder + "/Floor", {"special": "floor", "size": 2 * BUB_R + 2, "y": FLOOR_Y - eye[1], "mat": mat})
    el.t("SpaceFade").add("a", 0, 2.5, lambda u: u, "smooth")
    el.t("SpaceFade").step("on", 0, 1); el.t("SpaceFade").step("on", 2.7, 0)
    el.t("Space").step("on", 0, 0); el.t("Space").step("on", 2.5, 1)

    # ---- the pivot ------------------------------------------------------------------------------------------------
    p_, rx_, s_ = pose_at(0)
    el.node("Pivot", {}, p=p_, e=(rx_, 0, 0), s=s_, on=0)
    el.t("Pivot").step("on", 0, 0); el.t("Pivot").step("on", T_ARR0, 1)
    for key, fn in (("p", lambda t: pose_at(t)[0]), ("e", lambda t: [pose_at(t)[1], 0, 0]), ("s", lambda t: [pose_at(t)[2]] * 3)):
        el.t("Pivot").add(key, T_ARR0, T_Z1, (lambda fn: lambda u: fn(T_ARR0 + (T_Z1 - T_ARR0) * u))(fn), "lin", hz=15)

    # ---- the globe ------------------------------------------------------------------------------------------------
    el.node("Pivot/Centre", {}, p=(0, -1, 0), e=(90.0 - lat, 0, 0))
    el.node("Pivot/Centre/Spin", {}, e=(0, 95, 0))
    el.node("Pivot/Centre/Spin/GlobeW", {"asset": A, "part": "Globe_W"})
    el.node("Pivot/Centre/Spin/GlobeE", {"asset": A, "part": "Globe_E"})
    el.t("Pivot/Centre/Spin").add("e", T_ARR0, T_SPIN1, lambda u: [0, 95 * (1 - u), 0], "inout", hz=10)
    T_GLOBE_OFF = t_of(160.0)                     # the 5,000 km layer now reaches past the bubble
    el.t("Pivot/Centre").step("on", 0, 1); el.t("Pivot/Centre").step("on", T_GLOBE_OFF, 0)

    # ---- the layers: fade in over a range of radii, switch off once the next one covers the bubble ----------------
    #        name   holder        fade-in radii       off at radius (None = stays)
    plan = [("L1", "Pivot",      (12.0, 30.0),        800.0),
            ("L2", "Pivot",      (60.0, 150.0),       4000.0),
            ("L3", "Pivot/Site", (300.0, 750.0),      20000.0),
            ("L4", "Pivot/Site", (1500.0, 3700.0),    50000.0),
            ("L5", "Pivot/Site", (7500.0, 18000.0),   None),
            ("L6", "Pivot/Site", (22000.0, 42000.0),  None)]
    el.node("Pivot/Site", {})
    el.nodes[-1]["rest"]["s"] = [1.0 / R_M] * 3   # not rounded to 4 places like el.node() would
    times = {}
    for name, holder, (a, b), off in plan:
        path = f"{holder}/{name}"
        el.node(path, {"asset": A, "part": name}, on=0, a=0)
        ta, tb = t_of(a), t_of(b)
        el.t(path).step("on", 0, 0); el.t(path).step("on", ta, 1)
        el.t(path).step("a", 0, 0); el.t(path).add("a", ta, tb, lambda u: u, "smooth")
        if off: el.t(path).step("on", t_of(off), 0)
        times[name] = (ta, tb, t_of(off) if off else None)

    # ---- the buildings rise as the 8 km layer comes in --------------------------------------------------------------
    el.node("Pivot/Site/Blocks", {}, s=(1, 0.02, 1), on=0)
    el.node("Pivot/Site/Blocks/DC", {"asset": A, "part": "Blocks_DC"})
    el.node("Pivot/Site/Blocks/Other", {"asset": A, "part": "Blocks_Other"})
    tr0, tr1 = t_of(9000.0), t_of(36000.0)
    el.t("Pivot/Site/Blocks").step("on", 0, 0); el.t("Pivot/Site/Blocks").step("on", tr0, 1)
    el.t("Pivot/Site/Blocks").add("s", tr0, tr1, lambda u: [1, 0.02 + 0.98 * u, 1], "out")

    one_shot(el, "Arrive", "whoosh_slow.wav", T_ARR0, pos=C0, vol=0.4, spatial=0.6)
    one_shot(el, "Descend", "drift_low.wav", T_Z0, pos=P1, vol=0.35, spatial=0.3)
    el.play_dur = T_END

    # ---- exit: the buildings sink, the ground fades, the bubble opens ---------------------------------------------
    el.t("Pivot/Site/Blocks", "exit").add("s", 0, 1.0, lambda u: [1, 1 - 0.98 * u, 1], "in")
    el.t("Pivot/Site/Blocks", "exit").step("on", 1.05, 0)
    for name in ("L5", "L6"):
        el.t(f"Pivot/Site/{name}", "exit").add("a", 0.4, 1.8, lambda u: 1 - u, "smooth")
    el.t("Pivot", "exit").step("on", 1.85, 0)
    el.t("Space", "exit").step("on", 2.7, 0)        # stays until a following module's bubble has closed (2.5 s)
    el.t("SpaceFade", "exit").step("on", 0, 0); el.t("SpaceFade", "exit").step("on", 2.7, 1)
    el.t("SpaceFade", "exit").step("a", 0, 1); el.t("SpaceFade", "exit").add("a", 2.7, 5.0, lambda u: 1 - u, "smooth")
    el.t("SpaceFade", "exit").step("on", 5.05, 0)
    el.exit_dur = 5.1

    # ---- checks (printed by choreo.py's run) ----------------------------------------------------------------------
    box = g["SHOW"]["audience"]["seatBox"]; clear = 1e9; when = 0
    corners = [[x, y, z] for x in (box[0][0], box[1][0]) for y in (box[0][1], box[1][1]) for z in (box[0][2], box[1][2])]
    t = 0.0
    while t <= T_END:
        P, rx, S = pose_at(t); n = nrm(rx)
        cen = [p - S * q for p, q in zip(P, n)]
        for c in corners:
            d = math.dist(c, cen) - S
            if d < clear: clear, when = d, t
        t += 0.25
    print(f"  ashburn: zoom {S1 / S0:,.0f} x in {T_Z1 - T_Z0:.0f} s; nearest the Earth's surface comes to a seat: {clear:.1f} m (t = {when:.1f} s); "
          f"globe off at {T_GLOBE_OFF:.1f} s; layers " + ", ".join(f"{k} {v[0]:.1f}-{v[1]:.1f}" + (f" off {v[2]:.1f}" if v[2] else "") for k, v in times.items())
          + f"; buildings rise {tr0:.1f}-{tr1:.1f} s")
    if clear < g["SHOW"]["audience"].get("clearance", 3.0): raise SystemExit("ashburn: the ground comes too close to the seats")

    cue = {"id": opts.get("id", "5B3"), "name": opts.get("cueName", "Ashburn from Space (3D)"), "on": ["ashburn"], "off": [], "video": "stop", "alone": True}
    return [{"after": opts.get("after", "5B"), "cue": cue, "offAtNext": ["ashburn"]}]
