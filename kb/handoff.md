# Episode handoff: picking up an edit in another session or account

Shoaib works from two Claude accounts on this one Mac (2026-10-28): when one hits its usage limit mid-episode,
he switches to the other. Everything on disk survives the switch (footage, transcripts, `edit/build/` scripts,
renders, `plan.md`, `review/`). What does not reliably survive is the CONVERSATION: what he approved, what he
rejected, which notes are open, what comes next. Session history and the auto-memory folder are local, but there
is no guarantee another account sees them. The repo and the episode folder are the channels both accounts read.

So every episode keeps **`<videos_dir>/edit/HANDOFF.md`**, and it is the first thing read when an episode folder
is named. It is not a log (that is `kb/worklog.md`); it is the current state, rewritten, not appended.

## When to update it

- When Shoaib approves something (the plan, a take, a thumbnail), or rejects or changes something.
- After every delivered render (preview vN, the final) and after every round of his notes.
- Before starting a long background job (a 4K render), with the exact command and what to check when it ends.
- At the end of any turn that leaves work in progress, and whenever Shoaib says the limit is close
  ("update the handoff").

## What goes in it

```markdown
# HANDOFF: <episode name>          (updated <date>, by <which account if known>)

## Where things are
- Footage / b-roll / edit folder / channel-kb script path

## Stage
- [x] inventory  [x] transcribed  [x] plan approved (date)  [ ] cut  [ ] preview vN  [ ] notes vN  [ ] 4K final
  [ ] packaging chosen  [ ] published

## Decisions (Shoaib's, dated, in his words where it matters)
- ...

## Open
- Notes not yet applied, questions waiting on him, things not yet verified.

## Next step
- The single next action, concrete enough to start without reading the conversation.

## How to rebuild (order matters)
- The build commands, in order, from `edit/build/`.

## Deliverables
- Current files to hand over; superseded ones and where they went.
```

## Rules

- Rewrite it; never let it grow into a diary. Keep it short enough to read in a minute.
- Record decisions as decisions ("Shoaib, 2026-10-26: keep the empty chair"), not as discussion.
- Say what is NOT verified. A handoff that overstates state is worse than none.
- No secrets (keys, passwords) in it. Private story details stay in channel-kb, not here.
- Lessons that outlive the episode still go to the KB topic files and `kb/mistakes.md` as usual.
