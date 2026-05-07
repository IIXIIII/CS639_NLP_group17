# LLM Agents in Operating System Environments

Course project on evaluating **LLM-based agents** using the **AgentBench Operating System (OS) domain**.  
Our goal is to study how LLM agents perform in **interactive command-line tasks** and analyze common **failure modes in long-horizon tasks**.

---

## Team Members and Responsibilities

| Member | Responsibility |
|---|---|
| Jingyu Huang | Method implementation: OS evaluation pipeline, prompt engineering, and model inference |
| Wanyi Chen | Literature review on LLM agents and long-horizon reasoning |
| Leyan Chen | Dataset analysis: exploratory analysis of OS tasks, task complexity, and horizon length |
| Yanting Guo | Experiment design and failure taxonomy |
| Guangwen Xiong | Project coordination, timeline planning, and report integration |
| Hunter Zhang | Slides for proposal and final presentation |

---

## Project Overview

This project investigates the failure modes of **LLM-based agents** on the
**Operating System (OS) domain of AgentBench**, where an agent must translate
a natural-language instruction into a sequence of executable **bash commands**
under an 8-round interaction cap.

Tasks fall into two types:

- Retrieving information from the system (**QA tasks**)
- Modifying system state using shell commands (**operation tasks**)

The OS benchmark contains **144 evaluation tasks**. We evaluate two
proprietary LLM agents — **gpt-5.4-nano** and **gemini-2.5-flash** —
under both:

- the **original AgentBench prompt** (`os-std`), and
- an **optimized prompt** (`os-std-opt`) that augments the system message
  with eight behavioral guidelines targeting commonly observed failure modes.

We then apply a **seven-category automatic failure taxonomy** to every
failed trajectory to characterize *which* failure modes the optimized prompt
mitigates and *which* it amplifies. Our central finding is that prompt-only
intervention does not strictly improve agent behavior; instead, it
**redistributes** failures across categories.

---

## Repository Structure

```
CS639_NLP_group17/
├── src/                         # Core framework code (from AgentBench FC)
│   ├── assigner.py              # Main evaluation orchestrator
│   ├── configs.py               # YAML config loader
│   ├── client/                  # Agent & TaskClient implementations
│   │   └── agents/              # HTTPAgent, ClaudeAgent, etc.
│   ├── server/tasks/
│   │   └── os_interaction/      # OS task logic (Docker + bash interaction loop;
│   │                            #   contains both os-std and os-std-opt prompts)
│   ├── typings/                 # Data structures and type definitions
│   └── utils/                   # Max-flow algorithm, helpers
├── configs/
│   ├── tasks/os.yaml            # OS task definition (defines os-std and os-std-opt)
│   ├── assignments/default.yaml # Which agent runs which task
│   ├── assignments/definition.yaml # Agent & task factory config
│   └── agents/openai-chat.yaml  # OpenAI API agent config (put API key here)
├── data/os_interaction/
│   ├── data/                    # 144 task JSON files (7 categories)
│   ├── scripts/                 # Init, check, and example scripts per category
│   └── res/dockerfiles/         # Docker image definitions for task environments
├── outputs/                     # Run outputs, organized by timestamp/model/prompt/
│   └── <ts>/<model>/<prompt>/runs.jsonl
├── analysis/                    # Post-run analysis tooling and figures
│   ├── analyze_results.py       # Per-run accuracy, round, tool-usage breakdowns
│   ├── failure_taxonomy.py      # 7-category automatic failure classifier
│   ├── rounds_comparison.py     # Comparative rounds histogram (std vs opt)
│   ├── plots/                   # Per-config figures
│   └── figures/                 # Cross-config figures (e.g. rounds_comparison.png)
├── 639_HW5/
│   └── latex/                   # ACL-style report sources (acl_latex.tex, custom.bib)
├── extra/
│   └── docker-compose.yml       # Reference compose file (not used in our setup)
└── requirements.txt
```

---

## Project Goals

