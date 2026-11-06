# XR Time Machine: spatial recorder plugin (v0.3)

A recorder and in-world playback for Altspace worlds built with the Creator SDK, packaged as a plugin. Copy this folder into the root of any world's Unity project, beside `Assets`, and run the installer. It runs the same on Windows and macOS (Node 22). Spec: `docs/spatial-recorder-spec.md` in the XR-Time-Machine repo; the plugin design is in [PLUGIN-PLAN.md](PLUGIN-PLAN.md).

| File | What it is |
|---|---|
| `plugin.json` | The manifest: name, version, which sources make the build, where it installs |
| `src/xrtm-core.js` | The core, not tied to any platform or world: the `.xrtm` format, poses, playback scheduling, the storage budget, the error breaker |
| `src/adapter-altspace.js` | Everything Altspace: permissions, shared state, messages, the panel, the stand-in, device storage, video |
| `install.mjs` | Builds `src/` into one block at the end of `Assets/WebRoot/script.js`, and into `dist/xrtm.js`. `install.sh` and `install.ps1` just run it. |
| `dist/xrtm.js` | The built plugin, made by the installer. Not edited by hand. |
| `helper/xrtm-helper.ps1` | Windows only, optional. While it runs, recordings are also written as `.xrtm` files to `Documents\AltspaceVR\XRTimeMachine\`, and the recorder gets the drive's exact free space. |
| `test/` | Logic checks against a fake SDK, in Node 22. `node XRTimeMachine/test/all.mjs` runs them all. They prove nothing about the real app. |

Edit `src/`, never the block in `script.js`, then run the installer again.

## How it sits in the world
The Builder uploads only `index.html`, `script.js` and `asset.world`. The plugin adds nothing to Unity, so `asset.world` doesn't change. In `script.js`, below the world's own code, there are two marked blocks:

```js
// >>> XR Time Machine config (yours to edit: install keeps it; …)
window.XRTM_CONFIG = {
    enabled: true,          // false: XR Time Machine does nothing in this world
    trackObjects: [],       // object names to record and replay
};
// <<< XR Time Machine config

