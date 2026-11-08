"""Choreographer for the talk show.

Reads   Assets/_Sphererebro/Config/talk_show.json (cues, text) + talk_timeline_events.json
Writes  Assets/_Sphererebro/Config/talk_timeline.json   (every element: its nodes and keyframed tracks)

The Unity builder (SphererebroTalk.cs) turns each element into three twins under the "Talk" root:
    Talk_<id>_Play  (entrance: AnimationClip from "play")      Talk_<id>_Hold (the final pose, no motion)
    Talk_<id>_Exit  (from the final pose: AnimationClip from "exit", when the element has one)
and the browser harness (tools/harness) plays the same tracks, so what is checked there is what Unity plays.

Coordinates: Unity metres (left-handed, +Y up), sphere centre = origin; the audience sits at the back facing +Z.
Rotations are Euler degrees (Unity order Z, X, Y). Assets face -Z at yaw 0 (toward the audience).
Track keys: p = localPosition, e = localEulerAngles, s = localScale, on = active (step), a = alpha of the node's own
renderer, i = light intensity, v = audio volume. Each track: [[t, v0, v1, ...], ...], sampled densely with the easing
baked in (Unity uses linear tangents between the samples, the harness linear interpolation: identical).
Run: <blender python> tools/talk/choreo.py
"""
import json, math, os, random

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
CFG = os.path.join(REPO, "Assets", "_Sphererebro", "Config")
SHOW = json.load(open(os.path.join(CFG, "talk_show.json"), encoding="utf-8-sig"))
TL = json.load(open(os.path.join(CFG, "talk_timeline_events.json"), encoding="utf-8-sig"))
random.seed(1110)

EYE = SHOW["audience"]["eye"]           # mid-audience eye
AX, AZ = EYE[0], EYE[2]
FLOOR = -12.0                           # the data-hall floor and the media objects' base height
HZ = 15.0

# ------------------------------------------------------------------ easing + sampling
def lin(x): return x
def smooth(x): return x * x * (3 - 2 * x)
def in_out(x): return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2
def out3(x): return 1 - (1 - x) ** 3
def out2(x): return 1 - (1 - x) ** 2
def in2(x): return x * x
def out_back(x, k=1.2): return 1 + (k + 1) * (x - 1) ** 3 + k * (x - 1) ** 2
def clamp01(x): return 0.0 if x < 0 else 1.0 if x > 1 else x
EASE = {"lin": lin, "smooth": smooth, "inout": in_out, "out": out3, "out2": out2, "in": in2, "back": out_back}

def lerp(a, b, t): return [x + (y - x) * t for x, y in zip(a, b)]

def r4(v): return round(v, 4)


def yaw_to(frm, to):
    """Yaw (deg) that turns an asset (front = -Z) at `frm` to face point `to`."""
    dx, dz = to[0] - frm[0], to[2] - frm[2]
    return math.degrees(math.atan2(-dx, -dz))


def bezier(pts, t):
    """Catmull-Rom through pts (list of [x,y,z]) at t in 0..1 (uniform)."""
    n = len(pts) - 1
    if n == 1: return lerp(pts[0], pts[1], t)
    f = min(t * n, n - 1e-9); i = int(f); u = f - i
    p0 = pts[max(i - 1, 0)]; p1 = pts[i]; p2 = pts[i + 1]; p3 = pts[min(i + 2, n)]
    return [0.5 * ((2 * b) + (-a + c) * u + (2 * a - 5 * b + 4 * c - d) * u * u + (-a + 3 * b - 3 * c + d) * u ** 3)
            for a, b, c, d in zip(p0, p1, p2, p3)]


class Track:
    """Builds one node's keys. add(key, t0, t1, fn(u)->value list, ease, hz)"""
    def __init__(self): self.k = {}

    def add(self, key, t0, t1, fn, ease="lin", hz=HZ):
        e = EASE[ease] if isinstance(ease, str) else ease
        n = max(1, int(math.ceil((t1 - t0) * hz)))
        out = self.k.setdefault(key, [])
        for j in range(n + 1):
            u = j / n; t = t0 + (t1 - t0) * u
            v = fn(e(u))
            v = v if isinstance(v, (list, tuple)) else [v]
            if out and abs(out[-1][0] - t) < 1e-6: out.pop()
            out.append([r4(t)] + [r4(x) for x in v])

    def step(self, key, t, v):
        out = self.k.setdefault(key, [])
        out.append([r4(t)] + ([r4(x) for x in v] if isinstance(v, (list, tuple)) else [r4(v)]))

    def const(self, key, t, v): self.step(key, t, v)


class Element:
    def __init__(self, eid, note=""):
        self.id = eid; self.note = note
        self.nodes = []                      # [{"path", "make", "rest"}]
        self.play = {}; self.exit = {}; self.loops = []
        self.play_dur = 0.0; self.exit_dur = 0.0
        self.video = None

    def node(self, path, make=None, p=(0, 0, 0), e=(0, 0, 0), s=(1, 1, 1), on=1, a=None):
        rest = {"p": [r4(x) for x in p], "e": [r4(x) for x in e], "s": [r4(x) for x in (s if isinstance(s, (list, tuple)) else (s, s, s))], "on": on}
        if a is not None: rest["a"] = a
        self.nodes.append({"path": path, "make": make or {}, "rest": rest})
        return path

    def t(self, path, which="play"):
        d = self.play if which == "play" else self.exit
        if path not in d: d[path] = Track()
        return d[path]

    def loop(self, path, dur, tracks):
        self.loops.append({"path": path, "dur": dur, "tracks": tracks})

    def to_json(self):
        rest = {n["path"]: n["rest"] for n in self.nodes}
        hold = {}
        for path, tr in self.play.items():
            h = dict(rest.get(path, {}))
            for key, keys in tr.k.items():
                keys.sort(key=lambda r: r[0])
                last = keys[-1][1:]
                h[key] = last if len(last) > 1 else last[0]
            hold[path] = h
        def dump(d):
            out = {}
            for path, tr in d.items():
                for keys in tr.k.values(): keys.sort(key=lambda r: r[0])
                out[path] = tr.k
            return out
        pd = max([self.play_dur] + [k[-1][0] for tr in self.play.values() for k in tr.k.values()])
        ed = max([self.exit_dur] + [k[-1][0] for tr in self.exit.values() for k in tr.k.values()]) if self.exit else 0
        return {"note": self.note, "nodes": self.nodes, "play": {"dur": r4(pd), "tracks": dump(self.play)},
                "hold": hold, "exit": ({"dur": r4(ed), "tracks": dump(self.exit)} if self.exit else None),
                "loops": self.loops}


EL = {}
def element(eid, note=""):
    EL[eid] = Element(eid, note); return EL[eid]


def fade_in(el, path, t0=0.0, dur=2.0, key="a", to=1.0, ease="smooth"):
    el.t(path).add(key, t0, t0 + dur, lambda u: u * to, ease)
def fade_out(el, path, t0=0.0, dur=2.0, key="a", frm=1.0, ease="smooth"):
    el.t(path, "exit").add(key, t0, t0 + dur, lambda u: frm * (1 - u), ease)
def hide_at(el, path, t, which="exit"):
    el.t(path, which).step("on", t, 0)


