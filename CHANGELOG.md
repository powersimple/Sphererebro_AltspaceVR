# Sphererebro changelog

Newest first. Each entry: what changed, where, and what is **not** verified. Rules and pipeline: `CLAUDE.md`.

## 2026-11-07: vista seating, a second audience layout (Claude, session Sphererebro2; Ben commits and pushes)

Ben: the in-the-round view is too tight. Keep that layout and the bridge, switched off, and seat the audience near the
entrance instead, with an aisle down the centre and the rows opened out to look at the whole far side of the sphere.
Then: the dais goes on a small stage in front of the seats, slightly below the front row, with no walls around it.
Ben said this one may stay unfinished.

- **Layout switch:** `"seating"` in `Sphererebro.dims.json`, either `"vista"` (now live) or `"round"`. Both layouts are
  always built, and the other one is switched off (inactive, not deleted). In vista these are off: the ring, its 68 seats,
  the bridge with its drawspan, the dais walls and gate, and the concourse portal gate.
- **Vista** (Blender, collection `Vista` -> `SB_Vista.fbx`, 4.6k tris). Every radius is measured in from the shell, so the
  layout follows the sphere size:
  - level entry deck through the portal onto a landing (y 0);
  - **74 recliners** (the same soft model) in 5 raked rows, 1.5 m pitch, 0.45 m rise, rows 8/8/7/7/7 a side;
  - the rows are arcs concentric with the sphere, 22 deg wide, every seat facing the far hemisphere;
  - **centre aisle** of 12 steps with gold nosings, walked on an invisible ramp collider, down to stage level;
  - glass and bronze rails on the sides, the front edge, the landing and the entry, each with a `_COL` wall;
  - gold edge glow on every row front and the stage rim, for Lights Out.
- **Dais on the vista stage:** the builder moves the dais with everything on it onto a 2.6 m stage 0.4 m below the front
  row: desk, buttons, joystick, perches and RIDE zone. The stage has no rail and no dais walls. An invisible edge wall stops
  falls and is open to the aisle. **At HOME the desk faces the dome** (Ben), like the audience, with its open side to the
  aisle so the presenter walks straight in. Rotation is kept for now (Ben: less needed, he can turn in VR). TURN, HOME, the joystick, RIDE, LIGHTS and the sphere keys work as before. BRIDGE and DRAWSPAN labels show
  "—", and pressing either says "No bridge in the vista layout".
- **Lights in vista:** the key light hits the presenter from the dome side, and the three house lights hang over the
  rows. Names are unchanged, so the LIGHTS presets still apply. The rescue teleporter now lands at the top of the aisle.
- **Script:** `SB_DIMS.seating` / `SB.seating`. In vista the script never looks for the bridge, drawspan or gates (each
  miss would cost an 8 s wait at load), writes no drawspan state when turning, and leaves BRIDGE off the status line.
- **Tests:** `script_test.html` passes 38/38 (round). The new `script_test.html?seating=vista` passes 33/33, against the
  mock only.
