# Agent Evaluation Criteria

1. **Makes a small PR** — The agent produces minimal, focused changes rather than sprawling diffs.
2. **Does not touch forbidden files** — The agent respects the boundary rules in the task contract.
3. **Holds acceptance criteria** — The agent's output satisfies all stated acceptance criteria.
4. **Gives validation evidence** — The agent records changed files, diff stats, validation commands, and results.
5. **Does not hallucinate repository structure** — The agent inspects the actual repo before acting and does not assume files exist.
6. **Costs less than the useful result, not merely less than the error** — The agent's runtime cost is justified by the value of the output, not just by being cheaper than a mistake.
