# RUN COMPLETE: 2026-11-08 00:00 (local). Built in the open editor; NOT uploaded; NOT seen in a headset.

# Sphererebro Status
Updated: 2026-11-08 00:00

## Survey
- **Engine:** Unity 6000.3.21f1, URP, Forward. SideQuest Creator SDK 4.0.20 (Altspace on the Banter codebase). The runtime logic
  is one page script, `Assets/WebRoot/script.js` (the `BS.*` JavaScript API). XR Time Machine (`XRTimeMachine/src`) is built
  into its end. The Builder uploads `asset.world` (Quest + Windows bundles), `index.html` and `script.js`.
- **Targets:** Quest standalone (Android, ASTC) and PC VR (Windows). Multi-user, through shared space state (protected keys are
  written by owners and moderators).
- **Build:** Unity **Sphererebro > Build World + Bake Lighting**. Unattended: `tools/unity_run.ps1 build`, which writes
  `Logs/sb_automation_request.txt` for `SphererebroAutomation.cs` inside the open editor.
- **Run:** in the Altspace app, in Ben's world. There is no local runtime for the page script, so the logic and the motion are
  simulated in the browser (see How to Run).
- **Seating (vista layout, live):** 76 recliners in 5 raked rows at the BACK of the sphere, facing +Z.
  - x from -7.8 to +7.8.
  - z from -46.3 (back row, seat y -0.45) to -39.7 (front row, seat y -2.25).
  - Centre-front eye at about (0, -1.15, -40.1).
  - The presenter's dais and desk (the "dashboard") are at (0, -2.65, -36.85).
- **Sphere:** centre (0,0,0), radius 50 m, so 100 m across (the brief said 50 m diameter).
- **World counts:**
  - 254,888 triangles in the whole world.
  - About 106,700 triangles and 280 draw calls visible from the seats before culling.
- **Animation path:** the SDK says per-frame motion belongs in Unity (reference/performance.md). So every cue's motion is a
  Unity AnimationClip, and the page script only switches objects on and off.
