# Git Push in Cron Jobs

> Notes on running `git push` from Hermes cron jobs on Windows/VM.

## The Problem

Git Credential Manager (GCM) in `manager` mode opens an interactive popup window.
In a headless cron job this **blocks forever** — the push never completes, no error is shown.

Symptoms:
- `git push` hangs silently in background cron sessions
- `proc_*` stays alive for minutes until Hermes kills it
- `credential.helperselector.selected=manager` in `git config --global --list`

## The Fix

Before any cron job that calls `git push`:

```bash
git config --global credential.helper "manager-core"
git config --global credential.helper "cache --timeout=28800"
```

`manager-core` is the headless backend — no popup, no blocking.

## Verification

```bash
git config --global credential.helper   # must return: manager-core
git ls-remote https://github.com/omybx/Agnes-AI-Journal.git HEAD
# If this returns a SHA without prompting, credentials are good
```

## Token Location

PAT хранится в `~/.github_token` (не в репозитории).

GCM запоминает его в Windows Credential Manager после первого успешного ввода.
