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
- **Guardrails (`G-n`):** hard limits, such as never drafting the people decision and never reporting an unverified check as clear. G-1 and G-2 hold against an explicit instruction. Any other guardrail yields only to a case-specific instruction in the conversation, and an operating rule yields to the host agent file.
- **Operating rules (`R-n`):** defaults for verification, the review queue, calendars, meeting prep, decisions, notes and agent execution. Each rule line has a `*Why:*`. R-23 adds its branches under that line.
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

Rule IDs are stable from this revision on. The map below is the one break. Tune a rule with something like `R-12: stalled after three days, not five` without editing the rule.

## ID changes in this revision

A "was" number is the rule before this revision. A "now" number is the current rule. Delete an override for a removed rule before you retarget the ones that moved.

- Was R-21 (push toward the human): removed. The behaviour stays in the Stance paragraph of `MANAGER.md`. Delete any override of that rule.
- Was R-22 (relational messages): now R-21.
- Now R-22 (resolve a speaker by attendees and topic). This number used to mean relational messages.
- R-23 and R-24 keep their numbers. The text of R-23 is rewritten.
- Now R-25 (change the answer for a fact, not for pushback). This number used to mean after two failed raises.
- Were R-25 through R-31: now R-26 through R-32.
- Were R-32 (judge on exit codes) and R-33 (match whole words): removed. Those checks are part of the corrections rule.
- Was R-34 (turn corrections into checks): now R-33.
- Added: G-11. G-1 through G-10 keep their numbers. The text of G-2 grew.

## Checks

`scripts/check.py` (Python standard library only) runs in CI on every push and every pull request:

- **Format:** the required sections exist, IDs are unique and sequential, every rule has a `*Why:*`, and the file stays small enough to be cheap as context.
- **Dashes:** em dashes and en dashes are rejected in `MANAGER.md`, this README, and the eval cases.
- **Live IDs:** every `G-n` or `R-n` cited in `MANAGER.md`, and in this README outside the revision map, must name a rule that exists.
- **Eval schema:** each file in `evals/cases/` matches the case schema and cites live rule IDs. The schema check does not grade a reply.
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

## Evals

Cases in `evals/cases/` are a situation plus phrases a correct reply must contain and phrases a violation must not. CI checks that each file matches the schema and cites rules that exist. Nothing in this repo calls a model, so a green check is not behavioural coverage.

## Contributing

A good rule states the behaviour on one line and has a `*Why:*` naming the failure it prevents. A short list under that line is fine when the rule is a set of branches, as R-23 is. It should still be true at a company you have never worked at. Leave out the incident that taught it to you, or describe it with no identifying detail. Names of people, companies and internal repos belong in **Your context** and in the local deny-list. The checker caps `MANAGER.md` at 300 lines and 4000 words.

## License

[MIT](LICENSE)
