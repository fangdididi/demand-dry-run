---
name: demand-dry-run
description: Use before building a product, feature, course, or service to find out whether strangers will commit to it. Freezes a bet card (who, pain, real price, honest status, one commitment ask, pass and kill lines, sample size, budget, deadline) before any traffic, builds a one-ask offer page that passes an honesty lint, keeps warm traffic out of the count, and reads the log with confidence intervals into GO, STOP, KEEP, or RESHAPE, then closes the test out cleanly (refunds, notices, data deletion).
---

# Demand Dry Run

**English** | [简体中文](SKILL.zh-CN.md)

## What this is

A demand dry run is a small, honest rehearsal of selling something that does not exist yet. You show a single offer page with the real price and the real status ("not built yet"), ask visitors for one specific commitment, send measured traffic to it, and decide in advance what result would make you build and what result would make you stop.

The problem it solves: most pre-build "validation" cannot fail. Friends sign up to be kind, the page has no price so clicks measure curiosity, the success line is chosen after the numbers come in, and a beautiful page gets credit that belongs to the offer. This skill closes each of those holes:

- the success and failure lines are written and hashed **before** the first visitor,
- the page must show the price and the true status, and must not invent scarcity, crowds, testimonials, or countdowns,
- warm traffic (friends, your own followers, the team) is logged but kept out of the verdict,
- the verdict uses an interval, not a single rate, so "3 of 40" is not mistaken for proof,
- every test ends with a close-out: refunds, a truthful message to everyone who signed up, and deletion of data you no longer need.

## When to use it

- You have an idea and want evidence before spending weeks building it.
- You are choosing between two framings, audiences, or prices for the same offer.
- Someone (a co-founder, a manager, a grant panel) asks "how do you know people want this?"
- You already ran a "waitlist" and are not sure what the numbers mean.

Do not use it for: products that need regulatory approval before they can be offered (medical, financial advice, securities), anything where taking a deposit would itself be illegal where you operate, or measuring satisfaction with something already live (that is a different study).

## The commitment ladder

Pick the rung you will count. Higher rungs cost the visitor more, so they mean more and convert less.

| Rung | `rung` value | Visitor gives | What a yes tells you |
|---|---|---|---|
| 1 | `email` | an email address | the headline is interesting |
| 2 | `form` | answers to qualifying questions, or books a call | they see themselves in the problem |
| 3 | `deposit` | a small refundable payment | they would pay something now |
| 4 | `preorder` | the full price, refundable | they would pay this price |

Rule of thumb: count at least rung 2. An email-only test can tell you a headline works; it cannot tell you a product will sell.

## Steps

### 1. Write the bet card

Run `python3 scripts/dryrun.py init bet.json` and fill it in. Every field has a reason:

- `who`: the narrowest group you will buy traffic for. "Small businesses" is not a who; "freelance bookkeepers with 10+ monthly clients" is.
- `pain`: one sentence in *their* words, ideally lifted from an interview or a forum post you can point to.
- `offer`: what they get, in one sentence, without features they would not miss.
- `price`, `currency`, `billing`: a real number. A test without a price measures curiosity.
- `status` and `status_line`: the sentence that will appear on the page saying where the product really is.
- `rung`: which ladder step counts as a commitment.
- `pass_line` and `kill_line`: commitment rates as fractions (0.04 = 4%). Above the pass line you build; below the kill line you stop. Write down *why* each line sits where it does (for example "at 4% and our expected cost per click, one customer costs less than two months of revenue").
- `min_visitors`: visitors per cell (variant × channel). Run `dryrun.py size --pass-line 0.04 --kill-line 0.015` to see the floor; the card will not freeze below it.
- `budget_cap` and `max_cost_per_commit`: the money you will spend, and the most a single commitment may cost before a good rate stops being good.
- `deadline`, `channels`, `warm_channels`, `variants`.

### 2. Freeze it

`python3 scripts/dryrun.py freeze bet.json` checks the card and writes `bet.lock` with a hash. If you edit the card later, the verdict command will say so and refuse to call the result. That is the point: the lines were set before you saw the numbers.

If you truly must change the bet, start a new card with a new name and treat the old traffic as a pilot.

### 3. Spec the page before building it

Write a short page spec first; quality is decided here, not in the code. Above the fold, five slots, in this order:

