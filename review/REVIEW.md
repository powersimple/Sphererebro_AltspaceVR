# Talk review

Generated 2026-11-07 23:46 by tools/talk/make_review.py.

## Summary

- All 30 cues (the brief's cues 1 to 11 with their B/C/... steps, plus Ben's 2T timeline) are built in the Unity scene and step from XR Time Machine's Show tab on the desk dashboard (or arrow keys / A and X). Built in the open editor; not uploaded; not yet seen in a headset.
- Every cue's held state is inside the Quest budget (under 200,000 talk triangles, at most 62 draw calls; review/PERFORMANCE.md). During the rack fly-in (cue 4B, about 25 s) the unmerged waves cost more, about 140 draw calls, before the merged pose takes over.
- Clearance: PASS. No moving object comes within 3 m of any seat in any entrance or exit (review/CLEARANCE.md). The closest pass is the commons halls rising beside the front rows.
- Show logic: 32/32 checks against the real script.js with a mock SDK: forward through every cue plays exactly its entrances; back from every cue restores the prior cue exactly; late arrivals and other presenters' changes show held poses; only the owner/moderators can drive; rehearsal auto-advances and stops at the end.

## What works

- Cue engine inside XR Time Machine 0.4 (generic: any world can give it cues and objects). Cue state is the protected key xrtm.show, so everyone in the space sees the same cue.
- Presenter-only Show tab on the desk dashboard: cue number and name, next cue, Back / Next (round pill keys), Cue 1, Rehearse, End show, a jump list of every cue. A (right) next and X (left) back while a show runs; arrows, Home and R on a keyboard.
- All motion is Unity animation (no per-frame script traffic): racks in waves of nine at ~40 m/s easing to a stop, overhead and side passes, the label racks turning their panels and swaying, the bill unrolling with its odometer, tanks filling, stamps, doors opening, beams growing, halls rising.
- Sound is in the animations too: 30 synthesised sounds (rack landings, whooshes, rumble, paper, odometer, water, shatter, chimes, beds) plus Ben's Om bowl in the cue 1 bed. Beds fade in and out with their cues.
- Video: the curved screen (and dome 360 / front-half 180 surfaces) in mono, side-by-side and top-bottom stereo; a stereo shader picks each eye's half; audio comes from the screen.
- Cue 2T: Ben's 200-year media timeline as a comet running a ribbon around the audience; every event's card blooms large, then settles as a small tile.
- Going back or arriving late shows the final pose at once; going forward plays each entrance. The world hides its dome shells and lattice while a show runs and puts them back at the end.

## What doesn't (or is unverified)

