"""
Analysis script for AgentBench OS task evaluation results.
Usage: python analysis/analyze_results.py --runs outputs/<timestamp>/gpt-5.4-nano/os-std/runs.jsonl
"""

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np


def load_runs(path: str) -> list[dict]:
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def parse_record(record: dict) -> dict:
    output = record.get("output", {})
    result = output.get("result", {})
    conversation = result.get("conversation", [])

    # Count rounds (excluding system message)
    rounds = sum(1 for m in conversation if m.get("role") == "assistant")

    # Extract tool calls
    tool_calls = []
    for m in conversation:
        if m.get("role") == "assistant" and m.get("tool_calls"):
            for tc in m["tool_calls"]:
                tool_calls.append(tc["function"]["name"])

    # Final action
    final_action = tool_calls[-1] if tool_calls else None

    return {
        "index": record.get("index"),
        "status": output.get("status"),
        "score": result.get("score", 0.0),
        "passed": result.get("result", False),
        "rounds": rounds,
        "tool_calls": tool_calls,
        "final_action": final_action,
        "timestamp": record.get("time", {}).get("str"),
    }


# ── text sections ──────────────────────────────────────────────────────────────

def section_accuracy(parsed: list[dict]) -> str:
    total = len(parsed)
    passed = sum(1 for r in parsed if r["passed"])
    lines = [
        "=" * 50,
        "  ACCURACY",
        "=" * 50,
        f"  Total tasks : {total}",
        f"  Passed      : {passed}",
        f"  Failed      : {total - passed}",
        f"  Accuracy    : {passed / total * 100:.1f}%",
        "",
    ]
    return "\n".join(lines)


def section_round_stats(parsed: list[dict]) -> str:
    rounds = [r["rounds"] for r in parsed]
    if not rounds:
        return ""
    dist = defaultdict(int)
    for r in rounds:
        dist[r] += 1
    lines = [
        "=" * 50,
        "  INTERACTION ROUNDS",
        "=" * 50,
        f"  Mean   : {sum(rounds) / len(rounds):.2f}",
        f"  Min    : {min(rounds)}",
        f"  Max    : {max(rounds)}",
        "",
        "  Distribution:",
    ]
    for k in sorted(dist):
        bar = "█" * dist[k]
        lines.append(f"    {k:2d} rounds : {bar} ({dist[k]})")
    lines.append("")
    return "\n".join(lines)


def section_tool_usage(parsed: list[dict]) -> str:
    counter = defaultdict(int)
    for r in parsed:
        for tc in r["tool_calls"]:
            counter[tc] += 1
    total_calls = sum(counter.values())
    lines = [
        "=" * 50,
        "  TOOL CALL USAGE",
        "=" * 50,
    ]
    for name, count in sorted(counter.items(), key=lambda x: -x[1]):
        pct = count / total_calls * 100 if total_calls else 0
        lines.append(f"  {name:<25} {count:4d}  ({pct:.1f}%)")
    lines.append("")
    return "\n".join(lines)


def section_final_action(parsed: list[dict]) -> str:
    counter = defaultdict(lambda: {"total": 0, "passed": 0})
    for r in parsed:
        fa = r["final_action"] or "none"
        counter[fa]["total"] += 1
        if r["passed"]:
            counter[fa]["passed"] += 1
    lines = [
        "=" * 50,
        "  FINAL ACTION BREAKDOWN",
        "=" * 50,
        f"  {'Action':<25} {'Total':>6} {'Passed':>7} {'Acc':>7}",
        f"  {'-'*25} {'-'*6} {'-'*7} {'-'*7}",
    ]
    for name, stats in sorted(counter.items()):
        acc = stats["passed"] / stats["total"] * 100 if stats["total"] else 0
        lines.append(f"  {name:<25} {stats['total']:>6} {stats['passed']:>7} {acc:>6.1f}%")
    lines.append("")
    return "\n".join(lines)


def section_failure_analysis(parsed: list[dict]) -> str:
    failed = [r for r in parsed if not r["passed"]]
    round_dist = defaultdict(int)
    for r in failed:
        round_dist[r["rounds"]] += 1
    max_round_fail = [r for r in failed if r["rounds"] >= 8]
    early_fail = [r for r in failed if r["rounds"] < 3]
    lines = [
        "=" * 50,
        "  FAILURE ANALYSIS",
        "=" * 50,
        f"  Total failed: {len(failed)}",
        "",
        "  Failed tasks by round count:",
    ]
    for k in sorted(round_dist):
        lines.append(f"    {k:2d} rounds : {round_dist[k]}")
    lines += [
        "",
        f"  Hit round limit (8 rounds) and failed: {len(max_round_fail)}",
        f"  Failed in < 3 rounds: {len(early_fail)}",
        "",
    ]
    return "\n".join(lines)