1. **Who it is for**, in a short eyebrow line.
2. **The outcome**, in the pain sentence turned around ("Stop losing the first three days of every month...").
3. **The price**, exactly as on the bet card.
4. **The status line**, word for word from the bet card.
5. **One ask**, marked `data-cta="primary"`, worded as the commitment ("Hold my spot with a $10 refundable deposit"), not "Learn more".

Below the fold: how it would work in three steps, what it is *not*, refunds and timeline in plain words, and a privacy note.

Make it look good, but keep the polish equal across variants. If variant B gets a cinematic hero video and A gets stock text, you have tested video, not the offer. Change one thing per variant: the audience framing, the outcome sentence, or the price.

### 4. Build, look, and lint

Build the page with whatever you normally use. Then:

- Screenshot it at 1280 px and 375 px wide. On the phone width the price, status line, and ask must be visible without scrolling, nothing should overflow sideways, and images must load.
- Fire each tracking event once by hand (page view, ask click, commitment) and confirm it lands in your analytics or form tool. Delete those test rows afterwards.
- Run `python3 scripts/dryrun.py lint bet.json page.html`. It blocks the page if the price or status line is missing, there is no primary ask, a testimonial has no `data-source`, the copy invents scarcity or crowds, a countdown timer is present, or money is asked for without mentioning refunds.

Fix every FAIL before any traffic goes out.

### 5. Send traffic and log it

Keep a CSV with `date,channel,variant,visitors,commits,spend`. One row per day per channel per variant. Rules:

- Count unique visitors who saw the page, not ad impressions or clicks.
- Log warm traffic under its own channel name (`friends`, `own_followers`). It is reported but excluded from the verdict.
- Do not peek-and-stop on a lucky day. The verdict only says GO or STOP when the interval is clear of a line; otherwise it says KEEP until the visitor floor is met.
- Stop buying traffic when the budget cap is reached, whatever the numbers say.

### 6. Read the verdict

`python3 scripts/dryrun.py verdict bet.json log.csv`

For each cell and each variant it prints commitments over visitors and a 95% Wilson interval, then a call:

- **GO**: the whole interval sits at or above the pass line (and cost per commitment is under the cap).
- **STOP**: the whole interval sits below the kill line.
- **KEEP**: not enough visitors yet to tell.
- **RESHAPE**: enough visitors, but the rate sits between the lines, or the rate passes while each commitment costs too much. Change one variable and run a new card.
- **UNLOCKED**: there is no lock, or the card changed after freezing. No call is made.

Read the notes too. "Channels disagree" means one audience said yes and another said no; often the audience is the real finding.

### 7. Close it out

Whatever the verdict, within a week:

- **Deposits and pre-orders**: refund anyone who asks, and everyone if you stop. Say so in plain words.
- **Signups**: send one truthful message: what you learned, what happens next, and how to be removed. If you stop, delete their data.
- **Write a one-paragraph result** next to the bet card: the call, the numbers, what surprised you, and the next card if there is one.

## Example

`examples/` holds a full run for a receipt-chasing tool for bookkeepers: the bet card, the page, the traffic log, and the verdict. Variant A ("save time") landed between the lines; variant B ("stop losing three days a month") cleared the 4% pass line on paid traffic at $8.73 per deposit, while the friends channel (15% conversion) was excluded:

```
VARIANT A: 17/760 [1.4% .. 3.6%] cost/commit 22.94 -> RESHAPE
VARIANT B: 45/783 [4.3% .. 7.6%] cost/commit 8.73 -> GO
excluded visitors (warm or off-card): 60
VERDICT GO (best: B)
```

## Tips

- Put the price in the headline area even when it hurts. A page that hides the price will overstate demand every time.
- If you cannot name where your first 700 visitors per cell will come from, the test is too expensive for this audience. That is a finding too.
- Interviews come before the page, not instead of it. Lift the pain sentence from them.
- A deposit as small as a coffee still separates "sounds nice" from "I want this".
- Never show a counter of signups or a "spots left" number on a test page. It changes what you are measuring.
- In China-facing tests, local ad platforms and private-domain channels (WeChat groups, Xiaohongshu notes) work the same way: give each its own channel name.
- Keep the old bet cards. A run of STOP and RESHAPE results is the most honest record of how you found the thing that worked.
