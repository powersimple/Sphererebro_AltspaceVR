"""Module "media_tour": where public media is. The Earth turns from one major public broadcaster to the next (the atlas
package's 14: BBC, RTÉ, ARTE, RAI, SVT, Al Jazeera, Prasar Bharati, KBS, NHK, ABC, SABC, EBC, PBS, CBC), a light bouncing
from each to the next along a gold arc; a gold pin rises at every stop and a small warm name card shows while it is in
front (name, city, country, year founded).

Switched on by talk_show.json:  "modules": [..., {"name": "media_tour", "after": "5F"}]   (delete the entry to remove it).
About 55 s. Unlit, no lights, no video: one Unity AnimationClip. The globe (18 m across) hangs above the sphere's equator.
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
    element, one_shot, EASE = g["element"], g["one_shot"], g["EASE"]
    in_out, smooth = EASE["inout"], EASE["smooth"]
    stops = json.load(open(os.path.join(REPO, "tools", "geo", "media_data.json"), encoding="utf-8"))["stops"]
    A = "media_globe"
    HOP, DWELL = 2.0, 1.5
    T_A0, T_A1, T_FIRST = 1.5, 4.5, 6.5
    PIN_TIP = 1.13

    el = element("media_tour", "module: public media around the world. The Earth turns from one major public broadcaster to the next "
                               f"({len(stops)} stops), a light bouncing between them; a pin rises and a name card shows at each")
    SP.bubble(el, g)
    centre, eps, spin = SP.globe(el, g, A, T_A0, T_A1)

    # the globe's pose for each stop: yaw = longitude (the short way round from the stop before), tilt = EPS - latitude
    yaws = []; prev = None
    for s in stops:
        y = s["lon"] if prev is None else prev + ((s["lon"] - prev + 180.0) % 360.0 - 180.0)
        yaws.append(y); prev = y
    tilts = [eps - s["lat"] for s in stops]
    t_hop = [T_FIRST + (k - 1) * (HOP + DWELL) for k in range(len(stops))]         # t_hop[k]: when the hop TO stop k starts (k >= 1)
    T_END = t_hop[-1] + HOP + DWELL + 0.5

    el.nodes[[n["path"] for n in el.nodes].index("Globe/Tilt")]["rest"]["e"] = [round(tilts[0], 4), 0, 0]
    el.nodes[[n["path"] for n in el.nodes].index(spin)]["rest"]["e"] = [0, round(yaws[0] + 70, 4), 0]
    el.t(spin).add("e", T_A0, T_A1 + 0.8, lambda u: [0, yaws[0] + 70 * (1 - u), 0], "out", hz=10)
    el.t("Globe/Tilt").step("e", 0, [tilts[0], 0, 0])
    for k in range(1, len(stops)):
        t0 = t_hop[k]
        el.t(spin).add("e", t0, t0 + HOP, (lambda a, b: lambda u: [0, a + (b - a) * u, 0])(yaws[k - 1], yaws[k]), "inout", hz=12)
        el.t("Globe/Tilt").add("e", t0, t0 + HOP, (lambda a, b: lambda u: [a + (b - a) * u, 0, 0])(tilts[k - 1], tilts[k]), "inout", hz=12)

    def arc_point(k, u):
        """The hop to stop k at u in 0..1 (the same curve tools/blender/media_globe.py builds the arc on)."""
        a = SP.unit(stops[k - 1]["lat"], stops[k - 1]["lon"]); b = SP.unit(stops[k]["lat"], stops[k]["lon"])
        ang = math.acos(max(-1.0, min(1.0, sum(x * y for x, y in zip(a, b)))))
        hgt = 0.03 + 0.12 * ang / math.pi
        d = [(x * math.sin((1 - u) * ang) + y * math.sin(u * ang)) / math.sin(ang) for x, y in zip(a, b)]
        r = PIN_TIP + hgt * math.sin(math.pi * u)
        return [c * r for c in d]

    ball = spin + "/Ball"
    el.node(ball, {"asset": A, "part": "Ball"}, p=SP.unit(stops[0]["lat"], stops[0]["lon"], PIN_TIP), on=0)
    el.t(ball).step("on", 0, 0); el.t(ball).step("on", T_A1 + 1.0, 1)

    for k, s in enumerate(stops):
        t_arrive = (T_A1 + 1.0) if k == 0 else t_hop[k] + HOP
        pin = f"{spin}/Pin_{k:02d}"
        el.node(pin, {"asset": A, "part": f"Pin_{k:02d}"}, s=0.86, on=0)            # 0.86: the whole pin is inside the globe
        el.t(pin).step("on", 0, 0); el.t(pin).step("on", t_arrive - 0.1, 1)
        el.t(pin).add("s", t_arrive - 0.1, t_arrive + 0.6, lambda u: [0.86 + 0.14 * u] * 3, "back")
        card = f"{spin}/Card_{k:02d}"
        el.node(card, {"asset": A, "part": f"Card_{k:02d}"}, on=0, a=0)
        el.t(card).step("on", 0, 0); el.t(card).step("on", t_arrive, 1)
        el.t(card).step("a", 0, 0); el.t(card).add("a", t_arrive, t_arrive + 0.5, lambda u: u, "smooth")
        if k < len(stops) - 1:                                                       # it leaves as the next hop starts
            t_leave = t_hop[k + 1]
            el.t(card).add("a", t_leave, t_leave + 0.5, lambda u: 1 - u, "smooth")
            el.t(card).step("on", t_leave + 0.55, 0)
        if k:
            arc = f"{spin}/Arc_{k:02d}"
            el.node(arc, {"asset": A, "part": f"Arc_{k:02d}"}, on=0)
            el.t(arc).step("on", 0, 0); el.t(arc).step("on", t_hop[k], 1)
            el.t(ball).add("p", t_hop[k], t_hop[k] + HOP, (lambda k: lambda u: arc_point(k, u))(k), "inout", hz=15)
        # no sound at the stops (Ben, 2026-11-10: "Remove the chime from the stops on the media tour")

    one_shot(el, "Arrive", "whoosh_slow.wav", T_A0, pos=centre, vol=0.35, spatial=0.6)
    el.play_dur = T_END
    print(f"  media_tour: {len(stops)} stops, {HOP + DWELL:.1f} s each, {T_END:.0f} s; globe r {SP.RADIUS:g} m at {[round(c, 1) for c in centre]}, "
          f"underside {centre[1] - SP.RADIUS:.1f} m above the equator")

    cue = {"id": opts.get("id", "5F2"), "name": opts.get("cueName", "Public Media Around the World (3D)"), "on": ["media_tour"], "off": [], "video": "stop", "alone": True}
    return [{"after": opts.get("after", "5F"), "cue": cue, "offAtNext": ["media_tour"]}]
