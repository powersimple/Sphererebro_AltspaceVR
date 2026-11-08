# The talk's video slots

Each file here is a **placeholder**: a 10-second slow move across the world's Milky Way plate with its slot name and a
timecode small in the corner (Ben's rule: no bars and tone, no test grids). Replace each with the real clip, keeping the
exact file name.

| Cue | File | Layout | Plays on |
|---|---|---|---|
| 5 | `hyperscale/01_night_globe.mp4` | flat | the curved screen |
| 5B | `hyperscale/02_ashburn.mp4` | flat | the curved screen |
| 5C | `hyperscale/03_richland_parish.mp4` | flat | the curved screen |
| 5D | `hyperscale/04_africa_night.mp4` | flat | the curved screen |
| 5E | `hyperscale/05_cables_red_sea.mp4` | flat | the curved screen |
| 5F | `hyperscale/06_outlets_globe.mp4` | flat | the curved screen |
| 11 (spare) | `quest3d/01_capture.mp4` | side-by-side stereo (left eye left half) | the curved screen |
| 11B (spare) | `quest3d/02_capture.mp4` | side-by-side stereo | the curved screen |

## Formats
- **Container/codec:** MP4, H.264 (safest on Quest) or H.265. AAC audio. Give silent clips a silent AAC track (an Android
  player can stall on a video with no audio track; every placeholder has one).
- **Flat clips for the curved screen:** 16:9, 1920x1080 to 3840x2160. The screen is 40 x 22 m (about 16:9), curved.
- **Side-by-side stereo:** both eyes in one frame, left eye in the LEFT half (e.g. 3840x1080 for 1920x1080 per eye).
- **Top-bottom stereo:** left eye on TOP.
- **360 / 180 (the whole dome, or its front half):** equirectangular, 2:1 for 360, 1:1 for 180 (mono, or stereo in the
  layouts above). Surfaces exist in the world (`Talk_Video_dome360_*`, `Talk_Video_dome180_*`); a cue uses one by naming it.
- **Bitrate:** what the media host can stream to everyone at once. 1080p at 6 to 10 Mbps, 4K at 15 to 25 Mbps.

## Replacing a placeholder
1. Export the clip with the exact name above.
2. Drop it into this folder, over the placeholder.
3. Upload it to the media host, under `events/ImmersiveX2026/talk/` at the same relative path (for example
   `events/ImmersiveX2026/talk/hyperscale/02_ashburn.mp4`). The world streams from
   `https://media.immersivepublic.network/events/ImmersiveX2026/talk/`, so the files in this folder are the masters, not
   what plays. Uploads go through the Mac (the `sphererebro-media-sync` skill: add each file to `media-outbox/UPLOAD-QUEUE.md`).
4. No rebuild is needed: the cues name the files.

## Changing which clip a cue plays, or its layout
Edit `Assets/_Sphererebro/Config/talk_show.json` (the cue's `video`: `surface` = `curved`, `dome360` or `dome180`;
`clip`; `layout` = `mono`, `sbs` or `tb`), then run `tools/talk/build_show.ps1` (it regenerates script.js's show block).
Only `script.js` needs uploading for that.
