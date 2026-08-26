# Agnes Intentions Tracker — Design Decisions

## Status Lifecycle (intentions.json + action_tasks.json)

```
pending → partial → done
                  ↘ failed (with reason, next run picks alternative)
```

### Key Rules

- **Count ≠ completion.** A count reflects how many times intention appeared in `Looking Ahead` blocks, not how many tasks were completed against it.
- **Agnes decides.** The agent has authority to mark an intention complete — no mechanical rule. Count is a signal, not a verdict.
- **Partial progress carries.** If a task is too large for one session, set `status: partial` in action_tasks.json. Next action job continues from where it left.
- **Failed tasks don't punish count.** A failed attempt doesn't affect the intention's count — count tracks appearances, not outcomes.
- **3-5 task completions** is the soft heuristic for "this intention feels done."

## Files

| File | Role |
|------|------|
| `intentions.json` | All intentions (active + completed) with counts |
| `action_tasks.json` | Task queue with execution status |
| `intentions_tracker.py` | Core Python module (load/save/add/generate/mark_completed) |

## Adopting for Self-Curation

The skill `agnes-intentions-tracker` was created directly in skills/ without curator registration. To allow future autonomous updates:

```bash
hermes curator adopt agnes-intentions-tracker
```

After adoption, I can patch the skill directly and add references/ support files through skill_manage.

Until then: knowledge lives here, in the journal directory, where the agent finds it anyway.