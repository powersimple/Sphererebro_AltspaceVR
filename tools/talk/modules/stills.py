"""Module "stills": Ben's own pictures (and his Venus figure) on keys of their own. Three elements, three cues.
Ben, 2026-11-10: "add some static images that I can trigger with a button. You can have it come in from a distance and
dominate the field of view. Not too close, but big."

Switched on by talk_show.json:  "modules": [..., {"name": "stills", "after": "T"}]  and their ids in "keys"
(delete the entry and the ids to remove it; nothing else refers to this module).

  Innovation   the chart "200 Years of Innovation" comes in from far ahead and stops 21 m away, 20 m wide
  Venus        the picture of the carver comes in the same way, left of centre; then the Venus figure rises through the
               floor on the right, floats, and turns very slowly clockwise seen from above (one turn in two minutes)
  Stewart      the room goes dark, the clip plays (with a hall's resonance, tools/geo/stills_art.py); then the picture
               fades in large, if tools/stills/stewart.* exists (Ben is sending a new one: without it, dark and sound)

Each plays inside the black bubble of _space.py (29 m, centred on the audience), so the room is dark behind it whatever
was showing; everything stays above the sphere's equator except the Venus figure on her way up through the floor.
Pictures: tools/stills/ -> tools/geo/stills_art.py -> talk/gen/still_*.png; meshes: tools/blender/stills.py and
venus_poly.py; materials: talk_materials_stills.json.
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
    EYE = g["EYE"]
    D = json.load(open(os.path.join(REPO, "tools", "geo", "stills_data.json"), encoding="utf-8"))
    have = D["stills"]
    AHEAD, FAR = 21.0, 27.0                       # where a picture stops / where it starts, metres ahead of the eye

    def face(pos):                                # the yaw that turns a part (front -Z) at pos toward the eye
        return math.degrees(math.atan2(pos[0] - EYE[0], pos[2] - EYE[2]))

    def picture(el, name, height, x=0.0, y=8.25, t0=1.0, travel=5.0, fade=1.5, fly=True):
        """A picture `height` m high. fly: it comes in from FAR to AHEAD, growing; else it fades in where it stands."""
        end = [EYE[0] + x, y, EYE[2] + AHEAD]
        w = height * have[name]["w"] / have[name]["h"]
        reach = max(math.dist([end[0] + sx * w / 2, end[1] + sy * height / 2, end[2]], EYE) for sx in (-1, 1) for sy in (-1, 1))
        if reach > SP.BUB_R - 0.3: raise SystemExit(f"stills: {name} reaches {reach:.1f} m, outside the {SP.BUB_R:g} m bubble")
        if end[1] - height / 2 < 0: raise SystemExit(f"stills: {name} goes below the equator")
        start = [EYE[0] + x * FAR / AHEAD, y, EYE[2] + FAR]
        el.node("Pic", {"asset": "stills", "part": "Pic_" + name}, p=start if fly else end, e=(0, face(end), 0), s=height * (0.12 if fly else 1.0), on=0, a=0)
        el.t("Pic").step("on", 0, 0); el.t("Pic").step("on", t0, 1)
        el.t("Pic").step("a", 0, 0); el.t("Pic").add("a", t0, t0 + fade, lambda u: u, "smooth")
        if fly:
            el.t("Pic").add("p", t0, t0 + travel, lambda u: [a + (b - a) * u for a, b in zip(start, end)], "out")
            el.t("Pic").add("s", t0, t0 + travel, lambda u: [height * (0.12 + 0.88 * u)] * 3, "out")
        el.t("Pic", "exit").step("on", 0.05, 0)
        return end, w

    out = []; after = opts.get("after", "T")

    def cue(cid, name, eid):
        nonlocal after
        out.append({"after": after, "cue": {"id": cid, "name": name, "on": [eid], "off": [], "video": "stop", "alone": True}, "offAtNext": [eid]})
        after = cid

    # ---- Innovation ---------------------------------------------------------------------------------------------------
    if "innovation" in have:
        el = element("still_innovation", "module stills: the chart '200 Years of Innovation' comes in from far ahead and fills the view")
        SP.bubble(el, g, "TK_Still")
        end, w = picture(el, "innovation", 13.5)
        one_shot(el, "Arrive", "whoosh_slow.wav", 1.0, pos=end, vol=0.3, spatial=0.6)
        el.play_dur = 6.5
        print(f"  stills: innovation {w:.1f} x 13.5 m, {AHEAD:g} m ahead ({math.degrees(2 * math.atan(w / 2 / AHEAD)):.0f} deg wide)")
        cue("S1", "Innovation", "still_innovation")

    # ---- Venus --------------------------------------------------------------------------------------------------------
    if "venus" in have:
        T_RISE0, T_RISE1, TALL = 5.0, 11.0, 5.5
        el = element("still_venus", "module stills: the carver's picture comes in left of centre; the Venus figure rises through the floor "
                                    "on the right, floats, and turns slowly clockwise seen from above")
        SP.bubble(el, g, "TK_Still")
        end, w = picture(el, "venus", 11.0, x=-6.5, y=7.5)
        rest = [EYE[0] + 7.5, 3.0, EYE[2] + 15.0]                       # her feet, floating
        low = [rest[0], SP.FLOOR_Y - TALL - 0.5, rest[2]]               # under the bubble's black floor
        el.node("Venus", {}, p=low, on=0)
        el.t("Venus").step("on", 0, 0); el.t("Venus").step("on", T_RISE0, 1)
        el.t("Venus").add("p", T_RISE0, T_RISE1, lambda u: [a + (b - a) * u for a, b in zip(low, rest)], "out")
        el.node("Venus/Bob", {})
        BOB, TURN = 9.0, 120.0
        el.loop("Venus/Bob", BOB, {"": {"p": [[BOB * k / 12, 0, round(0.18 * (1 - math.cos(math.tau * k / 12)), 4), 0] for k in range(13)]}})
        el.node("Venus/Bob/Spin", {}, e=(0, face(rest), 0))
        # clockwise seen from above: in Unity (left-handed, Y up) that is the yaw rising
        el.loop("Venus/Bob/Spin", TURN, {"": {"e": [[0, 0, face(rest), 0], [TURN, 0, face(rest) + 360.0, 0]]}})
        el.node("Venus/Bob/Spin/Model", {"asset": "venus_poly"}, s=TALL)
        # two lights of her own (the bubble is black): a warm key from the seats' side, a cool rim from behind
        for nm, col, I, off in (("Key", [1.0, 0.86, 0.66], 30.0, (-4.0, 5.5, -6.0)), ("Rim", [0.55, 0.7, 1.0], 22.0, (4.5, 4.0, 4.5))):
            el.node(nm, {"light": {"type": "point", "color": col, "intensity": I, "range": 22}}, p=[rest[0] + off[0], rest[1] + off[1], rest[2] + off[2]], on=0)
            el.t(nm).step("on", 0, 0); el.t(nm).step("on", T_RISE0, 1)
            el.t(nm).step("i", 0, 0); el.t(nm).add("i", T_RISE0, T_RISE0 + 3.0, (lambda I: lambda u: I * u)(I), "smooth")
            el.t(nm, "exit").step("on", 0.05, 0)
        el.t("Venus", "exit").step("on", 0.05, 0)
        one_shot(el, "Arrive", "whoosh_slow.wav", 1.0, pos=end, vol=0.3, spatial=0.6)
        one_shot(el, "Rise", "drift_low.wav", T_RISE0, pos=rest, vol=0.3, spatial=0.5)
        el.play_dur = T_RISE1 + 0.5
        print(f"  stills: venus picture {w:.1f} m square; the figure {TALL:g} m tall, feet {rest[1]:g} m above the equator, "
              f"{math.dist(rest, EYE):.1f} m from the eye; one turn in {TURN:g} s")
        cue("S2", "Venus", "still_venus")

    # ---- Stewart ------------------------------------------------------------------------------------------------------
    voice = D.get("voice")
    if voice or "stewart" in have:
        T_SND, T_PIC = 2.0, 6.0
        el = element("still_stewart", "module stills: the room goes dark, the clip plays, then the picture fades in large")
        SP.bubble(el, g, "TK_Still")
        t_end = T_PIC + 5.0
        if voice:
            src = [EYE[0], 9.0, EYE[2] + AHEAD]
            el.node("Voice", {"audio": {"clip": voice["clip"], "vol": 1.0, "loop": False, "spatial": 0.6, "min": 40, "max": 400}}, p=src, on=0)
            el.t("Voice").step("on", 0, 0); el.t("Voice").step("on", T_SND, 1)
            t_end = max(t_end, T_SND + voice["dur"] + 0.3)
            el.t("Voice").step("on", t_end, 0)             # off in the held pose: the clip is never played a second time
            el.t("Voice", "exit").step("on", 0.05, 0)
        if "stewart" in have:
            end, w = picture(el, "stewart", 14.0, y=8.5, t0=T_PIC, fade=4.0, fly=False)
            if have["stewart"].get("depth"):
                # the picture is a relief (stills_art.py): it turns a few degrees each way, slowly, so the depth shows
                SWAY, PERIOD, y0 = 7.0, 18.0, face(end)
                el.loop("Pic", PERIOD, {"": {"e": [[PERIOD * k / 24, 0, round(y0 + SWAY * math.sin(math.tau * k / 24), 4), 0] for k in range(25)]}})
            print(f"  stills: stewart {w:.1f} x 14 m, fades in from {T_PIC:g} s")
        else: print("  stills: stewart has no picture yet (tools/stills/stewart.png): dark and the clip only")
        el.play_dur = t_end + 0.2
        cue("S3", "Stewart", "still_stewart")
    return out
