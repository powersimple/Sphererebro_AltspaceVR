"""Shared by the globe modules (media_tour, media_capture): the black bubble and the globe rig.

The bubble: a black shell (29 m, centred on the audience, inside the curved screen's 30 m) with a black floor just under
the stage. It fades in over 2.5 s on a transparent copy, then an opaque copy takes over, so everything outside it is
really hidden and the module looks the same whatever cue it is played from. On exit the opaque copy stays for 2.7 s (a
following module's bubble has closed by then), then the transparent one fades out.

The globe rig (Unity axes; the asset's parts are unit-radius with Y = the north pole and longitude 0 facing -Z):
    Globe  (position = centre, scale = radius in metres)
      Tilt (X rotation: EPS - latitude brings that latitude to face the seats)
        Spin (Y rotation: the longitude that faces the seats)
Ben, 2026-11-10: everything is seen above the equator of the sphere (y = 0), so the globe hangs above it.
"""
import math

BUB_R = 29.0
FLOOR_Y = -3.2
# Ben, 2026-11-10 (after seeing it): "place it lower and make it larger and closer". Was 12 up, 21 ahead, radius 9.
# Ben, later the same day: "The Globe is too close, move it back": 18 -> 23 m ahead (still 11 m in radius, as low).
CENTRE_UP, CENTRE_AHEAD, RADIUS = 11.6, 23.0, 11.0       # the globe's centre above the equator / ahead of the eye; its radius


def bubble(el, g, mat="TK_Media"):
    eye = list(g["EYE"])
    el.node("SpaceFade", {"special": "envsphere", "radius": BUB_R + 0.3, "mat": mat + "SpaceFade", "segments": 48}, p=eye, a=0)
    el.node("Space", {"special": "envsphere", "radius": BUB_R, "mat": mat + "Space", "segments": 48}, p=eye, on=0)
    for holder, m in (("SpaceFade", mat + "SpaceFade"), ("Space", mat + "Space")):
        el.node(holder + "/Floor", {"special": "floor", "size": 2 * BUB_R + 2, "y": FLOOR_Y - eye[1], "mat": m})
    el.t("SpaceFade").add("a", 0, 2.5, lambda u: u, "smooth")
    el.t("SpaceFade").step("on", 0, 1); el.t("SpaceFade").step("on", 2.7, 0)
    el.t("Space").step("on", 0, 0); el.t("Space").step("on", 2.5, 1)
    # exit
    el.t("Space", "exit").step("on", 2.7, 0)
    el.t("SpaceFade", "exit").step("on", 0, 0); el.t("SpaceFade", "exit").step("on", 2.7, 1)
    el.t("SpaceFade", "exit").step("a", 0, 1); el.t("SpaceFade", "exit").add("a", 2.7, 5.0, lambda u: 1 - u, "smooth")
    el.t("SpaceFade", "exit").step("on", 5.05, 0)
    el.exit_dur = 5.1


def globe(el, g, asset, t0=1.5, t1=4.5):
    """The rig, arriving between t0 and t1 (it grows from a point), leaving in the exit. Returns (centre, EPS, spin path)."""
    eye = g["EYE"]
    centre = [eye[0], CENTRE_UP, eye[2] + CENTRE_AHEAD]
    eps = math.degrees(math.atan2(eye[1] - centre[1], centre[2] - eye[2]))     # the direction from the globe down to the seats
    el.node("Globe", {}, p=centre, s=0.02 * RADIUS, on=0)
    el.t("Globe").step("on", 0, 0); el.t("Globe").step("on", t0, 1)
    el.t("Globe").add("s", t0, t1, lambda u: [RADIUS * (0.02 + 0.98 * u)] * 3, "out")
    el.node("Globe/Tilt", {})
    el.node("Globe/Tilt/Spin", {})
    spin = "Globe/Tilt/Spin"
    el.node(spin + "/GlobeW", {"asset": asset, "part": "Globe_W"})
    el.node(spin + "/GlobeE", {"asset": asset, "part": "Globe_E"})
    el.t("Globe", "exit").add("s", 0, 1.6, lambda u: [RADIUS * (1 - 0.98 * u)] * 3, "in")
    el.t("Globe", "exit").step("on", 1.65, 0)
    return centre, eps, spin


def unit(lat, lon, r=1.0):
    """The asset's frame: Y = north pole, longitude 0 toward -Z."""
    a, d = math.radians(lat), math.radians(lon)
    return [r * math.cos(a) * math.sin(d), r * math.sin(a), -r * math.cos(a) * math.cos(d)]
