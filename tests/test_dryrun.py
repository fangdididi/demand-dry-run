import copy
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import dryrun as d  # noqa: E402

EX = os.path.join(HERE, "..", "examples")


def good_bet(**kw):
    with open(os.path.join(EX, "bet.json"), encoding="utf-8") as fh:
        bet = json.load(fh)
    bet.update(kw)
    return bet


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = d.main(argv)
    return code, out.getvalue(), err.getvalue()


PAGE = """<html><body><p>For bookkeepers</p><p>$29 per month</p>
<p>Not built yet. We open to the first 50 bookkeepers in March.</p>
<a data-cta="primary" href="#r">Reserve</a>
<form><input name=email></form><p>Deposit is refundable. Privacy: email only.</p></body></html>"""


class Wilson(unittest.TestCase):
    def test_zero_n(self):
        self.assertEqual(d.wilson(0, 0), (0.0, 1.0))

    def test_bounds_inside_unit(self):
        lo, hi = d.wilson(0, 50)
        self.assertEqual(lo, 0.0)
        self.assertGreater(hi, 0)
        lo, hi = d.wilson(50, 50)
        self.assertLess(lo, 1)
        self.assertEqual(round(hi, 9), 1.0)

    def test_contains_point(self):
        lo, hi = d.wilson(30, 500)
        self.assertLess(lo, 0.06)
        self.assertGreater(hi, 0.06)

    def test_narrows_with_n(self):
        a = d.wilson(5, 100)
        b = d.wilson(50, 1000)
        self.assertLess(b[1] - b[0], a[1] - a[0])

    def test_known_value(self):
        lo, hi = d.wilson(10, 100)
        self.assertAlmostEqual(lo, 0.0552, places=3)
        self.assertAlmostEqual(hi, 0.1744, places=3)

    def test_bad_counts(self):
        with self.assertRaises(d.InputError):
            d.wilson(5, 3)


class Size(unittest.TestCase):
    def test_wider_gap_needs_fewer(self):
        self.assertLess(d.visitors_needed(0.10, 0.02), d.visitors_needed(0.04, 0.03))

    def test_interval_fits_gap(self):
        n = d.visitors_needed(0.04, 0.015)
        k = round(0.0275 * n)
        lo, hi = d.wilson(k, n)
        self.assertLessEqual(hi - lo, 0.025)

    def test_bad_lines(self):
        for p, k in ((0.02, 0.04), (0.04, 0.04), (1.2, 0.1), (0.1, 0)):
            with self.assertRaises(d.InputError):
                d.visitors_needed(p, k)

    def test_cli(self):
        code, out, _ = run(["size", "--pass-line", "0.05", "--kill-line", "0.02", "--cpc", "1"])
        self.assertEqual(code, 0)
        self.assertIn("visitors per cell", out)
        self.assertIn("paid traffic", out)


