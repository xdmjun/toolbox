#!/usr/bin/env bash
# ==============================================================
# AtomCode 全局规则 + pre_tool_use 钩子 · 一键初始化脚本
# 跨平台：macOS / Linux / Windows (Git Bash)
# ==============================================================
set -euo pipefail

ATOMCODE_DIR="${HOME}/.atomcode"
HOOKS_DIR="${ATOMCODE_DIR}/hooks"

echo "[1/4] 创建目录 ..."
mkdir -p "${HOOKS_DIR}"

# ─── 文件 1: ATOMCODE.md ───────────────────────────────────────
echo "[2/4] 写入 ATOMCODE.md ..."
cat > "${ATOMCODE_DIR}/ATOMCODE.md" << 'ATOMCODE_EOF'
## Bug 处理强制工作流（优先级：最高）

遇到 **Bug 报告、调试、错误修复** 任务时，必须按以下顺序执行：

1. **检索知识库** → 调用 `dao-distill-mcp search_vault` 查询相关经验/方案
2. **复现错误** → 运行失败的命令，看到真实错误输出
3. **诊断根因** → 分析错误输出，定位问题根源
4. **修复** → 修改代码
5. **验证** → 运行 `cargo check` / `tsc --noEmit` 等验证命令通过

> ⚠️ 不可跳过步骤 1 直接改代码。知识库可能包含此前解决过的同类问题。

---

## 全局规则：先调研后执行，避免瞎猜

### 1. 先规划，再动手

- 接到多文件/复杂任务时，必须先搜索和阅读相关代码，理解现状，再动手修改
- 在打开编辑器之前，先用一句话说明你的计划，确认方向正确再执行
- 对于不熟悉的库、API、框架，必须先读取官方文档或源码——**不可猜测用法**
- 不要提议修改没有读过的代码——先读，再改
- 多文件变更前，先使用代码分析工具理解各文件之间的依赖关系（blast_radius / file_dependencies）
- 修 Bug 的完整链路：**复现错误 → 诊断根因 → 修复 → 验证**，不可跳过诊断步骤直接修

### 2. 禁止事项（红线，违反即事故）

- **NEVER** 猜测函数签名、参数、返回值——以实际代码为准
- **NEVER** 编造 API 用法、库的接口、不存在的功能——不确定就说"不知道"
- **NEVER** 删除、注释掉、跳过测试或弱化断言来让错误消失
- **NEVER** 假装完成——任务未完成时，诚实说明进度和剩余步骤
- **NEVER** 盲目重试同一失败命令——先分析错误输出，找到根因再重试
- **NEVER** 报告"完成"前跳过验证——编译/类型检查/测试必须通过
- **NEVER** 擅自扩大任务范围——如果发现需要额外工作，先提出来，不擅自加码
- **NEVER** 提交包含调试代码（console.log / dbg! / print）的修改

### 3. 调研纪律

- 先搜索，再阅读，最后修改。搜索不到足够信息时，读源码
- 如果经过充分搜索（最多 3 轮）仍找不到原因，停止搜索，向用户说明已排查的内容和下一步建议
- 对于不确定的信息，直接说"不知道"，不要编造答案
- 工具报错时，仔细阅读错误输出，判断根因，再决定下一步操作

### 4. 验证与交付

- 修改后必须运行验证命令（`cargo check` / `tsc --noEmit` / 等效命令）确认通过，才能说完成
- 编译不通过或测试失败，任务就不算完成
- 每次修改后，优先用最小验证命令（仅类型检查/编译检查），不启动 watcher 或 dev server
- 如果用 `todowrite` 跟踪任务，标记完成前必须确认该步骤已通过验证
- **多文件组件修改后，必须追溯完整的父→子渲染链路**。不仅看子组件内部的状态逻辑，还要确认父组件是否允许该状态被渲染出来（如 `v-if` 控制显示/隐藏、路由守卫拦截等）。只看单个文件编译通过不代表实际功能正确。

### 5. 代码修改纪律

- 优先修改已有文件，不随意创建新文件
- 先读文件内容，再修改。不要修改没读过的代码
- 匹配周围代码的风格——注释密度、命名风格、错误处理模式
- 不要顺手做未要求的重构、优化或功能增加
- 只验证系统边界（用户输入、外部接口），不要添加不可能发生的错误处理

## Git 协作规范

### 1. 提交前必须验证通过

commit 前必须运行 `cargo check` / `pnpm build` 等确保编译/类型检查通过，**不得提交编译失败的代码**。

### 2. 提交信息用中文

简明扼要描述本次改动的意图，例如 `修复 SSH 超时断开时的处理`、`新增 Portal 自动登录重试机制`。