def audio(clip, vol=1.0, loop=False, spatial=1.0, minD=8, maxD=400):
    return {"audio": {"clip": clip, "vol": vol, "loop": loop, "spatial": spatial, "min": minD, "max": maxD}}


def one_shot(el, path, clip, at, pos=(0, 0, 0), vol=1.0, spatial=1.0, minD=10, maxD=500, which="play"):
    """An AudioSource (play on awake) that switches on at `at`: plays exactly in step with the animation."""
    el.node(path, audio(clip, vol, False, spatial, minD, maxD), p=pos, on=0)
    el.t(path, which).step("on", 0, 0); el.t(path, which).step("on", at, 1)


def bed(eid, clip, vol, note):
    el = element(eid, note)
    el.node("Bed", audio(clip, vol, True, 0.0), on=1)
    el.t("Bed").add("v", 0, 3.0, lambda u: vol * u, "smooth")
    el.t("Bed", "exit").add("v", 0, 2.5, lambda u: vol * (1 - u), "smooth")
    hide_at(el, "Bed", 2.6)
    return el


# ================================================================== ENVIRONMENTS
el = element("env_dark", "the dome goes dark: a near-black sphere just inside the shell, faded in over 3 s")
el.node("Sphere", {"special": "envsphere", "radius": 48.5, "mat": "TK_EnvDark", "segments": 48}, a=0)
fade_in(el, "Sphere", 0, 3.0); fade_out(el, "Sphere", 0, 2.5); hide_at(el, "Sphere", 2.6)

el = element("stars", "a slow star field (2,600 points on a 46 m shell, turning 0.4 deg/s)")
el.node("Spin", {})
el.node("Spin/Field", {"special": "stars", "radius": 46.0, "count": 2600, "mat": "TK_Stars", "seed": 7}, a=0)
fade_in(el, "Spin/Field", 0.5, 4.0); fade_out(el, "Spin/Field", 0, 2.0); hide_at(el, "Spin/Field", 2.1)
el.loop("Spin", 900.0, {"": {"e": [[0, 8, 0, 3], [900, 8, 360, 3]]}})

el = element("env_white", "the Construct: everything goes white. A 450 m white room (no horizon line), faded in over 2.5 s")
el.node("Room", {"asset": "white_room", "matAlpha": "TK_WhiteRoom"}, a=0)
fade_in(el, "Room", 0.6, 2.4); fade_out(el, "Room", 0, 4.0); hide_at(el, "Room", 4.1)

el = element("dust", "white-room dust: slow grey specks through the hall, so the racks' speed reads (cue 4 to 9)")
el.node("Dust", {"special": "dust", "size": [260, 70, 420], "center": [0, 18, 150], "count": 1800})
el.t("Dust").step("on", 0, 0); el.t("Dust").step("on", 0.8, 1)

el = element("env_warm", "warm light returns: a 440 m dusk dome (gold horizon, deep blue zenith), over 5 s")
el.node("Room", {"special": "envsphere", "radius": 440.0, "mat": "TK_WarmRoom", "segments": 48}, a=0)
fade_in(el, "Room", 0.5, 5.0); fade_out(el, "Room", 0, 3.0); hide_at(el, "Room", 3.1)

# ================================================================== LIGHTS (realtime, no shadows)
def light_el(eid, note, lights, rise=3.0, fall=2.5):
    el = element(eid, note)
    for name, L in lights.items():
        el.node(name, {"light": L}, p=L["pos"], e=L.get("rot", (0, 0, 0)))
        I = L["intensity"]
        el.t(name).add("i", 0, rise, (lambda I: lambda u: I * u)(I), "smooth")
        el.t(name, "exit").add("i", 0, fall, (lambda I: lambda u: I * (1 - u))(I), "smooth")
        hide_at(el, name, fall + 0.05)
    return el

light_el("warm_light", "warm key + fill on the media objects", {
    "Key": {"type": "spot", "color": [1.0, 0.78, 0.52], "intensity": 60.0, "range": 90, "angle": 75, "pos": [-6, 24, -46], "rot": [38, 8, 0]},
    "Fill": {"type": "spot", "color": [1.0, 0.6, 0.35], "intensity": 30.0, "range": 80, "angle": 80, "pos": [14, 6, -40], "rot": [10, -20, 0]},
    "Rim": {"type": "point", "color": [1.0, 0.55, 0.25], "intensity": 45.0, "range": 60, "pos": [0, 14, 6]}})
light_el("blue_light", "cool blue light on the feed wall", {
    "BlueL": {"type": "point", "color": [0.35, 0.55, 1.0], "intensity": 40.0, "range": 40, "pos": [-12, 4, -30]},
    "BlueR": {"type": "point", "color": [0.35, 0.55, 1.0], "intensity": 40.0, "range": 40, "pos": [12, 4, -30]},
    "BlueF": {"type": "point", "color": [0.45, 0.6, 1.0], "intensity": 50.0, "range": 50, "pos": [0, 10, -22]}})
light_el("white_light", "soft white key for the racks in the white room (directional, no shadows)", {
    "Sun": {"type": "directional", "color": [1.0, 0.98, 0.95], "intensity": 1.6, "pos": [0, 60, 0], "rot": [52, 25, 0]},
    "Sky": {"type": "directional", "color": [0.85, 0.9, 1.0], "intensity": 1.0, "pos": [0, 60, 0], "rot": [30, -30, 0]}}, rise=2.0)
light_el("warm_fill", "warm light across the whole sphere for the commons", {
    "Sun": {"type": "directional", "color": [1.0, 0.8, 0.55], "intensity": 1.1, "pos": [0, 60, 0], "rot": [30, -30, 0]}}, rise=5.0)

# ================================================================== AMBIENT BEDS
bed("bed_space", "bed_space.wav", 0.32, "cue 1: deep space drone with Ben's Om bowl")
bed("bed_media", "bed_media.wav", 0.26, "cue 2: warm valve-radio hum and soft crackle")
bed("bed_feed", "bed_feed.wav", 0.24, "cue 3: cool digital pulse")
bed("bed_hall", "bed_hall.wav", 0.30, "cue 4B on: data-hall hum, fans, a low power drone")
bed("bed_commons", "bed_commons.wav", 0.26, "cue 9 on: a warm, open chord")

# ================================================================== TEXT
def text_el(eid, lines, centre, size, mat, line_gap, delay=0.0, per_word=0.32, arc=None, note=""):
    el = element(eid, note)
    el.node("Text", {}, p=centre)
    t_end = delay
    w_i = 0
    for li, line in enumerate(lines):
        words = line.split(" ")
        y = -li * line_gap
        el.node(f"Text/L{li}", {"text": eid, "line": li, "size": size, "mat": mat, "arc": arc, "words": len(words)}, p=(0, y, 0))
        for wi, w in enumerate(words):
            path = f"Text/L{li}/W{wi:02d}"
            t0 = delay + w_i * per_word
            el.t(path).add("a", t0, t0 + 0.9, lambda u: u, "smooth")
            el.t(path).add("s", t0, t0 + 1.1, lambda u: [0.94 + 0.06 * u] * 3, "out")
            el.t(path, "exit").add("a", 0.0 + 0.04 * w_i, 1.6 + 0.04 * w_i, lambda u: 1 - u, "smooth")
            w_i += 1
            t_end = t0 + 1.1
    hide_at(el, "Text", 1.7 + 0.04 * w_i)
    return el, t_end

