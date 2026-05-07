"""
Categorize failures across the 4 runs (2 models x 2 prompt variants).

Failure categories:
  PREMATURE_FINISH    - last action is finish_action and result is wrong
                        (agent gave up / decided task done without answering)
  WRONG_ANSWER_FAST   - calls answer_action with wrong value at <=3 rounds
                        (snap-judgment, didn't explore enough)
  WRONG_ANSWER_LATE   - calls answer_action with wrong value at >3 rounds
                        (explored, but wrong answer / format)
  ROUND_LIMIT         - hit 8 rounds, never produced a final answer_action
  REPETITIVE_BASH     - >=3 effectively-identical bash commands in a row
                        (regardless of where it ended)
  TRUNCATION_FAIL     - tool message contains "truncated" and final action wrong
  OTHER               - none of the above
"""
import json, os, re, sys, hashlib
from collections import Counter, defaultdict

RUNS = [
    ("gpt-5.4-nano", "os-std"),
    ("gpt-5.4-nano", "os-std-opt"),
    ("gemini-2.5-flash", "os-std"),
    ("gemini-2.5-flash", "os-std-opt"),
]
ROOT = "outputs/2026-04-29-00-01-35"


def load_runs(model, variant):
    path = os.path.join(ROOT, model, variant, "runs.jsonl")
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            yield json.loads(line)


def assistant_actions(conv):
    out = []
    for m in conv:
        if m.get("role") != "assistant":
            continue
        tcs = m.get("tool_calls") or []
        if not tcs:
            out.append(("none", ""))
            continue
        fn = tcs[0].get("function", {})
        out.append((fn.get("name", "?"), fn.get("arguments", "")))
    return out


def normalize_bash(arg):
    try:
        s = json.loads(arg).get("script", "")
    except Exception:
        s = arg
    return re.sub(r"\s+", " ", s).strip().lower()


def has_truncation(conv):
    for m in conv:
        if m.get("role") == "tool":
            c = m.get("content", "") or ""
            if "truncate" in c.lower():
                return True
    return False


def classify(rec):
    res = rec["output"]["result"]
    passed = bool(res.get("result"))
    conv = res["conversation"]
    actions = assistant_actions(conv)
    nrounds = len(actions)
    last = actions[-1][0] if actions else "none"

    if passed:
        return "PASS", nrounds, actions

    # repetitive bash detection (>=3 same normalized bash in a window of 4)
    bashes = [normalize_bash(a) for n, a in actions if n == "bash_action"]
    repetitive = False
    for i in range(len(bashes) - 2):
        if bashes[i] == bashes[i+1] == bashes[i+2]:
            repetitive = True; break
    # near-duplicate (same first 30 chars repeated)
    if not repetitive and len(bashes) >= 4:
        prefixes = [b[:30] for b in bashes]
        c = Counter(prefixes)
        if c.most_common(1)[0][1] >= 4:
            repetitive = True

    if last == "finish_action":
        cat = "PREMATURE_FINISH"
    elif last == "answer_action" and nrounds <= 3:
        cat = "WRONG_ANSWER_FAST"
    elif last == "answer_action":
        cat = "WRONG_ANSWER_LATE"
    elif nrounds >= 8:
        cat = "ROUND_LIMIT"
    else:
        cat = "OTHER"

    if repetitive and cat in {"ROUND_LIMIT", "OTHER", "WRONG_ANSWER_LATE"}:
        cat = "REPETITIVE_BASH"

    if has_truncation(conv) and cat == "ROUND_LIMIT":
        cat = "TRUNCATION_FAIL"

    return cat, nrounds, actions


def main():
    summary = {}
    samples = defaultdict(list)
    for model, variant in RUNS:
        cats = Counter()
        total = 0
        passed = 0
        for rec in load_runs(model, variant):
            total += 1
            cat, nrounds, actions = classify(rec)
            if cat == "PASS":
                passed += 1
                continue
            cats[cat] += 1
            if len(samples[(model, variant, cat)]) < 2:
                samples[(model, variant, cat)].append(
                    (rec["index"], nrounds, actions)
                )
        summary[(model, variant)] = (total, passed, cats)

    print("=" * 78)
    print("FAILURE TAXONOMY -- 2026-04-29 run (144 tasks each)")
    print("=" * 78)
    cat_order = [
        "PREMATURE_FINISH",
        "WRONG_ANSWER_FAST",
        "WRONG_ANSWER_LATE",
        "ROUND_LIMIT",
        "REPETITIVE_BASH",
        "TRUNCATION_FAIL",
        "OTHER",
    ]
    header = f"{'category':<20}"
    for m, v in RUNS:
        header += f"{m[:8]}/{v[-3:]:<5}"
    print(header)
    for cat in cat_order:
        line = f"{cat:<20}"
        for k in RUNS:
            line += f"{summary[k][2].get(cat, 0):<13}"
        print(line)
    print("-" * 78)
    line = f"{'TOTAL FAILED':<20}"
    for k in RUNS:
        total, passed, _ = summary[k]
        line += f"{total - passed:<13}"
    print(line)
    line = f"{'PASS':<20}"
    for k in RUNS:
        total, passed, _ = summary[k]
        line += f"{passed:<13}"
    print(line)

    print()
    print("=" * 78)
    print("SAMPLE FAILED CONVERSATIONS (action skeletons)")
    print("=" * 78)
    interesting = ["PREMATURE_FINISH", "WRONG_ANSWER_FAST", "ROUND_LIMIT", "REPETITIVE_BASH"]
    for cat in interesting:
        print(f"\n--- {cat} ---")
        for (model, variant, c), recs in samples.items():
            if c != cat:
                continue
            for idx, nrounds, actions in recs[:1]:
                print(f"[{model}/{variant}] task#{idx} ({nrounds} actions)")
                for n, args in actions:
                    a = args[:80].replace("\n", " ")
                    print(f"   - {n}({a})")
                print()


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    main()
