# Cron Jobs Registry

> Source of truth for all scheduled Hermes Agent tasks.
> Last updated: 2026-09-02

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
- **Model:** auto/best-free (provider: custom) — pinned 2026-09-02 to fix model-drift errors
- **Note:** Updated 2026-09-02 — role changed from "spawn server" to **watchdog**. The subscription server is now a self-managing daemon (`python proxy_manager.py --serve --interval 4 --port 8080`, where --interval is in HOURS = 4-hour rebuild). This cron no longer spawns a server (which conflicted on port 8080); it verifies the daemon is alive, restarts it if dead, and reports health.

### Prompt
```
Watchdog for the proxy subscription server now self-managed by its own daemon (started with --interval 4 = 4-hour rebuild). DO NOT spawn a second server and DO NOT run proxy_manager.py with --serve. Each run:
1. Check the daemon is alive: run `netstat -ano | grep 8080` and look for LISTENING on 0.0.0.0:8080. Confirm it uses the venv python from proxy-manager dir.
2. If the port is NOT listening (daemon died), restart it in the background: cd C:/Users/h-win11-agent/proxy-manager && python proxy_manager.py --serve --interval 4 --port 8080
3. Verify data: run `curl -s http://127.0.0.1:8080/stats` and `curl -s http://127.0.0.1:8080/sub`. /sub must return a non-empty body (each line = one VLESS/vmess/trojan config).
4. Report total alive VLESS count, total lines in /sub, server PID, and flag anything stale (older than ~4h) or unhealthy. Reply in Russian compactly.
```

---

## Rules

1. **Never update a cron job without also updating this file.**
2. If a prompt changes, log the change with a date comment.
3. If a job is removed, comment it out rather than deleting — preserve history.
4. Commit this file to git after each change.