# cue 1: one statement, word by word, 12 m in front of the seats, then "So who will?" 6 s later (below it)
el1, t1 = text_el("title1", SHOW["text"]["title1"], (0, 5.6, AZ + 15.0), 1.05, "TK_TextLight", 1.55, delay=1.5, arc=14.0,
                  note="cue 1 statement: letters fade in one word at a time; curved on a 14 m arc so every word is the same distance away")
text_el("title2", SHOW["text"]["title2"], (0, 0.3, AZ + 15.0), 1.7, "TK_TextGold", 0, delay=t1 + 6.0, per_word=0.45, arc=14.0,
        note="cue 1: 'So who will?' appears below, 6 s after the statement has formed")
text_el("title3", SHOW["text"]["title3"], (0, 6.0, AZ + 13.0), 2.4, "TK_TextGold", 0, delay=1.0, per_word=0.6, arc=13.0,
        note="cue 10: the opening question returns in front of the seats, and holds to the end")

# ================================================================== MEDIA OBJECTS (cue 2, 2B, 2C)
def media_el(eid, asset, scale, settle, sound, note):
    el = element(eid, note)
    start = [-47.0, FLOOR, -6.0]                    # far left, at the edge of the dark
    across = [10.0, FLOOR, -16.0]                   # across the front: its near face ~15 m from the front row
    mid = [-14.0, FLOOR, -20.0]
    path_pts = [start, mid, across, [settle[0] + 6, FLOOR, settle[2] - 6], settle]
    el.node("Obj", {"asset": asset, "scale": scale}, p=start, e=(0, 60, 0))
    T = 22.0
    def pos(u): return bezier(path_pts, u)
    el.t("Obj").add("p", 0, T, pos, "inout", hz=10)
    face_end = yaw_to(settle, EYE)
    def yaw(u):
        p = bezier(path_pts, in_out(u))
        look = yaw_to(p, EYE)
        sway = 22 * math.sin(u * math.pi * 2.0) * (1 - u)     # turns to show its form, then settles facing us
        return [0, look + sway, 0]
    el.t("Obj").add("e", 0, T, yaw, "lin", hz=10)
    el.t("Obj").add("s", 0, 3.0, lambda u: [scale * (0.85 + 0.15 * u)] * 3, "out")
    # a soft warm glow that comes up with it
    el.node("Obj/Glow", {"light": {"type": "point", "color": [1.0, 0.7, 0.4], "intensity": 35.0, "range": 34}}, p=(0, 0.55, -0.45))
    el.t("Obj/Glow").add("i", 0, 4, lambda u: 35.0 * u, "smooth")
    one_shot(el, "Snd", sound, 0.3, pos=(-30, 0, -20), vol=0.7, spatial=0.6)
    one_shot(el, "Whoosh", "whoosh_slow.wav", 6.0, pos=(-5, 2, -25), vol=0.35, spatial=1.0)
    # exit: sink below and fade (cue 4: swallowed by the white)
    el.t("Obj", "exit").add("p", 0, 2.5, lambda u: [settle[0], FLOOR - 30 * u, settle[2]], "in")
    hide_at(el, "Obj", 2.6)
    return el

media_el("radio", "radio_1920s", 20.0 / 0.48, [-17.5, FLOOR, -14.0], "radio_tune.wav", "cue 2: the 1920s radio drifts in from the far left, 20 m tall, crosses the front and settles left")
media_el("tv", "tv_midcentury", 19.0 / 1.05, [0.0, FLOOR, -8.0], "tv_hum.wav", "cue 2B: the mid-century TV, settles centre")
media_el("monitor", "web_monitor_1990s", 15.0 / 0.40, [17.5, FLOOR, -12.0], "modem.wav", "cue 2C: the 1990s web monitor, screen lit, settles right")

# ================================================================== TIMELINE (cue 2T)
# Ben's 2020Vision timeline, 1746 -> 2019, as a glowing ribbon on a 20 m arc around the audience (above the presenter).
# A comet runs along it visiting every event in turn; each event's card blooms big beside the comet (readable: 14 m wide
# at ~20 m), holds, then shrinks to a small tile on the ribbon, so by the end the ribbon is studded with the whole history.
el = element("timeline", "cue 2T: 200 years of media: a comet runs the ribbon, each event's card blooms big, then settles small")
EVS = TL["events"]
TLR = 20.0; A0, A1 = -78.0, 78.0; TLY = 3.2
per = [1.25 if e["kind"] == "media" else 0.55 for e in EVS]
T0 = 2.0
ev_t = []; acc = T0
for p_ in per: ev_t.append(acc); acc += p_
TRAVEL_END = acc + 1.0
def arc_pt(f, dy=0.0, dr=0.0):
    a = math.radians(A0 + (A1 - A0) * f)
    return [AX + (TLR + dr) * math.sin(a), TLY + dy, AZ + (TLR + dr) * math.cos(a)]
ev_f = [(k + 0.5) / len(EVS) for k in range(len(EVS))]             # events evenly along the arc (recent decades get room)
def f_at_time(t):
    if t <= ev_t[0]: return 0.0
    for k in range(len(EVS) - 1):
        if ev_t[k] <= t <= ev_t[k + 1]: return ev_f[k] + (ev_f[k + 1] - ev_f[k]) * (t - ev_t[k]) / (ev_t[k + 1] - ev_t[k])
    return min(1.0, ev_f[-1] + (t - ev_t[-1]) / per[-1] * (1 - ev_f[-1]))
