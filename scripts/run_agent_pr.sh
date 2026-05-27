#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/run_agent_pr.sh <task_id> <slug> <task_json> <prompt_file>

Example:
  scripts/run_agent_pr.sh 005 readme-update .agent/tasks/005-readme-update.json .agent/prompts/005-readme-update.md
USAGE
}

die() {
  echo "ERROR: $*" >&2
  exit 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

[[ $# -eq 4 ]] || {
  usage
  exit 2
}

TASK_ID="$1"
SLUG="$2"
TASK_JSON="$3"
PROMPT_FILE="$4"

BRANCH="agent/${TASK_ID}-${SLUG}"
IMAGE="opencode-deepseek-agent:local"

need_cmd git
need_cmd docker
need_cmd python3
need_cmd gh

[[ -n "${DEEPSEEK_API_KEY:-}" ]] || die "DEEPSEEK_API_KEY is not set"
[[ -f "$TASK_JSON" ]] || die "Task JSON not found: $TASK_JSON"
[[ -f "$PROMPT_FILE" ]] || die "Prompt file not found: $PROMPT_FILE"

CURRENT_BRANCH="$(git branch --show-current)"
[[ -n "$CURRENT_BRANCH" ]] || die "Not on a named git branch"

echo "Current branch: $CURRENT_BRANCH"

if [[ "$CURRENT_BRANCH" == "main" ]]; then
  echo "Updating main..."
  git pull --ff-only

  if git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
    die "Local branch already exists: ${BRANCH}"
  fi

  echo "Creating branch: ${BRANCH}"
  git switch -c "$BRANCH"
elif [[ "$CURRENT_BRANCH" == "$BRANCH" ]]; then
  echo "Continuing on existing branch: ${BRANCH}"
else
  die "Current branch must be main or ${BRANCH}; got ${CURRENT_BRANCH}"
fi

echo
echo "Pre-run status:"
git status --short

echo
echo "Starting OpenCode container..."
echo "When OpenCode opens, use the prompt printed below."
echo

docker run --rm -it \
  --name opencode-agent \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp/agent-home \
  -e DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY}" \
  -e TASK_JSON="${TASK_JSON}" \
  -e PROMPT_FILE="${PROMPT_FILE}" \
  -v "$PWD:/workspace" \
  -w /workspace \
  "${IMAGE}" \
  bash -lc '
    set -euo pipefail
    mkdir -p "$HOME"

    echo "=== container identity ==="
    id || true

    echo
    echo "=== repository status ==="
    git status
    echo
    git ls-files

    echo
    echo "=== opencode version ==="
    opencode --version

    echo
    echo "=== task contract ==="
    cat "$TASK_JSON"

    echo
    echo "=== prompt to use in OpenCode ==="
    echo "------------------------------------------------------------"
    cat "$PROMPT_FILE"
    echo
    echo "------------------------------------------------------------"
    echo "OpenCode is starting now."
    echo "If it does not consume the prompt automatically, paste the prompt above."
    echo

    opencode
  '

echo
echo "Agent container exited."

echo
echo "Changed files before validation:"
git status --short || true
git diff --name-only || true
git diff --stat || true

echo
echo "Running boundary check with working-tree mode..."
python3 scripts/agent_boundary_check.py --include-working-tree "$TASK_JSON"

echo
echo "Running task validation_commands, if any..."
mapfile -t VALIDATION_COMMANDS < <(
  python3 - "$TASK_JSON" <<'PY'
import json
import sys
from pathlib import Path

task = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for cmd in task.get("validation_commands", []):
    print(cmd)
PY
)

if [[ "${#VALIDATION_COMMANDS[@]}" -eq 0 ]]; then
  echo "No validation_commands in task JSON."
else
  for cmd in "${VALIDATION_COMMANDS[@]}"; do
    echo
    echo "+ ${cmd}"
    bash -lc "$cmd"
  done
fi

echo
echo "Final changed files:"
git status --short
git diff --name-only
git diff --stat

if [[ -z "$(git status --short)" ]]; then
  die "No changes to commit"
fi

echo
echo "Boundary and validations passed."
echo "Type COMMIT to commit, push, and create PR:"
read -r CONFIRM

[[ "$CONFIRM" == "COMMIT" ]] || die "Commit cancelled"

git add -A

COMMIT_MESSAGE="agent ${TASK_ID}: ${SLUG}"
git commit -m "$COMMIT_MESSAGE"

git push -u origin "$BRANCH"

PR_TITLE="agent ${TASK_ID}: ${SLUG}"
PR_BODY_FILE="$(mktemp)"
cat > "$PR_BODY_FILE" <<PRBODY
## What changed
Agent task implementation for ${TASK_ID}-${SLUG}.

## Task contract
\`${TASK_JSON}\`

## Prompt
\`${PROMPT_FILE}\`

## Validation
- \`python3 scripts/agent_boundary_check.py --include-working-tree ${TASK_JSON}\`
$(for cmd in "${VALIDATION_COMMANDS[@]}"; do echo "- \`${cmd}\`"; done)

## Rollback
Revert this PR.

## Boundary
Commit and push are performed by the local runner after boundary validation, not by OpenCode.
PRBODY

echo
echo "Creating PR..."
PR_URL="$(gh pr create --title "$PR_TITLE" --body-file "$PR_BODY_FILE")"
rm -f "$PR_BODY_FILE"

echo
echo "PR created:"
echo "$PR_URL"
