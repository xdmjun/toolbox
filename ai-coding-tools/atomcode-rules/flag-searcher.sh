#!/usr/bin/env bash
# ─── 知识库查询标记脚本 ──────────────────────────────────────
# 当 AI 调用 dao-distill-mcp 的搜索/读取接口时，
# 创建标记文件，表示"已查询过知识库"。
# 跨平台：macOS / Linux / Windows (Git Bash)
# ─────────────────────────────────────────────────────────────

FLAG_FILE="${TMPDIR:-/tmp}/atomcode_kb_$(whoami).flag"
touch "$FLAG_FILE"
echo '{"action":"allow"}'
exit 0
