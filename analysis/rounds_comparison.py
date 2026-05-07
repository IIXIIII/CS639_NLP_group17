"""Comparative trajectory-length histogram: std vs opt for both models.

Output: analysis/figures/rounds_comparison.png
"""
import json
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent / "outputs" / "2026-04-29-00-01-35"
OUT = Path(__file__).resolve().parent / "figures" / "rounds_comparison.png"

MODELS = ["gpt-5.4-nano", "gemini-2.5-flash"]
PROMPTS = [("os-std", "std", "#4c72b0"), ("os-std-opt", "opt", "#dd8452")]


def rounds_of(record):
    conv = record["output"]["result"]["conversation"]
    return sum(1 for m in conv if m.get("role") == "assistant")


def load_rounds(path):
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(rounds_of(json.loads(line)))
    return out


def main():
    xs = np.arange(1, 9)
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 5.2), sharex=True)

    for ax, model in zip(axes, MODELS):
        bars_data = []
        for prompt_dir, label, color in PROMPTS:
            rounds = load_rounds(ROOT / model / prompt_dir / "runs.jsonl")
            c = Counter(rounds)
            counts = [c.get(k, 0) for k in xs]
            bars_data.append((label, counts, np.mean(rounds), color))

        width = 0.4
        for i, (label, counts, _, color) in enumerate(bars_data):
            offset = (i - 0.5) * width
            ax.bar(xs + offset, counts, width=width, label=label,
                   color=color, edgecolor="white")
            for x, h in zip(xs + offset, counts):
                if h > 0:
                    ax.text(x, h + 0.8, str(h), ha="center", va="bottom",
                            fontsize=7)

        mean_std, mean_opt = bars_data[0][2], bars_data[1][2]
        ax.set_title(
            f"{model}    mean rounds: std={mean_std:.2f}, opt={mean_opt:.2f}",
            fontsize=10.5,
        )
        ax.set_ylabel("# Tasks")
        ax.legend(loc="upper center", frameon=False, fontsize=9)
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_xticks(xs)
        ax.set_ylim(0, max(max(d[1]) for d in bars_data) * 1.18 + 2)

    axes[-1].set_xlabel("Number of interaction rounds")
    fig.suptitle("Trajectory length distribution: baseline vs optimized prompt",
                 fontsize=11.5, y=1.01)
    fig.tight_layout()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=160, bbox_inches="tight")
    print(f"saved: {OUT}")


if __name__ == "__main__":
    main()
