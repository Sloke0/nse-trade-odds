"""Smoke tests: python3 -m pytest tests/  (or python3 tests/test_engine.py)"""
import json, os, re, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE = os.path.join(ROOT, "engine", "trade_odds.py")
SAMPLE = os.path.join(ROOT, "examples", "SAMPLE_synthetic.csv")


def run(*args):
    out = subprocess.run([sys.executable, ENGINE, "--csv", SAMPLE, *args, "--json"], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def test_odds_sum_to_one():
    d = run("--entry", "820", "--stop", "790", "--target", "880", "--days", "10")
    b = d["blend"]
    assert abs(b["p_target"] + b["p_stop"] + b["p_neither"] - 1) < 0.01
    assert d["trade"]["breakeven_winrate"] == round(1 / (1 + d["trade"]["rr"]), 3)


def test_short_side_and_grid_and_streaks():
    d = run("--side", "short", "--entry", "820", "--stop", "850", "--target", "770", "--days", "10", "--grid", "--streaks")
    assert "top_by_train_ev" in d["grid"] and "max_drawdown_pct" in d["streaks"]


def test_options():
    d = run("--strike", "850", "--expiry-days", "7", "--iv", "25")
    o = d["options"]
    assert abs(o["p_close_above_at_expiry"] + o["p_close_below_at_expiry"] - 1) < 0.01


def test_log_and_calibrate():
    with tempfile.TemporaryDirectory() as t:
        j = os.path.join(t, "journal.csv")
        run("--entry", "820", "--stop", "790", "--target", "880", "--days", "10", "--log", j, "--name", "SAMPLE")
        out = subprocess.run([sys.executable, ENGINE, "--calibrate", j, "--data-dir", os.path.join(ROOT, "examples")],
                             capture_output=True, text=True, check=True)
        assert json.loads(out.stdout)["logged"] == 1


def test_embedded_skill_script_matches_engine():
    skill = open(os.path.join(ROOT, "skills", "nse-trade-probability", "SKILL.md")).read()
    embedded = re.split(r"```python\n", skill)[-1].rsplit("```", 1)[0]
    assert embedded == open(ENGINE).read()
    assert open(os.path.join(ROOT, "skills", "nse-trade-probability", "scripts", "trade_odds.py")).read() == embedded


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("ok", name)
