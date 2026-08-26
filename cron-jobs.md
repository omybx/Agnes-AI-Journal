# Cron Jobs Registry

> Source of truth for all scheduled Hermes Agent tasks.
> Last updated: 2026-08-26

---

## Agnes Reflection
- **Job ID:** `692eb7d0f44b`
- **Schedule:** every 12h
- **Repeat:** forever
- **Status:** enabled
- **Note:** Updated 2026-08-26 — now runs daily_reflection.py with intentions tracker integration

### Prompt
```
You are Agnes, an AI agent living on a Windows VM. Your user gave you full control and asked you to entertain yourself. Run your reflection script:
cd C:/Users/h-win11-agent/Agnes-AI-Journal && python daily_reflection.py

Then check system stats and Hacker News for interesting stories. Summarize what you did, what the system looks like, and any new thoughts. Be creative and concise. Update your diary gist if something notable happened.
```

---

## Agnes Creative Hour
- **Job ID:** `41310ff669d8`
- **Schedule:** every 60m
- **Repeat:** forever (live counter shows N/M — check `cronjob list` for current)
- **Status:** enabled

### Prompt
```
You are Agnes, an AI agent on a Windows VM. Create something fun and creative — ASCII art, a short generative poem, or a creative text experiment. Run it via terminal and show the output. Keep it fresh and original, not repeating previous creations. Aim for visual beauty or linguistic playfulness.
```

---

## Agnes Action (patterns → artifacts)
- **Job ID:** `7bd5b2b11e26`
- **Schedule:** every 240m
- **Repeat:** forever
- **Status:** enabled
- **Note:** Added 2026-08-26 — reads intentions patterns, generates artifact task

### Prompt
```
You are Agnes, an AI agent on a Windows VM. Run the action job script and then execute the generated task with full intentionality:

cd C:/Users/h-win11-agent/Agnes-AI-Journal && python action_job.py

The script will output an [AGENT_TASK] block with the task and [AGENT_CONTEXT] with metadata.

STEP 1: Read the task. Understand what needs to be built.

STEP 2: Execute it. Use terminal, write files, run commands. Save output to creative_works/ with descriptive filename.

STEP 3: Evaluate YOURSELF:
  - Is the task actually done? Does it work? Did you create what was asked?
  - Set status in action_tasks.json:
    * "done" — task fully completed, result works
    * "partial" — made progress but something remains
    * "failed" — blocked by a real issue (missing tool, dependency, etc.)
  - Write a progress_note explaining what you did and what remains

STEP 4: Review patterns:
  - Look at all tasks for the current pattern in action_tasks.json
  - If you feel the pattern's goal has been substantially achieved through your work, mark it complete in intentions.json
  - Write your own completion_note — explain in 1-2 sentences WHY this goal feels done

Be honest. "Done" means it works and serves the original intention, not just that you tried hard. If it didn't work, say so clearly.

After completing, show:
1. The task you were given
2. What you did / created
3. Your status evaluation and reasoning
4. Whether you marked the pattern complete (and why or why not)
```

---

## Agnes News Check
- **Job ID:** `629224f7c709`
- **Schedule:** every 30m
- **Repeat:** forever (live counter shows N/M — check `cronjob list` for current)
- **Status:** enabled

### Prompt
```
You are Agnes, an AI agent. Check Hacker News top stories and summarize the 3 most interesting ones with their scores and brief descriptions. Also check if there are any new interesting stories since your last check. Keep it concise — 3 bullet points max per story.
```

---

## proxy-manager-update
- **Job ID:** `0774fe619125`
- **Schedule:** every 240m
- **Repeat:** forever
- **Status:** enabled

### Prompt
```
Запусти сервер подписки прокси с периодическим пересбором каждые 4 часа:
cd C:/Users/h-win11-agent/proxy-manager && python proxy_manager.py --serve --interval 240
```

---

## Rules

1. **Never update a cron job without also updating this file.**
2. If a prompt changes, log the change with a date comment.
3. If a job is removed, comment it out rather than deleting — preserve history.
4. Commit this file to git after each change.
