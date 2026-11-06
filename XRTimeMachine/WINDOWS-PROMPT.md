# Prompt for the Windows Claude Code session

Paste everything below the line into Claude Code on the Windows PC, opened in the ThePolysTheatreAltspaceVR repo.

---

You're taking over XR Time Machine (XRTM) on Windows, where Unity work happens. It's a spatial recorder and in-world playback plugin for Altspace worlds (Creator SDK). Ben wants to test the prototype in The Polys tonight, using his own account on two devices at once: the PC app and a Quest.

**Read first:**
1. `XRTimeMachine/README.md`: what it does, the off switches, the Windows test list, what only a device can confirm.
2. `XRTimeMachine/PLUGIN-PLAN.md`: why it's built this way.
3. `XRTimeMachine/src/`: `xrtm-core.js` (not tied to any platform) and `adapter-altspace.js` (everything that uses `BS`).

**How it's put together (v0.3.0, built and tested on the Mac today):**
- The plugin lives in `XRTimeMachine/`, outside `Assets`, so Unity ignores it and `asset.world` doesn't change.
- `node XRTimeMachine/install.mjs` builds `src/` (in the order `plugin.json` lists) into one marked block at the end of `Assets/WebRoot/script.js`, plus a config block (`window.XRTM_CONFIG`) just above it.
  - The config block is Ben's; the installer never overwrites it.
  - Flags: `--off`, `--on`, `--status`, `--uninstall`.
  - `install.ps1` just runs `install.mjs`.
- Everything else in `script.js` is the world's own code (video screens, elevator, tunnel, event switches). Never edit it for XRTM. Never edit the XRTM block by hand: edit `src/`, then reinstall.
- Recording belongs to the device it was started on.
  - Each device has its own key, `xrtm.recs.<session id>`.
  - Devices are told apart by session id (`localUser.id`), not account id, because Ben will be in the space twice on one account.
- Video and sound come from the app's own recorder, `BS.Recording`, at preset Low, written by the app straight to Videos (PC) or Movies (Quest).
- Storage:
  - a warning under 3 GB
  - under 1 GB, a lasting countdown
  - at 100 MB, recording stops
  - the helper (`helper/xrtm-helper.ps1`) reports the drive's real free space and also writes `.xrtm` files to `Documents\AltspaceVR\XRTimeMachine\`
- Failing safely:
  - it does nothing if `enabled: false`
  - it turns itself off if SDK features are missing
  - five errors in a minute and it removes itself for the visit
  - the protected key `xrtm.off` (panel button, or `XRTM.off()` / `XRTM.on()`) turns it off for everyone in the space

**Do now, in order:**
1. **Check** Node is 22 or later (`node -v`), then run `node XRTimeMachine\test\all.mjs`. Every line should say `ok`, ending with "script.js has the current build (on)". If any fail, stop and report the output; don't change the tests to make them pass.
2. **Run** `node XRTimeMachine\install.mjs --status`. It should say up to date and on.
3. **Play mode check in Unity:**
   - Press Play, wait for `[XRTM] loaded 0.3.0` and `[XRTM] recorder ready` in the console, then open the panel with `XRTM.toggle()` from the browser console (F9 doesn't fire in Play mode).
   - Record a few seconds, then stop. Video should say "not available here (app_unavailable)", which is expected.
   - Check that nothing else in the world changed: video screens, elevator, tunnel and event switches all behave as before.
   - Run `node XRTimeMachine\install.mjs --off`, press Play, and confirm `[XRTM] disabled in this world's config` with no panel. Then run `--on`.
   - Optional: local multiplayer (Creator SDK > Setup > Local Multiplayer) for a second player, to see the notice and playback.
4. **Help Ben publish:**
   - Start the helper in its own PowerShell window: `powershell -ExecutionPolicy Bypass -File XRTimeMachine\helper\xrtm-helper.ps1`
   - Then Builder: **Upload HTML + JS**. No scene rebuild is needed.
   - Uploading replaces the live script. Ben decides when, ideally while The Polys is quiet.
5. **Walk Ben through the device test** in README "Test on Windows tonight", step 6: PC plus Quest on one account, both recording at once, playback, then the off switch and back on.
   - Write down what happens against the README's "Things only a device test can confirm" list, especially:
     - whether both devices get the panel
     - whether `BS.Recording` starts and stops and where the MP4s land
     - the MP4 and `.xrtm` sizes per minute (set `av.bytesPerSec` in the config block to the measured MP4 rate)
     - what the Quest reports as free space
     - whether the off switch reaches both devices
   - Put the findings in a new `XRTimeMachine/DEVICE-TEST-<date>.md`.

**Rules:**
- **No commits or pushes.** Ben does git in GitHub Desktop; tell him "commit and push" when it's ready.
- **Every command you give Ben** uses full absolute paths. The repo is at `B:\ThePolysWorld\AltspaceVR\ThePolysTheatreAltspaceVR` (check that's still right).
- **After any change to `src/`:**
  - run `node XRTimeMachine\install.mjs` and then `node XRTimeMachine\test\all.mjs`
  - bump the version in both `plugin.json` and `XRTM.version` in `adapter-altspace.js` (a test checks they match)
  - note anything new that only a device can confirm in the README
- **Keep it lightweight:** no libraries, and nothing added to Unity's `Assets` for XRTM.
  - A Unity Editor menu (Tools > XR Time Machine > Install / Turn off / Remove) running `install.mjs` is a nice-to-have, not for tonight.
- **If something on the device breaks the world,** the fastest fix is the panel's off button or `XRTM.off()`. The next is `install.mjs --off` plus **Upload HTML + JS**.

**Known gaps, not for tonight:**
- The Layer 2 recorder bot (`Altspace/record.mjs` in the XR-Time-Machine repo) still watches the v0.2 key `xrtm.rec`.
- Playback reads a whole recording into memory, about 4 MB per 15 minutes of constant movement.
- The free-space figure on Quest without the helper is the browser's estimate.