class BetCard(unittest.TestCase):
    def test_example_is_clean(self):
        self.assertEqual(d.check_bet(good_bet()), [])

    def test_missing_field(self):
        bet = good_bet()
        del bet["price"]
        self.assertTrue(any("missing field: price" in p for p in d.check_bet(bet)))

    def test_zero_price(self):
        self.assertTrue(any("price" in p for p in d.check_bet(good_bet(price=0))))

    def test_status_line_needed(self):
        self.assertTrue(any("status_line" in p for p in d.check_bet(good_bet(status_line=""))))

    def test_live_needs_no_status_line(self):
        self.assertEqual(d.check_bet(good_bet(status="live", status_line="")), [])

    def test_bad_status(self):
        self.assertTrue(d.check_bet(good_bet(status="soon")))

    def test_bad_rung(self):
        self.assertTrue(any("rung" in p for p in d.check_bet(good_bet(rung="like"))))

    def test_lines_order(self):
        self.assertTrue(any("kill_line" in p for p in d.check_bet(good_bet(pass_line=0.01, kill_line=0.03))))

    def test_lines_as_percent_rejected(self):
        self.assertTrue(d.check_bet(good_bet(pass_line=4, kill_line=1.5)))

    def test_min_visitors_too_small(self):
        probs = d.check_bet(good_bet(min_visitors=100))
        self.assertTrue(any("too small" in p for p in probs))

    def test_no_channels(self):
        self.assertTrue(any("channels" in p for p in d.check_bet(good_bet(channels=[]))))

    def test_bad_deadline(self):
        self.assertTrue(any("deadline" in p for p in d.check_bet(good_bet(deadline="next week"))))

    def test_duplicate_variants(self):
        self.assertTrue(any("variants" in p for p in d.check_bet(good_bet(variants=["A", "A"]))))

    def test_empty_who(self):
        self.assertTrue(any("who" in p for p in d.check_bet(good_bet(who="  "))))

    def test_hash_stable_and_sensitive(self):
        a = good_bet()
        b = copy.deepcopy(a)
        self.assertEqual(d.bet_hash(a), d.bet_hash(b))
        b["pass_line"] = 0.035
        self.assertNotEqual(d.bet_hash(a), d.bet_hash(b))


class Lint(unittest.TestCase):
    def levels(self, html, **kw):
        return d.lint_page(html, good_bet(**kw))

    def test_example_page_clean(self):
        with open(os.path.join(EX, "page.html"), encoding="utf-8") as fh:
            self.assertEqual([f for f in d.lint_page(fh.read(), good_bet()) if f[0] == "FAIL"], [])

    def test_minimal_page_clean(self):
        self.assertEqual([f for f in self.levels(PAGE) if f[0] == "FAIL"], [])

    def test_missing_price(self):
        f = self.levels(PAGE.replace("$29", "$39"))
        self.assertTrue(any("price" in m for _, m in f))

    def test_missing_status(self):
        f = self.levels(PAGE.replace("Not built yet.", ""))
        self.assertTrue(any("status_line" in m for _, m in f))

    def test_status_whitespace_tolerant(self):
        f = self.levels(PAGE.replace("Not built yet. We", "Not built yet.\n   We"))
        self.assertFalse(any("status_line" in m for _, m in f))

    def test_no_cta(self):
        f = self.levels(PAGE.replace('data-cta="primary"', ""))
        self.assertTrue(any(l == "FAIL" and "call to action" in m for l, m in f))

    def test_two_ctas_warn(self):
        f = self.levels(PAGE + '<a data-cta="primary">Again</a>')
        self.assertTrue(any(l == "WARN" for l, m in f))

    def test_unsourced_testimonial(self):
        f = self.levels(PAGE + '<blockquote data-testimonial>Great!</blockquote>')
        self.assertTrue(any("testimonial" in m for _, m in f))

    def test_sourced_testimonial_ok(self):
        f = self.levels(PAGE + '<blockquote data-testimonial data-source="interview-07">I lose days</blockquote>')
        self.assertFalse(any("testimonial" in m for _, m in f))

    def test_scarcity(self):
        f = self.levels(PAGE + "<p>Only 3 spots left!</p>")
        self.assertTrue(any("scarcity" in m for _, m in f))

    def test_crowd_claim(self):
        f = self.levels(PAGE + "<p>Join 10,000 users</p>")
        self.assertTrue(any("crowd" in m for _, m in f))

    def test_chinese_patterns(self):
        f = self.levels(PAGE + "<p>仅剩 5 个名额，已有 3000 人加入</p>")
        labels = " ".join(m for _, m in f)
        self.assertIn("scarcity", labels)
        self.assertIn("crowd", labels)

    def test_available_now_when_not_built(self):
        f = self.levels(PAGE + "<p>Available now</p>")
        self.assertTrue(any("available now" in m for _, m in f))

    def test_available_now_ok_when_live(self):
        f = self.levels(PAGE + "<p>Available now</p>", status="live")
        self.assertFalse(any("available now" in m for _, m in f))

    def test_countdown(self):
        f = self.levels(PAGE + "<script>setInterval(tick,1000)</script>")
        self.assertTrue(any("countdown" in m for _, m in f))

    def test_deposit_needs_refund(self):
        f = self.levels(PAGE.replace("refundable", "secure"))
        self.assertTrue(any("refund" in m for _, m in f))

    def test_email_rung_needs_no_refund(self):
        f = self.levels(PAGE.replace("refundable", "secure"), rung="email")
        self.assertFalse(any("refund" in m for _, m in f))

    def test_privacy_warn(self):
        f = self.levels(PAGE.replace("Privacy", "Note"))
        self.assertTrue(any(l == "WARN" and "privacy" in m for l, m in f))

    def test_script_text_not_counted_as_copy(self):
        f = self.levels(PAGE.replace("$29 per month", "") + "<script>var p='$29';</script>")
        self.assertTrue(any("price" in m for _, m in f))


