#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# run_eval.sh  —  一键启动 AgentBench OS 评测流水线
#
# 用法:
#   bash run_eval.sh            # 正常跑
#   bash run_eval.sh --dry-run  # 只检查环境，不真正启动
#   bash run_eval.sh --skip-build  # 跳过 docker build（镜像已存在时用）
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── 颜色输出 ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ── 参数解析 ──────────────────────────────────────────────────────────────────
DRY_RUN=false
SKIP_BUILD=false
for arg in "$@"; do
    case $arg in
        --dry-run)    DRY_RUN=true ;;
        --skip-build) SKIP_BUILD=true ;;
        *) error "Unknown argument: $arg"; exit 1 ;;
    esac
done

# ── 路径配置 ──────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$HOME/myenv"
CONTROLLER_BIN="$HOME/agentrl-controller"
DOCKER_HOST_SOCK="unix:///run/user/$(id -u)/docker.sock"

export DOCKER_HOST="$DOCKER_HOST_SOCK"

# ── 工具函数 ──────────────────────────────────────────────────────────────────
cleanup() {
    info "清理后台进程..."
    # 杀掉本脚本启动的后台进程
    [[ -n "${CONTROLLER_PID:-}" ]] && kill "$CONTROLLER_PID" 2>/dev/null && info "Controller stopped"
    [[ -n "${WORKER_PID:-}" ]]     && kill "$WORKER_PID"     2>/dev/null && info "Worker stopped"
    exit 0
}
trap cleanup SIGINT SIGTERM

wait_for_port() {
    local port=$1 label=$2 timeout=${3:-30}
    info "等待 $label (port $port) 就绪..."
    for i in $(seq 1 $timeout); do
        if curl -sf "http://localhost:$port" >/dev/null 2>&1 \
           || curl -sf "http://localhost:$port/api/list_workers" >/dev/null 2>&1; then
            success "$label 已就绪"
            return 0
        fi
        sleep 1
    done
    error "$label 在 ${timeout}s 内未就绪，检查日志: logs/"
    return 1
}

# ─────────────────────────────────────────────────────────────────────────────
# Step 0: 前置检查
# ─────────────────────────────────────────────────────────────────────────────
info "========== 环境检查 =========="

# Python venv
if [[ ! -f "$VENV/bin/activate" ]]; then
    error "找不到 venv: $VENV"
    exit 1
fi
success "venv: $VENV"

# Controller binary
if [[ ! -x "$CONTROLLER_BIN" ]]; then
    error "找不到 controller binary: $CONTROLLER_BIN"
    exit 1
fi
success "controller: $CONTROLLER_BIN"

# Docker
systemctl --user start docker 2>/dev/null || true
if ! docker info >/dev/null 2>&1; then
    error "Docker 不可用，尝试: systemctl --user start docker"
    exit 1
fi
success "Docker: $DOCKER_HOST_SOCK"

# OpenAI key（只检查 configs 里有没有 key）
KEY_IN_CONFIG=$(grep -r "Authorization: Bearer " "$SCRIPT_DIR/configs/" 2>/dev/null | grep -v "Bearer $" | head -1 || true)
if [[ -z "$KEY_IN_CONFIG" ]]; then
    warn "configs 里没有检测到 OpenAI key，请确认 configs/agents/openai-chat.yaml 已填写 Authorization"
fi

if $DRY_RUN; then
    success "Dry-run 完成，环境检查通过"
    exit 0
fi

cd "$SCRIPT_DIR"
mkdir -p logs

# ─────────────────────────────────────────────────────────────────────────────
# Step 1: 构建 Docker 镜像
# ─────────────────────────────────────────────────────────────────────────────
if $SKIP_BUILD; then
    warn "跳过 Docker 镜像构建 (--skip-build)"
else
    info "========== 构建 Docker 镜像 =========="
    DOCKERFILE_DIR="data/os_interaction/res/dockerfiles"
    for img in default packages ubuntu; do
        if docker image inspect "local-os/$img" >/dev/null 2>&1; then
            info "镜像 local-os/$img 已存在，跳过"
        else
            info "构建 local-os/$img ..."
            docker build -t "local-os/$img" \
                -f "$DOCKERFILE_DIR/$img" \
                "$DOCKERFILE_DIR/" \
                > "logs/docker_build_${img}.log" 2>&1
            success "local-os/$img 构建完成"
        fi
    done
