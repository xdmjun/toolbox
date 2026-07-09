#!/usr/bin/env bash
# ============================================================================
# install.sh — 远程一键安装 toolbox 技能到项目或 AI 编程工具（macOS / Linux）
#
# 用法（curl 管道）：
#   curl -fsSL https://你的域名/path/to/install.sh | bash
#   curl -fsSL https://你的域名/path/to/install.sh | bash -s -- --to claude --common
#
# 或下载到本地执行：
#   curl -fsSL -o install.sh https://你的域名/path/to/install.sh
#   chmod +x install.sh
#   ./install.sh --to claude --common
#
# 环境变量：
#   TOOLBOX_REPO  — toolbox 仓库地址（默认见下文）
# ============================================================================
set -euo pipefail

# ── 默认配置 ─────────────────────────────────────────────
DEFAULT_REPO_URL="https://github.com/atomgit-atomcode/toolbox"
DEFAULT_BRANCH="main"
CACHE_DIR="${HOME}/.cache/toolbox"
REPO_DIR="${CACHE_DIR}/repo"

# ── 颜色 ─────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ── 工具函数 ─────────────────────────────────────────────

log()  { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }
err()  { echo -e "${RED}✗${NC} $1" >&2; }
info() { echo -e "${CYAN}›${NC} $1"; }
banner() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║   Toolbox Skills Installer (Bash)       ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
    echo ""
}

usage() {
    cat <<EOF
用法: $(basename "$0") [选项]

选项：
  远程安装（curl | bash 管道）：
    curl -fsSL https://.../install.sh | bash -s -- [选项]

  项目安装：
    -t, --target <path>     目标项目目录（默认：当前目录）
    -d, --dir <name>        目标目录名（默认：skills）

  全局安装（AI 工具）：
    --to <tool>             安装到 AI 工具：claudecode, cursor, workbuddy, windsurf, trae, atomcode, codex
    -g, --global            自动检测本机已安装的 AI 工具

  技能选择（默认安装常用技能）：
    -c, --category <id>     只安装指定分类
    -s, --skills <list>     只安装指定技能（逗号分隔）
    --common                安装常用技能（14 个）
    -i, --interactive       交互式选择

  其他：
    -f, --force             覆盖已有目录
    -n, --dry-run           预览操作
    --repo-url <url>        自定义 toolbox 仓库地址
    --branch <name>         指定仓库分支
    --clean-cache           清理缓存后重新下载
    -h, --help              显示此帮助

示例：
    curl -fsSL https://raw.atomgit.com/atomgit_atomcode/atomcode/raw/main/scripts/install.sh | bash
    curl -fsSL https://raw.atomgit.com/atomgit_atomcode/atomcode/raw/main/scripts/install.sh | bash -s -- --to claude --common
EOF
    exit 0
}

# ── 命令行解析 ───────────────────────────────────────────

ARGS=()
SKILL_SELECTED=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        -t|--target)       TARGET="$2"; shift 2 ;;
        -d|--dir)          DIR="$2"; shift 2 ;;
        --to)              TO="$2"; shift 2 ;;
        -g|--global)       GLOBAL=true; shift ;;
        -c|--category)     CATEGORY="$2"; SKILL_SELECTED=true; shift 2 ;;
        -s|--skills)       SKILLS="$2"; SKILL_SELECTED=true; shift 2 ;;
        --common)          COMMON=true; SKILL_SELECTED=true; shift ;;
        -i|--interactive)  INTERACTIVE=true; SKILL_SELECTED=true; shift ;;
        -f|--force)        FORCE=true; shift ;;
        -n|--dry-run)      DRY_RUN=true; shift ;;
        --repo-url)        REPO_URL="$2"; shift 2 ;;
        --branch)          BRANCH="$2"; shift 2 ;;
        --clean-cache)     CLEAN_CACHE=true; shift ;;
        -h|--help)         usage ;;
        *)                 err "未知参数: $1"; usage ;;
    esac
done

# ── 默认值 ───────────────────────────────────────────────

TARGET="${TARGET:-$(pwd)}"
DIR="${DIR:-skills}"
TO="${TO:-}"
GLOBAL="${GLOBAL:-false}"
CATEGORY="${CATEGORY:-}"
SKILLS="${SKILLS:-}"
COMMON="${COMMON:-false}"
INTERACTIVE="${INTERACTIVE:-false}"
FORCE="${FORCE:-false}"
DRY_RUN="${DRY_RUN:-false}"
REPO_URL="${REPO_URL:-${TOOLBOX_REPO:-$DEFAULT_REPO_URL}}"
BRANCH="${BRANCH:-$DEFAULT_BRANCH}"
CLEAN_CACHE="${CLEAN_CACHE:-false}"

# ── 下载 / 更新 toolbox ──────────────────────────────────

ensure_toolbox() {
    if [[ "$CLEAN_CACHE" == "true" ]] && [[ -d "$REPO_DIR" ]]; then
        warn "清理缓存..."
        rm -rf "$REPO_DIR"
    fi

    if [[ -f "${REPO_DIR}/install_skills.py" ]]; then
        info "使用缓存: ${REPO_DIR}"
        # 尝试更新
        (cd "$REPO_DIR" && git pull --ff-only 2>/dev/null) && log "已更新到最新" || warn "更新失败，使用缓存版本"
    else
        info "下载 toolbox 从 ${REPO_URL} ..."
        mkdir -p "$CACHE_DIR"
        git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$REPO_DIR" 2>/dev/null || {
            err "下载失败，请检查仓库地址和网络"
            exit 1
        }
        log "下载完成"
    fi
}

# ── 构建 install_skills.py 参数 ──────────────────────────

build_py_args() {
    PY_ARGS=()
    PY_ARGS+=(--target "$TARGET")

    [[ "$DIR" != "skills" ]]          && PY_ARGS+=(--dir "$DIR")
    [[ -n "$TO" ]]                    && PY_ARGS+=(--to "$TO")
    [[ "$GLOBAL" == "true" ]]         && PY_ARGS+=(--global)
    [[ -n "$CATEGORY" ]]              && PY_ARGS+=(--category "$CATEGORY")
    [[ -n "$SKILLS" ]]                && PY_ARGS+=(--skills "$SKILLS")
    [[ "$COMMON" == "true" ]]         && PY_ARGS+=(--common)
    [[ "$INTERACTIVE" == "true" ]]    && PY_ARGS+=(--interactive)
    [[ "$FORCE" == "true" ]]          && PY_ARGS+=(--force)
    [[ "$DRY_RUN" == "true" ]]        && PY_ARGS+=(--dry-run)

    # 未指定技能选择时默认 --common
    if [[ "$SKILL_SELECTED" == "false" ]]; then
        PY_ARGS+=(--common)
    fi
}

# ── 入口 ─────────────────────────────────────────────────

main() {
    banner

    ensure_toolbox

    build_py_args

    INSTALL_SCRIPT="${REPO_DIR}/install_skills.py"
    if [[ ! -f "$INSTALL_SCRIPT" ]]; then
        err "未找到 install_skills.py，请检查仓库地址"
        exit 1
    fi

    info "运行: python install_skills.py ${PY_ARGS[*]}"
    echo ""

    # 设置 TOOLBOX_PATH 确保脚本能找到 skills/
    export TOOLBOX_PATH="$REPO_DIR"

    python3 "$INSTALL_SCRIPT" "${PY_ARGS[@]}" || {
        err "安装失败"
        exit 1
    }

    log "安装完成"
}

main
