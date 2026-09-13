# Production progress

## Shots rendered

| Sequence | Visual | Lipsync |
|---|---|---|
| Scene 0 — opening | 4 / 4 | done |
| Seq 1 — helicopter | 9 / 9 | done |
| Seq 2 — Kinder theft | 10 / 10 | pending |
| Seq 3 — police car | 11 / 11 | pending |
| Seq 5 — ending | 3 rendered, 3 in flight | pending |

Dialogue is generated for every shot in the film, including all eight French moments.

## Sound effects

Helicopter rotor · police radio (beep, squelch, static, chatter) · megaphone feedback + wind ·
Kinder wrapper + crunch. Clips run 1–2 s with loop off, so continuous beds are looped in the edit.

## Lessons that changed how shots are built

**Every shot with Michel must carry his Reference Element.** Shot 3L was written with a verbal
description instead — "a man in navy police uniform" — to save cost on the cheaper model, and the
model invented a different face. It was re-rendered with the element. There is no shortcut: a
described Michel is not Michel.

**Pauses are split, not prompted.** A line that needs a beat becomes two files with the silence
placed in the edit, and the held shot is lipsynced with `sync_mode: silence` so the wait is not
retimed away.

**Concurrency has two ceilings.** ElevenLabs allows 3 parallel generations; a fourth fails and is
still charged. Higgsfield returns 429 when too many renders are queued, and separately reserves
credits for in-flight jobs — so a submission can be refused for "no credits" while the balance
still reads several hundred. Submit in waves.

**The preset recommender intercepts submissions.** Several shots came back as a preset suggestion
instead of a job; they need `declined_preset_id` on resubmit.

## Remaining

1. Finish the three closing shots
2. Lipsync pass across Sequences 2, 3 and 5
3. Sequence 4 (teamwork) — one VO shot, montage rebuilt from existing footage
4. Post: megaphone and PA processing, CCTV timestamp, the `לא ללחוץ` label, callout graphics,
   subtitles, five-stem mix
