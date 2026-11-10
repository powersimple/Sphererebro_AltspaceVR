"""The media timeline's layout (Ben, 2026-11-10): layers of firsts stacked on one time axis, on the inside of the dome.
Shared by choreo.py (where each thing goes) and make_cards.py (what each card says), so the two can't disagree.

Each layer is a rail at its own latitude on a sphere of radius R about the mid-audience eye (so every rail reads as a
level line from the seats, and the whole wall stays inside the dome); the year runs along the
longitude (a0 left .. a1 right, seen from the seats). A card sits above or below its rail, on the first level where it
doesn't cover its neighbour. Layers are stacked bottom (first layer: Media, nearest eye level) to top, each as tall as
"""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = json.load(open(os.path.join(REPO, "Assets", "_Sphererebro", "Config", "talk_timeline_layers.json"), encoding="utf-8-sig"))

R = 46.0                    # metres from the mid-audience eye
A0, A1 = -78.0, 78.0        # longitude span, degrees from straight ahead
LAT0 = 3.0                  # latitude of the lowest thing (the year axis), degrees
CW, CH = 6.0, 1.5            # an item's card, metres (4:1, as the atlas cell)
GAP = 0.4                   # least gap between two cards on one level, metres
LEVEL = CH + 0.2            # level pitch
FIRST = CH / 2 + 0.4        # the first level's centre above (or below) its rail
PAD = 0.7                   # clear metres between two layers' cards


def frac(year):
    s = DATA["scale"]
    if year <= s[0][0]: return 0.0
    for (y0, f0), (y1, f1) in zip(s, s[1:]):
        if year <= y1: return f0 + (f1 - f0) * (year - y0) / (y1 - y0)
    return 1.0


def layout():
    """-> {"rails": [{name, color, lat, cards: [...]}], "axis": {lat, years}, "cards": [flat list, card index = i]}"""
    rails = []
    for layer in DATA["layers"]:
        ends = {}           # level (+1, -1, +2, -2 ...) -> right edge (metres along the rail) of its last card
        items = []
        for it in sorted(layer["items"], key=lambda x: x["y"]):
            f = frac(it["y"])
            items.append({"f": f, "y": it["y"], "t": it["t"], "approx": it.get("approx", False), "img": it.get("img")})
        rails.append({"name": layer["name"], "color": layer["color"], "items": items, "ends": ends})
    # stack from the bottom: the axis, then the first layer ... up to the last; a rail's latitude sets its length, and
    # its length sets how many levels its cards need, so settle each rail in turn
    lat = LAT0
    axis = {"lat": lat, "years": DATA["axis"]}
    below = 1.3 + PAD       # the axis's own year labels sit above it
    for rail in rails:
        # the levels depend on the latitude and the latitude on the levels: a few rounds settle it
        down = 1
        for _ in range(4):
            lat_r = lat + math.degrees((below + extent(down)) / R)
            up, d2 = place(rail, lat_r)
            if d2 <= down: break
            down = d2
        rail["lat"] = lat_r
        lat = lat_r; below = extent(up) + PAD
    cards = []
    for rail in rails:
        for it in rail["items"]:
            it["i"] = len(cards); cards.append({"i": it["i"], "kind": "item", "year": it["y"], "approx": it["approx"], "t": it["t"], "color": rail["color"], "w": CW, "h": CH, "img": it["img"]})
        rail["label"] = len(cards); cards.append({"i": rail["label"], "kind": "layer", "t": rail["name"], "color": rail["color"], "w": CW, "h": CH})
    axis["cards"] = []
    for y in axis["years"]:
        axis["cards"].append(len(cards)); cards.append({"i": len(cards), "kind": "axis", "year": y, "t": "", "color": "9a8a6a", "w": 3.6, "h": 0.9})
    for rail in rails:          # a picture is a card of its own (square): it opens big, then settles on its card's left end
        for it in rail["items"]:
            if it["img"]: it["pic"] = len(cards); cards.append({"i": it["pic"], "kind": "pic", "t": it["t"], "img": it["img"], "color": rail["color"], "w": CH, "h": CH})
    return {"rails": rails, "axis": axis, "cards": cards}


def extent(levels):
    """Metres a rail's cards reach above (or below) it with this many levels on that side."""
    return 0.3 if levels == 0 else FIRST + (levels - 1) * LEVEL + CH / 2


def place(rail, lat):
    """Give every card of the rail a level at this latitude; -> (levels used above, levels used below)."""
    length = math.radians(A1 - A0) * R * math.cos(math.radians(lat))
    ends = {}
    up = down = 0
    for it in rail["items"]:
        x = it["f"] * length
        for lv in (1, -1, 2, -2, 3, -3, 4, -4):
            if ends.get(lv, -1e9) + GAP <= x - CW / 2:
                ends[lv] = x + CW / 2; it["level"] = lv; break
        else:
            it["level"] = 4; ends[4] = x + CW / 2
        if it["level"] > 0: up = max(up, it["level"])
        else: down = max(down, -it["level"])
    return up, down


def offset(level):
    """A card's centre above (+) or below (-) its rail, metres."""
    return (FIRST + (abs(level) - 1) * LEVEL) * (1 if level > 0 else -1)


if __name__ == "__main__":
    L = layout()
    for r in L["rails"]:
        print(f"{r['name']:18s} lat {r['lat']:5.1f}  levels {sorted({i['level'] for i in r['items']})}")
    print("cards:", len(L["cards"]))
