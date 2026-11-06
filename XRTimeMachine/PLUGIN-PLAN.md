# XR Time Machine as a plugin: plan

2026-10-30. Status: built as v0.3.0 the same day, with these changes from Ben:
- no cap on recording length, only the storage limits: warn under 3 GB, a countdown under 1 GB, stop at 100 MB;
- recording per device, so one account on two devices can record on both;
- video and sound from the app's own recorder (`BS.Recording`, compressed MP4 on the device);
- the installer is one Node script, `install.mjs`, so it works on any OS.

The README describes what was built; the rest of this page is the original proposal.

XRTM has to stand on its own until platforms build it into their core. That means:
- its own folder;
- one clean hook into a world;
- a switch that turns it off in seconds;
- it never takes a world down with it.

## Where it stands today

- **What works:**
  - The recorder and the v0.2 playback are one file, `XRTimeMachine/xrtm-world.js` (57 KB).
  - `install.sh` / `install.ps1` copy it into `Assets/WebRoot/script.js` between marker lines.
- **What it needs from Unity:** nothing. It adds no Unity assets, so `asset.world` doesn't change size.
- **Where it's tied to Altspace:**
  - The recording format, clock, store and playback scheduler are generic, but they're mixed in with Altspace-only code: the `BS` calls, the panel and the stand-in.
  - The Node bot core in the XR-TimeMachine repo (`core/`) writes a different layout (session.json, jsonl files and WAVs). So there are two formats so far.
- **How it fails today:** startup has a try/catch. There's no kill switch, no protection against repeated errors, and no storage cap.
- **Storage:** about 6 MB per 15 minutes of recording, kept on the device.

## 1. The generic version: three layers

| Layer | What's in it | Knows about |
|---|---|---|
| **Core** `src/xrtm-core.js` | The `.xrtm` line format and header, the clock, chunked writing, the recorder's start/stop/chapters, the playback scheduler (buffer, seek, keyframes, end), packing lines into messages, storage budget, error breaker | Nothing outside plain JavaScript. It runs in a world page, a browser or Node. |
| **Platform adapter** `src/adapter-altspace.js` | Who may record, shared state, messages, sampling the head and hands, finding and moving objects, the panel, the stand-in, device storage (IndexedDB plus the Windows helper) | The Altspace Creator SDK (`BS`) |
| **World config** (a few lines in the world) | Which objects to track, panel sizes, on/off | That one world |

The core talks to the platform only through a small adapter object: `now`, `canControl`, `getShared`, `setShared`, `broadcast`, `onMessage`, `samplePoses`, `moveObject`, `store`, `ui`. A new platform means writing a new adapter, with the core unchanged:
- CSP / the IPN World
- WebXR / three.js
- a C# port for the native client later

Next, the bot core in `core/` writes the same `.xrtm` lines as the world recorder, so there's one format until the MCAP container in PLAN.md replaces it.

## 2. How it travels in a build

The Builder uploads only `index.html`, `script.js` and `asset.world`. Any other file in `Assets/WebRoot` works in Play mode but is missing once the world is published.

```
ThePolysTheatreAltspaceVR/
  XRTimeMachine/            the plugin: outside Assets, so Unity ignores it and the build doesn't grow
    plugin.json             name, version, hook markers, which files make the build
    src/                    xrtm-core.js, adapter-altspace.js
    dist/xrtm.js            core + adapter in one file (made by the installer)
    install.sh / .ps1       --install, --uninstall, --off, --on, --status
    helper/                 Windows file-writer helper (optional)
    test/                   fake SDK + tests (Node 22)
    README.md
  Assets/WebRoot/script.js  the world's own code, plus one marked XRTM block at the end
```

- **The hook:** one marked block at the end of `script.js`. It's baked in, so it always travels with an upload.
- **The world config** lives at the top of that block, with a single on/off line:
  ```js
  window.XRTM_CONFIG = { enabled: true, trackObjects: [] };
  ```