fi

# ─────────────────────────────────────────────────────────────────────────────
# 工具: 清理占用指定端口的进程
# ─────────────────────────────────────────────────────────────────────────────
kill_port() {
    local port=$1
    local pids
    pids=$(lsof -ti:"$port" 2>/dev/null || true)
    if [[ -n "$pids" ]]; then
        warn "端口 $port 被占用 (PID: $pids)，正在清理..."
        echo "$pids" | xargs kill -9 2>/dev/null || true
        sleep 1
        if lsof -i:"$port" >/dev/null 2>&1; then
            error "端口 $port 清理失败，请手动执行: kill -9 \$(lsof -ti:$port)"
            exit 1
        fi
        success "端口 $port 已释放"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Step 2: 启动 Controller
# ─────────────────────────────────────────────────────────────────────────────
info "========== 启动 Controller (port 5020) =========="

kill_port 5020

"$CONTROLLER_BIN" controller \
    > logs/controller.log 2>&1 &
CONTROLLER_PID=$!
info "Controller PID: $CONTROLLER_PID (logs/controller.log)"
sleep 2
if ! kill -0 "$CONTROLLER_PID" 2>/dev/null; then
    error "Controller 启动失败，查看: logs/controller.log"
    tail -20 logs/controller.log
    exit 1
fi
success "Controller 已启动"

# ─────────────────────────────────────────────────────────────────────────────
# Step 3: 启动 Worker
# ─────────────────────────────────────────────────────────────────────────────
info "========== 启动 Worker (port 5021) =========="

kill_port 5021

if true; then
    source "$VENV/bin/activate"

    python -m agentrl.worker os-std \
        --config configs/tasks/os.yaml \
        --controller http://localhost:5020/api \
        --self http://localhost:5021/api \
        > logs/worker.log 2>&1 &
    WORKER_PID=$!
    info "Worker PID: $WORKER_PID (logs/worker.log)"

    # 等待 worker 注册成功
    info "等待 Worker 注册到 Controller..."
    for i in $(seq 1 30); do
        if grep -q "registered\|ALIVE\|started" logs/worker.log 2>/dev/null; then
            success "Worker 注册成功"
            break
        fi
        if ! kill -0 "$WORKER_PID" 2>/dev/null; then
            error "Worker 进程意外退出，查看: logs/worker.log"
            cat logs/worker.log | tail -20
            exit 1
        fi
        sleep 1
    done
fi

# 验证 worker 在 controller 里可见
sleep 2
WORKER_STATUS=$(curl -sf http://localhost:5020/api/list_workers 2>/dev/null || echo "{}")
if echo "$WORKER_STATUS" | grep -q "os-std"; then
    success "Worker 在 Controller 中可见 (os-std ALIVE)"
else
    warn "Worker 可能还未完全注册，继续启动 assigner..."
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 4: 启动 Assigner（前台运行，显示进度）
# ─────────────────────────────────────────────────────────────────────────────
info "========== 启动 Assigner =========="
info "评测开始，结果将保存到 outputs/<timestamp>/"
info "按 Ctrl+C 可中断（已完成的任务会保存，下次可断点续跑）"
echo ""

source "$VENV/bin/activate"
python -m src.assigner --config configs/assignments/default.yaml

# ─────────────────────────────────────────────────────────────────────────────
# Step 5: 评测完成，自动分析
# ─────────────────────────────────────────────────────────────────────────────
echo ""
success "========== 评测完成，开始分析结果 =========="

LATEST_RUNS=$(find outputs -name "runs.jsonl" | sort | tail -1)
if [[ -n "$LATEST_RUNS" ]]; then
    info "分析: $LATEST_RUNS"
    python analysis/analyze_results.py --runs "$LATEST_RUNS"
else
    warn "未找到 runs.jsonl，跳过分析"
fi

cleanup