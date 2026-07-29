#!/usr/bin/env bash
# ─── 知识库强制检查钩子 ──────────────────────────────────────────
# 在 edit_file / write_file 之前检查 AI 是否已查询过知识库。
# 如果尚未查询，阻止操作并要求先查 dao-distill-mcp。
# 跨平台：macOS / Linux / Windows (Git Bash)
# ────────────────────────────────────────────────────────────────

FLAG_FILE="${TMPDIR:-/tmp}/atomcode_kb_$(whoami).flag"

if [ -f "$FLAG_FILE" ]; then
    # 已经查过知识库，放行
    echo '{"action":"allow"}'
    exit 0
fi

# 未查询知识库 → 阻止，并提示
TOOL_NAME="${ATOMCODE_TOOL_NAME:-unknown}"
cat <<EOF
{"action":"block","reason":"⚠️ 检测到您正在修改代码（${TOOL_NAME}），但当前会话尚未查询过知识库。请先通过 dao-distill-mcp 的 search_vault 搜索相关经验，然后再执行修改。"}
EOF
exit 0
