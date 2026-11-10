"""Module "media_capture": who controls the world's public media. The Earth turns slowly (one turn a minute) with every
outlet in State Media Monitor's survey on it as a dot; then the dots take the colour of who controls them (captured or
state-controlled red, independent but state-funded or state-managed teal, not stated grey), the teal and grey dim, and a
gold spike rises on each of the few independent public outlets.

Switched on by talk_show.json:  "modules": [..., {"name": "media_capture", "after": "5F2"}]  (delete the entry to remove it).
About 22 s to form, then it keeps turning until the next cue. Unlit, no lights, no video, no numbers on stage.
The counts are the atlas package's (586 outlets, 17 independent public on 2026-11-10; the slide says 606 and 19).
Data: tools/geo/media_data.json (tools/geo/media_fetch.py); meshes: tools/blender/media_globe.py; shared: _space.py.
"""
import importlib.util, json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))


def _space():
    spec = importlib.util.spec_from_file_location("talk_module_space", os.path.join(HERE, "_space.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def build(g, opts):
    SP = _space()
    element, one_shot = g["element"], g["one_shot"]
    counts = json.load(open(os.path.join(REPO, "tools", "geo", "media_data.json"), encoding="utf-8"))["counts"]
    A = "media_globe"
    T_A0, T_A1 = 1.5, 4.5
    T_ALL, T_SORT, T_DIM, T_BEAM, T_AI, T_END = 4.5, 12.0, 17.5, 18.5, 21.5, 25.0
    TURN = 60.0                                   # seconds a turn
    YAW0 = 130.0                                  # East Asia faces the seats first; Europe is in front as the spikes rise (20 s)

    el = element("media_capture", "module: who controls the world's public media. A turning Earth with a dot for every outlet "
                                  f"({sum(counts.values())}); they take their colours ({counts.get('captured', 0)} captured red), "
                                  f"and a gold spike rises on the {counts.get('independent', 0)} independent public ones")
    SP.bubble(el, g)
    centre, eps, spin = SP.globe(el, g, A, T_A0, T_A1)
    el.nodes[[n["path"] for n in el.nodes].index("Globe/Tilt")]["rest"]["e"] = [round(eps - 8.0, 4), 0, 0]      # latitude 8 N faces the seats: "just north of the equator so you can see both the north and south hemispheres" (Ben, 2026-11-10; was 25 N)
    # the Earth turns west to east: the longitude facing the seats falls
    el.loop(spin, TURN, {"": {"e": [[0, 0, YAW0, 0], [TURN, 0, YAW0 - 360.0, 0]]}})

    def dots(name, part, t_in, dim_to=None):
        path = f"{spin}/{name}"
        el.node(path, {"asset": A, "part": part}, on=0, a=0)
        el.t(path).step("on", 0, 0); el.t(path).step("on", t_in, 1)
        el.t(path).step("a", 0, 0); el.t(path).add("a", t_in, t_in + 3.0, lambda u: u, "smooth")
        if dim_to is not None: el.t(path).add("a", T_DIM, T_DIM + 3.0, lambda u: 1 - (1 - dim_to) * u, "smooth")
        return path

    every = dots("All", "Dots_All", T_ALL)                         # first: every outlet, the same warm dot
    el.t(every).add("a", T_SORT, T_SORT + 3.0, lambda u: 1 - u, "smooth")
    el.t(every).step("on", T_SORT + 3.05, 0)
    dots("Captured", "Dots_Captured", T_SORT)                      # then: by who controls them
    dots("Mixed", "Dots_Mixed", T_SORT, dim_to=0.3)
    dots("Unknown", "Dots_Unknown", T_SORT, dim_to=0.25)
    dots("Independent", "Dots_Independent", T_SORT)
    dots("AI", "Dots_AI", T_AI)                                    # last: the AI data centers (magenta diamonds, by power)
    beams = f"{spin}/Beams"
    el.node(beams, {"asset": A, "part": "Beams_Independent"}, s=0.82, on=0)     # 0.82: the spikes are inside the globe
    el.t(beams).step("on", 0, 0); el.t(beams).step("on", T_BEAM, 1)
    el.t(beams).add("s", T_BEAM, T_BEAM + 2.5, lambda u: [0.82 + 0.18 * u] * 3, "out")

    one_shot(el, "Arrive", "whoosh_slow.wav", T_A0, pos=centre, vol=0.35, spatial=0.6)
    one_shot(el, "Sort", "timeline_shimmer.wav", T_SORT, pos=centre, vol=0.3, spatial=0.4)
    # no chime as the spikes rise (Ben, 2026-11-10: "Get rid of the bell sound")

    # ---- the legend: lower right of the globe, turned to the seats (Ben, 2026-11-10: "add a legend on the lower right
    # side"). Warm and small (CLAUDE.md rule 12), no numbers; it comes up as the dots take their colours.
    LEG_W = 8.0                                                              # metres wide (the part is 1 x 0.5)
    leg = [g["EYE"][0] + 10.5, 3.4, g["EYE"][2] + 15.0]
    yaw = math.degrees(math.atan2(leg[0] - g["EYE"][0], leg[2] - g["EYE"][2]))
    el.node("Legend", {"asset": A, "part": "Legend"}, p=leg, e=(0, yaw, 0), s=LEG_W, on=0, a=0)
    el.t("Legend").step("on", 0, 0); el.t("Legend").step("on", T_SORT, 1)
    el.t("Legend").step("a", 0, 0); el.t("Legend").add("a", T_SORT, T_SORT + 2.0, lambda u: u, "smooth")
    el.t("Legend", "exit").step("on", 0.05, 0)
    el.play_dur = T_END
    print(f"  media_capture: {sum(counts.values())} outlets {counts}; one turn in {TURN:g} s; formed at {T_END:g} s")

    off = ["media_tour"] if "media_tour" in g["EL"] else []
    cue = {"id": opts.get("id", "5F3"), "name": opts.get("cueName", "19 of 606 Not Captured (3D)"), "on": ["media_capture"], "off": off, "video": "stop", "alone": True}
    return [{"after": opts.get("after", "5F2" if off else "5F"), "cue": cue, "offAtNext": ["media_capture"]}]
