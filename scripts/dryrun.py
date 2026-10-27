#!/usr/bin/env python3
"""dryrun.py - helper for the demand-dry-run skill.

Subcommands
  init     write a blank bet card (bet.json)
  freeze   check the bet card and lock it (bet.lock holds a hash)
  size     visitors needed per cell before a verdict is possible
  lint     check a landing page (HTML) against the bet card
  verdict  read the traffic log (CSV) and print GO / STOP / KEEP / RESHAPE

Standard library only. Exit codes: 0 ok, 1 check failed, 2 usage/input error.
"""
import argparse
import csv
import hashlib
import json
import math
import re
import sys
from html.parser import HTMLParser

RUNGS = {
    "email": 1,       # leaves an email address
    "form": 2,        # answers a qualifying form or books a call
    "deposit": 3,     # refundable deposit
    "preorder": 4,    # full paid pre-order (refundable)
}
STATUSES = ("not_built", "prototype", "private_beta", "live")
REQUIRED = ("who", "pain", "offer", "price", "currency", "status", "rung",
            "pass_line", "kill_line", "min_visitors", "budget_cap",
            "deadline", "channels")
WARM_DEFAULT = ("friends", "own_followers", "existing_customers", "team")

BLANK = {
    "who": "",
    "pain": "",
    "offer": "",
    "price": 0,
    "currency": "USD",
    "billing": "one_time",
    "status": "not_built",
    "status_line": "",
    "rung": "email",
    "pass_line": 0.0,
    "kill_line": 0.0,
    "min_visitors": 0,
    "budget_cap": 0,
    "deadline": "",
    "channels": [],
    "warm_channels": list(WARM_DEFAULT),
    "variants": ["A"],
    "max_cost_per_commit": None,
}


class InputError(Exception):
    pass


# ---------------------------------------------------------------- statistics
def wilson(successes, n, z=1.96):
    """Wilson score interval for a proportion. Returns (low, high)."""
    if n <= 0:
        return (0.0, 1.0)
    if successes < 0 or successes > n:
        raise InputError("successes must be between 0 and n")
    p = successes / n
    z2 = z * z
    denom = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def visitors_needed(pass_line, kill_line, z=1.96):
    """Smallest n where an observed rate sitting exactly at the midpoint
    between kill and pass lines would have a Wilson interval no wider than
    the gap. Below this, the test cannot tell pass from kill."""
    if not (0 < kill_line < pass_line < 1):
        raise InputError("need 0 < kill_line < pass_line < 1")
    mid = (pass_line + kill_line) / 2
    gap = pass_line - kill_line
    n = 10
    while n < 10_000_000:
        k = round(mid * n)
        lo, hi = wilson(k, n, z)
        if hi - lo <= gap:
            return n
        n = int(n * 1.05) + 1
    return n


# ---------------------------------------------------------------- bet card
def check_bet(bet):
    problems = []
    for key in REQUIRED:
        if key not in bet:
            problems.append(f"missing field: {key}")
    if problems:
        return problems
    for key in ("who", "pain", "offer", "deadline"):
        if not str(bet[key]).strip():
            problems.append(f"empty field: {key}")
    if not isinstance(bet["price"], (int, float)) or bet["price"] <= 0:
        problems.append("price must be a real number above 0 (a test without a price measures curiosity)")
    if bet["status"] not in STATUSES:
        problems.append(f"status must be one of {', '.join(STATUSES)}")
    if bet["status"] != "live" and not str(bet.get("status_line", "")).strip():
        problems.append("status_line is required when the product is not live")
    if bet["rung"] not in RUNGS:
        problems.append(f"rung must be one of {', '.join(RUNGS)}")
    try:
        pl, kl = float(bet["pass_line"]), float(bet["kill_line"])
        if not (0 < kl < pl < 1):
            problems.append("need 0 < kill_line < pass_line < 1 (rates as fractions, e.g. 0.04)")
    except (TypeError, ValueError):
        problems.append("pass_line and kill_line must be numbers")
    if not isinstance(bet["min_visitors"], int) or bet["min_visitors"] <= 0:
        problems.append("min_visitors must be a positive integer")
    elif not problems:
        need = visitors_needed(float(bet["pass_line"]), float(bet["kill_line"]))
        if bet["min_visitors"] < need:
            problems.append(f"min_visitors {bet['min_visitors']} is too small to separate the lines; need at least {need} per cell")
    if not isinstance(bet["budget_cap"], (int, float)) or bet["budget_cap"] < 0:
        problems.append("budget_cap must be 0 or more")
    if not isinstance(bet["channels"], list) or not bet["channels"]:
        problems.append("channels must list at least one traffic source")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(bet["deadline"])):
        problems.append("deadline must be YYYY-MM-DD")
    variants = bet.get("variants", ["A"])
    if not isinstance(variants, list) or not variants or len(set(variants)) != len(variants):
        problems.append("variants must be a non-empty list of unique names")
    return problems


