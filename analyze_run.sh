#!/usr/bin/env bash
# Analyze all runs.jsonl files under a given output directory.
# Usage: bash analyze_run.sh [output_dir]
# Default: outputs/2026-04-29-00-01-35

set -euo pipefail

OUTPUT_DIR="${1:-outputs/2026-04-29-00-01-35}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR"
source ~/myenv/bin/activate

find "$OUTPUT_DIR" -name "runs.jsonl" | sort | while read -r runs_file; do
    agent_task=$(echo "$runs_file" | sed "s|$OUTPUT_DIR/||" | sed 's|/runs.jsonl||')
    out_dir="analysis/plots/${OUTPUT_DIR##*/}/${agent_task}"
    mkdir -p "$out_dir"
    echo "=== Analyzing: $agent_task ==="
    python analysis/analyze_results.py --runs "$runs_file" --output-dir "$out_dir"
    echo ""
done

echo "Done. Plots saved under analysis/plots/${OUTPUT_DIR##*/}/"