def section_passed_vs_failed_rounds(parsed: list[dict]) -> str:
    passed = [r["rounds"] for r in parsed if r["passed"]]
    failed = [r["rounds"] for r in parsed if not r["passed"]]
    lines = [
        "=" * 50,
        "  AVG ROUNDS: PASSED vs FAILED",
        "=" * 50,
    ]
    if passed:
        lines.append(f"  Passed tasks avg rounds : {sum(passed) / len(passed):.2f}")
    if failed:
        lines.append(f"  Failed tasks avg rounds : {sum(failed) / len(failed):.2f}")
    lines.append("")
    return "\n".join(lines)


# ── plots ──────────────────────────────────────────────────────────────────────

def plot_accuracy(parsed: list[dict], out_dir: str):
    total = len(parsed)
    passed = sum(1 for r in parsed if r["passed"])
    failed = total - passed

    fig, ax = plt.subplots(figsize=(5, 4))
    bars = ax.bar(["Passed", "Failed"], [passed, failed],
                  color=["#4caf50", "#f44336"], width=0.45, edgecolor="white")
    for bar, val in zip(bars, [passed, failed]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                str(val), ha="center", va="bottom", fontweight="bold")
    ax.set_title(f"Task Accuracy  ({passed}/{total} = {passed/total*100:.1f}%)", fontsize=13)
    ax.set_ylabel("Number of Tasks")
    ax.set_ylim(0, max(passed, failed) * 1.2 + 1)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "accuracy.png"), dpi=150)
    plt.close(fig)


def plot_round_distribution(parsed: list[dict], out_dir: str):
    rounds_pass = [r["rounds"] for r in parsed if r["passed"]]
    rounds_fail = [r["rounds"] for r in parsed if not r["passed"]]
    all_rounds = sorted(set(rounds_pass + rounds_fail))
    if not all_rounds:
        return

    x = np.arange(len(all_rounds))
    w = 0.35
    cnt_pass = [rounds_pass.count(k) for k in all_rounds]
    cnt_fail = [rounds_fail.count(k) for k in all_rounds]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(x - w/2, cnt_pass, w, label="Passed", color="#4caf50", edgecolor="white")
    ax.bar(x + w/2, cnt_fail, w, label="Failed", color="#f44336", edgecolor="white")
    ax.set_xticks(x)
    ax.set_xticklabels([str(k) for k in all_rounds])
    ax.set_xlabel("Number of Rounds")
    ax.set_ylabel("Number of Tasks")
    ax.set_title("Round Distribution (Passed vs Failed)")
    ax.legend()
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "round_distribution.png"), dpi=150)
    plt.close(fig)


def plot_tool_usage(parsed: list[dict], out_dir: str):
    counter = defaultdict(int)
    for r in parsed:
        for tc in r["tool_calls"]:
            counter[tc] += 1
    if not counter:
        return
    names = [n for n, _ in sorted(counter.items(), key=lambda x: -x[1])]
    counts = [counter[n] for n in names]

    fig, ax = plt.subplots(figsize=(max(7, len(names) * 0.9), 4))
    colors = plt.cm.tab10(np.linspace(0, 1, len(names)))
    bars = ax.bar(names, counts, color=colors, edgecolor="white")
    for bar, val in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                str(val), ha="center", va="bottom", fontsize=8)
    ax.set_title("Tool Call Usage")
    ax.set_ylabel("Call Count")
    ax.set_xticklabels(names, rotation=30, ha="right", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "tool_usage.png"), dpi=150)
    plt.close(fig)


def plot_passed_vs_failed_rounds(parsed: list[dict], out_dir: str):
    passed = [r["rounds"] for r in parsed if r["passed"]]
    failed = [r["rounds"] for r in parsed if not r["passed"]]
    if not passed and not failed:
        return

    labels, means, colors = [], [], []
    if passed:
        labels.append(f"Passed\n(n={len(passed)})")
        means.append(sum(passed) / len(passed))
        colors.append("#4caf50")
    if failed:
        labels.append(f"Failed\n(n={len(failed)})")
        means.append(sum(failed) / len(failed))
        colors.append("#f44336")

    fig, ax = plt.subplots(figsize=(5, 4))
    bars = ax.bar(labels, means, color=colors, width=0.45, edgecolor="white")
    for bar, val in zip(bars, means):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                f"{val:.2f}", ha="center", va="bottom", fontweight="bold")
    ax.set_title("Average Rounds: Passed vs Failed")
    ax.set_ylabel("Avg Rounds")
    ax.set_ylim(0, max(means) * 1.25 + 0.5)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "avg_rounds_passed_vs_failed.png"), dpi=150)
    plt.close(fig)