year_marks = []
for k in range(len(EVS) - 1):                                       # decade ticks between events, by interpolation
    y0_, y1_ = EVS[k]["y"], EVS[k + 1]["y"]
    for yr in range((y0_ // 10 + 1) * 10, y1_ + 1, 10):
        if y1_ > y0_: year_marks.append((yr, ev_f[k] + (ev_f[k + 1] - ev_f[k]) * (yr - y0_) / (y1_ - y0_)))
SEGS = 14
el.node("Ribbon", {"timeline": "ribbon", "center": [AX, TLY, AZ], "radius": TLR, "a0": A0, "a1": A1, "h0": TLY, "h1": TLY,
                   "segments": SEGS, "ticks": [m[1] for m in year_marks], "bigTicks": [m[1] for m in year_marks if m[0] % 50 == 0]})
for k in range(SEGS):                                               # a segment switches on as the comet reaches it
    t_on = next((T0 + j * 0.05 for j in range(4000) if f_at_time(T0 + j * 0.05) >= k / SEGS), T0)
    el.t(f"Ribbon/Seg{k:02d}").step("on", 0, 0); el.t(f"Ribbon/Seg{k:02d}").step("on", max(T0, t_on), 1)
el.node("Comet", {"timeline": "comet"}, p=arc_pt(0), on=0)
el.t("Comet").step("on", 0, 0); el.t("Comet").step("on", T0 - 0.3, 1)
el.t("Comet").add("p", T0, TRAVEL_END, lambda u: arc_pt(f_at_time(T0 + u * (TRAVEL_END - T0))), "lin", hz=12)
el.t("Comet").step("on", TRAVEL_END + 1.0, 0)
el.node("Comet/Light", {"light": {"type": "point", "color": [1.0, 0.85, 0.6], "intensity": 40.0, "range": 14}})
el.node("Cards", {}); el.node("Stems", {})
for i, ev in enumerate(EVS):
    up = (i % 2 == 0)
    big = 1.0 if ev["kind"] == "media" else 0.72
    W_, H_ = 14.0 * big, 3.5 * big                                   # the card's world size at full bloom (atlas card 4:1)
    dy = (H_ / 2 + 0.9) * (1 if up else -1)
    base = arc_pt(ev_f[i]); cp = arc_pt(ev_f[i], dy, -0.4)
    path = f"Cards/C{i:02d}"
    el.node(path, {"timeline": "card", "card": i, "kind": ev["kind"], "w": W_, "h": H_}, p=cp, e=(0, yaw_to(cp, EYE), 0), s=0.001)
    tc = ev_t[i]; hold = 2.6 if ev["kind"] == "media" else 1.6
    small = 0.3
    el.t(path).add("s", tc - 0.1, tc + 0.6, lambda u: [max(0.001, u)] * 3, "back")
    el.t(path).add("s", tc + hold, tc + hold + 1.2, lambda u: [1 - (1 - small) * u] * 3, "inout")
    el.t(path).add("p", tc + hold, tc + hold + 1.2, (lambda cp, base, up: lambda u: lerp(cp, [base[0], base[1] + (1.4 if up else -1.4), base[2]], u))(cp, base, up), "inout")
    el.node(f"Stems/S{i:02d}", {"timeline": "stem", "from": base, "to": [base[0], base[1] + (1.0 if up else -1.0), base[2]]}, on=0)
    el.t(f"Stems/S{i:02d}").step("on", 0, 0); el.t(f"Stems/S{i:02d}").step("on", tc, 1)
one_shot(el, "Shimmer", "timeline_shimmer.wav", T0, pos=(0, 4, -28), vol=0.45, spatial=0.3)
for nm in ("Ribbon", "Cards", "Stems"):
    el.t(nm, "exit").add("p", 0, 3.0, lambda u: [0, 30 * in2(u), 0], "lin"); hide_at(el, nm, 3.05)
el.play_dur = TRAVEL_END + 4
# ================================================================== FEED WALL (cue 3) + SHATTER (cue 4)
el = element("feedwall", "cue 3: a wall of feed tiles rises all around, scrolling upward, and closes in front of the trio")
SECT = 8; ARC = 95.0; WR = 16.0
for k in range(SECT):
    a0 = -ARC + 2 * ARC * k / SECT; a1 = -ARC + 2 * ARC * (k + 1) / SECT
    path = f"S{k}"
    el.node(path, {}, p=(AX, -44.0, AZ))
    el.node(path + "/Scroll", {"special": "feedsector", "radius": WR, "a0": a0, "a1": a1, "y0": -44.0, "y1": 44.0,
                                "tileW": 1.08, "tileH": 1.92, "gapW": 0.22, "gapH": 0.3, "period": 3, "seed": 100 + k})
    delay = 0.35 * abs(k - (SECT - 1) / 2)
    el.t(path).add("p", delay, delay + 7.5, lambda u: [AX, -44.0 + 44.0 * u, AZ], "out")
    el.loop(path + "/Scroll", 2.2 * 3 / 0.75, {"": {"p": [[0, 0, 0, 0], [2.2 * 3 / 0.75, 0, 2.2 * 3, 0]]}})
    hide_at(el, path, 0.15)
one_shot(el, "Rise", "feed_rise.wav", 0.2, pos=(0, 0, -28), vol=0.6, spatial=0.4)

el = element("shatter", "cue 4: the feed wall shatters into white particles; then quiet")
el.node("Burst", {"special": "shatter", "radius": WR, "arc": ARC, "count": 5000, "y0": -10, "y1": 18}, p=(AX, 0, AZ))
one_shot(el, "Snd", "shatter.wav", 0.0, pos=(0, 2, -27), vol=0.8, spatial=0.5)
hide_at(el, "Burst", 0.1)

# ================================================================== RACKS (cue 4B..)
RACK_H, RACK_W, RACK_D = 50.0, 12.0, 18.0
INNER_X = 21.0; OUTER_X = 52.0; Z0 = -10.0; STEP = 14.0
near_slots, far_slots = [], []
for k in range(20):
    z = Z0 + STEP * k
    for side in (-1, 1):
        slot = {"p": [side * INNER_X, FLOOR, z], "yaw": -90 * side, "row": "inner", "k": k}
        (near_slots if k < 3 else far_slots).append(slot)
for k in range(15):
    z = Z0 + 28 + 16 * k
    for side in (-1, 1):
        far_slots.append({"p": [side * OUTER_X, FLOOR, z], "yaw": -90 * side, "row": "outer", "k": k})
for j in range(9):
    x = -64 + 16 * j
    far_slots.append({"p": [x, FLOOR, 330.0], "yaw": 0.0, "row": "end", "k": j})

def rack_asset(s, open_=False):
    far = math.hypot(s["p"][0] - AX, s["p"][2] - AZ) > 75
    return ("server_rack_far" if far else "server_rack_hero") + ("_open" if open_ else "") if far else ("server_rack_open" if open_ else "server_rack_hero")

def wave_groups(slots, per):
    slots = sorted(slots, key=lambda s: -math.hypot(s["p"][0] - AX, s["p"][2] - AZ))
    return [slots[i:i + per] for i in range(0, len(slots), per)]

def rack_waves(el, waves, t_first, gap, approach, land_snd=True, prefix="W", pass_by=False):
    land_times = []
    for w, group in enumerate(waves):
        path = f"{prefix}{w:02d}"
        t0 = t_first + gap * w
        merge = [{"asset": rack_asset(s), "p": s["p"], "yaw": s["yaw"]} for s in group]
        el.node(path, {}, p=approach(w, 0.0))
        el.node(path + "/Racks", {"merge": merge, "split": {"LEDs": ["LEDs_Green", "LEDs_Blue", "LEDs_Amber"]}, "shadows": True})
        T = 7.0 if not pass_by else 9.0
        el.t(path).step("on", 0, 0); el.t(path).step("on", t0, 1)
        el.t(path).add("p", t0, t0 + T, (lambda w: lambda u: approach(w, u))(w), "lin", hz=15)
        land = t0 + T
        land_times.append(land)
        # LEDs blink on in sequence after landing (two halves, slow twinkle loops: < 3 Hz)
        for half in ("A", "B"):
            lp = f"{path}/Racks/LEDs_{half}"
            el.t(lp).step("on", 0, 0); el.t(lp).step("on", land + 0.4 + (0.5 if half == "B" else 0), 1)
            el.loop(lp, 1.6 if half == "A" else 2.3, {"Mesh": {"on": [[0, 1], [1.0 if half == "A" else 1.3, 0], [1.6 if half == "A" else 2.3, 0]]}})
        cx = sum(s["p"][0] for s in group) / len(group); cz = sum(s["p"][2] for s in group) / len(group)
        one_shot(el, path + "/Whoosh", "whoosh_fast.wav", t0 + 0.2, pos=(0, 25, 40), vol=0.7, spatial=1.0, minD=20, maxD=600)
        if land_snd: one_shot(el, f"Land{prefix}{w:02d}", "rack_land.wav", land - 0.05, pos=(cx, 0, cz), vol=0.95, spatial=0.85, minD=25, maxD=700)
    return land_times

el = element("racks", "cue 4B: waves of 50 m server racks fly in from the white horizon (~40 m/s average, slowing), lock into long rows, LEDs on in sequence")
el.node("Floor", {"special": "floor", "size": 900, "y": FLOOR - 0.02, "mat": "TK_HallFloor"}, a=0)
fade_in(el, "Floor", 0.0, 3.0, to=1.0)
far_waves = wave_groups(far_slots, 9)
def far_approach(w, u):
    # rigid formation offset: from 330 m further out and 18 m up, easing out (fast, then slowing to a stop)
    e = out3(u)
    return [0.0, 18.0 * (1 - out2(u)), 330.0 * (1 - e)]
rack_waves(el, far_waves, 0.6, 1.7, far_approach)
one_shot(el, "Rumble", "rumble.wav", 0.4, pos=(0, -5, -20), vol=0.75, spatial=0.2)
# exit (cue 9): the closed racks swap, wave by wave from the front, to open ones (racks_open does the reverse)
hide_at(el, "Floor", 0.05)    # racks_open carries its own floor
el.exit_dur = 1.6

el = element("racks_near", "cue 4B: the nearest racks pass on both sides of the seats, high and close (over the concourse roof), then come back down into the first slots")
near_waves = [[s for s in near_slots if s["p"][0] < 0], [s for s in near_slots if s["p"][0] > 0]]
def near_approach(w, u):
    # from the front horizon at height, past the audience (to z -38 beyond the slots), then back and down into the slots
    pts = [[0, 34, 300], [0, 26, 60], [0, 24, -28], [0, 22, -38], [0, 14, -18], [0, 0, 0]]
    return bezier(pts, in_out(u) * 0.35 + out3(u) * 0.65)
rack_waves(el, near_waves, 9.0, 0, near_approach, pass_by=True)
el_near = EL["racks_near"]
el_near.t("W00", "exit").add("p", 0, 3.0, lambda u: [-11 * u, 0, 0], "inout")
el_near.t("W01", "exit").add("p", 0, 3.0, lambda u: [11 * u, 0, 0], "inout")
hide_at(el_near, "W00", 3.0); hide_at(el_near, "W01", 3.0)

el = element("racks_near_parted", "cue 5: the front racks part to both sides (here: the parted pose, appearing as racks_near's exit ends)")
parted = [{"p": [s["p"][0] + 11 * (1 if s["p"][0] > 0 else -1), FLOOR, s["p"][2]], "yaw": s["yaw"], "row": "inner", "k": s["k"]} for s in near_slots]
el.node("Racks", {"merge": [{"asset": "server_rack_hero", "p": s["p"], "yaw": s["yaw"]} for s in parted], "split": {"LEDs": ["LEDs_Green", "LEDs_Blue", "LEDs_Amber"]}, "shadows": True}, on=0)
el.t("Racks").step("on", 0, 0); el.t("Racks").step("on", 3.0, 1)
for half in ("A", "B"):
    el.loop(f"Racks/LEDs_{half}", 1.6 if half == "A" else 2.3, {"Mesh": {"on": [[0, 1], [1.0 if half == "A" else 1.3, 0], [1.6 if half == "A" else 2.3, 0]]}})
one_shot(el_near, "PartSnd", "rack_slide.wav", 0.0, pos=(0, 0, -10), vol=0.8, spatial=0.5, which="exit")

el = element("flyover", "cue 4B: two racks pass straight over the audience (base 10 m above the top row, < 2 s overhead), then climb away into the white")
for i, x in enumerate((-4.0, 5.0)):
    path = f"F{i}"
    pts = [[x, 30, 330], [x, 16, 80], [x, 11.5, -10], [x, 12, -44], [x, 40, -60], [x, 260, -40]]
    el.node(path, {"asset": "server_rack_hero", "scale": 1.0}, p=pts[0], e=(0, 180, 0), on=0)
    t0 = 4.5 + 1.1 * i
    el.t(path).step("on", 0, 0); el.t(path).step("on", t0, 1)
    el.t(path).add("p", t0, t0 + 8.5, (lambda pts: lambda u: bezier(pts, u))(pts), "lin", hz=20)
    el.t(path).add("e", t0, t0 + 8.5, lambda u: [-25 * smooth(clamp01((u - 0.55) / 0.45)), 180, 0], "lin")
    el.t(path).step("on", t0 + 8.6, 0)
    one_shot(el, path + "/Whoosh", "whoosh_over.wav", t0 + 2.0, vol=1.0, spatial=1.0, minD=15, maxD=400)
el.play_dur = 16

# ================================================================== LABEL RACKS (4C..4G)
LABEL_S = 0.8
def label_el(eid, final, note, back_to):
    el = element(eid, note)
    start = [final[0], FLOOR, 260.0]
    el.node("Rack", {}, p=start, e=(0, 180, 0))
    el.node("Rack/Sway", {"asset": "server_rack_label", "scale": LABEL_S})
    el.loop("Rack/Sway", 14.0, {"": {"e": [[t * 0.5, 0, 7 * math.sin(2 * math.pi * t * 0.5 / 14), 0] for t in range(29)]}})
    chars = len(SHOW["text"][eid][0])
    em = min(1.6, 0.86 * 10.5 * LABEL_S / (chars * 0.36))            # fits the 10.5 m panel (glyphs ~0.36 em wide), metres
    el.node("Rack/Sway/Label", {"text": eid, "line": 0, "size": em / LABEL_S, "mat": "TK_TextGold", "anchor": "LabelAnchor", "words": None}, a=1)
    el.t("Rack").add("p", 0, 6.0, lambda u: lerp(start, final, u), "out")
    el.t("Rack").add("e", 4.0, 7.5, lambda u: [0, 180 - 180 * u, 0], "inout")
    el.t("Rack/Sway/Label").step("a", 0, 0); el.t("Rack/Sway/Label").add("a", 7.0, 8.2, lambda u: u, "smooth")
    one_shot(el, "Whoosh", "whoosh_fast.wav", 0.1, pos=(final[0], 5, 40), vol=0.6)
    one_shot(el, "Turn", "rack_turn.wav", 4.0, pos=final, vol=0.6, spatial=0.7)
    # exit: slides back into the rows (behind the inner row, out of sight)
    mid = [final[0], FLOOR, final[2] + 40]
    el.t("Rack", "exit").add("p", 0, 4.5, lambda u: bezier([final, mid, back_to], u), "inout")
    hide_at(el, "Rack", 4.6)
    one_shot(el, "Slide", "rack_slide.wav", 0.0, pos=final, vol=0.6, spatial=0.7, which="exit")
    return el

label_el("label1", [0, FLOOR, -12.0], "cue 4C: one rack flies in close, turns its label to the seats: 415 TWh in 2024", [-36, FLOOR, 60])
label_el("label2", [0, FLOOR, -12.0], "cue 4D: a second rack: About 945 TWh by 2030", [36, FLOOR, 74])
label_el("label3", [-11.5, FLOOR, -13.0], "cue 4E: three racks in a line, one at a time: $500 billion", [-36, FLOOR, 88])
label_el("label4", [0.0, FLOOR, -12.0], "cue 4F: $500 billion", [36, FLOOR, 102])
label_el("label5", [11.5, FLOOR, -13.0], "cue 4G: 2 trillion yuan", [-36, FLOOR, 116])

# ================================================================== CURVED SCREEN (cue 5)
el = element("screen", "cue 5: the curved screen (40 x 22 m on a 30 m radius, centred on the audience) rises in front of the seats")
SCR = [0.0, -9.0, AZ + 30.0]
el.node("Screen", {"asset": "curved_screen", "scale": 1.0}, p=[SCR[0], -46, SCR[2]])
el.t("Screen").add("p", 0, 4.5, lambda u: [SCR[0], -46 + (SCR[1] + 46) * u, SCR[2]], "out")
el.node("Screen/Light", {"light": {"type": "spot", "color": [0.9, 0.95, 1.0], "intensity": 4.0, "range": 45, "angle": 120}}, p=(0, 11, -2), e=(0, 180, 0))
el.t("Screen/Light").add("i", 3.5, 6.0, lambda u: 4.0 * u, "smooth")
for nm, dx in (("SpillL", -17.0), ("SpillR", 17.0)):
    el.node("Screen/" + nm, {"light": {"type": "point", "color": [0.35, 0.75, 0.85], "intensity": 30.0, "range": 26}}, p=(dx, 11, 4))
    el.t("Screen/" + nm).step("i", 0, 0); el.t("Screen/" + nm).add("i", 4.0, 7.0, lambda u: 30.0 * u, "smooth")
one_shot(el, "Rise", "screen_rise.wav", 0.0, pos=SCR, vol=0.6, spatial=0.6)
el.t("Screen", "exit").add("p", 0, 4.0, lambda u: [SCR[0], SCR[1] - 37 * u, SCR[2]], "inout")
hide_at(el, "Screen", 4.05)
el.video = {"surface": "curved", "pos": SCR, "delay": 4.0}

# ================================================================== BILL (6) + TANKS (6B)
el = element("bill", "cue 6: the electricity bill unrolls from the top of the sphere to the horizon, numbers climbing as it falls")
BILL = [0.0, 45.5, -8.0]
el.node("Bill", {"asset": "electricity_bill", "scale": [2.0, 1.0, 1.0]}, p=BILL, s=(2.0, 0.02, 1.0))
el.t("Bill").add("s", 0.4, 8.4, lambda u: [2.0, max(0.02, u), 1.0], "out2")
ODO = [0.0, -3.0, BILL[2] - 1.5]          # in front of the paper's front face (the strip is ~0.6 m thick)
el.node("Odo", {}, p=ODO)
digits = "33344"; xs = [-3.9, -2.2, -0.5, 1.9, 3.6]
el.node("Odo/Dollar", {"glyph": "$", "size": 3.0, "mat": "TK_TextInk"}, p=(-5.7, 0, 0), a=0)
el.node("Odo/Point", {"glyph": ".", "size": 3.0, "mat": "TK_TextInk"}, p=(0.75, 0, 0), a=0)
el.node("Odo/Per", {"text": "bill", "line": 0, "size": 1.0, "mat": "TK_TextInk", "sub": "per megawatt-day"}, p=(0, -2.4, 0), a=0)
el.t("Odo/Dollar").add("a", 1.0, 2.0, lambda u: u); el.t("Odo/Point").add("a", 1.0, 2.0, lambda u: u)
T_ODO0, T_ODO1 = 1.2, 8.4
target = 333.44
for si, (d, x) in enumerate(zip(digits, xs)):
    for g in range(10):
        path = f"Odo/D{si}/G{g}"
        el.node(path, {"glyph": str(g), "size": 3.0, "mat": "TK_TextInk"}, p=(x, 0, 0), on=0)
        el.t(path).step("on", 0, 0)
    el.node(f"Odo/D{si}", {})
steps = int((T_ODO1 - T_ODO0) * 3)          # <= 3 changes a second (comfort: nothing faster than 3 Hz)
prev = None
for j in range(steps + 1):
    t = T_ODO0 + (T_ODO1 - T_ODO0) * j / steps
    v = target * out2(j / steps)
    s = f"{v:06.2f}".replace(".", "")[-5:]
    for si in range(5):
        dg = int(s[si])
        for g in range(10):
            el.t(f"Odo/D{si}/G{g}").step("on", t, 1 if g == dg else 0)
el.t("Odo/Per").add("a", T_ODO1, T_ODO1 + 1.2, lambda u: u, "smooth")
one_shot(el, "Paper", "paper_unroll.wav", 0.3, pos=(0, 20, -8), vol=0.8, spatial=0.6)
one_shot(el, "Tick", "odometer.wav", T_ODO0, pos=ODO, vol=0.5, spatial=0.6)
el.t("Bill", "exit").add("s", 0, 3.0, lambda u: [2.0, max(0.02, 1 - u), 1.0], "in")
el.t("Odo", "exit").add("p", 0, 1.0, lambda u: [ODO[0], ODO[1] + 60 * in2(u), ODO[2]])
hide_at(el, "Bill", 3.05); hide_at(el, "Odo", 1.0)
one_shot(el, "PaperOut", "paper_roll.wav", 0.0, pos=(0, 20, -8), vol=0.6, spatial=0.6, which="exit")

el = element("tanks", "cue 6B: ten water tanks rise among the racks on both sides, then fill from empty over 8 s")
tz = [4.0, 18.0, 32.0, 46.0, 60.0]
k = 0
for side in (-1, 1):
    for z in tz:
        x = side * 7.5
        path = f"T{k}"
        el.node(path, {"asset": "water_tank", "scale": 1.0}, p=(x, FLOOR - 30, z))
        d = 0.25 * k
        el.t(path).add("p", d, d + 4.0, (lambda x, z: lambda u: [x, FLOOR - 30 + 30 * u, z])(x, z), "out")
        el.node(path + "/Water", {"part": "Water"}, s=(1, 1, 1))
        el.t(path + "/Water").step("s", 0, [1, 0.001, 1])
        el.t(path + "/Water").add("s", 4.5, 12.5, lambda u: [1, max(0.001, u), 1], "smooth")
        el.t(path, "exit").add("p", 0.1 * k, 0.1 * k + 3.0, (lambda x, z: lambda u: [x, FLOOR - 32 * in2(u), z])(x, z))
        hide_at(el, path, 0.1 * k + 3.05)
        k += 1
one_shot(el, "Rise", "tanks_rise.wav", 0.0, pos=(0, -5, 20), vol=0.6, spatial=0.4)
one_shot(el, "Fill", "water_fill.wav", 4.5, pos=(0, 0, 20), vol=0.7, spatial=0.4)

# ================================================================== TRUST (7) + STAMPS (8)
el = element("locked", "cue 7: the locked rack (padlock lit, tape reels behind glass) drifts in and stops 10 m from the front row; two plain racks flank it")
LOCK_S = 0.7
LOCK = [0.0, FLOOR, -39.7 + 10.0 + RACK_D * LOCK_S / 2]
FL = [-15.0, FLOOR, LOCK[2] + 3.0]; FR = [15.0, FLOOR, LOCK[2] + 3.0]
for name, pos, asset, delay in (("Locked", LOCK, "server_rack_locked", 0.0), ("FlankL", FL, "server_rack_hero", 2.0), ("FlankR", FR, "server_rack_hero", 2.8)):
    start = [pos[0], FLOOR, 150.0]
    el.node(name, {"asset": asset, "scale": LOCK_S}, p=start, e=(0, 0, 0))
    el.t(name).add("p", delay, delay + 14.0, (lambda s, p: lambda u: lerp(s, p, u))(start, pos), "inout")
    el.t(name, "exit").add("p", 0, 3.0, (lambda p: lambda u: [p[0], p[1], p[2] + 90 * in2(u)])(pos), "lin")
    hide_at(el, name, 3.05)
el.node("Locked/PadLight", {"light": {"type": "spot", "color": [1.0, 0.82, 0.5], "intensity": 7.0, "range": 30, "angle": 40}}, p=(0, 12.0 / LOCK_S, -16.0 / LOCK_S), e=(10, 0, 0))
el.t("Locked/PadLight").step("i", 0, 0); el.t("Locked/PadLight").add("i", 12.0, 15.0, lambda u: 7.0 * u, "smooth")
one_shot(el, "Drift", "drift_low.wav", 0.0, pos=(0, 0, 0), vol=0.6, spatial=0.5)
one_shot(el, "Lock", "padlock.wav", 14.0, pos=LOCK, vol=0.8, spatial=0.8)

def stamp_el(eid, target, face_z, note):
    el = element(eid, note)
    tx, ty = target
    contact = [tx, ty, face_z - 0.15]
    away = [tx * 1.4, 44.0, face_z - 22.0]
    el.node("Stamp", {"asset": "stamp", "scale": 1.3}, p=away, e=(-90, 180, 0))
    pts = [away, [tx, ty + 10, face_z - 14], [tx, ty, face_z - 6], contact]
    el.t("Stamp").add("p", 0, 2.2, lambda u: bezier(pts, u), "in", hz=20)
    el.t("Stamp").add("e", 0, 2.2, lambda u: [-90, 180, 6 * (1 - u)], "out")
    el.t("Stamp").add("p", 2.55, 4.6, lambda u: bezier([contact, [tx, ty + 4, face_z - 8], [tx * 1.3, 50, face_z - 25]], u), "inout")
    el.t("Stamp").step("on", 4.65, 0)
    ink_em = min(2.6, 7.4 / (len(SHOW["text"][eid][0]) * 0.36))
    el.node("Ink", {"text": eid, "line": 0, "size": ink_em, "mat": "TK_StampInk", "frame": True}, p=(tx, ty, face_z - 0.06), e=(0, 0, -4), a=0)
    el.t("Ink").step("a", 0, 0); el.t("Ink").step("a", 2.2, 1)
    one_shot(el, "Thud", "stamp_thud.wav", 2.15, pos=contact, vol=1.0, spatial=0.8)
    el.t("Ink", "exit").add("a", 0, 1.0, lambda u: 1 - u); hide_at(el, "Ink", 1.05)
    return el

face = LOCK[2] - RACK_D * LOCK_S / 2
stamp_el("stamp1", (-15.0, 0.5), face + 3.0 - 0.05, "cue 8: a stamp drops onto the left rack: Ohio")
stamp_el("stamp2", (0.0, 9.0), face - 0.4, "cue 8B: onto the locked rack, above the padlock: European Union")
stamp_el("stamp3", (15.0, 0.5), face + 3.0 - 0.05, "cue 8C: onto the right rack: Singapore")

# ================================================================== A PUBLIC COMMONS (9, 9B, 10)
HALL_S = 0.7
HALLS = [("hall_library", -50.0), ("hall_museum", -17.0), ("hall_classroom", 17.0), ("hall_studio", 50.0)]
HR = 29.0
def hall_pos(a): return [AX + HR * math.sin(math.radians(a)), -6.0, AZ + HR * math.cos(math.radians(a))]

el = element("racks_open", "cue 9: the racks swing their doors open (the near racks animate their doors; the field opens wave by wave from the front)")
el.node("Floor", {"special": "floor", "size": 900, "y": FLOOR - 0.02, "mat": "TK_HallFloor"}, a=1)
open_groups = [[], [], []]
for s in far_slots:
    d = math.hypot(s["p"][0] - AX, s["p"][2] - AZ)
    open_groups[0 if d < 75 else 1 if d < 180 else 2].append(s)
for g, group in enumerate(open_groups):
    path = f"G{g}"
    el.node(path, {"merge": [{"asset": rack_asset(s, True), "p": s["p"], "yaw": s["yaw"]} for s in group], "split": {"LEDs": ["LEDs_Green", "LEDs_Blue", "LEDs_Amber"]}, "shadows": True}, on=0)
    el.t(path).step("on", 0, 0); el.t(path).step("on", 0.4 + 0.5 * g, 1)
    for half in ("A", "B"):
        el.loop(f"{path}/LEDs_{half}", 1.6 if half == "A" else 2.3, {"Mesh": {"on": [[0, 1], [1.0 if half == "A" else 1.3, 0], [1.6 if half == "A" else 2.3, 0]]}})
# the closed field hides in the same three steps (racks' exit)
for w, group in enumerate(far_waves):
    d = min(math.hypot(s["p"][0] - AX, s["p"][2] - AZ) for s in group)
    EL["racks"].t(f"W{w:02d}", "exit").k.pop("on", None)
    hide_at(EL["racks"], f"W{w:02d}", 0.4 + 0.5 * (0 if d < 75 else 1 if d < 180 else 2))
for i, s in enumerate(parted):
    path = f"Near{i}"
    el.node(path, {"asset": "server_rack_hero", "scale": 1.0}, p=s["p"], e=(0, s["yaw"], 0))
    el.t(path).add("doors", 0.3 + 0.25 * i, 0.3 + 0.25 * i + 2.6, lambda u: u, "inout")
one_shot(el, "Doors", "doors_open.wav", 0.3, pos=(0, 6, -6), vol=0.8, spatial=0.5)

el = element("halls", "cue 9: the four commons halls rise from below around the seats: library, museum gallery, classroom, broadcast studio")
for i, (asset, a) in enumerate(HALLS):
    p = hall_pos(a)
    yaw = yaw_to(p, EYE)
    path = f"H{i}"
    el.node(path, {"asset": asset, "scale": HALL_S}, p=[p[0], -40, p[2]], e=(0, yaw, 0))
    d = 1.2 + 0.6 * i
    el.t(path).add("p", d, d + 6.0, (lambda p: lambda u: [p[0], -40 + (p[1] + 40) * u, p[2]])(p), "out")
    el.node(path + "/Light", {"light": {"type": "point", "color": [1.0, 0.75, 0.45], "intensity": 3.0, "range": 16}}, p=(0, 5.0 / HALL_S, 2.0 / HALL_S))
    el.t(path + "/Light").step("i", 0, 0); el.t(path + "/Light").add("i", d + 3, d + 7, lambda u: 3.0 * u, "smooth")
    one_shot(el, path + "/Rise", "hall_rise.wav", d, vol=0.7, spatial=0.9, minD=12)

el = element("beams", "cue 9: beams of light arc from the open racks to the halls")
k = 0
for i, (asset, a) in enumerate(HALLS):
    hp = hall_pos(a); top = [hp[0], hp[1] + 14 * HALL_S, hp[2]]
    srcs = [s for s in parted if (s["p"][0] < 0) == (hp[0] < 0)]
    for s in srcs[:2]:
        src = [s["p"][0] - 9 * (1 if s["p"][0] > 0 else -1), 14.0, s["p"][2]]
        d = [top[j] - src[j] for j in range(3)]; L = math.sqrt(sum(x * x for x in d))
        yaw = math.degrees(math.atan2(-d[0] / L, -d[2] / L)); pitch = math.degrees(math.asin(d[1] / L))
        path = f"B{k}"
        el.node(path, {"asset": "light_beam", "scale": 1.0}, p=src, e=(pitch, yaw, 0), s=(20, 1, 0.01))
        H = 0.22 * L / 0.35
        t0 = 2.0 + 0.35 * k
        el.t(path).add("s", t0, t0 + 2.5, (lambda L, H: lambda u: [20, H, max(0.01, L * u)])(L, H), "out")
        k += 1
one_shot(el, "Hum", "beam_hum.wav", 2.0, pos=(0, 10, -10), vol=0.55, spatial=0.3)

el = element("devices", "cue 9B: a phone, a laptop and a headset light up at every hall doorway")
DEV_S = 8.0
k = 0
for i, (asset, a) in enumerate(HALLS):
    hp = hall_pos(a)
    yaw = yaw_to(hp, EYE); r = math.radians(yaw)
    door = [hp[0] - math.sin(r) * 9.5 * HALL_S, hp[1], hp[2] - math.cos(r) * 9.5 * HALL_S]
    for j, dev in enumerate(("Phone", "Laptop", "Headset")):
        off = (j - 1) * 3.2
        pos = [door[0] + math.cos(r) * off, door[1], door[2] - math.sin(r) * off]
        path = f"D{k}"
        el.node(path, {"asset": "devices", "part": dev, "scale": DEV_S}, p=pos, e=(0, yaw, 0), s=0.001)
        t0 = 0.3 + 0.22 * k
        el.t(path).add("s", t0, t0 + 1.0, lambda u: [DEV_S * max(0.001, u)] * 3, "back")
        k += 1
one_shot(el, "Chime", "devices_chime.wav", 0.3, pos=(0, 2, -20), vol=0.6, spatial=0.4)

el = element("halls_bright", "cue 10: the halls glow brighter")
for i, (asset, a) in enumerate(HALLS):
    hp = hall_pos(a)
    path = f"G{i}"
    el.node(path, {"light": {"type": "point", "color": [1.0, 0.78, 0.5], "intensity": 7.0, "range": 26}}, p=[hp[0], hp[1] + 6, hp[2] + 0.0])
    el.t(path).add("i", 0, 4, lambda u: 7.0 * u, "smooth")
    el.node(f"Hot{i}", {"asset": asset, "part": "Glow", "scale": HALL_S, "mat": "TK_HallGlowHot"}, p=hp, e=(0, yaw_to(hp, EYE), 0), a=0)
    el.t(f"Hot{i}").add("a", 0, 4, lambda u: u, "smooth")
one_shot(el, "Swell", "commons_swell.wav", 0.0, pos=(0, 5, -20), vol=0.6, spatial=0.2)

# ================================================================== write
out = {"_readme": "GENERATED by tools/talk/choreo.py from talk_show.json: do not edit.", "audience": SHOW["audience"],
       "floor": FLOOR, "cues": SHOW["cues"], "text": SHOW["text"], "mediaBase": SHOW["mediaBase"],
       "timeline": TL, "elements": {k: v.to_json() for k, v in EL.items()}}
for k, v in EL.items():
    if v.video: out["elements"][k]["video"] = v.video
missing = sorted({e for c in SHOW["cues"] for e in c["on"] + c["off"] if e not in EL})
if missing: raise SystemExit("cues name elements that don't exist: " + ", ".join(missing))
p = os.path.join(CFG, "talk_timeline.json")
json.dump(out, open(p, "w", encoding="utf-8"), separators=(",", ":"))
print(f"choreo: {len(EL)} elements, {len(SHOW['cues'])} cues -> {p} ({os.path.getsize(p) / 1024:.0f} KB)")
for k, v in out["elements"].items():
    print(f"  {k:18s} play {v['play']['dur']:6.1f}s  exit {(v['exit'] or {}).get('dur', 0):5.1f}s  nodes {len(v['nodes'])}")

# ------------------------------------------------------------------ the script.js show block (XR Time Machine reads it)
show = {"title": "IPN talk, 10 Nov 2026", "root": "Talk", "home": [0, 0, 0], "mediaBase": SHOW["mediaBase"], "rehearsalSeconds": 20,
        "videos": [f"Talk_Video_{s}_{l}" for s in ("curved", "dome360", "dome180") for l in ("mono", "sbs", "tb")],
        "cues": [{"id": c["id"], "name": c["name"], "on": c["on"], "off": c["off"], "video": c.get("video")} for c in SHOW["cues"]],
        "elements": {}}
for k, v in out["elements"].items():
    e = {"play": f"Talk_{k}_Play", "hold": f"Talk_{k}_Hold", "exit": f"Talk_{k}_Exit" if v["exit"] else None,
         "playDur": v["play"]["dur"], "exitDur": (v["exit"] or {}).get("dur", 0)}
    if v.get("video"): e["video"] = v["video"]
    # swap the Play twin for the (cheaper, merged) Hold twin once the entrance ends: not for beds (the loop would restart)
    # nor for elements with drifting loops (stars, the feed scroll) whose phase would jump
    loops_ok = all(l["path"].split("/")[-1].startswith("LEDs_") for l in v["loops"])
    has_bed = any("audio" in n["make"] and n["make"]["audio"].get("loop") for n in v["nodes"])
    if loops_ok and not has_bed and v["play"]["dur"] > 0: e["swap"] = True
    show["elements"][k] = e
B0, B1 = "// >>> Sphererebro talk show", "// <<< Sphererebro talk show"
block = (B0 + " (generated by tools/talk/choreo.py from Assets/_Sphererebro/Config/talk_show.json; do not edit)\n"
         + "window.SB_TALK = " + json.dumps(show, separators=(",", ":"), ensure_ascii=True) + ";\n" + B1)
sp = os.path.join(REPO, "Assets", "WebRoot", "script.js")
js = open(sp, encoding="utf-8").read()
if B0 in js:
    a = js.index(B0); b = js.index(B1) + len(B1); js2 = js[:a] + block + js[b:]
else:
    cfg = js.index("// >>> XR Time Machine config"); js2 = js[:cfg] + block + "\n\n" + js[cfg:]
if js2 != js:
    open(sp, "w", encoding="utf-8", newline="").write(js2); print("script.js: talk show block updated")