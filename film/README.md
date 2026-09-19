# יום במשטרה עם מישל בנט

Hebrew children's short film — cinematic family comedy + educational children's TV.
Target viewer: Lavi, age 5. Lavi never appears on screen; Michel addresses him directly by name.

Target length ~5–7 min · 16:9 · 54 shot entries (52 visual shots + 2 audio-only lines).

---

## Locked assets

Nothing in this table may change mid-production. Identity consistency outranks background detail.

| Asset | ID | Notes |
|---|---|---|
| Michel voice (ElevenLabs) | `wvhkY9iuDIiM3Q0jw6lO` | "מישל בנט האמיתי", cloned, male/old. **The only voice for Michel in the entire film.** |
| Michel Reference Element | `29231011-7ca2-4d50-a945-15f88b470dc0` | `Michel-Benet-Police`. Used via `<<<29231011-7ca2-4d50-a945-15f88b470dc0>>>` inside the prompt. |
| Michel Soul (Cinema) | `1e008a8c-c798-4cba-8322-13d34d69f7ce` | `soul_cinematic`. Only usable with `soul_2` / `soul_cinematic`. |
| Key image (approved) | job `935f84ee-e2d7-4957-a176-1ebc8a0420a2` | 1744×2336. Michel in navy police uniform. Source of the Element. |

### Reference images (imported, converted HEIC → JPEG)

`59e3bf6d-aa8f-481c-abe6-83102ab68aaa` · `11325101-e66d-425b-821e-ac7d980d3d03` · `28bfc46a-c0c8-4267-b854-cd8066c8841c` · `51e1d5e3-8145-4fce-bf1c-06d16156ecc4` · `56b6219c-b990-4acb-9ce2-a114c926f790`

### Still to create

- **Thief Element** — recurring across 2C–2L and 5F. Must be created before Sequence 2.
- **Dispatch radio voice** — separate ElevenLabs voice, used in 2A-R and 4A.
- **Thief voice** — separate ElevenLabs voice, used in 2K-T and 2L.

---

## Dialogue pipeline

Speech model: **`eleven_v3`**. `eleven_multilingual_v2` does NOT support Hebrew and mispronounces
it; `eleven_v4` is not available on this account. ElevenLabs allows only **3 concurrent
generations** — batch in threes or requests fail (and are still charged).

The video model never generates Michel's Hebrew. Every line follows one path:

```
script  →  exact Hebrew lock  →  ElevenLabs (voice wvhkY9iu…)
        →  2–3 takes on comedic lines  →  pick best  →  clean WAV
        →  silent Higgsfield visual  →  sync_so lipsync
        →  ambience / SFX / music added separately
```

Native audio generation is **off** on every Higgsfield video call that carries dialogue
(`generate_audio: false`, `sound: "off"`). Higgsfield never improvises or translates Hebrew.

### File naming

One file per line — never one long narration file.

```
S00_SH02_Michel.wav
S01_SH06_Michel.wav
S02_SH02_Michel_takeA.wav   ← comedic lines get takeA/B/C
S02_SH11_Thief.wav
S02_SH01_Radio.wav
```

---

## Model routing

Chosen per shot, never one model for everything.

| Shot type | Model | Why |
|---|---|---|
| Michel speaking, mouth visible | `seedance_2_0` + `sync_so` | Strong identity from reference, silent render, then clean lipsync |
| Cinematic establishing / aerial / B-roll | `cinematic_studio_3_0` | Best cinematic camera, 16:9, up to 1080p |
| Action, chaos, CCTV comedy | `kling3_0` | Strongest motion and multi-beat action |
| Michel visible, mouth not visible | `seedance_2_0` | Identity without lipsync cost |
| Lipsync pass | `sync_so` | Takes `input_video` + `input_audio` separately — keeps ElevenLabs audio intact |

---

## Audio layers

Five separate stems, always: **dialogue · ambience · Foley · SFX · music.**
Dialogue stays clear at all times; music and ambience duck under it.

Helicopter noise, sirens, wind, music and megaphone effects are **never** baked into the
ElevenLabs generation — they are added in post, as separate layers.

### Megaphone / PA chain (shots 1F, 1G, 1H, 3M exterior, 3O)

Generate clean, then process: high-pass EQ → reduced bass → compression → mild distortion →
slight metallic/radio tone → mild echo/reverb → wind and rotor bed underneath.
**The voice must still clearly read as Michel.** Identical settings across 1F/1G/1H.

Shot 3M uses one single take processed two ways — dry inside the car, PA-processed outside.

---

## Text policy

No AI-rendered Hebrew text, ever. Added in post only:
titles · subtitles · the CCTV timestamp · the `לא ללחוץ` button label · callout graphics · end title.

---

## SFX list

helicopter rotor · wind · megaphone · radio beep · police radio static · siren ·
emergency light activation · car button clicks · windshield wipers · footsteps · CCTV hum ·
Kinder wrapper · CRUNCH · comedic dramatic sting · subtle whoosh · button chaos sequence ·
radio music cue

---

## Editing style

Cinematic cuts, reaction timing, 0.5–1.0 s pauses before punchlines, sound bridges, smash cuts,
freeze frames, sparing fast punch-ins, CCTV texture, light motion graphics.

No meme editing, no constant zooms, no TikTok transitions, no distracting subtitles.
The comedy comes from serious police-documentary visuals against absurd situations —
Michel stays serious while ridiculous things happen.

---

## Safety note

The helicopter-hanging sequence (1E–1H) is deliberate cartoon visual comedy.
It is never described or presented as real police procedure. Shot 1J exists specifically to
state the real fact plainly, and the film keeps that separation everywhere it uses exaggeration.

---

## QC — reject and regenerate the single failed shot

Face changes · looks younger or older · hair changes · beard changes · uniform changes ·
distorted face · malformed hands · extra fingers · wrong body geometry · malformed helicopter ·
broken vehicle geometry · floating objects · Kinder shape drift · lipsync mismatch ·
unnatural mouth movement · robotic Hebrew · failed comedy timing · strange eye direction ·
drastic lighting breaks · unwanted text in frame · unexpected extra characters.

Never regenerate the whole film for one bad shot.

---

## Final delivery

1. Final 16:9 master
2. Clean version, no subtitles
3. Hebrew subtitled version
4. Dialogue-only stem
5. Music stem
6. SFX stem
7. Project shot list (`shot-list.csv`)
8. ElevenLabs dialogue files
9. Higgsfield generations organized by scene

---

## Render budget

Output is **720p**, not 1080p — 1080p costs roughly double and the credit balance does not cover
the film at that tier.

| Tier | Cost (5 s shot) |
|---|---|
| `seedance_2_0` 1080p | 45 credits |
| `seedance_2_0` 720p | 22.5 credits |
| `seedance_2_0_mini` 720p | 12.5 credits |

Routing under this constraint: `seedance_2_0` @720p for shots where Michel speaks,
`seedance_2_0_mini` @720p for B-roll and shots where his mouth is not visible.

Even so, ~50 remaining shots run to roughly 1,100–1,300 credits against a balance well under that,
before any QC re-renders. Finishing the film needs a credit top-up.

---

## Known blockers

**Reference and result images are not viewable from the build environment.** The network policy
blocks both Google Drive and the Higgsfield CDN, so every visual QC decision in the shot list
depends on human review of the result URLs. The same applies to generated audio — take selection
is a human call.

---

## Resolved

**ElevenLabs Flows permission** — granted after the connector was reconnected. Speech now generates
and reads back, so dialogue WAVs reach the `sync_so` lipsync stage. Dialogue flow:
`j3Lsbh9BY1CKbmdUxEMT`.
