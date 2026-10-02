# MANAGER.md

![A brass comb between a heap of blank cards and a leather tray of three, with one card left alone.](assets/hero.webp)

*The comb sits between the pile and the three cards worth keeping: the agent sorts, and the manager decides.*

A drop-in operating file for the coding agent an engineering manager already runs (Claude Code, Cursor, Codex, anything that reads `AGENTS.md` or `CLAUDE.md`).

Most "AI executive assistant" prompts describe a persona. This file is a set of rules, and each one comes from a failure that looked fine at the time: a brief that said "all clear" for a check that never ran, an approval quietly attached to code nobody had read, a two-week absence that a calendar view showed as one day.

## Why

The framing comes from Camille Fournier's [*The Manager's Path in the Age of AI*](https://skamille.medium.com/the-managers-path-in-the-age-of-ai-279cb6611d66). An agent is very good at signal processing and should never make the management decision. Visibility is not understanding. Summaries drop the signal that matters. The agent prepares the manager to talk to people. The manager does the talking.

## Use it

1. Copy [`MANAGER.md`](MANAGER.md) into the repo or folder where you run your agent.
2. Reference it from your agent file, for example add `Read and follow MANAGER.md.` to `CLAUDE.md` or `AGENTS.md`.
3. Fill in the **Your context** block: team, sources, frameworks, and any rule overrides by ID.

## How it is organised

- **Stance:** what the agent is for, and what it is not.
- **Guardrails (`G-n`):** hard limits, such as never drafting the people decision and never reporting an unverified check as clear.
- **Operating rules (`R-n`):** defaults for verification, the review queue, calendars, meeting prep, decisions, notes and agent execution. Each is one line with a `*Why:*`.
- **Your context:** the only part you are meant to edit.
- **Output:** a decision-first summary, about ten bullets at most, then a short narrative. Tables come after both. A short reply skips the structure.

A normal reply looks like this:

```markdown
- Decide today: re-request review on [example/repo#1234](https://github.com/example/repo/pull/1234). Your approval predates two later commits.
- Unverified: the absence check did not run.

The approval is still mergeable. The author re-requests and merges.

| Check | State |
| --- | --- |
| Review head | finding |
| Absence span | unverified |
```

Rule IDs are stable, so you can tune a rule with something like `R-12: stalled after three days, not five` without editing the rule.

## Checks

`scripts/check.py` (Python standard library only) runs in CI on every push and every pull request:

- **Format:** the required sections exist, IDs are unique and sequential, every rule has a `*Why:*`, and the file stays small enough to be cheap as context.
- **Leak scan:** emails, phone numbers and common secret token shapes.

The deny-list is a separate check. It stays on your machine, and public CI never receives it. Put your company's names (people, handles, internal repos) in a file outside the repo and run:

```sh
python3 scripts/check.py --denylist ~/.config/manager-md/denylist.txt --require-denylist
```

Terms match as whole words and case-sensitively. A hit prints the term's index, never the term. `--require-denylist` fails the run when the list is missing or empty.

The hook that runs this is local to your clone. Cloning the repo does not install it, so a listed name can still be committed until you add it. Create both `.git/hooks/pre-commit` and `.git/hooks/pre-push` with:

```sh
#!/bin/sh
python3 scripts/check.py --denylist ~/.config/manager-md/denylist.txt --require-denylist
```

Then `chmod +x .git/hooks/pre-commit .git/hooks/pre-push`.

Tests: `python3 -m unittest discover -s tests`.

## Contributing

A good rule is one line, states the behaviour, and has a `*Why:*` naming the failure it prevents. It should still be true at a company you have never worked at. Leave out the incident that taught it to you, or describe it with no identifying detail. Names of people, companies and internal repos belong in **Your context** and in the local deny-list. The checker caps `MANAGER.md` at 300 lines and 4000 words.

## License

[MIT](LICENSE)