class Verdict(unittest.TestCase):
    def rows(self, *spec):
        return [{"date": "2026-11-01", "channel": c, "variant": v, "visitors": n, "commits": k, "spend": s}
                for c, v, n, k, s in spec]

    def test_decide_go(self):
        self.assertEqual(d.decide(80, 1000, good_bet())[0], "GO")

    def test_decide_stop(self):
        self.assertEqual(d.decide(3, 1000, good_bet())[0], "STOP")

    def test_decide_keep(self):
        self.assertEqual(d.decide(3, 100, good_bet())[0], "KEEP")

    def test_decide_reshape(self):
        self.assertEqual(d.decide(28, 1000, good_bet())[0], "RESHAPE")

    def test_warm_excluded(self):
        out = d.verdict(self.rows(("friends", "A", 100, 40, 0), ("linkedin_ads", "A", 100, 1, 50)), good_bet())
        self.assertEqual(out["excluded_visitors"], 100)
        a = [v for v in out["variants"] if v["variant"] == "A"][0]
        self.assertEqual(a["visitors"], 100)

    def test_warm_included_on_request(self):
        out = d.verdict(self.rows(("friends", "A", 100, 40, 0)), good_bet(), include_warm=True)
        self.assertEqual(out["excluded_visitors"], 0)

    def test_unknown_channel_noted(self):
        out = d.verdict(self.rows(("tiktok", "A", 50, 5, 0)), good_bet())
        self.assertTrue(any("tiktok" in n for n in out["notes"]))
        self.assertEqual(out["excluded_visitors"], 50)

    def test_unknown_variant_noted(self):
        out = d.verdict(self.rows(("linkedin_ads", "Z", 50, 5, 0)), good_bet())
        self.assertTrue(any("variant 'Z'" in n for n in out["notes"]))

    def test_cost_cap_downgrades_go(self):
        out = d.verdict(self.rows(("linkedin_ads", "A", 1000, 80, 4000)), good_bet())
        a = [v for v in out["variants"] if v["variant"] == "A"][0]
        self.assertEqual(a["call"], "RESHAPE")

    def test_budget_note(self):
        out = d.verdict(self.rows(("linkedin_ads", "A", 1000, 80, 1000)), good_bet())
        self.assertTrue(any("budget cap" in n for n in out["notes"]))

    def test_channel_disagreement(self):
        out = d.verdict(self.rows(("linkedin_ads", "A", 1000, 90, 100), ("bookkeeper_forum", "A", 1000, 2, 0)), good_bet())
        self.assertTrue(any("disagree" in n for n in out["notes"]))

    def test_overall_prefers_go(self):
        out = d.verdict(self.rows(("linkedin_ads", "A", 1000, 2, 0), ("linkedin_ads", "B", 1000, 90, 100)), good_bet())
        self.assertEqual(out["overall"], "GO")
        self.assertEqual(out["best_variant"], "B")

    def test_example_log(self):
        rows = d.read_log(os.path.join(EX, "log.csv"))
        out = d.verdict(rows, good_bet())
        self.assertEqual(out["overall"], "GO")
        self.assertEqual(out["best_variant"], "B")


class LogAndCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.bet = os.path.join(self.dir, "bet.json")
        with open(self.bet, "w", encoding="utf-8") as fh:
            json.dump(good_bet(), fh)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, text):
        p = os.path.join(self.dir, name)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        return p

    def test_log_missing_column(self):
        p = self.write("l.csv", "date,channel,variant,visitors\n2026-11-01,x,A,3\n")
        with self.assertRaises(d.InputError):
            d.read_log(p)

    def test_log_commits_over_visitors(self):
        p = self.write("l.csv", "date,channel,variant,visitors,commits\n2026-11-01,x,A,3,4\n")
        with self.assertRaises(d.InputError):
            d.read_log(p)

    def test_log_non_number(self):
        p = self.write("l.csv", "date,channel,variant,visitors,commits\n2026-11-01,x,A,three,1\n")
        with self.assertRaises(d.InputError):
            d.read_log(p)

    def test_log_spend_optional(self):
        p = self.write("l.csv", "date,channel,variant,visitors,commits\n2026-11-01,x,A,3,1\n")
        self.assertEqual(d.read_log(p)[0]["spend"], 0.0)

    def test_init_refuses_overwrite(self):
        code, _, _ = run(["init", self.bet])
        self.assertEqual(code, 2)

    def test_init_writes_blank(self):
        p = os.path.join(self.dir, "new.json")
        code, _, _ = run(["init", p])
        self.assertEqual(code, 0)
        self.assertTrue(d.check_bet(json.load(open(p, encoding="utf-8"))))

    def test_freeze_then_verdict(self):
        self.assertEqual(run(["freeze", self.bet])[0], 0)
        code, out, _ = run(["verdict", self.bet, os.path.join(EX, "log.csv")])
        self.assertEqual(code, 0)
        self.assertIn("VERDICT GO", out)

    def test_freeze_rejects_bad_card(self):
        bad = self.write("bad.json", json.dumps(good_bet(price=0)))
        code, out, _ = run(["freeze", bad])
        self.assertEqual(code, 1)
        self.assertIn("FAIL", out)

    def test_verdict_without_lock(self):
        code, out, _ = run(["verdict", self.bet, os.path.join(EX, "log.csv")])
        self.assertEqual(code, 1)
        self.assertIn("UNLOCKED", out)

    def test_verdict_after_edit(self):
        run(["freeze", self.bet])
        bet = good_bet(kill_line=0.01)
        with open(self.bet, "w", encoding="utf-8") as fh:
            json.dump(bet, fh)
        code, out, _ = run(["verdict", self.bet, os.path.join(EX, "log.csv")])
        self.assertEqual(code, 1)
        self.assertIn("changed after it was frozen", out)

    def test_verdict_json(self):
        run(["freeze", self.bet])
        code, out, _ = run(["verdict", self.bet, os.path.join(EX, "log.csv"), "--json"])
        self.assertEqual(json.loads(out)["overall"], "GO")

    def test_lint_cli_blocks(self):
        page = self.write("p.html", "<html><body>hello</body></html>")
        code, out, _ = run(["lint", self.bet, page])
        self.assertEqual(code, 1)
        self.assertIn("PAGE BLOCKED", out)

    def test_lint_cli_ok(self):
        code, out, _ = run(["lint", self.bet, os.path.join(EX, "page.html")])
        self.assertEqual(code, 0)
        self.assertIn("PAGE OK", out)

    def test_missing_file(self):
        code, _, err = run(["lint", self.bet, os.path.join(self.dir, "nope.html")])
        self.assertEqual(code, 2)
        self.assertIn("not found", err)


if __name__ == "__main__":
    unittest.main()
