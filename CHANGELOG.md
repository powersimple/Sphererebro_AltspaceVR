# Sphererebro changelog

Newest first. Each entry: what changed, where, and what is **not** verified. Rules and pipeline: `CLAUDE.md`.

## 2026-11-10, 15:00: arrive at the foot of the escalator, by script; NOT uploaded (Claude; Ben commits and uploads)

Ben: "can we move the spawn point back to the bottom of the escalator without a drawn out build?" The spawn point is in
`asset.world`, so moving it needs a full build. Instead `Assets/WebRoot/script.js` (`SB.arriveOnPlaza`) takes each
device to `SB_DIMS.spawn` (the plaza, facing the venue) once as it loads: a script-only upload (`tools\ship.ps1 -Web`,
about 40 s). People still appear inside the desk for the moment before the script runs. `SpawnAtDesk` is false again in
the builder, so the next full build moves the real spawn point; then set `arriveOnPlaza` false. `show_test.html` 41/41;
not tried in the app (whether `TeleportTo` is honoured that early in loading is unverified).

## 2026-11-10, 14:30: Stewart puts the house lights out; IPN Logo key on the Console; cube logos; NOT built (Claude; Ben commits and builds)

- **Stewart and the house lights:** Ben asked whether the Stewart key "turns the house lights off". It did not: the black
  bubble hid the dome and hall, but the theatre's own lights (key, three house lights) stayed as LIGHTS had them. Now
  `SB.lx.darkCues = ["S3"]` in `Assets/WebRoot/script.js`: while that cue is up the lights use the LIGHTS OUT preset
  (desk spot at half), and come back as they were when it ends. Script only; not seen.
- **"The IPN 3D logo button needs to work on the console":** the desk Console (keys only) had no key for the cube show.
  New `ui.worldKeys` in `XRTimeMachine/src/adapter-altspace.js` (a world's own keys after the show's); Sphererebro gives
  it one, "IPN Logo", which ends any running cue and then runs `SB.actions.Show` (the cube show, as the old desk key).
  Nine keys now: five rows of two. `install_xrtm.ps1` wrote script.js but could not rewrite the plugin's own dist file
  (locked by another program): the dist copy is one change behind.
- **"Seen outside the venue and above the bar", "cube IPN logo", "over the entrance to the theatre":** `SetupBarSign`
  now places two whole cubes (new helper `IpnLogo`): 1.0 m beside the word over the bar (it was pressed flat), and
  2.4 m on the roof's edge over the outer doorway, facing the plaza. Not compiled, not seen; they are not static, so
  they take their light from the probes and may be dim.
- Checks: `node --check` ok, `show_test.html` 41/41. The builder is not compiled.

## 2026-11-10, 14:00: a browser over the door, the mirror above it; NOT built (Claude; Ben commits and builds)

Ben: "above door, move the mirror up and add a web browser there and point it here" (his Google Doc). In
`SphererebroBuilder.cs` `SetupPresenterMirror`: new `Presenter_Browser` (`BS.BSBrowser`, 1280 x 720 page, 8.0 x 4.5 m)
at (0, 6.4, -(R - 2)) where the mirror was; `Presenter_Mirror` moves to y 11.2 straight above it; both 0.8 m further in
from the shell so the mirror's top corners stay inside the sphere. The address is `PresenterBrowserUrl`.
**Not compiled** (Unity had not picked the file up; the MCP bridge is attached to another project) and not seen: which
way the browser faces (yaw 180, as the mirror) is a guess, and a Google Doc may ask the in-world browser to sign in.

## 2026-11-10, 13:45: three new keys: Innovation, Venus, Stewart; NOT built, NOT uploaded (Claude; Ben commits and builds)

Ben: "add some static images that I can trigger with a button ... come in from a distance and dominate the field of view.
Not too close, but big." New module `tools/talk/modules/stills.py` (entry `{"name": "stills", "after": "T"}` and ids
S1, S2, S3 in `keys` of `talk_show.json`; delete both to remove it). Sources in `tools/stills/`; prep
`tools/geo/stills_art.py`; meshes `tools/blender/stills.py`, `venus_poly.py`; materials `talk_materials_stills.json`.
Each key is `alone` inside the black bubble of `_space.py`.
- **Innovation (S1):** `InnovationLogarithm.png` comes in from 27 m to 21 m ahead, 20 x 13.5 m (51 deg wide). The
  simulator cannot show its transparency (it draws a grey plate); in Unity it uses the same path as the tour's name
  cards. Its lines are thin and pale: may read faint. It is white text on dark (rule 12), by Ben's request.
- **Venus (S2):** the carver's picture, 11 m square, left of centre; from 5 s Ben's `VenusPoly.glb` (cut from 393,000
  to 40,000 triangles) rises through the bubble's floor on the right, 5.5 m tall, floats (9 s bob) and turns clockwise
  seen from above, one turn in 120 s. Two point lights of her own. Gold made less mirror-like (nothing to reflect in a
  black room) with a little glow; brightness in Unity is a guess.
- **Stewart (S3):** dark, the clip at 2 s (`still_stewart_voice.wav`: the mp3 with early reflections and a tail added,
  played from high ahead, wide spread), the picture fades in from 6 s over 4 s, 14 m high. "Depth map it and make it
  look 3d": no depth model is installed, so the depth is drawn from the picture (lit silhouette as a dome, brighter
  parts nearer, caption a flat plate); the picture is a 30,000-triangle relief, 2.2 m deep, that turns 7 deg each way
  every 18 s. The picture is Ben's replacement, `..\Assets\Images\PatrickStewart.jpg`
  (copied to `tools/stills/stewart.jpg`, 1710 x 2048 after the 2048 cap), swapped in at 13:55 and seen in the simulator.
- Checks: `node --check` ok, `show_test.html` 41/41; all three looked at in the simulator. Nothing in Unity or a headset;
  the resonance has not been listened to.

## 2026-11-10, 09:30: Ben's second list; NOT built, NOT uploaded (Claude; Ben commits and triggers builds)

Ben: "Hold new builds and uploads, let me trigger them." Everything below is in the generators and regenerated outputs
(show block in `script.js`, talk assets, world FBX); none of it is in the uploaded world until Ben builds.
- **"Remove that rectangle in the back of the data center hall" / no video screen there:** the end wall and its five
  racks are gone (`tools/blender/datahall.py`); the last 44 m of the aisle fade into the dark through seven black veils
  (part `Fog`, `TK_DhFog`). Seen in the simulator; not in a headset.
- **Lounge "lines":** the ceiling cove strips still used the 50 m sphere's zone edges (120..240 deg) and ran about 50 m
  past each end wall of the concourse. Cut to the concourse (`..\Assets\scripts\build_sphererebro.py`, `Band_Cove_EMIT`).
  Zone colours and lights unchanged. Geometry regenerated (SPHEREREBRO_OK); needs a build with bake.
- **"Do not load any sequence by default":** `XRTimeMachine/src/adapter-altspace.js` `arrival()`: a stored cue is picked
  up on arrival only while the presenter who set it (another device) is still in the space; otherwise house, and nothing
  plays until a key is pressed. Not tested with two devices.
- **Bell:** the chime as the spikes rise in Captured Media is removed, and the Timeline key is now `"alone"` so it no
  longer sets the earlier cues in their held poses first (the cause of the earlier blink and bell on Ashburn). If Ben
  means another sound, it is still there.
- **Media tour:** no chime at the stops.
- **Spawn "inside the desk":** the dais centre, radius 0.3 m (`SetupNavigation`).
- **Timeline:** the picture on 1908 "Color movies" is removed, not replaced (`talk_timeline_layers.json`); cards remade.
- **Captured Media:** the 5F3 key is relabelled; a legend (8 x 4 m, warm, no numbers) stands lower right of the globe
  from 12 s (`tools/geo/media_legend_art.py`, part `Legend` in `media_globe.py`, `TK_MediaLegend`).
