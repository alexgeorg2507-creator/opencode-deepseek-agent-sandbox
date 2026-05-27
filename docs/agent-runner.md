# Local OpenCode Agent PR Runner

## Purpose

`scripts/run_agent_pr.sh` reduces the manual overhead of running task-scoped OpenCode agent work.

It is not a fully autonomous agent platform.

The runner keeps the delivery boundary:

```text
human / ChatGPT defines task contract
OpenCode edits files inside Docker sandbox
local boundary checker validates changed files
local runner commits and pushes only after explicit confirmation
GitHub Actions validates the PR
human reviews and merges