- NOT SEEN IN A HEADSET. Everything here was checked in the Unity editor (renders below), a browser simulator and logic tests. Frame rate on Quest is unknown.
- The video slots play placeholders, and only after they are uploaded to the media host (events/ImmersiveX2026/talk/...). The world streams video from there, not from media/.
- The stereo shader (SB/StereoVideo) is custom; if the app ever shows it magenta, the mono surface still works (cue data: layout mono).
- Racks read as dark monoliths in the white room (by design they are silhouettes), with LEDs twinkling; their door detail shows close up.
- asset.world will be larger (the talk's textures and meshes); the size is only known after the Builder's build.
- Real figures and names on screen are only the brief's own text; the timeline text is Ben's 2019 file (two spelling fixes).

## Checks

- Clearance (3 m around every seat, every entrance and exit): Result: **PASS**: 79 motions checked. (review/CLEARANCE.md)
- Show logic (XR Time Machine Show against a mock SDK; forward, back from every cue, late arrival, presenter-only, rehearsal): 32/32 (tools/harness/show_test.html)
- Per-cue triangles and draw calls: review/PERFORMANCE.md (Quest budget: < 300,000 triangles, < 150 draw calls).
- Frame rate: not measurable without a headset; the browser harness's relative frame times are in review/HARNESS_FRAMES.md.

## Cue by cue

### 1. Cue 1: So Who Will?
Talk triangles 23,692, draw calls 6, real-time lights 0 (held pose).
The dome goes dark, a slow star field; the statement forms word by word on a 14 m arc above the presenter, then 'So who will?' in gold.

![01_1.png](cues/01_1.png)
![01_1_wide.png](cues/01_1_wide.png)
![01_1_t03.0.png](motion/01_1_t03.0.png)
![01_1_t09.0.png](motion/01_1_t09.0.png)

### 2. Cue 2: A Hundred Years of Public Media
Talk triangles 13,028, draw calls 8, real-time lights 4 (held pose).
The 20 m cathedral radio drifts in from the far left in warm light, turning to show its form, crosses the front and settles left.

![02_2.png](cues/02_2.png)
![02_2_wide.png](cues/02_2_wide.png)
![02_2_t05.0.png](motion/02_2_t05.0.png)
![02_2_t12.0.png](motion/02_2_t12.0.png)

### 3. Cue 2B: Television
Talk triangles 20,468, draw calls 14, real-time lights 5 (held pose).

![03_2B.png](cues/03_2B.png)
![03_2B_wide.png](cues/03_2B_wide.png)

### 4. Cue 2C: The Web
Talk triangles 24,026, draw calls 19, real-time lights 6 (held pose).

![04_2C.png](cues/04_2C.png)
![04_2C_wide.png](cues/04_2C_wide.png)

### 5. Cue 2T: 200 Years of Media
Talk triangles 24,678, draw calls 24, real-time lights 6 (held pose).
Ben's timeline: the comet runs 1746 -> 2019; each card blooms beside it, then shrinks onto the ribbon.

![05_2T.png](cues/05_2T.png)
![05_2T_wide.png](cues/05_2T_wide.png)
![05_2T_t10.0.png](motion/05_2T_t10.0.png)
![05_2T_t30.0.png](motion/05_2T_t30.0.png)

### 6. Cue 3: The Commercial Turn
Talk triangles 45,810, draw calls 43, real-time lights 6 (held pose).
The feed wall rises all round, sector by sector, scrolling upward, closing in front of the trio. Cool blue light.

![06_3.png](cues/06_3.png)
![06_3_wide.png](cues/06_3_wide.png)
![06_3_t03.0.png](motion/06_3_t03.0.png)

### 7. Cue 4: The Construct
Talk triangles 2,208, draw calls 3, real-time lights 2 (held pose).
The wall bursts into white particles; everything fades to the white room; silence.

![07_4.png](cues/07_4.png)
![07_4_wide.png](cues/07_4_wide.png)
![07_4_t00.8.png](motion/07_4_t00.8.png)

### 8. Cue 4B: Lots of Data Centers
Talk triangles 145,234, draw calls 27, real-time lights 2 (held pose).
Ten waves of 50 m racks fly in from the white horizon and lock into rows down a data hall; the nearest pass high beside the seats, two fly straight overhead and climb away. Heavy landings, LEDs on in sequence.

![08_4B.png](cues/08_4B.png)
![08_4B_wide.png](cues/08_4B_wide.png)
![08_4B_t03.0.png](motion/08_4B_t03.0.png)
![08_4B_t06.0.png](motion/08_4B_t06.0.png)
![08_4B_t09.0.png](motion/08_4B_t09.0.png)
![08_4B_t12.0.png](motion/08_4B_t12.0.png)
![08_4B_t15.0.png](motion/08_4B_t15.0.png)

### 9. Cue 4C: The Figures: 415 TWh
Talk triangles 150,640, draw calls 48, real-time lights 2 (held pose).

![09_4C.png](cues/09_4C.png)
![09_4C_wide.png](cues/09_4C_wide.png)
![09_4C_t03.0.png](motion/09_4C_t03.0.png)
![09_4C_t06.0.png](motion/09_4C_t06.0.png)

### 10. Cue 4D: The Figures: 945 TWh
Talk triangles 151,984, draw calls 49, real-time lights 2 (held pose).

![10_4D.png](cues/10_4D.png)
![10_4D_wide.png](cues/10_4D_wide.png)

### 11. Cue 4E: The Figures: $500 billion
Talk triangles 150,944, draw calls 46, real-time lights 2 (held pose).

![11_4E.png](cues/11_4E.png)
![11_4E_wide.png](cues/11_4E_wide.png)

### 12. Cue 4F: The Figures: $500 billion
Talk triangles 156,654, draw calls 65, real-time lights 2 (held pose).

![12_4F.png](cues/12_4F.png)
![12_4F_wide.png](cues/12_4F_wide.png)

### 13. Cue 4G: The Figures: 2 trillion yuan
Talk triangles 162,104, draw calls 85, real-time lights 2 (held pose).

![13_4G.png](cues/13_4G.png)
![13_4G_wide.png](cues/13_4G_wide.png)

### 14. Cue 5: Inside the Buildout
Talk triangles 146,498, draw calls 31, real-time lights 5 (held pose).
The front racks part; the curved screen rises; clip 01 plays (5B to 5F step through 02 to 06).

![14_5.png](cues/14_5.png)
![14_5_wide.png](cues/14_5_wide.png)
![14_5_t02.5.png](motion/14_5_t02.5.png)

### 15. Cue 5B: Ashburn
Talk triangles 146,498, draw calls 31, real-time lights 5 (held pose).

![15_5B.png](cues/15_5B.png)
![15_5B_wide.png](cues/15_5B_wide.png)

### 16. Cue 5C: Richland Parish
Talk triangles 146,498, draw calls 31, real-time lights 5 (held pose).

![16_5C.png](cues/16_5C.png)
![16_5C_wide.png](cues/16_5C_wide.png)

### 17. Cue 5D: Africa at Night
Talk triangles 146,498, draw calls 31, real-time lights 5 (held pose).

![17_5D.png](cues/17_5D.png)
![17_5D_wide.png](cues/17_5D_wide.png)

### 18. Cue 5E: Cables in the Red Sea
Talk triangles 146,498, draw calls 31, real-time lights 5 (held pose).

![18_5E.png](cues/18_5E.png)
![18_5E_wide.png](cues/18_5E_wide.png)

### 19. Cue 5F: Outlets Around the Globe
Talk triangles 146,498, draw calls 31, real-time lights 5 (held pose).

![19_5F.png](cues/19_5F.png)
![19_5F_wide.png](cues/19_5F_wide.png)

### 20. Cue 6: Who Pays
Talk triangles 152,126, draw calls 32, real-time lights 2 (held pose).
The bill unrolls from the top of the dome; its odometer climbs (no faster than 3 steps a second) to $333.44, then 'per megawatt-day'.

![20_6.png](cues/20_6.png)
![20_6_wide.png](cues/20_6_wide.png)
![20_6_t03.0.png](motion/20_6_t03.0.png)
![20_6_t06.0.png](motion/20_6_t06.0.png)

### 21. Cue 6B: Water
Talk triangles 180,386, draw calls 35, real-time lights 2 (held pose).

![21_6B.png](cues/21_6B.png)
![21_6B_wide.png](cues/21_6B_wide.png)
![21_6B_t03.0.png](motion/21_6B_t03.0.png)
![21_6B_t09.0.png](motion/21_6B_t09.0.png)

### 22. Cue 7: Trust
Talk triangles 164,424, draw calls 41, real-time lights 3 (held pose).
The locked rack (tape reels behind glass, padlock lit) drifts in to 10 m from the front row, flanked by two racks.

![22_7.png](cues/22_7.png)
![22_7_wide.png](cues/22_7_wide.png)
![22_7_t08.0.png](motion/22_7_t08.0.png)

### 23. Cue 8: Terms Already Attached: Ohio
Talk triangles 165,048, draw calls 43, real-time lights 3 (held pose).

![23_8.png](cues/23_8.png)
![23_8_wide.png](cues/23_8_wide.png)
![23_8_t01.4.png](motion/23_8_t01.4.png)
![23_8_t02.4.png](motion/23_8_t02.4.png)

### 24. Cue 8B: Terms: European Union
Talk triangles 167,106, draw calls 46, real-time lights 3 (held pose).

![24_8B.png](cues/24_8B.png)
![24_8B_wide.png](cues/24_8B_wide.png)

### 25. Cue 8C: Terms: Singapore
Talk triangles 169,124, draw calls 48, real-time lights 3 (held pose).

![25_8C.png](cues/25_8C.png)
![25_8C_wide.png](cues/25_8C_wide.png)

### 26. Cue 9: A Public Commons
Talk triangles 178,516, draw calls 39, real-time lights 5 (held pose).
Racks open their doors front to back; the white room gives way to dusk; the four commons halls rise; beams of light arc from the racks to them.

![26_9.png](cues/26_9.png)
![26_9_wide.png](cues/26_9_wide.png)
![26_9_t01.5.png](motion/26_9_t01.5.png)
![26_9_t04.0.png](motion/26_9_t04.0.png)
![26_9_t07.0.png](motion/26_9_t07.0.png)

### 27. Cue 9B: Devices at Every Doorway
Talk triangles 194,324, draw calls 44, real-time lights 5 (held pose).

![27_9B.png](cues/27_9B.png)
![27_9B_wide.png](cues/27_9B_wide.png)
![27_9B_t01.5.png](motion/27_9B_t01.5.png)

### 28. Cue 10: So Who Will?
Talk triangles 196,822, draw calls 51, real-time lights 9 (held pose).
The halls glow brighter; 'So who will?' returns.

![28_10.png](cues/28_10.png)
![28_10_wide.png](cues/28_10_wide.png)
![28_10_t02.0.png](motion/28_10_t02.0.png)

### 29. Cue 11: Quest Capture 1 (spare)
Talk triangles 198,086, draw calls 55, real-time lights 12 (held pose).

![29_11.png](cues/29_11.png)
![29_11_wide.png](cues/29_11_wide.png)

### 30. Cue 11B: Quest Capture 2 (spare)
Talk triangles 198,086, draw calls 55, real-time lights 12 (held pose).

![30_11B.png](cues/30_11B.png)
![30_11B_wide.png](cues/30_11B_wide.png)