// >>> XR Time Machine recorder v0.3.3 (built by XRTimeMachine/install.mjs …)
(function () { … })();
// <<< XR Time Machine recorder
```

- **The config block** is yours. The installer creates it once and never overwrites it.
- **The plugin block** is replaced on every install.
- **Everything is inside one function.** The plugin adds one global, `window.XRTM`. Its shared-state keys all start with `xrtm.`, and it ignores one-shots that aren't its own.
- **Uninstalling** removes both blocks and gives back `script.js` exactly as it was. The tests check this.

```bash
node XRTimeMachine/install.mjs              # install or update
node XRTimeMachine/install.mjs --status     # installed? up to date? on or off?
node XRTimeMachine/install.mjs --off        # keep it, switched off
node XRTimeMachine/install.mjs --on
node XRTimeMachine/install.mjs --uninstall
```

After any of these, upload the script (Builder: **Upload HTML + JS**). No scene rebuild is needed.

## Turning it off
| How | Who | Takes effect | Needs an upload |
|---|---|---|---|
| Panel: **Turn XR Time Machine off for everyone here** (tap twice) | the world owner or a moderator | at once, for everyone in the space | no |
| Browser console: `XRTM.off()` / `XRTM.on()` | the world owner or a moderator | at once, for everyone | no |
| `install.mjs --off` (`enabled: false`) | whoever uploads | next upload | script only |
| `install.mjs --uninstall` | whoever uploads | next upload | script only |

- **While it's off in a space**, owners still get one button, through **F9** or the wrist button: **Turn it back on**.
- **How long it stays off:** the off switch is the protected key `xrtm.off`, and space state lasts 24 hours.

**It also turns itself off:**
- **Missing SDK features** (no `BS`, no shared state, no one-shots): off for that visit, with one console line saying why.
- **No device storage:** the recorder is off, but playback still shows.
- **Five errors within a minute:** it removes its panel, wrist button, stand-in and notices, saves and closes any recording, unhooks everything, and stays off for that visit. None of its errors reach the world's code.

## Recording
- **Who gets the panel:** the world owner, or a community owner or moderator. It opens with **F9** on desktop, or the red **REC** button on the left forearm in a headset (point and click, or tap it with your right hand). Only you see it.
- **A recording belongs to the device it was started on.** Each device writes its own recording to its own storage.
  - One account in the space twice (a PC and a headset, or two headsets) can record on both at once, and only the recording device does the work.
  - Each recording device announces itself in the protected key `xrtm.recs.<session id>`. Everyone sees "This session is being recorded by …" once for each recording, including people who arrive during one.
- **What it captures, as data:**
  - who's there, joins and leaves
  - every user-state change (avatar, mute, raised hand…)
  - every space-state change
  - your own head and hands
  - the objects in `trackObjects`
  - chapters

  All of it is in world coordinates, on one clock from zero.
- **What it captures, as video and sound:** the app's own recorder (`BS.Recording`), on the same device.
  - It starts and stops with the recording.
  - The file is a compressed MP4 (preset **Low**, 1280×720 at 30 fps), written by the app straight into the PC's **Videos** folder or the headset's **Movies** folder. It never passes through the page's memory.
  - The sound is what you hear plus your own voice, as set in your recording settings.
  - The `.xrtm` file records when the video started (an `av` line with its take id), so the two line up.
  - If it isn't available (Play mode, or you're already recording video yourself), the panel says so and the data is recorded anyway.
- **Where the data goes, without filling memory:**
  - Lines are written to the device every second and then dropped.
  - They go to IndexedDB on Windows and Quest, plus `Documents\AltspaceVR\XRTimeMachine\<id>.xrtm` on Windows while the helper runs.
  - If the device can't keep up (30 writes waiting), the recording stops rather than fill memory.
- **Size:**
  - Data: positions are rounded to the millimetre and rotations to 4 places, and a pose that hasn't changed isn't written. Up to 20 poses a second.
    - Worst case, moving all the time: about 4 MB per 15 minutes.
    - Standing still: almost nothing.
    - These are estimates.
  - Video is most of it: roughly 1–2 GB an hour at Low. That figure isn't measured yet; see the device tests.
- **Storage limits.** Recordings have no length cap, only these:
  - **Under 3 GB free when you start:** a warning.
  - **Under 1 GB free:** a lasting warning under your view: "Storage low: 820 MB free · about 12 min of recording left". It counts down while you record.
  - **At 100 MB free:** recording stops and saves, so the device keeps room to work. It won't start again until there's more than 100 MB.
  - **How free space is measured:**
    - On Windows with the helper: the actual free space on the drive the helper writes to.
    - Otherwise: what the app's browser storage reports, which is an estimate.
  - **How time left is worked out:** from how fast free space is actually falling, or from the expected data and video rate until there are two readings.
- **Not captured:** other people's full bodies and separate voices. A world script can't see those; the recorder bot does (Layer 2, below).

## Playback
- **To start:** press **Play** on a recording in the list. It plays from the beginning for everyone in the space, in the original location.
  - One playback at a time.
  - Only the device that started it can control or stop it.
- **What everyone sees:**
  - A see-through stand-in for the person who recorded: a head with a dark visor showing where they looked, plus their hands.
  - A caption over it: who recorded it, how many were there, and recent events ("Ada joined", "Ada raised a hand", "Chapter: Finale").
  - Tracked objects move as they did, and go back where they were when playback stops.
  - Objects that aren't in this world are skipped.
- **The Playback tab:**
  - the time
  - a scrub slider (everyone jumps when you let go)
  - **▶ Play / ❚❚ Pause** and **■ Stop playback**
  - a time field with **Go to time** (`hh:mm:ss`, `mm:ss` or seconds)
  - the chapters, tap one to jump
- **At the end** it pauses on the last frame.
- **How everyone stays in step:**
  - The device playing it leads. The shared clock is the protected key `xrtm.play`.
  - The recording's lines go out in one-shots, about 2 seconds ahead of the playhead, with a keyframe after every jump and every 3 seconds.
  - Every player's page replays on its own copy of the clock.
  - If the device playing it leaves, it stops for everyone.

## Test on Windows tonight
Paths assume `B:\ThePolysWorld\AltspaceVR\ThePolysTheatreAltspaceVR`. Use Node 22.
1. **Pull** in GitHub Desktop.
2. **Check:**
   ```powershell
   node B:\ThePolysWorld\AltspaceVR\ThePolysTheatreAltspaceVR\XRTimeMachine\test\all.mjs
   ```
   Every line should start with `ok:`, the last one being "script.js has the current build (on)".
3. **Start the helper** in its own PowerShell window, and leave it running:
   ```powershell
   powershell -ExecutionPolicy Bypass -File B:\ThePolysWorld\AltspaceVR\ThePolysTheatreAltspaceVR\XRTimeMachine\helper\xrtm-helper.ps1
   ```
4. **Play mode** (optional, quick): press Play in Unity, click the Game view, and use the panel.
   - **F9 doesn't fire in Play mode:** open the panel from the browser console with `XRTM.toggle()`.
   - Video reports "not available here (app_unavailable)": that's expected.
5. **Publish:** Builder, **Upload HTML + JS**. This replaces the live world's script, so do it while The Polys is quiet.
6. **Two of you** (PC app plus Quest, same account):
   - **The PC:**
     - Press **F9**, then **Record**. Check: the notice appears for both of you, and the panel says where the video goes.
     - Walk around, add a chapter, then **Stop**.
     - Check: the recording is in the list, the `.xrtm` file is in `Documents\AltspaceVR\XRTimeMachine\`, and an MP4 is in `Videos`.
   - **The Quest:** use the wrist **REC** button. Record at the same time as the PC.
     - Check: both record, each to its own list.
     - Check: the PC's recording doesn't appear on the Quest, and the other way round.
   - **Playback:** press **Play** on the PC. Check: the Quest sees the stand-in walk the recorded path.
   - **The off switch:**
     - Tap it twice. Check: everything disappears on both devices.
     - Press **F9**, then **Turn it back on**. Check: it's back on both.
7. **Note sizes:** how big the MP4 and the `.xrtm` file are, and for how many minutes of recording. Set `av.bytesPerSec` in the config to what you measure.

The browser console lines start with `[XRTM]`.

## Layer 2: full bodies and voices (the recorder bot)
In the XR-Time-Machine repo, on a PC with Node 22:
```powershell
cd <XR-Time-Machine>\Altspace; npm run record -- thepolys --follow
```
The bot joins and records whenever a panel records, into `Documents\AltspaceVR\XRTimeMachine\<id>.bot\`. It's a visible participant: prototype only. It still watches the v0.2 key `xrtm.rec`; following `xrtm.recs.*` is a to-do there.

## Settings
In the config block in `script.js`. Groups merge, so `{ ui: { fontScale: 1.3 } }` changes only that one.

| Setting | Meaning |
|---|---|
| `enabled` | `false`: does nothing at all |
| `trackObjects` | Names of objects whose movement to record (playback moves objects by these names) |
| `poseHz` | Most poses per second (20). Unchanged poses aren't written. |
| `storage` | `warnBytes` (3e9), `countdownBytes` (1e9), `stopBytes` (1e8), `checkMs` (10000) |
| `av` | Video and sound: `enabled` (true), `preset` (`"Low"`), `bytesPerSec` (400000, the expected MP4 rate for the countdown; unmeasured) |
| `breaker` | `max` errors (5) within `windowMs` (60000) before it removes itself |
| `maxPendingWrites` | Writes waiting on a slow device before recording stops (30) |
| `toggleKeyCode` | The desktop key that opens the panel (290 = F9) |
| `inHeadset` | `false`: no recorder panel or REC button in a headset, so recording is desktop only; notices and playback still show everyone (true) |
| `wristButton` | `false`: no REC button on the forearm in a headset (true) |
| `wrist` | The REC button: `bone` (`"LEFTARM_LOWER"`), `position` and `rotation` on it (metres, degrees), `radius`, `thickness`, `fontSize`, and the tap from the right hand: `touchLayer` (13), `touchMs` (800) |
| `helperUrl` | Where the Windows helper listens |
| `playAheadMs`, `keyframeMs`, `pumpMs`, `oneShotBytes` | How playback lines are sent (2000, 3000, 250, 3600) |
| `ghostColor` | The stand-in's tint, `[r, g, b, a]` from 0 to 1 |
| `ui` | Sizes, because readability on a device is unverified |

The `ui` sizes:

| `ui.` | Meaning |
|---|---|
| `panelScale` | World size of the panel (0.1: 560 px wide is 0.56 m) |
| `panelWidth`, `panelHeight` | The panel in pixels (560 × 960) |
| `fontScale` | Multiplies every font size on the panel |
| `listHeight`, `chapterListHeight` | The recordings list (220 px) and the chapter list (150 px) |
| `noticeSize` | Size of the notices and warnings (0.11) |
| `ghostLabelFontSize`, `ghostLabelHeight` | The caption over the stand-in: font size (1) and metres above the head (0.35) |

## The .xrtm v0 file
Newline-delimited JSON, append-only, so everything written before a crash is still readable.
- **Line 1, the header:** `format: "xrtm"`, `version: 0`, the id, the world, `startedUtc`, and the recording device's session id.
- **Every other line:** `{ t, type, ... }`, where `t` is milliseconds since the start.
- **Types:**
  - `roster`
  - `space_state`
  - `join`, `leave`
  - `user_state`
  - `self_pose`
  - `object`, `object_pose`
  - `chapter`
  - `av` (the video recorder's start and state changes)
  - `end` (with a `reason` if storage or a slow device stopped it)
- **Ids** end with a short device tag, so two devices starting in the same second don't collide.

It will move to the MCAP-based format in the XR-Time-Machine plan; readers check `format` and `version`.

## Things only a device test can confirm
**The plugin:**
- that it behaves the same in Play mode and once published, and nothing in the world's own code (video screens, elevator, tunnel, event switches) changes with it on, off or removed
- that the off switch reaches everyone at once, and that **Turn it back on** works in a headset
- whether `scene.Off` exists in the app. If it doesn't, listeners stay attached after a shutdown, but they do nothing.

**One account twice:**
- that both devices get the panel
- what `scene.users` shows with one account in twice (the SDK keys it by account id, so the two may share one entry)
- that `localUser.id` (the session id) differs between the two

**Video and sound:**
- that `BS.Recording` starts and stops with the recording on both PC and Quest
- where the files land, and their size per minute at Low
- whether a world-started recording shows a badge to others

**Storage:**
- the free-space figure on Quest without the helper. The browser's estimate may not be the device's real free space.
- that the countdown is believable
- that the stop at 100 MB happens

**Panel and playback** (unchanged from v0.2):
- readability at 0.96 m tall
- slider dragging with a controller ray, and typing in the time field
- one-shot rate (2–3 a second)
- the stand-in's look and size
- objects going back after Stop
- how long a recording a Quest can load into memory to play