- **Removing it:** `install --uninstall` takes it all out and leaves the rest of `script.js` byte-for-byte as it was. The tests check this.
- **The alternative (not recommended):**
  - `dist/xrtm.js` uploaded on altvr.app (Edit world > Assets), with one `<script src="xrtm.js">` line in `index.html`.
  - That's cleaner on paper, but it's an extra manual step every time XRTM changes, and forgetting it fails silently.
  - It stays possible later with no code change.
- **Unity Editor menu (Windows, optional):** Tools > XR Time Machine > Install / Remove / Turn off, running the same installer.

## 3. It must work, or step aside quietly

- **One door in:** the whole block is wrapped, so nothing it does can throw into the world's code.
  - It adds one global, `window.XRTM`.
  - Its shared-state keys all start `xrtm.`, and it touches no other keys.
  - It ignores messages that aren't its own.
- **It checks before it starts:**
  - If `BS`, shared state, messages or IndexedDB are missing, it turns itself off for that visit.
  - It writes one log line saying why.
- **Error breaker:** 5 errors within a minute and it shuts down for that visit:
  - removes its panel, wrist button and stand-in
  - stops any recording, keeping what's already saved
  - unhooks its listeners
- **Three ways to turn it off:**

| Switch | Who | How fast | Needs a re-upload |
|---|---|---|---|
| `xrtm.off` shared key, from the panel ("Turn XRTM off in this world") | owner or moderator | instantly, for everyone in the space | no |
| `enabled: false` in the config line | whoever uploads | next upload | script only, no rebuild |
| `install --uninstall` | whoever uploads | next upload | script only, no rebuild |

  - The shared-key switch doesn't depend on the panel. If the panel itself is what fails, the owner can set the key from the browser console (one line, in the README).
- **Cost when idle:** for everyone except owners, XRTM only listens. It builds nothing until a playback starts.

## 4. Lightweight

- **Code:**
  - Now: 57 KB of readable source.
  - Target: under 100 KB readable in the build.
  - A minified build (about 25 KB) can come later if it matters.
  - Plain JavaScript, with no libraries.
- **Storage per recording** (not measured yet; I'll measure before promising numbers):
  - Positions are rounded to the millimetre and rotations to 4 places.
  - A pose that hasn't changed isn't written.
  - Default pose rate 20 Hz (from 30), set in the config.
  - Estimate: under 1 MB per 15 minutes, down from about 6 MB.
- **Storage cap:**
  - `maxStoreMB` in the config sets the most XRTM keeps on a device.
  - Recording stops cleanly at the cap and says why. Nothing is deleted without the owner asking.
- **Open question for Ben:** does "a MB or two" mean the plugin's own footprint in the build, which this already meets, or recordings kept on the device?
  - If it means recordings, 2 MB is about 30 minutes after slimming.
  - The panel can offer export to the Windows helper, then delete.

## 5. Steps

1. Split `xrtm-world.js` into core and Altspace adapter in `src/`, and make `plugin.json` and `dist/xrtm.js`.
2. Add the guard, the start-up checks, the error breaker and the three off switches.
3. Slim the poses, and add the storage cap.
4. Installer: add `--off`, `--on`, `--status` and `--uninstall`, and check that a round trip leaves the world's code untouched.
5. Tests, on the fake SDK under Node 22:
   - everything that passes today
   - plus: missing SDK, the breaker, the remote off switch, the cap, uninstall leaving script.js byte-for-byte, and a measured size per minute
6. Install into Polys and run `node --check` on script.js. Then write the Windows hand-over prompt, `XRTimeMachine/WINDOWS-PROMPT.md`.

## Only a device can confirm

These need the Windows editor (Play mode and a published upload) and a Quest:
- The block, and the off switches, behave the same in Play mode and once published.
- Nothing in the Polys world's own code (video screens, elevator, tunnel) changes with XRTM on, off or removed.
- Recording size on a real session, and how much IndexedDB room the Quest really gives.
- Everything already on the README's device-test list (panel readability, slider dragging, how many messages per second get through).
