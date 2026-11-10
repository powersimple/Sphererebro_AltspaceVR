"""Module "datahall": a data hall that starts small in the back, zooms in, and flies past the seats. One element, one cue.
Ben, 2026-11-10: "Let's rebuild the data center model. Let's have the data centers start small in the back and then zoom
in and fly past the seats", with three pictures of dark rack aisles (blue lamps, glossy floor, light strips overhead).

Switched on by talk_show.json:  "modules": [{"name": "datahall", "after": "4B"}]   (delete the entry to remove it; the
older rack cues 4B.. are untouched and nothing else refers to this module).

What plays (about 47 s):
  0 - 2.5 s    the dome goes black (a shell just inside the sphere, 48.5 m, and a black floor under the stage)
  1.5 - 3      the hall appears far ahead, above the equator: a small dark box with a glowing mouth
  3 - 15       it comes toward the seats and grows ten times, sinking until its floor is the theatre's floor and its
               mouth stands just in front of the stage, 23 m wide
  15.3 - 47    it flies over the audience: 47 bays of racks pass 3 m outside the seats on both sides (up to 10 m/s),
               slowing to rest with the end wall 81 m ahead
  hold         inside the aisle
Unlit and baked: one AnimationClip moves one object; no lights, video or scripts.

This one goes below the sphere's equator on purpose: the racks stand on the floor beside the seats (Ben asked for them
to fly past the seats). Mesh: tools/blender/datahall.py; images: tools/geo/datahall_art.py; materials:
talk_materials_datahall.json.
"""
import math


def build(g, opts):
    element, one_shot, EASE = g["element"], g["one_shot"], g["EASE"]
    smooth, out3 = EASE["smooth"], EASE["out"]
    A = "datahall"
    L, WX, POST = 281.6, 11.6, 0.28               # the asset: length, half width to the rack fronts, how far a post stands out
    SHELL_R, FLOOR_Y = 48.5, -3.2                 # as env_dark: just inside the 50 m sphere; the floor is under the stage (-2.65)
    S0 = 0.1                                      # the miniature: a mouth 2.2 m wide
    M0 = [0.0, 8.0, 36.0]                         # the mouth's floor point at first: far ahead, above the equator
    M1 = [0.0, FLOOR_Y + 0.05, -35.0]             # ... full size: in front of the stage (5 cm over the black floor)
    END_Z = 38.0                                  # where the end wall comes to rest (inside the black shell)
    M2 = [0.0, M1[1], END_Z - L]
    T_ON, T_Z0, T_Z1, T_F0, T_F1, T_END = 1.5, 3.0, 15.0, 15.3, 47.0, 47.5

    el = element("datahall", "module: a data hall starts small in the back, comes in and grows until its mouth stands before the "
                             "stage, then flies over the audience: rows of racks pass both sides of the seats, to rest inside the aisle")
    # ---- the black dome ---------------------------------------------------------------------------------------------
    el.node("SpaceFade", {"special": "envsphere", "radius": SHELL_R + 0.3, "mat": "TK_DhSpaceFade", "segments": 48}, a=0)
    el.node("Space", {"special": "envsphere", "radius": SHELL_R, "mat": "TK_DhSpace", "segments": 48}, on=0)
    for holder, mat in (("SpaceFade", "TK_DhSpaceFade"), ("Space", "TK_DhSpace")):
        el.node(holder + "/Floor", {"special": "floor", "size": 2 * SHELL_R + 2, "y": FLOOR_Y, "mat": mat})
    el.t("SpaceFade").add("a", 0, 2.5, lambda u: u, "smooth")
    el.t("SpaceFade").step("on", 0, 1); el.t("SpaceFade").step("on", 2.7, 0)
    el.t("Space").step("on", 0, 0); el.t("Space").step("on", 2.5, 1)

    # ---- the hall ---------------------------------------------------------------------------------------------------
    def pose(t):
        if t <= T_Z0: return M0, S0 * (0.02 + 0.98 * out3(max(0.0, (t - T_ON) / (T_Z0 - T_ON))))
        if t <= T_Z1:
            w = smooth((t - T_Z0) / (T_Z1 - T_Z0))
            return [a + (b - a) * w for a, b in zip(M0, M1)], S0 * math.exp(-math.log(S0) * w)
        if t <= T_F0: return M1, 1.0
        w = smooth(min(1.0, (t - T_F0) / (T_F1 - T_F0)))
        return [a + (b - a) * w for a, b in zip(M1, M2)], 1.0

    el.node("Hall", {}, p=M0, s=S0 * 0.02, on=0)
    el.node("Hall/Model", {"asset": A})
    el.t("Hall").step("on", 0, 0); el.t("Hall").step("on", T_ON, 1)
    el.t("Hall").add("p", T_ON, T_F1, lambda u: pose(T_ON + (T_F1 - T_ON) * u)[0], "lin", hz=15)
    el.t("Hall").add("s", T_ON, T_F1, lambda u: [pose(T_ON + (T_F1 - T_ON) * u)[1]] * 3, "lin", hz=15)
    one_shot(el, "Arrive", "whoosh_slow.wav", T_ON, pos=M0, vol=0.35, spatial=0.6)
    one_shot(el, "Fly", "drift_low.wav", T_F0, pos=(0, 4, -30), vol=0.4, spatial=0.3)
    el.play_dur = T_END

    # ---- exit: the hall goes dark at once (any way of moving it out would pass through the seats), then the dome opens
    el.t("Hall", "exit").step("on", 0.05, 0)
    el.t("Space", "exit").step("on", 2.7, 0)
    el.t("SpaceFade", "exit").step("on", 0, 0); el.t("SpaceFade", "exit").step("on", 2.7, 1)
    el.t("SpaceFade", "exit").step("a", 0, 1); el.t("SpaceFade", "exit").add("a", 2.7, 5.0, lambda u: 1 - u, "smooth")
    el.t("SpaceFade", "exit").step("on", 5.05, 0)
    el.exit_dur = 5.1

    # ---- checks -------------------------------------------------------------------------------------------------------
    box = g["SHOW"]["audience"]["seatBox"]; need = g["SHOW"]["audience"].get("clearance", 3.0)
    side = (WX - POST) - max(abs(box[0][0]), abs(box[1][0])) - 0.45          # 0.45: an occupant's elbow room, as the harness measures                 # a post to the outermost seat, at full size
    ahead = min(pose(t / 4)[0][2] for t in range(int(T_F0 * 4) + 1)) - box[1][2]   # the mouth to the front row before the flight
    speed = max(abs(pose(t / 10 + 0.1)[0][2] - pose(t / 10)[0][2]) * 10 for t in range(int(T_F0 * 10), int(T_F1 * 10)))
    print(f"  datahall: racks pass {side:.2f} m outside the seats; the mouth stops {ahead:.1f} m ahead of the front row before the flight; "
          f"{(M1[2] - M2[2]) / 4.4:.0f} bays pass at up to {speed:.1f} m/s; end wall rests {END_Z - g['EYE'][2]:.0f} m ahead")
    if side < need or ahead < need: raise SystemExit("datahall: the hall comes too close to the seats")

    cue = {"id": opts.get("id", "4B2"), "name": opts.get("cueName", "Data Centers"), "on": ["datahall"], "off": [], "video": "stop", "alone": True}
    return [{"after": opts.get("after", "4B"), "cue": cue, "offAtNext": ["datahall"]}]