- **AI data centers layer in Captured Media** ("add the AI Data centers layer, bake that in"): the atlas package's
  `layers/compute.json` `ai` list (179 markers) is taken by `tools/geo/media_fetch.py` into `media_data.json` and baked
  into `media_globe` as part `Dots_AI` (magenta diamonds, larger with MW; `TK_MediaDotAI`). They fade in at 21.5 s, after
  the gold spikes; the cue forms in 25 s (was 22). The legend has a fifth row. The part is in the GLB (179 quads); the
  simulator does not show these materials' colours, so the look is unchecked.
- **Globe tilt in Captured Media:** latitude 8 N faces the seats (was 25 N), so both hemispheres show.
- Checks: `node --check` ok, `show_test.html` 41/41, simulator looked at for the hall and the legend. Nothing in a headset.

## 2026-11-10, 08:00: Ben's walk-round list from `..\ref\*.jpg` (Claude; Ben commits)

Ben, with ten pictures in `B:\VRWorlds\AltspaceVR\Sphererebro\ref`. Generator: `..\Assets\scripts\build_sphererebro.py`
(backup of the version before: `%TEMP%\claude\ashburn_backup\build_sphererebro_before_ref.py`); builder:
`Assets/Editor/SphererebroKit/SphererebroBuilder.cs`. Geometry regenerated (SPHEREREBRO_OK).
- **Globe "too close, move it back":** media globes 18 to 23 m ahead (`_space.py`), Ashburn's 16 to 22 m (`ashburn.py`);
  sizes and heights as they were. Clearance PASS, logic 42/42.
- **Desk faces the audience** ("Let's try"): `Vista_Dais_Mount` is turned 180 deg, so the script's yaw 0 is still HOME.
  The open side now faces the dome. Untested: which way the joystick drives the platform now.
- **Mirror over the door:** `Presenter_Mirror`, a Banter mirror (BS Mirror) 8 x 4.5 m above the portal, facing the
  dome. Untested: that the SDK prefab's reflecting side is the one I worked out from its file, and its cost on Quest
  for whoever looks at it (it is behind the audience).
- **Escalator banisters:** handrail 1.5 to 1.0 m over the steps, glass and skirt lowered with it.
- **Feet in the floor:** the recliner is 12 cm higher on a taller plinth (mesh, colliders, sit point, drink holders).
- **No standing on seats:** seat and arm colliders are on a child on the Invisible layer (teleport arcs stop on it),
  and a 1 m invisible wall stands on the front edge of the landing and of rows 1 to 4, open at the aisle. Untested:
  whether that wall gets in the way of clicking a seat from the row behind (enter a row from the aisle).
- **Lounge benches:** five seats on each sofa, facing its table; the sofa is a plump cushion and rolled back in the
  recliners' velvet on a carbon plinth.
- **RESTROOMS signs** (seen as "RESTRO" and "ROOMS"): switched off (`Retired`).
- **Spawn:** temporary, in the vista layout: on the stage on the dome side of the desk, facing the audience, within
  0.8 m (`SpawnAtDesk` in the builder; false puts it back on the plaza). I read "behind the deck" as the desk. Why the
  plaza spawn put Ben over the seats was not found.
- **Bar sign:** the word "Theatre" in Aldrich, plain gold (no emission), with a 0.9 m copy of the IPN logo cube to its
  left (`SetupBarSign`). Untested: how the cube is lit there (probes, not baked).
- **Fall guards:** the plaza rail now runs up to the escalator and stairs (it stopped 4 m short each side) and the
  slot between them is closed; three invisible walls close the concourse doorway beside and between them; the entry
  deck's side walls run out to the concourse and two walls close the doorway beside the deck.
- **NOT done: "remove that part of the lounge"** (`loungExtendsTooFar.jpg`). The lines are the far concourse's light
  strips seen through its windows. Removing it means shortening the concourse (`arcDeg` in dims.json), which squeezes
  the bar, lounges and restrooms together; waiting for Ben to say how much to keep.
- **Built and uploaded at 07:53-08:01** (`tools/ship.ps1`, Ben: "Build and upload"). The builder compiled and reported:
  mirror placed, 15 sofa seats, bar logo placed, spawn at (0, -2.63, -85.35), 15 objects retired, 76 vista recliners,
  TALK 48 elements, 0 warnings. (Its "desk faces the dome" log line was stale wording; corrected after the build.)
  **Not seen in a headset.**

## 2026-11-10, 06:40: all the keys show; the Earth lower, larger, closer; a new data hall module (Claude; Ben commits)

Ben (after the 05:00 build, with three pictures of dark rack aisles): "coming along. When the earth shows up, place it
lower and make it larger and closer. I'm only getting two buttons at a time, ashburn and the last one. We should now
have timeline, Ashburn, Public media. Let's rebuild the data center model. Let's have the data centers start small in
the back and then zoom in and fly past the seats." (His message ended "For the next one, let's": unfinished.)
- **Keys:** `XRTimeMachine/src/adapter-altspace.js`: the Console put up to five keys in a row, so four keys at 48 % width
  ran off the panel. Keys-only mode now puts two to a row. Five keys now: Data Centers, Ashburn, Media Tour, 19 of 606,
  Timeline (three rows).
- **Earth:** media globes (`tools/talk/modules/_space.py`): radius 9 to 11 m, centre 21 to 18 m ahead, underside 3 to
  0.6 m above the equator. Ashburn's opening globe (`ashburn.py`): radius 5 to 7.5 m, 18 to 16 m ahead, underside 2 to
  0.5 m. Both still clear every seat by 3 m.
- **Data hall, new module `datahall` (cue 4B2, key "Data Centers"):** `tools/talk/modules/datahall.py`,
  `tools/blender/datahall.py` (4,414 triangles), `tools/geo/datahall_art.py` (two drawn textures; nothing copied from
  the pictures), `tools/blender/talk_materials_datahall.json`. The dome goes black; a small dark box with a glowing
  mouth appears far ahead above the equator, comes in and grows ten times until its mouth (23 m wide) stands before the
  stage, then flies over the audience: 47 bays of 15 m racks pass 3 m outside the seats on both sides at up to 10 m/s,
  coming to rest inside the aisle with the end wall 81 m ahead. 47.5 s, unlit, one object moved by one clip. The racks
  stand on the floor beside the seats, so this module alone goes below the equator. The older rack cues (4B..) are
  untouched; remove the `datahall` entry from `talk_show.json` to drop it.