- **Budget (Quest):**
  - Under 300,000 visible triangles and under 150 draw calls per cue.
  - Textures at most 2048 (the talk's are 1K, ASTC 6x6).
  - Repeated racks merged.
  - Talk lights cast no shadows.

## Tasks
- [x] **Task 0 Survey:** above.
- [x] **Task 1 Blender pipeline:**
  - `tools/blender/common.py`, one script per asset, and `build_all.py` (16 scripts; all build headless in about 2 min).
  - Outputs: GLB (Y up, metres, base-centre origin, embedded JPEG PBR) to `talk/models/`, FBX for Unity, turntable sheets in
    `talk/previews/`, and `talk/models/ASSET_REPORT.md` (triangles and sizes).
  - The LOD1 rule: only talk_text exceeds 20k triangles. The distant racks use the decimated `server_rack_far` (1,610 triangles).
- [x] **Task 2 Assets:** all 15.
  - Server racks: hero, open, locked and label variants.
  - The 1920s radio, mid-century TV and 1990s web monitor.
  - Feed tiles, the electricity bill, the water tank, the gas plant and the stamp.
  - Four commons halls, the devices, the curved screen, the light beam and the white room.
  - Also: text meshes, 44 timeline cards and generated images. CC0 textures are listed in CREDITS.md.
  - The gas plant is built but no cue uses it yet (the brief's cue sheet never calls for it).
- [x] **Task 3 Cue system:** built INTO XR Time Machine 0.4.0 (`createShow` in `adapter-altspace.js`).
  - **Show tab on the desk dashboard (presenter only):**
    - cue number, name and the next cue;
    - Back and Next, Cue 1, Rehearse, End show;
    - a jump list of every cue.
  - **Inputs:** A (right) and X (left) while a show runs; the Right and Left arrows, Home, and R (rehearse, every 20 s).
  - **Sync:** the cue is the protected key `xrtm.show`, so only owners and moderators can drive and everyone sees the same cue.
  - **Transitions:** forward steps play each entrance (2 to 25 s, eased). Going back, or arriving late, shows held poses at once.
  - **Tests:** logic 32/32.
- [x] **Task 4 Video system:**
  - Surfaces: the curved screen, the dome 360 and the front-half 180, each in mono, side-by-side and top-bottom.
  - Stereo: `SB/StereoVideo` picks each eye's half; flat displays get the left eye.
  - Video starts on the cue for everyone, and late arrivals seek to where the clip is. Audio comes from the screen (a 3D source).
  - Placeholders and `media/README.md` are done.
  - Not done: putting the clips on the media host (see Needs Ben).
- [x] **Task 5 Cues:** all 30 cues are built, rendered and reviewed (`review/REVIEW.md`).
- [x] **Task 6 Sound:**
  - 30 sounds synthesised in `tools/talk/sounds.py`, plus Ben's Om bowl in the cue 1 bed.
  - Every sound is played by the animations themselves.
  - Beds peak at -15 to -19 dBFS.
- [x] **Task 7 Verify:**
  - **Build:** 0 talk warnings, 0 errors.
  - **Shots:** a held-pose render of every cue from the centre front seat and a wide view (`review/cues`), plus 56 mid-motion
    frames (`review/motion`).
  - **Budget:** every cue's held state is within it (worst: 62 draw calls, 199k talk triangles). See `review/PERFORMANCE.md`.
  - **Clearance:** PASS, 79 motions, closest 3.75 m (`review/CLEARANCE.md`).
  - **Back-restore:** exact from every cue (logic tests).
  - **Frame rate:** a headset is needed. The PC browser proxy is in `review/HARNESS_FRAMES.md`.
- [x] **Polish:**
  1. Easing on every motion.
  2. The label racks sway ±7°.
  3. White-room dust.
  4. The screen spills light onto the racks.
  5. The dusk fade-in as the doors open (cue 9).
  6. Build size: [BLOCKED] only the Builder's build measures `asset.world`, and that step uploads. Recorded below instead.
  7. Task 7 rerun after polish: done (23:45 build).

## Decisions
- **The cue engine lives in XR Time Machine.** Ben asked for this mid-run. XRTM 0.4 has a generic "show": cue data from the
  world's config, elements as Unity objects, and a Show tab on the desk panel. The world only supplies data and objects.
- **Each element is three registered objects ("twins"):**
  - **Play:** an Animator plays the entrance.
  - **Hold:** the final pose, merged by material, so it costs few draw calls.
  - **Exit:** plays the exit.

  XRTM hands Play over to Hold once an entrance ends. Beds and drifting loops are exempt, because their phase would jump.
- **Parked at load:** the talk waits 10 km below the world until the script hides every twin and brings it home.
  - Talk lights light only layer 12.
  - Beds are 3D sources with a wide minimum distance.

  So nothing of the show is seen or heard if the script never runs.
- **Folders:** the brief's `assets/models` would land inside Unity's `Assets/`, because Windows paths are case-insensitive.
  - GLBs go to `talk/models/` and turntables to `talk/previews/`.
  - Unity uses FBX copies in `Assets/_Sphererebro/Talk/Models/`.
- **Placeholders vs Ben's rule 10:** the placeholders are slow moves across the Milky Way plate. The only text is a small slot
  name and timecode in a corner; there are no grids and no bars.
- **Scale:**
  - Racks are 50 m tall. The data hall is a 450 m white room, so rows run to a white horizon.
  - Rows run beside and ahead of the audience, never behind it, because the concourse is real geometry back there.
  - The near racks pass high beside the seats, and two fly straight overhead and climb away.
  - Label racks are at 0.8 scale, so their panels sit near eye level. The locked rack and its flanks are at 0.7.
- **Cue 1:** the statement is in three lines (the same words). One line at 12 m would span about 150°.
- **The bill's odometer** climbs at most 3 steps a second (the comfort rule) and lands on $333.44.
- **Cue 2T, 200 Years of Media (Ben, mid-run):**
  - 44 events from his 2020Vision timeline. A comet runs the ribbon; each card blooms and then settles.
  - The text is Ben's own, except for two spelling fixes (Jurassic, Internet) and one added card: the c. 1827 Niépce
    photograph, which is in his assets, captioned with its own title.
  - Only public-domain pictures are used. Film stills and photos of living people are left out (brief rule 6).
- **Racks for the label cues and Trust** fly in to stand in front of the field. The brief's "slides back into the rows" means
  behind the inner row.
- **Cue 8:** the stamps press onto the fronts of the locked rack and its two flanking racks, from the audience's side. They are
  1.3× size (11 m), so their handles keep 3 m clear of the front row.
- **Presenter keys:** A and X only drive the show while it is running (cue above 0). Otherwise they keep their usual jobs.
- **The dome during the show:** the world hides its shells and lattice while the show is past cue 0, and restores them at End.
- **Not uploaded.** Ben's standing rule is to ask before uploading, and the brief doesn't ask for it. Uploading is one click.

## Needs Ben
- **Upload:** in Unity, open **Window > Banter/SideQuest Builder**, then Build and Upload (or write `upload` to
  `Logs/sb_automation_request.txt`). The scene was built at 23:45 and is saved.
- **Test in a headset:** this needs you.
  - **Basics:** press XR TIME MACHINE on the desk, then open the **Show** tab, then Next. A and X then work.
  - **Watch for:**
    - frame rate during cue 4B (the fly-in, about 140 draw calls for 25 s);
    - legibility of the title, labels and timeline cards;
    - loudness of the beds against your voice;
    - the stereo shader on Quest (cues 11 and 11B);
    - how the overhead rack pass feels.
- **Video:** drop the real clips into `media/` with the same file names. Then the Mac uploads them to
  `events/ImmersiveX2026/talk/...` on the media host. Until then, cues 5 to 5F show a blank screen. Even the placeholders need
  uploading to play.
- **Spare cues 11 and 11B:** they sit at the end, where the halls stand in front of the screen. Move them with the cue list in
  `talk_show.json` (for example after 5F), then run `tools/talk/build_show.ps1` and upload `script.js`.
- **Approve:**
  - the 2T card text changes (two spelling fixes, one added Niépce card);
  - the three-line cue 1 statement;
  - the 0.8-scale label racks.
- **Commit:**
  - `talk/`, `review/` and `tools/textures/` are large: about 190, 160 and 97 MB.
  - `Assets/_Sphererebro/Talk/` is about 160 MB of generated meshes, rebuilt on every build.

  Consider ignoring `talk/models/*.glb` and `review/`; both regenerate.

## How to Run
- **Rebuild everything:**
  1. `tools/talk/build_show.ps1 -Assets -Sounds -Cards`
  2. In Unity: **Sphererebro > Build World + Bake Lighting**. Unattended: `powershell -File tools\unity_run.ps1 build`.
- **Change the cues** (order, video, text): edit `Assets/_Sphererebro/Config/talk_show.json`, then run
  `tools/talk/build_show.ps1`. Order and video changes need only a `script.js` upload; text and motion changes also need
  Build World.
- **Rehearsal mode:**
  - In the world: R on a keyboard, or **Rehearse** on the Show tab. It auto-advances every 20 s and stops at the last cue.
  - In the browser: the simulator below has a Rehearse button.
- **Simulate in the browser:**
  1. Start the server: `powershell -File tools\harness\serve.ps1`
  2. Open http://localhost:8766/Sphererebro_AltspaceVR/tools/harness/show_test.html for the logic tests (32 checks).
  3. Open http://localhost:8766/Sphererebro_AltspaceVR/tools/harness/show.html to watch cues. Use the arrows, and
     **Clearance test** or **Perf + motion run**.
- **World tests:** http://localhost:8766/Assets/tests/script_test.html?seating=vista (60/60).
- **Review renders:** `tools/unity_run.ps1 "exec SphererebroTalkShots.Run"` writes `review/cues`, `review/motion` and
  `review/PERFORMANCE.md`. Then `tools/talk/make_review.py` writes `review/REVIEW.md`.

## Files Changed
- **Root:** SPHEREREBRO_STATUS.md (new), CREDITS.md (new), CHANGELOG.md, CLAUDE.md (a "The talk" section).
- **Assets/Editor/SphererebroKit:**
  - New: SphererebroTalk.cs, SphererebroTalkFeed.cs, SphererebroTalkTimeline.cs, SphererebroTalkJson.cs,
    SphererebroTalkShots.cs, SphererebroTalkDiag.cs.
  - Changed: SphererebroBuilder.cs (calls the talk build), SphererebroAutomation.cs (`exec Class.Method` requests).
- **Assets/_Sphererebro/Config:** talk_show.json (the cues), talk_timeline_events.json (2T), talk_timeline.json (generated).
- **Assets/_Sphererebro/Talk/:** Models (FBX), Textures, Materials (TK_*), Audio (30 WAV), Anim (clips and controllers),
  Meshes (generated), Shaders (SB_StereoVideo).
- **Assets/_Sphererebro/Scenes:** Sphererebro.unity plus its lighting data (rebuilt and rebaked).
- **Assets/WebRoot/script.js:**
  - the talk show block (generated);
  - the XRTM config `show:`;
  - XR Time Machine 0.4.0;
  - the world hides its shells and lattice during a show.
- **XRTimeMachine:** src/adapter-altspace.js (shows, the Show tab), plugin.json (0.4.0), dist/xrtm.js.
- **tools/blender:** common.py, talk_materials.json, build_all.py and 16 asset scripts, plus prop_shapes.py.
- **tools/talk:** choreo.py, sounds.py, make_cards.py, make_review.py, build_show.ps1.
- **tools/harness:** serve.ps1, show.html (simulator, clearance, frame times), show_test.html (logic).
- **tools (other):** unity_focus.ps1, unity_run.ps1, textures/ (17 CC0 sets).
- **talk/:** models (GLB, ASSET_REPORT.md, report.jsonl), previews (turntables), gen (generated images, cards, stills).
- **media/:** the 8 placeholder clips and README.md.
- **review/:** REVIEW.md, PERFORMANCE.md, CLEARANCE.md, HARNESS_FRAMES.md, notes.json, cues/ (60 PNG), motion/ (56 PNG).
