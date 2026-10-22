<#
.SYNOPSIS
    AtomCode 全局规则 + pre_tool_use 钩子 一键初始化脚本
.DESCRIPTION
    在目标机器上创建：
      1. ~/.atomcode/ATOMCODE.md          — 全局规则（含 Bug 强制工作流）
      2. ~/.atomcode/hooks.json           — pre_tool_use 钩子配置
      3. ~/.atomcode/hooks/*.ps1          — 3 个钩子脚本
    PowerShell 5.1+ / PowerShell Core 均兼容。
.LINK
    SOP: ~/.atomcode/hooks/SOP.md
#>

$ErrorActionPreference = 'Stop'
$atomcodeDir = "$env:USERPROFILE\.atomcode"
$hooksDir    = "$atomcodeDir\hooks"

# ─── 创建目录 ──────────────────────────────────────────────────
Write-Host '[1/4] 创建目录 ...' -ForegroundColor Cyan
$null = New-Item -ItemType Directory -Path $atomcodeDir -Force
$null = New-Item -ItemType Directory -Path $hooksDir  -Force

# ─── 文件 1: ATOMCODE.md ───────────────────────────────────────
Write-Host '[2/4] 写入 ATOMCODE.md ...' -ForegroundColor Cyan
@'
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
'@ | Set-Content -Path "$atomcodeDir\ATOMCODE.md" -Encoding UTF8

# ─── 文件 2: hooks.json ────────────────────────────────────────
Write-Host '[3/4] 写入 hooks.json ...' -ForegroundColor Cyan
@'
{
  "hooks": {
    "knowledge-flag-search": {
      "event": "pre_tool_use",
      "matcher": "mcp__dao-distill-mcp__search_vault|mcp__dao-distill-mcp__read_note|mcp__dao-distill-mcp__vault_structure",
      "command": "powershell -NoProfile -File \"$env:USERPROFILE\\.atomcode\\hooks\\flag-searcher.ps1\"",
      "timeout_ms": 1000
    },
    "knowledge-check-before-write": {
      "event": "pre_tool_use",
      "matcher": "edit_file|write_file",
      "command": "powershell -NoProfile -File \"$env:USERPROFILE\\.atomcode\\hooks\\knowledge-enforcer.ps1\"",
      "timeout_ms": 5000
    },
    "dangerous-command-guard": {
      "event": "pre_tool_use",
      "matcher": "bash",
      "command": "powershell -NoProfile -File \"$env:USERPROFILE\\.atomcode\\hooks\\danger-guard.ps1\"",
      "timeout_ms": 3000
    }
  }
}
'@ | Set-Content -Path "$atomcodeDir\hooks.json" -Encoding UTF8

# ─── 文件 3: flag-searcher.ps1 ─────────────────────────────────
Write-Host '[4/4] 写入 hooks/ 脚本 ...' -ForegroundColor Cyan
@'
param()

$flagFile = [System.IO.Path]::Combine($env:TEMP, "atomcode_kb_$pid.flag")
$null > $flagFile
Write-Output '{"action":"allow"}'
exit 0
'@ | Set-Content -Path "$hooksDir\flag-searcher.ps1" -Encoding UTF8

# ─── 文件 4: knowledge-enforcer.ps1 ───────────────────────────
@'
param()

$flagFile = [System.IO.Path]::Combine($env:TEMP, "atomcode_kb_$pid.flag")

if (Test-Path $flagFile) {
    Write-Output '{"action":"allow"}'
    exit 0
}

$toolName = $env:ATOMCODE_TOOL_NAME
Write-Output @"
{"action":"block","reason":"⚠️ 检测到您正在修改代码（$toolName），但当前会话尚未查询过知识库。请先通过 dao-distill-mcp 的 search_vault 搜索相关经验，然后再执行修改。"}
"@
exit 0
'@ | Set-Content -Path "$hooksDir\knowledge-enforcer.ps1" -Encoding UTF8

# ─── 文件 5: danger-guard.ps1 ─────────────────────────────────
@'
param()

$context = $env:ATOMCODE_HOOK_CONTEXT

$dangerPatterns = @(
    'rm -rf',
    'rm -r -f',
    'rm --recursive',
    'git reset --hard',
    'git checkout \.',
    'git checkout -- ',
    'git clean -f',
    'git clean -fd',
    'git restore \.',
    'del /F /S',
    'rd /s /q',
    'rmdir /s /q',
    'format ',
    'dd if=',
    '> /dev/sd'
)

foreach ($pattern in $dangerPatterns) {
    if ($context -match [regex]::Escape($pattern)) {
        Write-Output @"
{"action":"block","reason":"⛔ 危险操作被拦截：`"$pattern`" 可能造成数据丢失，请用户确认后再执行。"}
"@
        exit 0
    }
}

Write-Output '{"action":"allow"}'
exit 0
'@ | Set-Content -Path "$hooksDir\danger-guard.ps1" -Encoding UTF8

# ─── 完成 ──────────────────────────────────────────────────────
Write-Host ''
Write-Host '✅ AtomCode 全局规则 + 钩子部署完成！' -ForegroundColor Green
Write-Host "   目录: $atomcodeDir" -ForegroundColor Gray
Write-Host "   ├── ATOMCODE.md" -ForegroundColor Gray
Write-Host "   ├── hooks.json" -ForegroundColor Gray
Write-Host "   └── hooks/" -ForegroundColor Gray
Write-Host "        ├── flag-searcher.ps1" -ForegroundColor Gray
Write-Host "        ├── knowledge-enforcer.ps1" -ForegroundColor Gray
Write-Host "        └── danger-guard.ps1" -ForegroundColor Gray
Write-Host ''
Write-Host '接下来：' -ForegroundColor Yellow
Write-Host '  1. 运行 memory 记住偏好：' -ForegroundColor Yellow
Write-Host '     "处理 Bug 必须先调用 dao-distill-mcp search_vault 从知识库检索相关经验，然后才能修改代码"' -ForegroundColor DarkYellow
Write-Host '  2. 确保 dao-distill-mcp MCP 服务已配置在 mcp.json 中' -ForegroundColor Yellow
Write-Host '  3. 重启 AtomCode 后生效' -ForegroundColor Yellow
