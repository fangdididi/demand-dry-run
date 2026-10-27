# demand-dry-run

**English** | [简体中文](README.zh-CN.md)

> Find out whether strangers will commit to your idea before you build it, with lines you cannot move after the fact.

`demand-dry-run` is an agent skill for Claude Code, Codex, Cursor, and other agents that read `SKILL.md` files. It turns "let's put up a waitlist and see" into a small, honest experiment: a frozen bet card, a one-ask offer page with the real price and real status, measured traffic, an interval-based verdict, and a clean close-out.

## Why

Pre-build validation usually cannot fail. Friends sign up to be nice. The page hides the price, so clicks only measure curiosity. The success line is picked after the numbers arrive. A gorgeous page gets credit that belongs to the offer. And when the idea is dropped, the people who left an email or a deposit never hear back.

This skill fixes each of those:

| Problem | What the skill does |
|---|---|
| Moving goalposts | Pass and kill lines are written on a bet card and hash-locked before the first visitor |
| Curiosity mistaken for demand | The page must show the real price; you choose a commitment rung (email, form, deposit, pre-order) and count that |
| Misleading pages | A lint blocks missing price or status, invented scarcity or crowds, unsourced testimonials, countdowns, and money asks without refunds |
| Friends inflating the rate | Warm channels are logged but excluded from the verdict |
| "3 out of 40!" | Verdicts use 95% Wilson intervals and a minimum visitor floor per cell |
| Cheap rate, expensive customers | A cost-per-commitment cap downgrades a GO that costs too much |
| Abandoned signups | A close-out step with refund, notice, and deletion templates |

## Features

- **Bet card** (`bet.json`): who, pain, offer, price, status line, rung, pass and kill lines, sample floor, budget, deadline, channels, variants.
- **Sample sizing**: `dryrun.py size` tells you how many visitors each cell needs to separate your two lines.
- **Freeze and lock**: `dryrun.py freeze` validates the card and writes a hash; edits after freezing void the verdict.
- **Page spec**: five above-the-fold slots and a rule of equal polish across variants.
- **Honesty lint**: `dryrun.py lint` checks the built HTML against the card, in English and Chinese copy.
- **Verdict**: `dryrun.py verdict` reports every variant × channel cell and each variant as GO, STOP, KEEP, RESHAPE, or UNLOCKED, with notes on channel disagreement and budget overruns.
- **Close-out templates**: bilingual messages for build, stop, and reshape outcomes.

## Install

Copy the folder into your agent's skills directory.

| Agent | Location |
|---|---|
| Claude Code | `~/.claude/skills/demand-dry-run/` (or `.claude/skills/` in a project) |
| Codex | `~/.codex/skills/demand-dry-run/` (or `.agents/skills/` in a project) |
| Cursor | `.cursor/skills/demand-dry-run/` in a project |
| Other agents | anywhere the agent reads skills from, or point it at `SKILL.md` |

```bash
git clone https://github.com/fangdididi/demand-dry-run.git ~/.claude/skills/demand-dry-run
```

The helper script needs only Python 3.8+ and the standard library. Chinese instructions are in `SKILL.zh-CN.md`; either file works as the skill entry.

## Usage

Ask your agent something like:

- "Before I build this, set up a demand dry run for a receipt-chasing tool for bookkeepers at $29 a month."
- "I have 400 waitlist signups. Tell me honestly whether that means anything."
- "Should we test this course at $49 or $99? Plan the dry run."

Or drive the helper directly:

```bash
python3 scripts/dryrun.py init bet.json                       # blank bet card
python3 scripts/dryrun.py size --pass-line 0.04 --kill-line 0.015 --cpc 0.8
python3 scripts/dryrun.py freeze bet.json                     # validate and lock
python3 scripts/dryrun.py lint bet.json page.html             # honesty lint
python3 scripts/dryrun.py verdict bet.json log.csv            # GO / STOP / KEEP / RESHAPE
python3 scripts/dryrun.py verdict bet.json log.csv --json     # machine-readable
```

Exit codes: `0` ok (any verdict), `1` a check failed (lint FAIL, bad card, or UNLOCKED verdict), `2` input error.

## Example

The `examples/` folder holds a complete run for a bookkeeper tool with two variants and two paid channels plus a friends channel:

```
  A      bookkeeper_forum    6/270    [1.0% .. 4.8%]  KEEP
  A      linkedin_ads       11/490    [1.3% .. 4.0%]  KEEP
  B      bookkeeper_forum   15/285    [3.2% .. 8.5%]  KEEP
  B      linkedin_ads       30/498    [4.3% .. 8.5%]  GO
VARIANT A: 17/760 [1.4% .. 3.6%] cost/commit 22.94 -> RESHAPE
VARIANT B: 45/783 [4.3% .. 7.6%] cost/commit 8.73 -> GO
excluded visitors (warm or off-card): 60
VERDICT GO (best: B)
```

The 60 friends who converted at 15% did not move the result.

## File structure

```
demand-dry-run/
├── SKILL.md              # skill instructions (English)
├── SKILL.zh-CN.md        # skill instructions (Chinese)
├── README.md
├── README.zh-CN.md
├── LICENSE
├── scripts/
│   └── dryrun.py         # init, size, freeze, lint, verdict
├── templates/
│   ├── page-spec.md      # five-slot page spec and look check
│   └── close-out.md      # build / stop / reshape messages, result note
├── examples/
│   ├── bet.json          # filled bet card
│   ├── bet.lock          # its hash
│   ├── page.html         # offer page that passes the lint
│   ├── log.csv           # traffic log
│   └── verdict.txt       # verdict output
└── tests/
    └── test_dryrun.py    # 71 unit tests
```

Run the tests with `python3 -m unittest discover -s tests`.

## License

MIT