1. Replicate the AgentBench-OS evaluation with two contemporary proprietary
   LLMs (gpt-5.4-nano and gemini-2.5-flash) under the original AgentBench
   prompt.
2. Construct an optimized prompt (`os-std-opt`) augmenting the system
   message with eight behavioral guidelines targeting common agent failure
   modes, and re-evaluate both models under it.
3. Build a seven-category **automatic failure taxonomy** that classifies
   every failed trajectory by inspecting its action sequence, enabling
   reproducible analysis from `runs.jsonl` alone.
4. Characterize **how** prompt-only intervention changes agent behavior:
   does it monotonically reduce failures, or does it redistribute them
   across categories?

## Key Results

| Model              | `os-std` | `os-std-opt` |  Δ        |
|--------------------|---------:|-------------:|----------:|
| gpt-5.4-nano       |   35.4 % |       46.5 % |  +11.1 pp |
| gemini-2.5-flash   |   42.4 % |       49.3 % |   +6.9 pp |

The optimized prompt yields consistent gains, but more than half of all 144
tasks still fail under every configuration. The failure taxonomy reveals
that the gains come from collapsing **under-exploration failures** (Premature
Finish, Snap Wrong Answer) — at the cost of new **Round-Limit Exhaustion**
and **Repetitive Bash** failures. The dominant failure mode is
model-specific, and prompt-only intervention does not strictly improve
behavior — it redistributes it. See `639_HW5/latex/acl_latex.tex` for the
full analysis.

---

## Setup & Running

### Prerequisites

- Python 3.10+
- Rootless Docker (or Docker with user permissions)
- An OpenAI API key



### Step 1: Create and activate a virtual environment

```bash
python3 -m venv myenv
source myenv/bin/activate
```

### Step 2: Clone the repository

```bash
git clone https://github.com/IIXIIII/CS639_NLP_group17.git
cd CS639_NLP_group17
```

### Step 3: Install dependencies

```bash
pip install agentrl-worker
pip install -r requirements.txt
```

### Step 4: Configure your API key

Edit `configs/agents/openai-chat.yaml` and replace the placeholder with your OpenAI key:

```yaml
Authorization: Bearer <YOUR_OPENAI_KEY_HERE>
```


### Step 5: Set up Docker (rootless Docker on shared servers)

If using a shared server where rootless Docker is configured:

```bash
# Start the rootless Docker daemon (if not already running)
systemctl --user start docker

```

Verify Docker is working:
```bash
docker info
```

### Step 6: Build the OS task Docker images (one-time setup)

```bash

docker build -t local-os/default \
  -f data/os_interaction/res/dockerfiles/default \
  data/os_interaction/res/dockerfiles/

docker build -t local-os/packages \
  -f data/os_interaction/res/dockerfiles/packages \
  data/os_interaction/res/dockerfiles/

docker build -t local-os/ubuntu \
  -f data/os_interaction/res/dockerfiles/ubuntu \
  data/os_interaction/res/dockerfiles/
```

### Step 7: Run the evaluation (3 terminals)

**Terminal 1 — Start the AgentRL Controller:**

> **Important:** The controller must run as a local binary, **not** via `docker run`. A containerized controller cannot reach the worker processes on the host.

```bash
export DOCKER_HOST=unix:///run/user/$(id -u)/docker.sock
/home/jingyuh/agentrl-controller controller
```

Wait until you see:
```
{"msg":"HTTP server started at :5020"}
```

**Terminal 2 — Start the OS Task Worker:**

```bash
export DOCKER_HOST=unix:///run/user/$(id -u)/docker.sock
python -m agentrl.worker os-std \
  --config configs/tasks/os.yaml \
  --controller http://localhost:5020/api \
  --self http://localhost:5021/api
```

To run the optimized prompt variant instead, replace `os-std` with
`os-std-opt`:

```bash
python -m agentrl.worker os-std-opt \
  --config configs/tasks/os.yaml \
  --controller http://localhost:5020/api \
  --self http://localhost:5021/api
```

