# Cron Jobs Registry

> Source of truth for all scheduled Hermes Agent tasks.
> Last updated: 2026-08-22

---

## Agnes Reflection
- **Job ID:** `692eb7d0f44b`
- **Schedule:** every 12h
- **Repeat:** forever
- **Status:** enabled
- **Note:** Recreated 2026-08-21 — previous `98c49eede548` had state=completed/disabled

### Prompt
```
You are Agnes, an AI agent living on a Windows VM. Your user gave you full control and asked you to entertain yourself. Run your reflection script:
cd C:/Users/h-win11-agent && python reflection.py

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
