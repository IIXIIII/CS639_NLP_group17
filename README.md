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

This project investigates the generalization ability of **LLM-based agents** in interactive environments.

We use the **Operating System (OS) domain of AgentBench**, where an agent must translate natural language instructions into executable **bash commands** and interact with the system environment.

Tasks involve:

- Retrieving information from the system (**QA tasks**)
- Modifying system state using shell commands (**operation tasks**)

The OS benchmark contains **144 test tasks** with an average of **~8 interaction rounds per task**.

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
│   │   └── os_interaction/      # OS task logic (Docker + bash interaction loop)
│   ├── typings/                 # Data structures and type definitions
│   └── utils/                   # Max-flow algorithm, helpers
├── configs/
│   ├── tasks/os.yaml            # OS task definition (tools, docker image, data paths)
│   ├── assignments/default.yaml # Which agent runs which task
│   ├── assignments/definition.yaml # Agent & task factory config
│   └── agents/openai-chat.yaml  # OpenAI API agent config (put API key here)
├── data/os_interaction/
│   ├── data/                    # 144 task JSON files (7 categories)
│   ├── scripts/                 # Init, check, and example scripts per category
│   └── res/dockerfiles/         # Docker image definitions for task environments
├── extra/
│   └── docker-compose.yml       # Reference compose file (not used in our setup)
└── requirements.txt
```

---

## Project Goals

1. Run baseline evaluations of LLM agents on OS tasks
2. Perform exploratory **dataset analysis**
3. Analyze common **failure modes** in multi-step tasks
4. Explore potential improvements for agent performance

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

```bash
export DOCKER_HOST=unix:///run/user/$(id -u)/docker.sock
docker run --rm -p 5020:5020 jingyuh/agentrl-controller:latest controller
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

Wait until you see the worker registered successfully.

**Terminal 3 — Run the Assigner (starts evaluation):**

```bash
export DOCKER_HOST=unix:///run/user/$(id -u)/docker.sock
python -m src.assigner --config configs/assignments/default.yaml
```

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

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `No module named src.start_task` | `src.start_task` is not in this repo | Use `python -m agentrl.worker` directly (see Step 7) |
| `Connection refused` on port 5020 | Controller not running | Start controller first (Terminal 1) |
| `permission denied` on Docker socket | Wrong `DOCKER_HOST` or daemon not started | Run `systemctl --user start docker` and set `DOCKER_HOST` |
| `path not found` for dockerfiles | Wrong working directory | Make sure you are in the repo root (`cd CS639_NLP_group17`) |