def plot_final_action_accuracy(parsed: list[dict], out_dir: str):
    counter = defaultdict(lambda: {"total": 0, "passed": 0})
    for r in parsed:
        fa = r["final_action"] or "none"
        counter[fa]["total"] += 1
        if r["passed"]:
            counter[fa]["passed"] += 1
    if not counter:
        return

    names = sorted(counter.keys())
    accs = [counter[n]["passed"] / counter[n]["total"] * 100 for n in names]
    totals = [counter[n]["total"] for n in names]

    fig, ax = plt.subplots(figsize=(max(7, len(names) * 0.9), 4))
    colors = ["#4caf50" if a >= 50 else "#f44336" for a in accs]
    bars = ax.bar(names, accs, color=colors, edgecolor="white")
    for bar, acc, tot in zip(bars, accs, totals):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                f"{acc:.0f}%\n(n={tot})", ha="center", va="bottom", fontsize=8)
    ax.set_title("Accuracy by Final Action")
    ax.set_ylabel("Pass Rate (%)")
    ax.set_ylim(0, 120)
    ax.axhline(50, color="gray", linestyle="--", linewidth=0.8)
    ax.set_xticklabels(names, rotation=30, ha="right", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "final_action_accuracy.png"), dpi=150)
    plt.close(fig)


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Analyze AgentBench OS task results")
    parser.add_argument("--runs", type=str, default=None, help="Path to runs.jsonl file")
    parser.add_argument("--output-dir", type=str, default="/home/jingyuh/CS639_NLP_group17/analysis",
                        help="Directory to save report and plots (default: same folder as runs.jsonl)")
    args = parser.parse_args()

    # Auto-find latest runs.jsonl if not specified
    if args.runs is None:
        output_dirs = sorted(Path("outputs").glob("*/*/os-std/runs.jsonl"))
        if not output_dirs:
            print("No runs.jsonl found. Run: python -m src.assigner first.")
            return
        runs_path = str(output_dirs[-1])
        print(f"Auto-detected: {runs_path}\n")
    else:
        runs_path = args.runs

    records = load_runs(runs_path)
    parsed = [parse_record(r) for r in records]

    header = (
        f"Results from : {runs_path}\n"
        f"Model        : {Path(runs_path).parts[-3]}\n\n"
    )

    report = (
        header
        + section_accuracy(parsed)
        + section_round_stats(parsed)
        + section_passed_vs_failed_rounds(parsed)
        + section_tool_usage(parsed)
        + section_final_action(parsed)
        + section_failure_analysis(parsed)
    )

    # Print to terminal
    print(report)

    # Determine output directory:
    # If --output-dir is given explicitly, use it directly (no subdirectory added).
    # Otherwise, derive a unique subdirectory from the runs.jsonl path so that
    # multiple runs never overwrite each other.
    #   e.g. outputs/2026-04-04-17-03-53/gpt-5.4-nano/os-std/runs.jsonl
    #        → analysis/2026-04-04-17-03-53_gpt-5.4-nano/
    if args.output_dir != parser.get_default("output_dir"):
        out_dir = args.output_dir
    else:
        p = Path(runs_path)
        # parts[-4] = timestamp, parts[-3] = model name
        try:
            run_tag = f"{p.parts[-4]}_{p.parts[-3]}"
        except IndexError:
            run_tag = p.parent.name
        base_dir = Path(__file__).parent  # analysis/
        out_dir = str(base_dir / run_tag)

    figures_dir = os.path.join(out_dir, "figures")
    os.makedirs(figures_dir, exist_ok=True)

    # Save text report
    report_path = os.path.join(out_dir, "report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"[saved] {report_path}")

    # Save plots
    plot_accuracy(parsed, figures_dir)
    print(f"[saved] {figures_dir}/accuracy.png")

    plot_round_distribution(parsed, figures_dir)
    print(f"[saved] {figures_dir}/round_distribution.png")

    plot_tool_usage(parsed, figures_dir)
    print(f"[saved] {figures_dir}/tool_usage.png")

    plot_passed_vs_failed_rounds(parsed, figures_dir)
    print(f"[saved] {figures_dir}/avg_rounds_passed_vs_failed.png")

    plot_final_action_accuracy(parsed, figures_dir)
    print(f"[saved] {figures_dir}/final_action_accuracy.png")

    print(f"\nAll outputs saved to: {out_dir}")


if __name__ == "__main__":
    main()