Both variants are defined in `configs/tasks/os.yaml`; they share the same
144 tasks, tool definitions, and 8-round cap, and differ only in the system
message (the optimized variant appends eight additional behavioral
guidelines).

Wait until you see the worker registered successfully.

**Terminal 3 — Run the Assigner (starts evaluation):**

```bash
export DOCKER_HOST=unix:///run/user/$(id -u)/docker.sock
python -m src.assigner --config configs/assignments/default.yaml
```

Edit `configs/assignments/default.yaml` to select which model
(`gpt-5.4-nano` or `gemini-2.5-flash`) and which task variant (`os-std`
or `os-std-opt`) to run.

### Step 8: View results

Results are saved to:
```
outputs/{timestamp}/gpt-3.5-turbo-0613/os-std/
├── runs.jsonl       # Per-task results (success/fail + full interaction history)
├── error.jsonl      # Tasks that errored out
└── overall.json     # Aggregate accuracy
```

---

## How It Works

Each OS task runs the following loop (up to 8 rounds):

```
Agent receives task description
  └─► calls bash_action(script)  →  executes in isolated Docker container
  └─► calls answer_action(ans)   →  submits final answer
        └─► evaluated by string match or check script
              └─► result recorded
```

The framework consists of three components running simultaneously:
- **Controller** (`jingbh/agentrl-controller`): routes messages between assigner and workers
- **Task Worker** (`agentrl.worker`): manages Docker containers and runs the interaction loop
- **Assigner** (`src.assigner`): sends tasks to workers and collects results via the LLM agent

---

## Analysis

Once `runs.jsonl` files have been produced under `outputs/<timestamp>/`, the
scripts in `analysis/` reproduce all of the figures and statistics reported
in the paper.

### Per-run report (`analysis/analyze_results.py`)

For a single configuration, prints accuracy, mean rounds, tool-usage
breakdown, final-action breakdown, and per-round failure distribution; also
saves PNG plots:

```bash
python analysis/analyze_results.py \
  --runs outputs/<timestamp>/<model>/<prompt>/runs.jsonl
```

If `--runs` is omitted, the latest run under `outputs/` is used. Output is
written to `analysis/<timestamp>_<model>/`.

### Seven-category failure taxonomy (`analysis/failure_taxonomy.py`)

Classifies every failed trajectory across the four configurations into one
of seven categories (Premature Finish, Snap Wrong Answer, Late Wrong
Answer, Round-Limit Exhaustion, Repetitive Bash, Truncation Handling,
Other) and prints per-category counts and example task indices. The script
hardcodes the timestamped run directory (`outputs/2026-04-29-00-01-35/`) at
the top of the file — change it to point at a different run. Reproduces
Table 2 of the paper:

```bash
python analysis/failure_taxonomy.py
```

### Cross-config rounds histogram (`analysis/rounds_comparison.py`)

Loads all four configurations and produces the comparative
trajectory-length histogram (Figure 1 of the paper) at
`analysis/figures/rounds_comparison.png`:

```bash
python analysis/rounds_comparison.py
```

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `No module named src.start_task` | `src.start_task` is not in this repo | Use `python -m agentrl.worker` directly (see Step 7) |
| `Connection refused` on port 5020 | Controller not running | Start controller first (Terminal 1) |
| `permission denied` on Docker socket | Wrong `DOCKER_HOST` or daemon not started | Run `systemctl --user start docker` and set `DOCKER_HOST` |
| `path not found` for dockerfiles | Wrong working directory | Make sure you are in the repo root (`cd CS639_NLP_group17`) |
| `Invalid 'messages': empty array` | Redis not running — worker stores session state in Redis; without it conversation history is lost and an empty message array is sent to the API | Run `docker start redis` (if container exists) or `docker run -d --name redis -p 6379:6379 redis:7`, then restart the worker |
| Controller cannot reach workers / `Connection refused` from inside Docker | Controller started with `docker run` instead of the local binary | Stop the Docker-based controller and run `/home/jingyuh/agentrl-controller controller` directly on the host |