def bet_hash(bet):
    blob = json.dumps(bet, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def load_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        raise InputError(f"file not found: {path}")
    except json.JSONDecodeError as exc:
        raise InputError(f"bad JSON in {path}: {exc}")


# ---------------------------------------------------------------- page lint
class _PageScan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.primary_ctas = 0
        self.forms = 0
        self.scripts = []
        self.testimonials_unsourced = 0
        self._in_script = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "data-cta" in a and a.get("data-cta") in ("primary", ""):
            self.primary_ctas += 1
        if tag == "form":
            self.forms += 1
        if "data-testimonial" in a and not a.get("data-source"):
            self.testimonials_unsourced += 1
        if tag == "script":
            self._in_script = True
            self.scripts.append("")

    def handle_endtag(self, tag):
        if tag == "script":
            self._in_script = False

    def handle_data(self, data):
        if self._in_script:
            self.scripts[-1] += data
        else:
            self.text.append(data)


PRESSURE_PATTERNS = [
    (r"\bonly \d+ (left|spots?|seats?)\b", "invented scarcity"),
    (r"\b(join|trusted by) [\d,\.]+\+? (people|users|teams|founders|customers)\b", "crowd claim you cannot back yet"),
    (r"\boffer ends (today|tonight|soon)\b", "deadline pressure"),
    (r"\bavailable now\b", "says available now"),
    (r"\bin stock\b", "says in stock"),
    (r"仅剩\s*\d+", "invented scarcity"),
    (r"已有\s*[\d,\.万]+\s*(人|位|家)", "crowd claim you cannot back yet"),
    (r"(立即发货|现货)", "says available now"),
]
COUNTDOWN_HINTS = ("countdown", "setinterval(", "timer-ends", "evergreen")


def lint_page(html, bet):
    scan = _PageScan()
    scan.feed(html)
    text = " ".join(" ".join(scan.text).split())
    low = text.lower()
    findings = []

    price = bet.get("price")
    if isinstance(price, (int, float)) and price > 0:
        forms = {f"{price:g}", f"{price:,.2f}", f"{price:,.0f}", f"{price:.2f}"}
        if not any(f in text for f in forms):
            findings.append(("FAIL", f"price {price:g} from the bet card does not appear on the page"))
    status_line = str(bet.get("status_line", "")).strip()
    if bet.get("status") != "live":
        if not status_line:
            findings.append(("FAIL", "bet card has no status_line to show"))
        elif " ".join(status_line.split()).lower() not in low:
            findings.append(("FAIL", "status_line from the bet card is not on the page word for word"))
    if scan.primary_ctas == 0:
        findings.append(("FAIL", "no primary call to action (mark it with data-cta=\"primary\")"))
    elif scan.primary_ctas > 1:
        findings.append(("WARN", f"{scan.primary_ctas} primary calls to action; the test reads cleaner with one ask"))
    if scan.testimonials_unsourced:
        findings.append(("FAIL", f"{scan.testimonials_unsourced} testimonial(s) without data-source; a product that does not exist yet has no customers to quote"))
    for pattern, label in PRESSURE_PATTERNS:
        if re.search(pattern, low, re.IGNORECASE):
            if label.startswith("says") and bet.get("status") == "live":
                continue
            findings.append(("FAIL", f"pressure or false claim: {label}"))
    js = " ".join(scan.scripts).lower()
    if any(h in js for h in COUNTDOWN_HINTS) or 'id="countdown"' in html.lower():
        findings.append(("FAIL", "countdown timer found; a dry run must not invent urgency"))
    if RUNGS.get(bet.get("rung"), 0) >= 3 and "refund" not in low and "退款" not in text:
        findings.append(("FAIL", "money is asked for but the page never mentions refunds"))
    if scan.forms and not re.search(r"privacy|隐私", low):
        findings.append(("WARN", "page collects data but has no privacy note"))
    return findings


# ---------------------------------------------------------------- verdict
def read_log(path):
    need = {"date", "channel", "variant", "visitors", "commits"}
    rows = []
    try:
        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            missing = need - set(reader.fieldnames or [])
            if missing:
                raise InputError(f"log is missing columns: {', '.join(sorted(missing))}")
            for i, raw in enumerate(reader, start=2):
                try:
                    row = {
                        "date": raw["date"].strip(),
                        "channel": raw["channel"].strip(),
                        "variant": raw["variant"].strip(),
                        "visitors": int(raw["visitors"]),
                        "commits": int(raw["commits"]),
                        "spend": float(raw.get("spend") or 0),
                    }
                except ValueError:
                    raise InputError(f"line {i}: visitors/commits/spend must be numbers")
                if row["visitors"] < 0 or row["commits"] < 0:
                    raise InputError(f"line {i}: negative counts")
                if row["commits"] > row["visitors"]:
                    raise InputError(f"line {i}: more commits than visitors")
                rows.append(row)
    except FileNotFoundError:
        raise InputError(f"file not found: {path}")
    return rows


def decide(commits, visitors, bet):
    pl, kl = float(bet["pass_line"]), float(bet["kill_line"])
    lo, hi = wilson(commits, visitors)
    if visitors >= 1 and lo >= pl:
        call = "GO"
    elif visitors >= 1 and hi < kl:
        call = "STOP"
    elif visitors < bet["min_visitors"]:
        call = "KEEP"
    else:
        call = "RESHAPE"
    return call, lo, hi


def verdict(rows, bet, include_warm=False):
    warm = set(bet.get("warm_channels", WARM_DEFAULT))
    known = set(bet["channels"]) | warm
    variants = set(bet.get("variants", ["A"]))
    notes = []
    cells = {}
    excluded = 0
    spend_total = 0.0
    for r in rows:
        if r["channel"] not in known:
            notes.append(f"unknown channel '{r['channel']}' on {r['date']} (not on the bet card); counted as excluded")
            excluded += r["visitors"]
            continue
        if r["variant"] not in variants:
            notes.append(f"unknown variant '{r['variant']}' on {r['date']}; counted as excluded")
            excluded += r["visitors"]
            continue
        spend_total += r["spend"]
        if r["channel"] in warm and not include_warm:
            excluded += r["visitors"]
            continue
        key = (r["variant"], r["channel"])
        c = cells.setdefault(key, {"visitors": 0, "commits": 0, "spend": 0.0})
        c["visitors"] += r["visitors"]
        c["commits"] += r["commits"]
        c["spend"] += r["spend"]
    out = {"cells": [], "variants": [], "excluded_visitors": excluded,
           "spend_total": round(spend_total, 2), "notes": notes}
    for (v, ch), c in sorted(cells.items()):
        call, lo, hi = decide(c["commits"], c["visitors"], bet)
        out["cells"].append({"variant": v, "channel": ch, **c, "low": lo, "high": hi, "call": call})
    for v in sorted(variants):
        vis = sum(c["visitors"] for (vv, _), c in cells.items() if vv == v)
        com = sum(c["commits"] for (vv, _), c in cells.items() if vv == v)
        spend = sum(c["spend"] for (vv, _), c in cells.items() if vv == v)
        call, lo, hi = decide(com, vis, bet)
        cpc = round(spend / com, 2) if com else None
        cap = bet.get("max_cost_per_commit")
        if call == "GO" and cap is not None and (cpc is None or cpc > cap):
            call = "RESHAPE"
            notes.append(f"variant {v} clears the rate line but costs {cpc} per commitment, above the cap {cap}")
        out["variants"].append({"variant": v, "visitors": vis, "commits": com, "spend": round(spend, 2),
                                "cost_per_commit": cpc, "low": lo, "high": hi, "call": call})
        # channel disagreement: one channel GO, another STOP
        calls = {c["call"] for c in out["cells"] if c["variant"] == v}
        if "GO" in calls and "STOP" in calls:
            notes.append(f"variant {v}: channels disagree (one GO, one STOP); the audience, not the offer, may be the finding")
    if bet.get("budget_cap") and spend_total > bet["budget_cap"]:
        notes.append(f"spend {spend_total:.2f} is over the budget cap {bet['budget_cap']}; stop buying traffic")
    order = {"GO": 0, "RESHAPE": 1, "KEEP": 2, "STOP": 3}
    if out["variants"]:
        best = min(out["variants"], key=lambda x: (order[x["call"]], -x["low"]))
        out["overall"] = best["call"]
        out["best_variant"] = best["variant"]
    else:
        out["overall"] = "KEEP"
        out["best_variant"] = None
    return out


# ---------------------------------------------------------------- cli
def pct(x):
    return f"{x * 100:.1f}%"


def cmd_init(args):
    with open(args.out, "x", encoding="utf-8") as fh:
        json.dump(BLANK, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"wrote {args.out}; fill it in, then run: dryrun.py freeze {args.out}")
    return 0


def cmd_freeze(args):
    bet = load_json(args.bet)
    problems = check_bet(bet)
    if problems:
        for p in problems:
            print(f"FAIL {p}")
        return 1
    lock = args.bet.rsplit(".", 1)[0] + ".lock"
    with open(lock, "w", encoding="utf-8") as fh:
        fh.write(bet_hash(bet) + "\n")
    print(f"LOCKED {lock}  pass {pct(bet['pass_line'])}  kill {pct(bet['kill_line'])}  min {bet['min_visitors']} visitors per cell")
    return 0


def check_lock(bet_path, bet):
    lock = bet_path.rsplit(".", 1)[0] + ".lock"
    try:
        with open(lock, encoding="utf-8") as fh:
            saved = fh.read().strip()
    except FileNotFoundError:
        return "no lock file: run freeze before any traffic"
    if saved != bet_hash(bet):
        return "bet card changed after it was frozen; the lines no longer count as set in advance"
    return None


def cmd_size(args):
    n = visitors_needed(args.pass_line, args.kill_line)
    print(f"{n} visitors per cell to tell {pct(args.pass_line)} from {pct(args.kill_line)}")
    if args.cpc:
        print(f"at {args.cpc:g} per click that is about {n * args.cpc:,.0f} per cell in paid traffic")
    return 0


def cmd_lint(args):
    bet = load_json(args.bet)
    try:
        with open(args.page, encoding="utf-8") as fh:
            html = fh.read()
    except FileNotFoundError:
        raise InputError(f"file not found: {args.page}")
    findings = lint_page(html, bet)
    for level, msg in findings:
        print(f"{level} {msg}")
    fails = [f for f in findings if f[0] == "FAIL"]
    print("PAGE OK" if not fails else f"PAGE BLOCKED ({len(fails)} fail)")
    return 1 if fails else 0


def cmd_verdict(args):
    bet = load_json(args.bet)
    problems = check_bet(bet)
    if problems:
        for p in problems:
            print(f"FAIL {p}")
        return 2
    lock_problem = check_lock(args.bet, bet)
    rows = read_log(args.log)
    out = verdict(rows, bet, include_warm=args.include_warm)
    if lock_problem:
        out["notes"].insert(0, lock_problem)
        out["overall"] = "UNLOCKED"
    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        for c in out["cells"]:
            print(f"  {c['variant']:<6} {c['channel']:<16} {c['commits']:>4}/{c['visitors']:<6} "
                  f"[{pct(c['low'])} .. {pct(c['high'])}]  {c['call']}")
        for v in out["variants"]:
            cost = "n/a" if v["cost_per_commit"] is None else f"{v['cost_per_commit']:g}"
            print(f"VARIANT {v['variant']}: {v['commits']}/{v['visitors']} [{pct(v['low'])} .. {pct(v['high'])}] "
                  f"cost/commit {cost} -> {v['call']}")
        print(f"excluded visitors (warm or off-card): {out['excluded_visitors']}")
        for n in out["notes"]:
            print(f"NOTE {n}")
        print(f"VERDICT {out['overall']}" + (f" (best: {out['best_variant']})" if out["best_variant"] else ""))
    return {"GO": 0, "STOP": 0, "KEEP": 0, "RESHAPE": 0}.get(out["overall"], 1)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="dryrun.py", description="demand dry run helper")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init"); p.add_argument("out", nargs="?", default="bet.json"); p.set_defaults(fn=cmd_init)
    p = sub.add_parser("freeze"); p.add_argument("bet"); p.set_defaults(fn=cmd_freeze)
    p = sub.add_parser("size"); p.add_argument("--pass-line", type=float, required=True)
    p.add_argument("--kill-line", type=float, required=True); p.add_argument("--cpc", type=float); p.set_defaults(fn=cmd_size)
    p = sub.add_parser("lint"); p.add_argument("bet"); p.add_argument("page"); p.set_defaults(fn=cmd_lint)
    p = sub.add_parser("verdict"); p.add_argument("bet"); p.add_argument("log")
    p.add_argument("--include-warm", action="store_true"); p.add_argument("--json", action="store_true"); p.set_defaults(fn=cmd_verdict)
    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except InputError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2
    except FileExistsError as exc:
        print(f"ERROR {exc.filename} already exists", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