- **Harness:** `show.html` gained `__solo(cueId)` (a key's "alone" cue) and skips the hall's floor in the clearance test
  (it lies under the seats, like the bubbles' floor); `show_test.html` finds cue 5 by id.
- **Tested:** clearance PASS (87 motions), logic 42/42, `node --check` on script.js (it caught a comment of mine that
  had swallowed a closing brace; fixed before any build). **Built and uploaded at 06:40-06:47** (`tools/ship.ps1`, Ben:
  "Build and upload"; TALK: 48 elements, 0 warnings). **Not seen in a headset.** In the
  simulator the hall's posts and ceiling look lighter than their material says; unknown which Unity will match.

## 2026-11-10, 05:20: desk apron removed; the logo shows in every dome mode (Claude; Ben commits)

Ben (with a screenshot of the desk): "Remove the sidewalls from the desk below the trim. We don't have the immersive x by
default."
- **Desk:** `..\Assets\scripts\build_sphererebro.py`: the apron under the top (0.74 m up to it) is gone. `Desk_Body` is a
  2.5 cm slab under the sloped top with a sloped underside (`ring_solid` gained `z0_outer`), so nothing hangs below the
  bronze trim on either edge; the pedestal runs up to it (0.965); the underglow strip is tucked under the outer trim.
  Geometry regenerated (SPHEREREBRO_OK; Desk_Body 0 to 1.06 m, the slab 0.905 to 1.06).
- **Logo:** the scene had it right (active, 64 m, facing the seats); the script hid it. It showed only with the dome at
  "stars", and a dome mode saved in the space (DARK or PANELS) outlives every reload. Now: on unless a show is running
  or the dome is playing video. The reason is inferred (the saved state can't be read from here); the browser console
  now logs "[Sphererebro] logo on/off (dome ..., show cue ..., found ...)" to settle it if it is still missing.
- **Built and uploaded at 04:53-05:00** (`tools/ship.ps1`, Ben: "Build and upload"; TALK: 47 elements, 0 warnings).
  **Not seen in a headset.**

## 2026-11-10, 05:00: desk reset and spot, timeline flipped and its blank cards fixed, tour keys, IX logo (Claude; Ben commits)

Ben: "1) rotate the desk to the correct orientation. I moved it and it's stuck 2) light it up a little bit, put a
spotlight overhead on that 3) flip the vertical order so the top layer is at the bottom and remove the two empty
timelines. I don't have buttons for the other tours yet. Grab the Immersive X logo from the Polys build and have that be
the default when we enter [later: in the center of the sphere, large]. When you click Ashburn it blinks the data center
model and bell, remove that."
- **Desk back to HOME, once:** `SB.deskReset` ("2026-11-10a") in script.js. Five seconds after load, the first owner or
  moderator whose saved state shows a moved or turned desk writes it docked, yaw 0 (facing the dome), and records the
  id (`sb_reset`), so it happens once. A new id repeats it. WHY it stuck was not found: this undoes it, no more.
- **Desk spot:** `Desk Top`, a realtime spot 4.2 m over the desk (a child of it, so it rides along), warm, 14 x the
  preset (house 1, presenter 1.2, lights out 0.5: never fully dark). Builder `SetupDesk`; script `SB.lx.desk*`.
- **Timeline flipped:** `layers.py` stacks the first layer (Media) lowest, 3D and spatial at the top.
- **The "two empty timelines" were not empty: their cards were blank.** `make_cards.py` padded a part-filled atlas with
  ffmpeg colour frames in another pixel format; that sheet (`tl_cards_1.png`) came out with its 25 real cards
  transparent and the fillers solid black, so Digital video, 3D and spatial and the nine year labels drew nothing.
  Fillers are now made from a real card with its alpha zeroed. **Both layers are kept** (17 firsts between them): drop
  them from `talk_timeline_layers.json` if they should still go.
- **Console keys:** `talk_show.json` `"keys"` now `5B3, 5F2, 5F3, T` (Ashburn, Media Tour, 19 of 606, Timeline). With
  more than two keys the keys-only Console lays them two to a row (XR Time Machine `drawConsole`).
- **No flash on a module key:** module cues carry `"alone": true`. Played from a key, such a cue starts from nothing
  (XR Time Machine `apply`): the cue before it is no longer set in its held poses first, which is what flashed the data
  hall and replayed its sounds for the 2.5 s the bubble takes to close. Next / Back through the show are unchanged.
- **Immersive X logo:** `Models/ImmersiveX_Logo.glb` (copied from the Polys build), placed by the builder (`SetupIxLogo`)
  upright at the centre of the sphere, facing the seats, 64 m wide (0.64 x the radius), centre 16 m up so its underside
  is above the equator; unlit in its own colours, the letters a soft warm white (rule 12). The script (`SB.logo`) shows
  it whenever the dome is at its default with no show, video or cube running: so it is what you see on entering.
- **Checks:** show logic 42/42 (keys and "alone" checks updated); clearance PASS (85 motions); world script tests 65/66
  (the one failure, "LATTICE toggles off", is the lattice's new off-by-default from earlier today, not this change).
- **Built and uploaded at 04:21-04:27** (`tools/ship.ps1`, Ben: "Build and upload"): the builder compiled; "IX logo:
  64.0 x 21.9 m at (0, 16, 0), underside y 5.1, 8 parts"; `Desk Top` and `IX_Logo` are in the scene; TALK: 47 elements,
  0 warnings. **Not seen in a headset.** The logo's facing is worked out from the model's own parts and has not been
  looked at; the desk spot's brightness is a guess.

## 2026-11-10, 03:45: Ashburn raised above the equator; two public media globe modules (Claude; Ben commits)

Ben: "When you zoom in, it's too low, all the content should be seen above the equator of the sphere... Next, the
public media world tour: one where we see where public media is, major outlets around the world bouncing from one to the
other; then a second one where we see the illustration of 19 of 606 are not captured, with the globe spinning."
- **Ashburn (cue 5B3) raised:** the globe hangs with its underside 2 m above the equator; the map ends as a steep raked
  wall (60 deg) whose lower edge is at the equator, 2.4 km = 20 m across (was 30 m, below the seats). A black floor at
  y -3.2 (just under the stage) hides whatever ground runs on below. Bubble 29 m (inside the curved screen's 30 m).
  **Fixed with it:** the 1,000 km layer was lifted 0.18 % of the globe's radius, 7 m by the time it switches off: it
  floated over the next layer, and with the steeper wall it grazed the front row. Now 0.03 % (1.2 m at most).
- **New module `media_tour`, cue 5F2 "Public Media Around the World"** (after 5F), 52 s: an 18 m Earth, its underside 3 m
  above the equator, turns from one major public broadcaster to the next (the atlas package's 14: BBC, RTÉ, ARTE, RAI,
  SVT, Al Jazeera, Prasar Bharati, KBS, NHK, ABC, SABC, EBC, PBS, CBC), a light bouncing along a gold arc to each; a
  pin rises and a small warm name card (name, city, country, year founded) shows while the stop is in front.
- **New module `media_capture`, cue 5F3 "19 of 606 Not Captured"** (after 5F2; it takes the tour off): the Earth turns
  once a minute with a dot for every outlet; the dots take their colours (captured or state-controlled red, independent
  but state-funded or managed teal, not stated grey), teal and grey dim, and a gold spike rises on each independent
  public outlet as Europe comes round (20 s). It keeps turning until the next cue. No numbers on stage.
- **THE NUMBERS DO NOT MATCH THE SLIDE.** The atlas package (`layers/media.json`) holds **586 outlets, 17 "Independent
  public"** (479 captured or state-controlled, 67 independent state-funded/managed, 23 not stated). The slide says 606,
  19 and 512 (State Media Monitor's 2025 totals). The globe shows the package. Ben to decide: re-export the package or
  leave it.
- **Files:** `tools/geo/media_fetch.py` (reads the atlas package at `D:\Academy\Ben-Presentations\Public Hyperscale\...`,
  writes `tools/geo/media_data.json` and `talk/gen/media_cards.png`), `tools/blender/media_globe.py` (18,537 triangles),
  `tools/blender/talk_materials_media.json`, `tools/talk/modules/media_tour.py`, `media_capture.py`, `_space.py` (the
  bubble and globe rig both share). The globe reuses the Ashburn module's Earth images (`talk/gen/ash_globe_*.png`).
- **Shared code touched:** `choreo.py`'s module hook (the cue after a module cue no longer takes off what the module cue
  took off itself); `show.html` (any `*Space` material is a black bubble; each part gets its own material so an alpha
  track fades one node; `window.__view` and `window.__run(seconds)` for stills that don't depend on the frame rate).
- **To remove any of the three:** delete its entry from `talk_show.json` `"modules"` and run `tools/talk/build_show.ps1`.
- **Checks:** show logic 40/40; clearance PASS (85 motions; Ashburn's ground comes no nearer than 4.6 m to a seat).
  Seen in the browser simulator from a front seat: `review/ashburn/ashburn_raised_sheet.jpg`, `media_tour_sheet.jpg`,
  `media_capture_sheet.jpg` (the cards' black boxes are the simulator's: its GLB images carry no transparency).
- **The first Ashburn (the low one) was built and uploaded at 03:07-03:10** (Logs/SphererebroAutomation.txt; TALK: 45
  elements, 0 warnings), so the builder change compiles and Ben has seen that version. **The raised Ashburn and both
  media modules were built and uploaded at 03:45-03:51** (`tools/ship.ps1`, Ben: "Build and upload"; TALK: 47 elements,
  0 warnings; asset.world, index.html and script.js). **Not seen in a headset yet.** Unknown until then: the cards' and dots'
  transparency and draw order; whether the name cards' second line is readable in a Quest; Quest frame rate. Another session was editing `choreo.py`, `show.html`, `show_test.html`
  and `talk_show.json` during this work; its changes are intact.

## 2026-11-10, 02:45: module "ashburn": from space to Ashburn, Virginia, in 3D (Claude; Ben commits)

Ben: "make a module that can be played in XR Time Machine. Let's zoom in from space on Ashburn. Bake the whole
experience... Make this modular in case it doesn't work out, same branch."
- **What it is:** one element (`ashburn`) and one cue, **5B3 "Ashburn from Space (3D)"**, slotted in after 5B. About 42 s:
  a black 28 m bubble closes round the seats, the Earth arrives (10 m across), then one 16,000 x zoom about Ashburn
  through six imagery layers (5,000 km down to 2.4 km) while the ground tips into a raked floor below the seats and
  570 large buildings rise as blocks (147 data centres amber, the rest grey, heights x 2). Unlit, no lights, no video.
- **Modular:** switched on by one line in `talk_show.json`: `"modules": [{"name": "ashburn", "after": "5B", ...}]`.
  **To remove it:** delete that line, run `tools/talk/build_show.ps1` (and Build World if the scene was built with it).
  The cue list in `talk_show.json` is untouched; `choreo.py` slots module cues in when it runs.
- **Files:** `tools/geo/ashburn_fetch.py` (downloads + bakes `talk/gen/ash_*.png` and `tools/geo/ashburn_data.json`;
  tile cache in `tools/geo/cache/`, gitignored), `tools/blender/ashburn_zoom.py` (47,389 triangles),
  `tools/blender/talk_materials_ashburn.json`, `tools/talk/modules/ashburn.py` (the motion).
- **Shared code touched, all additive:** `choreo.py` (the MODULES block before "write"), `common.py` and
  `SphererebroTalk.cs` (merge `talk_materials_*.json`; material keys `queue` and `doubleSided`), `show.html` (bubble
  colours; shells skip the clearance test; the triangle test splits big triangles further), `show_test.html` (cues 6
  and 11 found by id, two module checks).
- **Sources:** NASA Blue Marble, USGS National Map imagery, OpenStreetMap buildings (ODbL: credit required). CREDITS.md.
- **Checks:** show logic 37/37; clearance PASS (81 motions; the ground's nearest approach to a seat is 10.5 m);
  seen in the browser simulator from the front seat (`review/ashburn/sim_sheet.jpg`).
- **NOT built in Unity, not uploaded, not seen in a headset.** The builder change has not been compiled yet. Unknown
  until a build: the transparent layers' draw order, the FBX's axes (the simulator uses the GLB), Quest frame rate.
- **Known:** from about 15 to 19 s the growing globe's underside is cut flat by the hall floor (y -12; the module lays
  a black floor over the white one). The 200 km layer shows USGS mosaic seams and blue fill over Chesapeake Bay.
  `talk/gen/ash_*.png` are 55 MB together (and Unity copies them into Assets on build).
- script.js and talk_timeline.json were regenerated with the module on at 02:36; another session changed `choreo.py`
  (the 2T timeline) at 02:39, after that run.

## 2026-11-09, 17:30: escalator walked, no ride, no lip (Claude; Ben commits)

Ben: "I hit the escalator and fell off the world. Make it so that I can climb the escalator again, no jump."
- **The ride is off** (`SB.escalatorRide: false` in script.js; uploaded 17:26). The carriage and foot trigger are still built.
- **Ramp:** `Esc_Ramp_COL` (and the stairs' ramp) is one prism, flat for 0.8 m at the foot and top. The solid `Esc_Body`
  landing plates stood 4 cm proud of the floor: now flush. Slope unchanged (about 21 deg).
- **New:** `tools/unity_run.ps1 web` uploads index.html and script.js only (the Builder's Upload HTML + JS), unattended.
- **Not verified in a headset.** My reading of the fall (the ride's attach) and the jump (the plate lip) is inferred from
  the code, not observed.

## 2026-11-09: XR Time Machine 0.5.0, the Console (Claude; Ben commits)

Ben: "XR Time Machine should reveal a console that has everything I want to play back, one at a time."
- **Top nav:** Console | Record | Library (was Show | Sequences | Record | Playback). All pills.
- **Console:** one list of every cue, then this device's recordings. Subnav filters: All, Cues, Video, Recordings. A tap
  plays that item alone from its start, for everyone (`show.play(i)`: the cue before it is set in held poses, then this
  cue's entrances play; state `xrtm.show` carries `play: 1`). **Again** replays the current cue. Back / Next, Rehearse,
  End show stay. `Cue 1` key removed (tap the first row).
- **Rule 12** in CLAUDE.md: no big white text on the dark sphere. The overnight title and label cues break it.
- Checks: show harness 35/35 (3 new console checks). Plugin tests pass except `plugin.mjs`'s installer check, which
  assumes the world's own code never names XRTM (written for The Polys; this world's desk key calls `XRTM.toggle`).
- script.js only: **no scene build needed. Not uploaded. The panel's layout has not been seen in the app or a headset.**

## 2026-11-08, overnight: THE TALK, cue by cue, built into XR Time Machine (Claude; Ben commits)

Ben's brief (`V:\Desktop\_Prompt for Claude Code - Sphererebro Overnight Build.md`) plus, mid-run: build the cue engine
INTO XR Time Machine and test it on the dashboard; big dominating visuals; rich textures; sound; and a 200-year media
timeline from his 2020Vision assets. Full record: `SPHEREREBRO_STATUS.md`; review with renders: `review/REVIEW.md`.
- **XR Time Machine 0.4.0: shows.** Cue data in the world's XRTM config (`show: window.SB_TALK`), a **Show tab** on the desk
  panel (cue, next, Back / Next, Cue 1, Rehearse, End show, jump list), A / X and arrow keys while a show runs, the
  protected key `xrtm.show` for everyone. Entrances play forward; back, jumps and late arrivals show held poses.
- **30 cues** (the brief's 1 to 11 with their steps, plus 2T), 44 elements, generated: `tools/talk/choreo.py` (motion) ->
  `Config/talk_timeline.json` -> `SphererebroTalk.cs` (Unity twins + AnimationClips) and script.js's show block.
- **Assets:** 15 procedural Blender models with CC0 ambientCG textures (`tools/blender/`, `talk/models/`), text meshes,
  timeline cards, 30 synthesised sounds (`tools/talk/sounds.py`), placeholder clips (`media/`).
- **The world** hides its dome shells and lattice while a show runs (event `xrtm-show`), and restores them at the end.
- **Checks:** show logic 32/32 (`tools/harness/show_test.html`), world tests 60/60 vista, clearance PASS (3 m, 79 motions),
  every cue's held state inside the Quest budget (`review/PERFORMANCE.md`).
- **Built** in the open editor (Build World + Bake, 23:45). **Not uploaded. Not seen in a headset.** Video placeholders are
  not on the media host yet.

## 2026-11-07, 17:16: unattended build and upload; seam, arch, backlit keys, skybox default (Claude; Ben commits)

Ben was away: "build and upload without me, I should not have to close Unity". All built and uploaded (all three files
OK, 17:16).
- **The seam at the back:** the dome shells had no vertices on the seam meridian, so the faces across it had u just past
  1 and the (clamped) video texture smeared into streaks. The shells are now cut along x = 0 (both seams), so u runs
  exactly 0 to 1 (checked in Blender: it was 0.0104 to 1.0104).
- **The arch:** the square flange is switched off (Retired). The shells now have a ROUND hole at the portal: subdivided
  round the bridge axis, faces inside the ring deleted, the edge snapped onto the ring's circle (r 2.8, 84 edge
  vertices). The ring alone frames the entrance. Sphere triangles 12.7k -> 24.5k (three shells).
- **Keys backlit:** the legend sheet is also `SB_KeyFace`'s emission map, so only the gold lettering glows and the black
  face doesn't (no hotspot); it stays lit in Lights Out. **The desk is dim, not black:** `SB_DeskMatte` has a faint
  emission.
- **Default dome = the 8K skybox** (`SB.sphereDefault = "stars"`: every shell off, so the cubemap shows; nothing
  rotates). VIDEO off returns to it; PANELS and DARK still have their keys.
- **`SphererebroAutomation.cs`** (new): a watched request file `Logs/sb_automation_request.txt` ("build", "upload",
  "build upload") runs Build World + Bake, then the Creator SDK Builder's own Build and Confirm (auto upload), inside
  the open editor. Progress goes to `Logs/SphererebroAutomation.txt`. It runs only when asked, and the request file is
  deleted when read.
  - To make Unity compile new editor code unattended, the session brings the Unity window to the front (Alt-key focus
    workaround); Unity's Auto Refresh does the rest.
  - The 17:15 confirm took about 27 min after the window opened (the hook waits while Unity is busy).
- Tests: 65/65 round, 60/60 vista.

## 2026-11-07 (after the 16:06 build): summon, Soft grip, the invisible joystick grip (Claude; Ben commits)

- **Summon (force grab) is on:** the world script sends `BS.SceneSettings` with `EnableForceGrab = true` at load, so a
  player can point at a glass or bottle and pull it to their hand. Nothing else in the world sets scene settings; the
  rest stay at the SDK defaults.
- **Glasses and bottles use the Soft grip. Verified in the headset by Ben ("that worked").** Ben, with a beer bottle: Cylinder faced the fist right, but bending the
  wrist moved the bottle the opposite way. Cylinder re-aims the hand onto the axis (the SDK's own code adds a fixed
  40 deg tilt and flips the object upright). Soft takes hold wherever the hand touches and keeps the object's angle, so
  it follows the wrist. The fist itself is drawn by the app; the SDK has no setting for a world to hide it.
- **Joystick:**
  - the hand grabs an invisible, free grip at the knob (`Desk_Joystick_Grip`, a trigger capsule): kinematic while it
    rides the dais, free while held, back on the knob on release;
  - the script reads the hand's turn **since it took hold**, in the desk's frame: pitch = drive, roll = slide (30 deg for
    full), twist = rotate (35 deg);
  - the visible stick only leans to show it;
  - a physically held-in-place stick would have pushed the physics hand the opposite way.
- **The builder refuses to run on stale code.** Unity compiles editor scripts only after a menu command finishes, so the
  16:03 build ran the old builder (RIDE still there). Build World now stops with a dialog when its scripts are newer
  than Unity's compiled copy. The 16:06 build was correct.
- Tests: 65/65 round, 60/60 vista. Builder compiles. **Not built yet.** Ben: click into Unity, wait for the compile,
  then Build World + Bake.

## 2026-11-07 (latest): drive the platform; RIDE and stools gone; grabbing; bar stool seats (Claude; Ben commits)

- **RIDE is gone**, the key and the feature (Ben: "a mess... a failure"). There's no Attached Object on the dais and no
  zone trigger. The dais stools (perches) are switched off too (Ben: "no stools").
- **Drive the platform with the joystick**, on its own level only:
  - twist = rotate left/right (14 deg/s);
  - push forward/back = drive forward/back;
  - push left/right = slide left/right (1.5 m/s, quantised, 0.2 dead zone);
  - it stays inside the sphere (44 m from the centre) and never enters the seating fan;
  - HOME glides it back to the dock on the stage (3 m/s) and turns it to face the dome.
  - State: `sb_drive` = `x|z|vx|vz|t0|tEnd` in the dais's parent frame, dead-reckoned by every client. Yaw stays in
    `sb_dais`.
  - The joystick is free to twist (Y rotation unlocked) and moved in to r 0.70 on the desk.
- **Standing players on the moving platform** (the SDK has no moving-platform support):
  1. the dais moves physically, through its kinematic Rigidbody (`MovePosition`/`MoveRotation`), so friction may carry
     people;
  2. if it doesn't, each player's own client moves its own player along (TeleportTo) when the platform has left them
     more than 25 cm from their spot on it, turned with it. It works from the head pose, since scripts get head and
     hands, not the body, and learns the body-to-head offset after the first correction.
  - Any number of people. **Headset test pending; this is an experiment.**
- **Grabbing** (Ben: hand orientations reversed):
  - glasses, bottles and the joystick now use the SDK's **Cylinder** grip ("Cylinder (Stick)" preset): held anywhere
    along their Y axis, from whichever side the hand comes;
  - the old Point grip snaps the hand to one fixed pose (the SDK: "grip along its Y, pointing along its Z"), which
    turned hands round;
  - grab radius: glass 4 cm, bottle 3.3 cm, stick 2 cm;
  - all on the Grabbable layer (20), collider on the same object.
- **The bar stools are seats now** (Ben: "the ones in the lounge don't have seats"): sit point 0.82 m, facing the
  counter.
- **Video:** the live 8M file plays in the Unity harness, both with SDK audio routing and with direct audio. The last
  test failed because the world was uploaded (15:06) before the file was synced (15:27). The script now asks the host
  first (HEAD) and says "Video not on the server: sync the media server" instead of a black dome.
- Tests: 62/62 round, 57/57 vista (new: drive limits, heading, joystick drive, stop on release, HOME docking, the
  follow). Builder compiles.

## 2026-11-07 (late night): video that plays, smaller; keys with printed legends (Claude, Sphererebro3; Ben commits)

- **Unity video harness** (a throwaway Unity project in Claude's scratchpad, not this repo): plays clips in Unity's
  VideoPlayer set up exactly as the SDK's `BSVideoPlayer` does (audio track 0 routed through an AudioSource, looping,
  url then Play), and reports prepare, clock, size, audio tracks, loop and errors.
  - **On Windows every clip played,** including the live 18M and 10M drift with no audio track.
  - So the files were fine. Two causes remain:
    1. **Quest's Android decoder**, which can stall on a file with no audio track. The grids that played had AAC.
       Fixed by giving the new file a silent AAC track.
    2. **The live world was a mismatch:** the scene from the 14:02 build with a 14:27 `script.js` that looks for
       objects that build doesn't have. That's fixed by the next Build + Upload.
  - Not verifiable here: Android itself.
- **One drift file instead of three (650 MB down to 120 MB):** 4096 x 2048 at **8 Mbps**, x264 two-pass, silent AAC.
  - Chosen by measurement. VMAF against a near-lossless reference on 10 s:
    3M 70.7, 4M 79.4, 5M 84.2, 6M 87.3, **8M 91.3**, 10M 93.7.
  - Smaller frames scored worse at the same bitrate (3840 at 8M: 81.9; 2880 at 8M: 78.6).
  - The harness plays it (prepared 1.1 s, loops).
  - Queued; the three big ones are queued for take-down.
  - `script.js` now points at it (`SB.media.clips` holds this one file).
- **Mac skill `sphererebro-media-sync`** (installed in the Mac's `~/.claude/skills/`, via V:). On the Mac: "sync the
  video server". It works through `media-outbox\UPLOAD-QUEUE.md`, which now has two tables, **Upload** and **Take down**:
  check, upload, curl-verify, log in `UPLOADED.md`, clear the outbox.
- **Keys, again** (Ben: glowing keys with hotspots are banned; the text must be rendered into the key, not floating):
  - flat rectangular keys, 60 x 24 x 6 mm, 1 mm softened edges, matt black, **no emission**;
  - the legends are a texture, `SB_KeyLegends.png`: gold Aldrich on near-black, rendered with ffmpeg by the Blender
    generator, each key's top face UV-mapped to its own cell (`SB_KeyFace`, ASTC 4x4 on Quest);
  - the floating TextMeshPro labels are gone;
  - TURN LEFT and TURN RIGHT swapped places, so each is on its own side.
- Tests: 60/60 round, 55/55 vista. Editor scripts compile. **Not built yet.**

## 2026-11-07 (night): headset notes, round two (Claude, Sphererebro3; Ben commits and pushes)

- **Bars and tone, killed.**
  - Why it came back: the old VIDEO stepping had saved a grid URL in the space state (`sb_video`), which outlives a
    script change.
  - Now `SB.bannedVideo` (`/ipn_grid_/`) is refused by `SB.setVideo`, and a saved one is ignored and cleared from the
    space.
  - The Mac is asked to **delete the three grid files from the host**, with Ben's authorization (prompt:
    `V:\Desktop\Sphererebro-Mac-Delete-Grids-And-Upload-Drift-2026-11-07.md`).
  - CLAUDE.md rule 10 and a memory record the ban.
- **"The new video didn't play":** the drift files weren't on the host yet (404); the Mac hasn't uploaded them. Same
  prompt.
- **Aisle steps** (Ben: "not smooth, you get stuck; some have yellow hilts, others don't"):
  - the walk is now one smooth ramp prism through every nosing, flat for 0.5 m at both ends, so there are no lips (the
    old rotated box sat a half step low: an 11 cm lip at each end);
  - the gold nosings now stand 2 mm proud of the tread (the old ones were coplanar with it and flickered in and out),
    12 mm thick, with a 1 cm overhang.
- **Escalator that carries you:**
  - step into `Esc_Foot_TRIG` at the foot and the script attaches you to `Esc_Carriage` (BS Attached Object,
    AvatarAttachTo, the RIDE mechanism);
  - the carriage glides up at 0.9 m/s (about 18 s), driven by its Rigidbody velocity, so it's smooth at the frame rate;
  - it lets you off at the top and resets; push the stick to step off;
  - local to each rider. Fallback: a teleport to the top;
  - path in derived.json and SB_DIMS (`escalator.foot`, `top`). **Not tried in the headset; RIDE (spike S1) isn't proven
    either.**
- **VIDEO submenu:** VIDEO switches the dome to video and opens a small panel on the desk (`Desk_Video_Mount`, right of
  straight ahead). It lists the videos (Milky Way drift at 18M, 15M and 10M) and Off, with the current one highlighted.
  It's drawn on the presser's own device, moderators only. VIDEO again turns the video off and closes the panel.
- **3D loading meter:** `Sphere_Load_Ring_EMIT` is a ring of 12 glowing segments, 8 m across, between the dome centre
  and the audience. It turns while a new video loads, and goes once the video's time moves (checked every 0.5 s), or
  after 30 s with a note.
- **Keys:** the square blocks with labels beside them are gone.
  - New keys are 60 x 24 x 7 mm pills: matt black face (`SB_KeyCap`), thin gold chamfer (`SB_KeyRim`), the legend
    printed ON the key (TextMeshPro, bold, auto-sized, lying on the key face).
  - CLAUDE.md rule 9 bans square buttons. Rule 11: no text over the dash.
- **One spotlight from the back** on the centre of the dais, for whoever is speaking: the vista Dais Key moves to the
  audience side (stage + 6 m up, 4.5 m behind), aimed at head height.
- Tests: 60/60 round, 55/55 vista (new: the loading ring, the bars-and-tone refusals, the escalator ride). Editor scripts
  compile.
- **Nothing built yet.** Ben runs Build World + Bake, then uploads.

## 2026-11-07 (late evening): a new dome test video, made on Windows (Claude, Sphererebro3; Ben commits and pushes)

- **Milky Way drift** replaces the bars-and-tone grids (Ben: "I hated that one").
  - The 8K skybox image, with a gently breathing glow (30 s period), turns 360° in a **120 s seamless loop**: 3°/s,
    slow on purpose, since a whole-sky turn can make people queasy.
  - 4096 x 2048 at 18M (261 MB), 3840 x 1920 at 15M (216 MB), 2880 x 1440 at 10M (143 MB). H.264 High 5.1, 30 fps,
    no audio, faststart.
  - Rendered in 8 minutes on the RTX 3070 (ffmpeg 9, NVENC).
  - Loop seam checked: last frame vs first frame 34 dB PSNR, against 25 dB for frames 45 s apart.
- **New pipeline** (Ben: the Mac only uploads). Finished files go to `B:\VRWorlds\AltspaceVR\Sphererebro\media-outbox\`
  with `UPLOAD-QUEUE.md` (bytes, SHA-256, target). The Mac pulls over `\\yoda-viii\B`, uploads, curl-verifies, logs in
  `UPLOADED.md` and deletes the file from the outbox. The Mac's prompt: `Sphererebro-Mac-Upload-From-Windows-Prompt-2026-11-07.md`.
- `script.js`: `SB.sphereVideo` is now the drift at 18M; `SB.media.clips` lists the three drift files (no grids left).
  **The drift files aren't on the host yet** (queued for the Mac). Until they are, VIDEO shows a black dome.
- Tests: 53/53 round, 48/48 vista.

## 2026-11-07 (evening): after the first headset look at the upload (Claude, Sphererebro3; Ben commits and pushes)

Ben: "That worked great, mostly." Changes, generators only. **The scene is not rebuilt yet.**
- **Escalator climbable (and the stairs):**
  - Why: players are held on slopes by their walking push, 4.6 m/s² (SDK scene-settings, `PhysicsMoveAcceleration`).
    On the old 28.6° ramp gravity pulled back harder (9.81 x sin 28.6 = 4.7).
  - The foot now starts at the plaza centre, so the slope is about 22° (a 3.7 m/s² pull).
  - Not tried in the headset.
- **VIDEO is on/off** (pressing it again used to restart the video). There's no default video any more (Ben: "I never
  want to see bars and tone again"). The grid clips stay in `SB.media.clips` for `SB.setVideo()`. The playlist console
  is the next proposal (`C:\Users\power\Desktop\Sphererebro-Console-Timeline-Brief-2026-11-07.md`).
- **Desk:**
  - no walls down to the floor: a floating apron (0.74 m up to the top) on one tapered pedestal straight ahead;
  - the blue glow is now under the apron's edge;
  - top and body are matt black (`SB_DeskMatte`, smoothness 0.12, no metal): no hotspot.
- **Pendants still glared:**
  - the diffuser is recessed 13 cm up inside the shade, so it's seen only from below, never edge-on;
  - its glow is 0.55 -> 0.3;
  - the bar pendant lights are 7 -> 5 (x gain 3.5).
- **Facade sign:** "IPN Theatre" in Aldrich (Google Fonts, OFL; copied to `..\Assets\fonts\`). The bar sign still says
  SPHEREREBRO.
- **The IPN cube show:**
  - Ben's IPN logo cube ("RGB Logo" in `D:\Academy\IPN\Branding\Logo\Draft\IPN-Cube2.blend`) is exported by
    `..\Assets\scripts\import_ipn_cube.py`. The .blend is opened read-only and never saved; its checksum is unchanged.
  - One mesh, about 4k triangles, 5 materials (`SB_IPN_*`). It's 10 m across corner to corner (7.07 m edge), pivot at
    its centre.
  - Placed halfway between the audience and the far wall (0, 1, 3.2), with three realtime lights of its own: a warm
    key from above the audience, and blue and magenta rims from behind. The cube and its lights are on only while the
    show runs.
  - New desk key **IPN CUBE** (`Desk_Btn_Show`). It runs once, for everyone, about 23 s:
    1. grows in with the top (IMMERSIVE) facing the audience;
    2. eases upright;
    3. turns P (PUBLIC), then N (NETWORK), square to the audience;
    4. tumbles away through the far wall.
  - Pressed while it runs, it's ignored. Late joiners see it from where it is. The XRTM tracks `IPN_Cube`.
  - Pose maths is pure and tested.
- **Handoff prompts** on the Desktop: `Sphererebro-Handoff-Video-Files-2026-11-07.md` (stereo VR180 test clips with
  ffmpeg, which isn't installed yet: ask Ben) and `Sphererebro-Handoff-3D-Assets-2026-11-07.md`. Neither thread writes
  in this repo or in `..\Assets`.
- **Tests:** 53/53 round, 48/48 vista, against the mock.
  - The test page had stray text at the top: the mock's `Find` line from the earlier perl accident had been pasted
    above `<!doctype>`. It's now where it belongs, so the vista run really hides the switched-off bridge objects.
- Editor scripts compile (Roslyn). **Not verified in Unity or the headset.**

## 2026-11-07, 13:14: uploaded (Ben pressed Build and Upload; the scene had been built and baked headless at 13:05)

- Uploaded `asset.world` 45.7 MB (was 26.7 MB: the 8K skybox, ~11 MB on Quest, ~24 MB on Windows), `index.html` and
  `script.js`. All three succeeded on the first attempt.
- Unity reported "Build Finished, Result: Failure" after each platform's bundle, with no error attached. The Builder
  carried on and uploaded anyway, so it's a false alarm. The only warning: "Serialization depth limit 10 exceeded at
  UnityEngine.Events::ArgumentCache.m_ObjectArgument". Not looked into yet.
- **Nothing from today has been in the headset yet.**

## 2026-11-07 (late afternoon): dome video wired to the media host, and a harness (Claude, Sphererebro3; Ben commits and pushes)

From the Mac session's handoff (`V:\Desktop\Sphererebro-Media-Handoff-for-Windows-2026-11-07.md`): the media host is up.
- **`MEDIA_BASE`** in `script.js` (`https://media.immersivepublic.network/`) and `MEDIA_EVENT` (`events/ImmersiveX2026/`).
  This is the one place the hostname lives. Monday's move to Bunny CDN keeps the same paths, so it's a one-line change.
- **The dome's default video** (`SB.sphereVideo`) is now the 60 s grid, 4096 x 2048 at 18M. Nothing downloads at load.
  **VIDEO** shows it, looping. **VIDEO again** steps to the next bitrate (18M -> 15M -> 10M -> 18M) and says which on
  the console. `SB.setVideo()` takes a full url or a file name in the event's video folder.
- **Bug found by the harness, fixed:** `Sphere_Screen` (the video surface) had **no UVs**. Blender's
  `create_uvsphere(calc_uvs=True)` only fills a UV layer that already exists, so every video would have shown as one
  flat colour. The inside surfaces now get UVs from direction (`uv_sphere_inward`, `u_offset`):
  - the video's FRONT is at 12 o'clock (Unity +Z, the far dome the audience faces);
  - RIGHT is at +X, LEFT at -X, BACK on the seam behind the audience (the portal), UP and DOWN at the poles.
  - Blender re-run. **Unity must rebuild the scene to pick up the new SB_Sphere.fbx.**
- **Harness** (`..\Assets\tests\harness\dome_video.html`, mesh from `export_screen.py`): three.js streams the real clip
  from the host onto the real `Sphere_Screen` mesh and looks from the dome centre and from a vista row 3 seat.
  - **Verified in the browser:** the 18M clip streams (CORS, ranges), decodes at 4096 x 2048 and loops.
  - FRONT, BACK, LEFT, RIGHT, UP and DOWN all land correctly, and the text isn't mirrored.
  - **Not Quest:** Unity's VideoPlayer and hardware decoding are different.
- Mock tests: 42/42 round (four new video checks).
- **"Loop, but only one download":** BS.VideoPlayer is Unity's VideoPlayer on a url (BSVideoPlayer.cs), streaming over
  HTTP with no cache setting. Whether Quest re-fetches on each loop can't be set from the script. Check it in the host's
  access log during the headset test.

## 2026-11-07 (afternoon): Ben's first look in the headset, the fixes (Claude, session Sphererebro3; Ben commits and pushes)

Ben's notes on ten screenshots (in `..\ref`), and what changed for each. Generators only: Blender re-run (FBX and
derived.json are new); **the scene has NOT been rebuilt** (Unity has the project open). Ben runs **Sphererebro > Build
World + Bake Lighting**, then looks.

- **Green obelisks** (the planters, concourse and plaza): switched off by the builder (`RetireRemoved`), not deleted.
  Their plaza lights stay.
- **Star motif** (spawn pad inlay, and the dais inlay): switched off until an on-brand motif replaces it.
- **Banisters you couldn't see from the side:** every vista and ring rail now has bronze posts at most 1.2 m apart and a
  bottom rail. New materials: `SB_RailGlass` (alpha 0.22, was 0.07) and `SB_RailCap` (satin bronze, metal 0.25, a faint
  glow). Why they were black: inside the sphere the renderers have reflection probes off, so fully metallic bronze
  reflects nothing. For the same reason `SB_Piping` is now metal 0.35.
- **Lounge lighting too hot, and flickering:**
  - softer fittings: `SB_Pendant_EMIT` on the pendants (was the signage white), the coves tucked behind a dark lip
    (`Band_Cove_Lip`) so you see light on the ceiling, not a thin hot line (thin bright strips shimmer on Quest);
  - final baked values after three headless builds checked in the review shots: pendants 7, coves 8, lounge spots
    12, sconces 12 (95 deg, 6 m), all times a gain of **3.5** (was 2.5). The first pass (pendants 5, coves 6, gain 2.5)
    came out too dark: the old hot strips and the glossy floor had been doing much of the lighting by bounce;
  - floor smoothness 0.82 -> 0.55 (the polished floor's glints);
  - new **up-light sconces** on the outer wall (`Band_Sconce_<zone>_<nn>`, each with a baked spot washing up the wall);
  - **club tints by zone**: rose at the restroom ends, amber at the bar, blue at the portal, violet in the lounges (no
    green). Coves, sconces and lounge spots take the zone colour (derived.json `zones`).
  - All of it is baked, per the SDK's performance page ("Bake your lighting"; on Quest a realtime light counts toward
    each object's 4).
- **Recliners:** the extended footrests are gone, and the sit point is 8 cm further forward (knees went through the
  cushion). The shiny arm squares are now **drink holders**: a matt collar 9.4 cm across inside, 6 cm deep, with a cup
  of box colliders. The seat's body collider no longer covers the arms, so a glass dropped in stays there.
- **Stemless wine glasses** (`Prop_StemlessGlass`, 8 cm wide) replace the flutes on the tables and the bar, so they fit
  the holders. Names are now `Wine Glass NN` (script and tests updated). The flute mesh stays in the model.
- **Row 3: two seats back.** The fan is 11.5 deg a side (was 11), which gives row 3 its 8th seat on each side. Rows are
  8/8/8/7/7 a side: **76 recliners** (was 74).
- **Text over the dash is gone.** `Desk_Status` stays, so the script still has somewhere to write, but it draws nothing.
  Each message also goes to the console. The discreet admin-only notification panel (like the Polys console) comes later.
- **XR Time Machine in the dash** (plugin v0.3.4):
  - new `ui.anchor` option: the panel is built onto a scene object instead of opening in front of the player (it opened
    in the floor);
  - Sphererebro's config points it at `Desk_XRTM_Mount`, above the desk front, leaning back 20 deg, turning with the dais;
  - it opens on a new **Sequences** tab: one big button per finished recording, oldest first, and a tap plays it for
    everyone, plus Stop;
  - only owners and moderators get it, drawn on their own device;
  - the desk key now says "owners and moderators only" to anyone else.
  - Built with `..\Assets\scripts\install_xrtm.ps1`. That port had a bug: an empty list compared with `-ne $null`
    filters instead of testing, so a second install doubled the blocks. It's fixed, and a re-run is stable.
- **The dome:** latitude and longitude lines every 15 deg (a meridian at 12 o'clock, a parallel at the equator), slightly
  lighter grey on dark purple, matt, with a faint self-glow (`Textures/SB_DomeGrid.png`, generated by the builder,
  2048 x 1024, ASTC 6x6 on Quest). The inner shell's UVs are now compass and latitude (Blender).
- **Skybox:**
  - the old one was an 8K panorama imported at 2048 x 1024 as a 2D texture, about 5.7 px a degree, hence the mush;
  - the builder now makes `SB_Skybox` (Skybox/Cubemap) from `Skybox/Sphererebro_Sky_8K.(jpg|png)` as a cubemap with
    2048 px faces, which keeps the full 8K detail inside Quest's 2048 limit. Optimised (Ben: "but optimize it"):
    ASTC 6x6 on Quest (~11 MB, against ~25 MB at 4x4), BC7 on PC (~25 MB; DXT1 smears small stars), no mipmaps (would
    add a third), RGB only, not readable;
  - the build report logs the face size;
  - the source is Ben's `Milkywaycolor-upscale.jpg` (8192 x 4096, 12 MB, from `..\ref`), copied in unchanged as
    `Skybox/Sphererebro_Sky_8K.jpg`. The old skybox material and its texture are left in place, unused.
- Realtime key and house lights are set to "Important" (pixel lights): they're never the ones dropped.

**Not verified:**
- The Unity build of all of this, and anything in the headset:
  - the new lighting and its bake;
  - drink holders holding glasses;
  - the sit point;
  - the XRTM panel on the desk (its size and readability, and whether a UIPanel parents to a moving dais);
  - the dome grid's look;
  - the skybox face size.
- The script tests pass (38/38 round, 33/33 vista), but against the mock only, and they don't exercise the new XRTM
  Sequences tab.
- **Side-view flicker** (seats seen from the far concourse windows): **cause not found.** There's no occlusion data in
  the scene, and nothing in the code explains it yet. Waiting on Ben: does the whole block vanish or flicker, or only the
  seats, and does it happen in every light preset?

## 2026-11-07 (later): seating toggle in the editor, no build needed (Claude; Ben commits and pushes)

Ben: no build or bake until he has seen the new layout, and it must be possible to switch the old one off and the new one on.

- **Sphererebro > Seating > Vista / Round (preview in the open scene).** Switches the scene you have open between the two
  layouts. Nothing is built or baked, and **nothing is saved**: use File > Save to keep it, or reopen the scene without
  saving to drop it. If the scene predates the vista layout (as the committed one does), the first switch to Vista adds
  the vista pieces: the model, 74 seats and colliders. Each switch:
  - moves the dais;
  - turns the round ring, its seats, the bridge and the portal gate off or on;
  - moves the in-sphere lights and the rescue landing.
  Everything it touches is real-time or a collider, so a switch needs no rebake.
- Build World uses the same routine (`ApplySeating`) with `"seating"` from dims.json, so the two can't drift apart.
- **Script:** reads the layout from the scene instead of `SB_DIMS`. If `Vista_Dais_Mount` (which now has an Object Id) is
  there, it's vista. So whatever is saved and uploaded, the script matches. Tests still pass 38/38 round and 33/33
  vista; both runs now check the detection.
- Builder compile-checked outside Unity: 0 errors. The toggle itself has **not been run in Unity yet**.

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

## 2026-11-10, 00:45: the show plays; console wraps the desk; lattice off
- **Why no cue played** (Ben's Player.log): the show looked up its 134 objects at "Unity Scene Loaded", before the object
  list had arrived, and found none. `createShow.init` now waits for `scene.objects` to settle and retries the missing.
  `show_test.html` delivers its objects 0.8 s late so this stays tested (35/35). Script fix uploaded 00:31.
- **Console** (`ui.wrap`): on a desk anchor the panel is three low panels (1000 x 340 px, 0.7 x 0.24 m, leaning back 52 deg)
  at -40 / 0 / +40 deg: left = now playing + Back / Again / Next; centre = filters + one key per cue, five to a row;
  right = Show / Record / Library (scrolls). Free-floating (no anchor) keeps the old tall panel. NOT seen in the app.
- **Lattice** off unless LATTICE is pressed (`sb_lattice === "1"`); it used to default on.
- Earlier today, not yet logged: dais drive limits scale with the sphere (dais was dragged off its dock), dais deck
  #111111 with the grid at 45 deg, no emissive on dais/desk trim, `tools/ship.ps1` (-Web / default / -Geo), automation
  requests `web` and `send`, SaveOpenScenes before a Builder build. Full world uploaded 2026-11-09 18:27.
- Open: Ben's "guard rails around the desk" not identified yet (only Vista_Rails exist near it). Desk logged
  "admin: false" at load for Ben; desk keys may be refused, unconfirmed.
- 2026-11-10 (later): vista rails are glass only (`GLASS_ONLY` in the generator: no cap, bottom rail, posts, gold strip).
  Lattice is matt black (`SB_LatticeBlack`) and shown only on request (LATTICE key). Not built or uploaded yet.

## 2026-11-10, 03:00: the media timeline rebuilt (not built in Unity, not uploaded)
- 01:17 world upload: glass-only vista rails, lattice on request. `tools/ship.ps1` now follows the Builder's log across midnight.
- Timeline (cue 2T, and new last cue T "Media Timeline"): no world history. Seven rails (Ben's five layers; digital formats
  drawn as image, video, 3D) on one time axis, on a 46 m sphere about the seats, 156 degrees wide, to 55 degrees up.
  Data `Config/talk_timeline_layers.json`; layout `tools/talk/layers.py`; cards `make_cards.py` (85 cards, 6 atlases).
  Dates are from memory, unchecked. The old events file is left in place, unused.
- Console: only cues named in talk_show.json `"keys"` get a key (now just T). The other 31 cues stay in the show.
- Harness: cards were drawn mirrored; fixed. show_test 37/37. Previews in `review/timeline/`.
- Untested: Unity build of the new timeline (needs Build World), anything in the app.

## 2026-11-10, 03:30: timeline pictures; Console is two keys (not built in Unity, not uploaded)
- Pictures (Ben's, copied to `talk/timeline_img/`): 12 items carry one. After the sweep each opens 9 m wide at its card,
  holds 1.3 s, then settles as a thumbnail on the card's left end, one at a time in date order (timeline play 34 s).
  Added to carry his pictures: Pepper's Ghost 1862, View-Master 1939, NASA VIEW headset 1985, Virtuality 1991.
  Not used: Niepce portrait, Holmes and Brewster stereoscopes, ENIAC, the First Kid still, the small Virtuality image,
  InnovationLogarithm.png (white line art on clear: rule 12). The Muybridge clip gives one still, it does not play.
- Texture budget: 3 sheets of 2048 (was 6): text cards packed at 512 x 128, 64 a sheet; pictures 512 x 512, 16 a sheet.
  Stale `gen_tl_cards_3..5.png` remain in Talk/Textures, unused.
- Console `ui.keysOnly` (on here): only the centre panel, only the keyed cues as two large pills: Ashburn (cue 5B3, the
  `ashburn` module) and Timeline (cue T). A key plays its cue alone; the other key takes over; the lit key again ends it.
  talk_show.json `"keys": ["5B3", "T"]`; the module's cue is now named "Ashburn". show_test 40/40.
- Open: picture clearance (Wizard of Oz still, the colour TV still, the Philips press photo, the Virtuality photo) is
  not checked; CREDITS.md not updated. Nothing here has been built in Unity or seen in the app.
