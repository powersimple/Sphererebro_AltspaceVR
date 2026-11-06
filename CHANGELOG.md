# Spherebro changelog

Newest first. Each entry: what changed, where, and what is **not** verified. Rules and pipeline: `CLAUDE.md`.

## 2026-11-06 — first build (Claude, on Ben's Windows machine, Ben AFK)

### State at the end of the day
- The whole world is generated and builds headless with baked concourse lighting. **Nothing has been uploaded and nothing has
  been in a headset.** Ben builds/uploads himself (Builder window).
- Generated: 8 FBX (57k triangles in total, incl. the hidden video and glow shells), 32 materials (15 reused Polys textures),
  the scene `Assets/_Spherebro/Scenes/Spherebro.unity` (246 renderers, 75 colliders, 41 lights, 184 BS Object Ids),
  `Assets/WebRoot/script.js` (desk + props + XR Time Machine v0.3.3).
- Script tests: 30/30 pass against a mock of the Banter API (`..\Assets\tests\script_test.html`). Mock only.
- Review renders: `..\Assets\previews\` (`0x_*.png` Blender workbench, `unity_*.png` Unity cameras).

### What was built
- **Sphere** r 50: lit solar-panel shell (dark by default: the sphere is real-time lit only, so it can go pitch black), a glowing
  copy for "PANELS", an inside-out video sphere (`Sphere_Screen`, `BS.VideoPlayer`) for "VIDEO", a bronze lattice, a bronze
  portal flange and ring where the bridge enters. "DARK" pressed twice hides every shell: the starfield skybox shows (STARS).
- **Concourse** (the band): 120 deg arc outside the sphere at bridge level; one-way windows (the inner shell is single-sided, so
  you see in, they can't see out); long bar (back bar, 3 shelves of bottles, 12 stools, 8 pendants, bartender gap), 8 standing
  tables, 3 lounge groups (curved sofa, table, rug), restroom doors at both ends, planters, warm baked lighting, cove strips.
- **Plaza** (spawn) 6 m below: compass-star spawn pad, planters, escalator (animated steps, ramp collider) + stairs up through the
  facade, a blue lift pad that teleports to the concourse, facade sign.
- **Bridge**: 3 telescoping segments (retract under the concourse floor) + a drawspan across the void to the dais. Gates
  (invisible walls) close the open edges whenever a piece is away.
- **Theatre**: ring 17.2 m across floating at the centre; **33 + 35 recliners** in two stadium rows (row 2 on a 0.5 m riser), each
  row over 330 deg with the 30 deg carve-out at 6 o'clock; walkway, landing, steps, glass rails, invisible safety walls.
- **Dais**: 3 m rotating floor with inlay; waist-high horseshoe desk (open toward the bridge) with 16 buttons and a joystick:
  TURN L/R, STOP, HOME, BRIDGE, DRAWSPAN, HOUSE LIGHTS, XR TIME MACHINE, DARK/STARS, PANELS, LATTICE, VIDEO, ORBS, ORBS UP/DOWN/SPREAD.
- **Show objects**: 6 glowing orbs the desk orbits, raises and spreads. They, the dais and the bridge pieces are in
  `XRTM_CONFIG.trackObjects`, so a rehearsal recorded with XR Time Machine replays the whole show.
- **Grabbables**: 22 champagne flutes + 14 beer bottles (tables and bar), Polys GrabLite spec, each returns home 10 s after
  being left more than 15 cm away.

### Decisions Claude made while Ben was away (change any of them)
1. **Ring size**: 33 + 35 recliners don't fit the 10 m ring (a luxury recliner needs ~0.9 m of arc). Kept the chair counts, grew
   the ring to **17.2 m across** (rows at r 5.4 and 7.1, pitch 0.94 m and 1.17 m). The 10 m figure is the inner void + dais.
2. **Concourse arc 120 deg**, not a full ring (a full ring is ~350 m of corridor: empty and heavy). `BAND_A0/A1` in the Blender script.
3. **Plaza below, escalator up** through the concourse facade on the bridge axis, so arrival walks straight to the portal.
4. **Admin-only desk**: every desk press writes protected state; guests get "Moderators only". (Ben's sentence "the admin
   should…" was cut off; assumed this.)
5. **Rotation safety**: turning auto-retracts the drawspan; the drawspan only extends at HOME and stopped. The dais is walled
   (invisible) all round; its gate opens only while the drawspan is out.
6. **Fall safety**: falling into the sphere hits a rescue teleporter at y -30 back to the ring landing.
7. **Joystick and buttons both** turn the dais (buttons are the dependable path; the joystick needs a headset test).
8. **Models in FBX** (Ben: native FBX over GLB for this). Materials are project materials remapped by name, so they're editable.
9. **Textures reused from the Polys theatre** (solar panel, bronze, tile, solar floor, wood, carbon, brushed metal, rug normal)
   instead of new ones: low poly, quality maps, small download.
10. **Video sphere** uses `BS.VideoPlayer` (an .mp4 URL, not YouTube). No URL is set yet: `SB.sphereVideo` in script.js or
    `SB.setVideo(url)` from the browser console.

### Not verified (needs Ben or a headset)
- Whether a **standing avatar rides the rotating dais** (fallback: presenter turns themselves; floor/desk still turn).
- Moving colliders: walking on a bridge segment while it retracts. Don't retract with people on it.
- `BS.VideoPlayer` on a 50 m inverted sphere: orientation of the equirect, mapping seam, performance on Quest.
- Seat click boxes and sit height on the recliners; joystick feel; button label legibility (font 0.18).
- Quest frame rate (only a headset gives real numbers). Real-time lights inside the sphere: key + 3 house (within the 4-per-object limit).
- XR Time Machine with these trackObjects (playback moving the dais and bridge) — untested anywhere but the mock.
- Build size: not built for Android yet.

### Open items / questions for Ben
- **Sibling `..\Assets\` folder is not in git** (Ben asked for sources there; the repo is the Unity project). Yoda-IX gets the FBX
  outputs through git but not the Blender script, .blend or tests. Options: move the git root up one level, a second repo, or
  copy sources in. Ben's call.
- `.claude/settings.json` (shared permissions) was not created: the desktop app blocked Claude from writing its own settings.
- A 360 video URL for the sphere; the Altspace avatar cap per instance (68 seats + presenter).
- Restrooms are doors and signs only. Bartender spot has no bartender tooling (BS seat or name tag), just room.
- Logos/branding for the event (`=== EVENTS ===` group is empty).