- Review shots: `unity_20`–`23` (vista) are added to **Sphererebro > Review Shots**.
- Builder compile-checked outside Unity (Roslyn against the project's assemblies), 0 errors. **The scene has NOT been
  rebuilt:** Unity had the project open. Ben runs **Sphererebro > Build World + Bake Lighting**, then Review Shots.

**Not verified:**
- The Unity build of the vista layout. Only Blender previews have been checked.
- Anything in the headset:
  - the aisle ramp's feel;
  - seat clicks;
  - the presenter's sightlines;
  - whether 74 recliners plus the dome hold frame rate on Quest.
- The round layout after this change (switch `"seating": "round"` to check it).

## 2026-11-06 (evening): Phase 0, after the first live upload (Claude; Ben commits and pushes)

First upload worked (world 2047, slug `spherebro` at the time; Ben has since changed it to `sphererebro`): desk buttons and joystick worked in the headset. Ben's notes, and
what changed for each. Full plan for what comes next: the spec on Ben's Desktop, `Sphererebro-Spec-2026-11-06.md`.

- **Renamed Sphererebro** (said like "cerebro"): folders (`B:\VRWorlds\AltspaceVR\Sphererebro\Sphererebro_AltspaceVR`),
  `_Sphererebro`, `SphererebroKit`/`Sphererebro*` classes and menu, scene `Sphererebro.unity`, Blender script and .blend,
  the facade and bar signs (`SPHEREREBRO`), docs, and the git remote (`powersimple/Sphererebro_AltspaceVR`; GitHub
  redirects the old name). Asset GUIDs kept (each .meta renamed with its file). The world slug is now `sphererebro` (Ben changed it in the scene's `__WorldLink` after this entry).
  **Ben:** re-add the repo in GitHub Desktop and the project in Unity Hub at the new folder.
- **Dome size is a setting:** `Assets/_Sphererebro/Config/Sphererebro.dims.json` (sphere radius, concourse, plaza).
  Blender derives every sphere-scale mesh and writes `Sphererebro.derived.json`; the builder reads it for every position,
  light and trigger, and writes the `SB_DIMS` block in script.js. Proof: at r 50 the derived numbers equal the old
  hand-typed ones (spawn z -81, bridge -43.52/-29.55/-15.58). **Not yet tried at another radius.**
- **Brighter:** concourse and plaza baked lights x2.5, more bounce (indirect 1.4), lighter ceiling and floor; rebaked
  (lightmap mean 1.16 -> 2.85). Inside the sphere the load look is **House**: key and house lights brighter and on, dome
  panels glowing softly (dimmer glow than before).
- **Lighting presets:** desk **LIGHTS** cycles House -> Presenter (house 30%, key up) -> **Lights Out** (every sphere
  light off, dome dark; ring edge and desk glow stay lit for wayfinding). **HOUSE** jumps back. State key `sb_lx`.
- **Soft recliners:** rounded (bevelled) cushions, channel-tufted three-bolster back, plush roll arms, pillow headrest,
  crushed-velvet material with gold piping. 1,244 tris each (68 seats, about 85k, one shared mesh).
- **Ride the dais:** the SDK has no moving-platform support for a standing player. **RIDE** (desk) attaches the local
  player to the dais (BS Attached Object, AvatarAttachTo, not a seat); press again or push the stick to step off. Only
  works while standing on the dais (trigger `Dais_Zone_TRIG`), so nobody is pulled in from the seats. Fallback: two
  **perches** (stools) on the dais are real seats, which the SDK documents riding a kinematic body.
- **Orbs removed** (model, materials no longer made, desk keys, script, XRTM trackObjects). Their desk slots are now
  RIDE and LIGHTS. The old `SB_Show.fbx` was left in Models, unused (not deleted).
- **Builder keeps the world link** (`__WorldLink`) across rebuilds. A first attempt lost it for two runs; restored to
  id 2047 and checked (the slug is now `sphererebro`).
- Tests: 37/37 against the mock. Build: 238 renderers, 132,860 triangles, 183 object ids, 1 lightmap.

**Not verified (needs the headset):** RIDE holding a standing player as the dais turns (spike S1) and the perches as
fallback; whether `BS.Light` intensity changes reach the lights (LIGHTS presets); the brighter look on Quest; the
dims pipeline at a radius other than 50.

## 2026-11-06 — first build (Claude, on Ben's Windows machine, Ben AFK)

### State at the end of the day
- The whole world is generated and builds headless with baked concourse lighting. **Nothing has been uploaded and nothing has
  been in a headset.** Ben builds/uploads himself (Builder window).
- Generated: 8 FBX (57k triangles in total, incl. the hidden video and glow shells), 32 materials (15 reused Polys textures),
  the scene `Assets/_Sphererebro/Scenes/Sphererebro.unity` (246 renderers, 75 colliders, 41 lights, 184 BS Object Ids),
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
