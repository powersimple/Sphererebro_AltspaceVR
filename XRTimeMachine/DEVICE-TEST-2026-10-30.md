# XR Time Machine device test, 2026-10-30

On Windows, in The Polys, on Ben's account. Most of it ran on the Windows app (AltspaceVR v0.5, desktop), driven from Claude Code over the app's browser debug port (`ora-windows.exe --remote-debugging-port 42067`). The local `script.js` was served in place of the live one, so no upload was needed. The Quest was reached the same way, over `adb forward tcp:9333 localabstract:webview_devtools_remote_<pid>`, but it paused whenever nobody wore it.

## What v0.3.0 did on a device

- **The panel was never seen**, on either device. Two causes:
  - A `UIPanel` switched off and on again with `SetActive` is never drawn again. The panel is built hidden, so it was invisible from the start. Shown by growing its scale instead, it draws, and its buttons take clicks.
  - On the PC, `pose-update` only arrives while the player moves (the SDK docs say so). Standing still, no head pose had arrived, and the panel opened at the world origin, 800 m under The Polys' spawn.
- **The wrist REC button never took a press** on the Quest. It was a `UIPanel` attached with `uid: "me"`.
  - Opening the panel from code (`XRTM.toggle()`) on the Quest placed it correctly from the head pose.
  - So the press itself never reached the script.
- **Stopping left the "recording" key behind**, so everyone kept being told they were recorded.
  - A protected key is deleted only by `SpaceStateDelete(path, { protected: true })`. Without it, the app answers `protected_path`.
  - The same applied to the playback key, the off switch (so `XRTM.on()` failed) and the cleanup of stale keys.
- **The recordings list showed each recording twice.** Two refreshes at once each cleared the list, waited for storage, then both drew it.
- **Recording names were invisible.** A `UITextField` draws dark text unless given a colour.
- **Stopping playback made the app throw** `NullReferenceException` in `SetJsTransform`, 4 times. The stand-in was destroyed partway through a move. On Windows this pops up the app's "Something went wrong" dialog.

## Fixed in v0.3.1 (src, reinstalled, all tests pass)

- **Panels hide and show by scale**, not `SetActive`. This covers the recorder panel and the off panel (`placeInFront` takes the size).
- **Panel placement:**
  - With a head pose from the last second, it works as before.
  - Without one, the panel is attached to the HEAD bone, 1.1 m out and 0.25 m down, then detached. This lands it in front of the camera, PC or headset.
  - Tested on Windows.
- **The wrist button is rebuilt as the kind that works in this world:**
  - a cylinder disc with a box collider on the UI layer (5);
  - attached with `Attach(scene.localUser.uid)`;
  - also pressed by a tap from the right hand: a trigger on layer 13 with `ColliderEvents`, tag `BSLocalCharacterRightHand`.
  - Presses are logged: `[XRTM] wrist button pressed by click|touch`.
  - Where it sits is set by `XRTM.wrist` (bone, position, rotation, sizes). `wristButton: false` turns it off.
  - The Polys sets `wrist: { position: [0, 0.03, 0.085] }`, beside the video's SOUND button.
- **All four protected deletes pass `{ protected: true }`.**
  - `test/fake-sdk.mjs` now rejects an unprotected delete of a protected key, as the app does.
  - With the old code, smoke and plugin fail ("state cleared on stop"). With the fix, they pass.
- **The list draws only the latest refresh.**
- **Text fields have white text** on a grey field (recording names, "go to time").
- **Stand-in moves run one at a time**, keeping only the newest pose. Teardown destroys the stand-in only after the move in progress.

## Seen working on Windows with v0.3.1

- F9 opens the panel in front of the camera, at the spawn, without moving.
- **Record**: the notice "This session is being recorded by Ben Erwin" shows. **Chapter** works, and so does **Stop**.
- `.xrtm` written through the helper to `Documents\AltspaceVR\XRTimeMachine\`: 54 s was 10,378 bytes, and 16 s was 6,604 bytes. That's about 190 B/s for one still desktop user.
- The list shows each recording once, with its name.
- **Play**: "Playing for everyone", the chapter is listed, and the stand-in is built (head, visor, hands, label).
- **Stop playback**: no app exception, no key left, the stand-in is removed.
- Close and reopen with F9.

## Not verified

- **On the Quest**, nothing of v0.3.1 ran. The app paused with nobody wearing it ("Finding position in room"). Still to do:
  - the wrist disc, both click and right-hand tap;
  - the panel in VR;
  - recording with video.
- **Video and sound on Windows**: `BS.Recording` reports `app_unavailable` in the Windows app, so PC recordings are data only. `av.bytesPerSec` is still unmeasured.
- **Desktop head pose:** `pose-update` on the PC reports the head about 0.8 m *below* the hands, and its rotation as identity. So a stand-in recorded on a PC shows its head at hip height. This needs a look at what the desktop app sends; VR should be fine.
- **Flaky test:** `test/playback.mjs` "paused: the stand-in stays put" failed once in a full run under load (0.429 vs 0.462). It then passed 5 times out of 5 on its own, and in every full run after.

## Also noted

- The Quest log, Unity lines only, reads with `adb logcat -s Unity:I`.
- `adb exec-out screencap -p` captures the Quest's view.
- The Windows app's world page and video pages are listed at `http://127.0.0.1:42067/json` while it runs.
