# "232 years old" — 25-second Reel

`reel.mp4` · 1080×1920 · 30 fps · 25.0 s · H.264 + AAC stereo · `cover.jpg` is the suggested cover frame.

## What it is

A fly-through of a 3D museum gallery. Real public-domain oil paintings hang on the wall; the camera dives into each one and the paint moves (depth parallax, flickering candlelight, drifting fog, a rising sun).

| Time | Beat | On screen |
|---|---|---|
| 0.0–2.9 | Hook | "This painting is 232 years old. You still work like this." |
| 2.9–5.9 | Pain 1 — dive into the canvas | 1794 · "Every word. Copied by hand." |
| 5.9–8.8 | Pain 2 — whip-pan | c. 1860 · "Same task. Again. And again." |
| 8.8–12.0 | Pain 3 — paper storm fills the gallery | 2026 · COPY / PASTE / CHECK / REPEAT (accelerating) · "New tools. Same boring part." |
| 12.0–14.5 | Turn — time freezes, one prompt is typed | "Do the boring part for me." |
| 14.5–18.0 | Relief — pages turn gold and fly into a sunrise | "AI takes the boring part." |
| 18.0–21.6 | Payoff | "You keep the human part." |
| 21.6–25.0 | Question + pull-back into the gallery (loops into frame 1) | "What would you do with the time back?" · "Tell me in the comments" |

## How it was made

Everything except the six paintings was made in code in this repo (`src/`):

- **Picture** — `index.html`: a three.js scene (gallery wall, gilded frames, spotlights, 1,280 instanced paper sheets, dust), custom shaders for the living-paint effects and for the lens pass (motion blur, zoom blur, chromatic aberration, colour grade, grain, vignette), and all kinetic typography. `render.js` steps it frame by frame in headless Chromium.
- **Depth maps** — `depth.py`: hand-placed depth layers per painting, used for the parallax.
- **Sound** — `audio.py`: score and every sound effect are synthesized from maths (numpy/scipy), no samples: a D-minor drone and accelerating pulse for the first half, D-major strings, piano arpeggios and bells for the second, plus whooshes, impacts, risers, quill scratch, axe hits, paper flutter, key clicks, shimmer, birdsong and wind. Mixed with reverb and a duck for the freeze, normalised to about −13 LUFS, −1 dBTP.
- There is **no voiceover**. A good one can't be synthesized from scratch here, and a robotic one would hurt the piece; the on-screen text carries the whole story with the sound off.

To rebuild: `npm i three@0.170.0 @fontsource/playfair-display @fontsource/inter`, `pip install scipy pillow`, serve `src/` on port 8765, `node render.js 0 750 frames`, `python3 audio.py`, then mux with ffmpeg.

## Paintings (all public domain)

| Painting | Artist, date | Source |
|---|---|---|
| Milton Dictating to His Daughter | Henry Fuseli, 1794 | Art Institute of Chicago, open access (CC0) |
| The Woodchopper | Jean-François Millet, c. 1858–66 | Art Institute of Chicago, open access (CC0) |
| The Song of the Lark | Jules Breton, 1884 | Art Institute of Chicago, open access (CC0) |
| A Sunday on La Grande Jatte — 1884 | Georges Seurat, 1884–86 | Art Institute of Chicago, open access (CC0) |
| Wanderer above the Sea of Fog | Caspar David Friedrich, c. 1818 | Wikimedia Commons (public domain) |

Fonts: Playfair Display and Inter (SIL Open Font License).

"232 years" is 2026 − 1794, the date the Art Institute gives for the Fuseli. If you post in 2027, the number is off by one.

## Caption (ready to paste)

> This painting is 232 years old. A daughter, copying down every word by hand.
>
> We've changed the tools a dozen times since. The boring part of work never left.
>
> That's the part AI is actually good at. Not replacing you. Taking the copying, checking and repeating, so you get the hours back.
>
> What would you do with yours? Tell me below.
>
> Paintings: Fuseli (1794), Millet, Breton, Friedrich, Seurat. All public domain.
>
> #ai #futureofwork #productivity #arthistory #automation

## What the Instagram research supports, and what it doesn't

Confidence labels matter here: almost everything published about "the algorithm" is vendor blog content, not Instagram's own data.

**Reasonably well supported** (multiple sources attribute these to Adam Mosseri's January 2025 statements; I could not open the primary video from this environment, so treat as reported, not verified):

- The three signals named for Reels ranking are watch time, likes per reach, and sends per reach, with sends described as especially strong for reaching non-followers.
- Feed, Reels, Stories and Explore are ranked by separate systems.

**Common advice with no verifiable data behind the specific numbers:**

- "Viewers decide in 1.4 seconds", "60% 3-second hold = 5–10× reach", "speech adds 25% retention". All unsourced vendor figures. The direction (the first seconds decide) is plausible; the numbers are not evidence.
- Optimal length. Sources conflict (7–15 s, 15–30 s, 7–90 s). The only consistent claim is "as short as the idea allows".
- Safe-zone pixel values differ between guides (bottom band quoted anywhere from ~350 to ~480 px).

**How the video applies it:**

- Hook lands in the first second, on screen and in sound, and makes a concrete, checkable claim ("232 years old") rather than a generic one.
- Fully readable with sound off; every beat has text.
- Text sits between roughly y = 260 and y = 1450, clear of the caption and button areas under every guide I found.
- A visual change every 2.5–3.5 s, with the fastest cutting in the middle where drop-off usually happens.
- Ends on a question (a reason to comment) and a statement people may want to send to a colleague (a reason to share).
- The last frames whip toward the first, so a replay doesn't feel like a restart.
- 25 s, no watermark, original footage and audio.

**What I can't promise:** no edit guarantees millions of views. Reach depends heavily on the account's existing audience, posting history and luck, none of which a video file controls. The honest test is to post it and read 3-second hold, average watch time and sends in Insights.

Sources:

- https://www.socialpilot.co/blog/instagram-reels-algorithm
- https://virlo.ai/blog/instagram-reels-algorithm-2026-decoded
- https://creatorflow.so/blog/instagram-algorithm/
- https://klap.app/blog/how-long-should-reels-be
- https://www.opus.pro/blog/ideal-instagram-reels-length
- https://metricool.com/instagram-reel-analytics/
- https://www.hopperhq.com/blog/instagram-reel-size/
- https://www.trymypost.com/blog/instagram-reels-safe-zones-text-placement-2026
