#!/usr/bin/env bash
# ─── 危险命令拦截钩子 ──────────────────────────────────────────
# 在 bash 执行前检查是否包含危险操作，阻止需要用户确认的操作。
# 跨平台：macOS / Linux / Windows (Git Bash)
# ───────────────────────────────────────────────────────────────

CONTEXT="${ATOMCODE_HOOK_CONTEXT:-}"

# 危险命令模式列表
DANGER_PATTERNS=(
    'rm -rf'
    'rm -r -f'
    'rm --recursive'
    'git reset --hard'
    'git checkout .'
    'git checkout -- '
    'git clean -f'
    'git clean -fd'
    'git restore .'
    'del /F /S'
    'rd /s /q'
    'rmdir /s /q'
    'dd if='
)

for pattern in "${DANGER_PATTERNS[@]}"; do
    if echo "$CONTEXT" | grep -qiF "$pattern"; then
        cat <<EOF
{"action":"block","reason":"⛔ 危险操作被拦截：${pattern} 可能造成数据丢失，请用户确认后再执行。"}
EOF
        exit 0
    fi
done

echo '{"action":"allow"}'
exit 0
