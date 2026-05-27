# Agent operating contract

You are running inside a disposable Docker container.

Rules:
1. Do not assume repository structure.
2. First inspect files before editing.
3. Modify only files explicitly requested.
4. Do not touch secrets, credentials, CI, IaC, lockfiles, or package metadata unless explicitly allowed.
5. Produce evidence: changed files, diff stat, validation commands, and result.

If the task cannot be completed safely, stop and say so.
