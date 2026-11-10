# Talk performance, per cue (Unity editor count of what is switched on)

Measured 2026-11-08 17:39 by SphererebroTalkShots (Unity editor, held pose of each cue).
Triangles and draw calls are the TALK's active renderers (each submesh = one draw call; the SRP batcher makes repeats cheap).
The world's own geometry visible from the seats adds about 104,276 triangles and 279 draw calls (seating, stage, sphere, all switched-on renderers; before frustum culling). Budget (Quest): < 300,000 visible triangles, < 150 draw calls.
Frame rate cannot be measured in the editor; see review/REVIEW.md for the browser harness and what needs a headset.

| # | Cue | Name | Talk triangles | Draw calls | Lights | Over budget? |
|---|---|---|---:|---:|---:|---|
| 1 | 1 | So Who Will? | 23,692 | 6 | 0 | no |
| 2 | 2 | A Hundred Years of Public Media | 13,028 | 8 | 4 | no |
| 3 | 2B | Television | 20,468 | 14 | 5 | no |
| 4 | 2C | The Web | 24,026 | 19 | 6 | no |
| 5 | 2T | 200 Years of Media | 24,678 | 24 | 6 | no |
| 6 | 3 | The Commercial Turn | 45,810 | 43 | 6 | no |
| 7 | 4 | The Construct | 2,208 | 3 | 2 | no |
| 8 | 4B | Lots of Data Centers | 145,234 | 27 | 2 | no |
| 9 | 4C | The Figures: 415 TWh | 150,640 | 48 | 2 | no |
| 10 | 4D | The Figures: 945 TWh | 151,984 | 49 | 2 | no |
| 11 | 4E | The Figures: $500 billion | 150,944 | 46 | 2 | no |
| 12 | 4F | The Figures: $500 billion | 156,654 | 65 | 2 | no |
| 13 | 4G | The Figures: 2 trillion yuan | 162,104 | 85 | 2 | no |
| 14 | 5 | Inside the Buildout | 146,498 | 31 | 5 | no |
| 15 | 5B | Ashburn | 146,498 | 31 | 5 | no |
| 16 | 5C | Richland Parish | 146,498 | 31 | 5 | no |
| 17 | 5D | Africa at Night | 146,498 | 31 | 5 | no |
| 18 | 5E | Cables in the Red Sea | 146,498 | 31 | 5 | no |
| 19 | 5F | Outlets Around the Globe | 146,498 | 31 | 5 | no |
| 20 | 6 | Who Pays | 152,126 | 32 | 2 | no |
| 21 | 6B | Water | 180,386 | 35 | 2 | no |
| 22 | 7 | Trust | 164,424 | 41 | 3 | no |
| 23 | 8 | Terms Already Attached: Ohio | 165,048 | 43 | 3 | no |
| 24 | 8B | Terms: European Union | 167,106 | 46 | 3 | no |
| 25 | 8C | Terms: Singapore | 169,124 | 48 | 3 | no |
| 26 | 9 | A Public Commons | 178,516 | 39 | 5 | no |
| 27 | 9B | Devices at Every Doorway | 194,324 | 44 | 5 | no |
| 28 | 10 | So Who Will? | 196,822 | 51 | 9 | no |
| 29 | 11 | Quest Capture 1 (spare) | 198,086 | 55 | 12 | no |
| 30 | 11B | Quest Capture 2 (spare) | 198,086 | 55 | 12 | no |