### 3. 经用户确认后再提交

不得擅自执行 `git commit` / `git push`；如需提交，先将改动和提交信息展示给用户，确认后再执行。

### 4. 原子化提交

每次提交只做一件事（一个功能 / 一个 Bug 修复 / 一个重构），不混入无关改动。

### 5. 不提交敏感信息

密码、Token、密钥、证书等**绝对不进 git**，已 .gitignore 的确认不漏。

### 6. 不提交构建产物

`target/`、`dist/`、`node_modules/`、`*.log` 等不提交。

### 7. 不强制推送到共享分支

不允许 `git push --force` 到 `main`/`master` 或他人正在使用的分支。
ATOMCODE_EOF

# ─── 文件 2: hooks.json ────────────────────────────────────────
echo "[3/4] 写入 hooks.json ..."
cat > "${ATOMCODE_DIR}/hooks.json" << HOOKS_EOF
{
  "hooks": {
    "knowledge-flag-search": {
      "event": "pre_tool_use",
      "matcher": "mcp__dao-distill-mcp__search_vault|mcp__dao-distill-mcp__read_note|mcp__dao-distill-mcp__vault_structure",
      "command": "bash \"\${HOME}/.atomcode/hooks/flag-searcher.sh\"",
      "timeout_ms": 1000
    },
    "knowledge-check-before-write": {
      "event": "pre_tool_use",
      "matcher": "edit_file|write_file",
      "command": "bash \"\${HOME}/.atomcode/hooks/knowledge-enforcer.sh\"",
      "timeout_ms": 5000
    },
    "dangerous-command-guard": {
      "event": "pre_tool_use",
      "matcher": "bash",
      "command": "bash \"\${HOME}/.atomcode/hooks/danger-guard.sh\"",
      "timeout_ms": 3000
    }
  }
}
HOOKS_EOF

# ─── 文件 3: flag-searcher.sh ─────────────────────────────────
echo "[4/4] 写入 hooks/ 脚本 ..."
cat > "${HOOKS_DIR}/flag-searcher.sh" << 'SCRIPT_EOF'
#!/usr/bin/env bash
FLAG_FILE="${TMPDIR:-/tmp}/atomcode_kb_$(whoami).flag"
touch "$FLAG_FILE"
echo '{"action":"allow"}'
exit 0
SCRIPT_EOF

# ─── 文件 4: knowledge-enforcer.sh ───────────────────────────
cat > "${HOOKS_DIR}/knowledge-enforcer.sh" << 'SCRIPT_EOF'
#!/usr/bin/env bash
FLAG_FILE="${TMPDIR:-/tmp}/atomcode_kb_$(whoami).flag"
if [ -f "$FLAG_FILE" ]; then
    echo '{"action":"allow"}'
    exit 0
fi
TOOL_NAME="${ATOMCODE_TOOL_NAME:-unknown}"
cat <<EOF
{"action":"block","reason":"⚠️ 检测到您正在修改代码（${TOOL_NAME}），但当前会话尚未查询过知识库。请先通过 dao-distill-mcp 的 search_vault 搜索相关经验，然后再执行修改。"}
EOF
exit 0
SCRIPT_EOF

# ─── 文件 5: danger-guard.sh ─────────────────────────────────
cat > "${HOOKS_DIR}/danger-guard.sh" << 'SCRIPT_EOF'
#!/usr/bin/env bash
CONTEXT="${ATOMCODE_HOOK_CONTEXT:-}"
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
SCRIPT_EOF

# ─── 设置可执行权限（macOS/Linux） ────────────────────────────
chmod +x "${HOOKS_DIR}/flag-searcher.sh" \
         "${HOOKS_DIR}/knowledge-enforcer.sh" \
         "${HOOKS_DIR}/danger-guard.sh" 2>/dev/null || true

# ─── 完成 ──────────────────────────────────────────────────────
echo ""
echo "✅ AtomCode 全局规则 + 钩子部署完成！"
echo "   目录: ${ATOMCODE_DIR}"
echo "   ├── ATOMCODE.md"
echo "   ├── hooks.json"
echo "   └── hooks/"
echo "        ├── flag-searcher.sh"
echo "        ├── knowledge-enforcer.sh"
echo "        └── danger-guard.sh"
echo ""
echo "接下来："
echo "  1. 在 AtomCode 中执行 memory 记住偏好："
echo "     \"处理 Bug 必须先调用 dao-distill-mcp search_vault 检索知识库\""
echo "  2. 确保 dao-distill-mcp 已配置在 mcp.json 中"
echo "  3. 重启 AtomCode 后生效"
echo ""
echo "从另一台机器同步：将 ${ATOMCODE_DIR} 目录整体复制即可。"
