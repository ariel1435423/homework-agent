# Locked assets

Nothing here changes mid-production. Identity consistency outranks background detail.

## Reference Elements (Higgsfield)

Used by embedding `<<<id>>>` inside the generation prompt.

| Element | ID | Source |
|---|---|---|
| `Michel-Benet-Police` | `29231011-7ca2-4d50-a945-15f88b470dc0` | Approved key image generated from 5 reference photos |
| `Kinder-Bar` | `f0fa126f-8c0a-4e77-b2d1-92669d02c4f4` | Photo supplied by the user |
| `Thief` | `6065b976-8ff6-4c06-ab8f-52c77bfce149` | Photo supplied by the user |

The Kinder and the Thief are both user-supplied photographs rather than generated characters —
the generated chocolate bar did not read as a real Kinder, and a supplied face locks the thief
across Sequence 2 and the final gag in 5F.

Trained Soul (`soul_cinematic`): `1e008a8c-c798-4cba-8322-13d34d69f7ce`. Usable only with
`soul_2` / `soul_cinematic`, so it is held in reserve for identity-critical close-ups.

## Voice

Michel: `wvhkY9iuDIiM3Q0jw6lO` ("מישל בנט האמיתי"), model `eleven_v3`, both languages.
Dialogue flow: `j3Lsbh9BY1CKbmdUxEMT`.

## Sound effects (ElevenLabs `eleven_text_to_sound_v2`)

Generated clips run 1–2 seconds with loop off, so continuous beds are built by looping in the
edit. That suits rotor and static, which are cyclic anyway, and suits one-shot hits exactly.

- Helicopter rotor
- Police radio: beep, squelch click, static, distant chatter
- Megaphone feedback squeal + heavy wind
- Kinder wrapper crinkle + loud crunch

**The megaphone is not an effect.** It is post-processing applied to Michel's clean voice —
high-pass, reduced bass, compression, mild distortion, metallic tone, slight echo — so he still
reads as himself. Generating a "megaphone sound" would only produce feedback squeal, which is the
layer underneath, not the voice.

## Timing note

Pauses are never left to the speech model. Where the script needs a beat — Michel asking a French
question and waiting for Lavi to answer — the line is generated as two separate files and the
silence is placed in the edit. Shot 1A is built this way: 1A-1 asks and holds, 1A-2 answers.
Lipsync on a held shot uses `sync_mode: silence` so the waiting beat survives instead of being
retimed away.
