# AtomCode 全局规则 + pre_tool_use 钩子 · SOP

> 在任意机器上初始化 AtomCode 的 Bug 处理强制工作流 + 危险命令拦截体系。
> 作者：AtomCode | 适用平台：macOS / Linux / Windows (Git Bash)

---

## 一、快速部署（2 分钟）

### 方式 A：一键脚本（推荐）

**macOS / Linux：**

```bash
bash ~/.atomcode/hooks/setup-atomcode-rules.sh
```

**Windows（Git Bash）：**

```bash
bash "$HOME/.atomcode/hooks/setup-atomcode-rules.sh"
```

> 首次部署（还没有该脚本时），从已有的机器复制整个 `~/.atomcode/` 目录，或者手动创建文件（参考"方式 B"）。
> # 从已有的机器拷贝 setup-atomcode-rules.sh 到该目录
> # 或者直接运行下方"方式 B"的逐条命令
> ```

### 方式 B：手动逐条

1. 创建目录：
   ```bash
   mkdir -p ~/.atomcode/hooks
   ```
2. 将 `ATOMCODE.md`、`hooks.json` 和 `hooks/*.sh` 文件从已有机器复制到 `~/.atomcode/`
3. （macOS/Linux）设置可执行权限：
   ```bash
   chmod +x ~/.atomcode/hooks/*.sh
   ```
4. 重启 AtomCode

### 方式 C：Git 托管（团队共享）

将整个 `~/.atomcode/` 目录（不含 sessions/）纳入 dotfiles 仓库：

```bash
cd ~
git init .atomcode
git add ATOMCODE.md hooks.json hooks/
git commit -m "feat: atomcode global rules + hooks"
git remote add origin <your-repo>
git push
```

其他机器 clone 即可：

```bash
git clone <your-repo> ~/.atomcode
```

---

## 二、部署后配置

### 2.1 注册 memory（跨会话持久化）

在 AtomCode 中执行一次：

```
请 memory 记住：处理 Bug 必须先调用 dao-distill-mcp search_vault 从知识库检索相关经验，然后才能修改代码
```

### 2.2 确认 dao-distill-mcp 可用

检查 `~/.atomcode/mcp.json` 中是否包含：

```json
{
  "mcpServers": {
    "dao-distill-mcp": {
      "type": "http",
      "url": "http://127.0.0.1:62525/mcp"
    }
  }
}
```

如果目标机器没有运行 `dao-distill` 服务，知识库查询会失败。知识服务不是本 SOP 的覆盖范围，请另行部署。

### 2.3 重启 AtomCode

关闭并重新打开 AtomCode，新的规则和钩子才会加载。

---

## 三、验证部署

### 验证钩子生效

检查文件存在：

```bash
ls -la ~/.atomcode/ATOMCODE.md            # 应存在
ls -la ~/.atomcode/hooks.json              # 应存在
ls -la ~/.atomcode/hooks/flag-searcher.sh  # 应存在
ls -la ~/.atomcode/hooks/knowledge-enforcer.sh  # 应存在
ls -la ~/.atomcode/hooks/danger-guard.sh   # 应存在
```

### 验证 ATOMCODE.md 正确加载

在 AtomCode 中输入：

```
/status
```

检查输出中是否包含 `ATOMCODE.md` 出现在 "Project instructions" 列表中。

### 验证钩子工作状态

当你尝试执行 `edit_file` 或 `write_file` 但尚未调用 `search_vault` 时，应被拦截并看到提示：

> ⚠️ 检测到您正在修改代码（edit_file），但当前会话尚未查询过知识库。

调用 `search_vault` 之后再编辑，应该能正常放行。

---

## 四、文件清单

```
~/.atomcode/
├── ATOMCODE.md                      # 全局规则（入口级约束）
│   ├── ## Bug 处理强制工作流         ← 新增：先查知识库再改代码
│   ├── ## 全局规则：先调研后执行
│   │   ├── 1. 先规划再动手
│   │   ├── 2. 禁止事项（红线）
│   │   ├── 3. 调研纪律
│   │   ├── 4. 验证与交付
│   │   └── 5. 代码修改纪律
│
├── hooks.json                       # 钩子注册表（事件 → 脚本绑定）
│   ├── knowledge-flag-search         #   mcp 调用 → 设标记
│   ├── knowledge-check-before-write  #   编辑文件 → 查标记
│   └── dangerous-command-guard       #   bash 命令 → 安全检查
│
└── hooks/                           # 钩子脚本
    ├── flag-searcher.sh             # 创建知识库查询标记
    ├── knowledge-enforcer.sh        # 改代码前检查标记
    └── danger-guard.sh              # 危险命令拦截
```

---

## 五、架构解读

### 三层拦截体系

| 层级 | 机制 | 强度 | 说明 |
|------|------|------|------|
| **L1 规则注入** | ATOMCODE.md 文本 → 上下文 | ⭐⭐ | 告诉 AI"应该怎么做"，随上下文压缩可能丢失 |
| **L2 钩子拦截** | hooks.json → Shell 脚本 | ⭐⭐⭐⭐ | **强制执行**，每次工具调用前触发，不可绕过 |
| **L3 持久记忆** | memory 工具 → 跨会话加载 | ⭐⭐⭐ | 补充语境，新会话自动带出偏好 |

### 数据流

```
AI 收到 Bug 任务
    │
    ▼
┌──────────────────────────────┐
│  L1: ATOMCODE.md 规则        │  "必须先查知识库"
│  文本引导 (可能被压缩)         │
└──────────────────────────────┘
    │
    ▼
AI 应调用 search_vault
    │
    ▼
┌──────────────────────────────┐
│  L2: flag-searcher.sh       │  → /tmp/atomcode_kb_$(whoami).flag
│  自动创建标记文件              │
└──────────────────────────────┘
    │
    ▼
AI 尝试 edit_file / write_file
    │
    ▼
┌──────────────────────────────┐
│  L2: knowledge-enforcer.sh  │
│  检查标记文件                  │
├──────────┬───────────────────┤
│ 有标记    │  无标记            │
│ → ALLOW  │  → BLOCK + 提示    │
└──────────┴───────────────────┘
    │
    ▼
AI 尝试 rm -rf / git reset
    │
    ▼
┌──────────────────────────────┐
│  L2: danger-guard.sh        │
│  匹配危险模式                  │
├──────────┬───────────────────┤
│ 安全操作   │ 危险操作           │
│ → ALLOW  │  → BLOCK + 提示    │
└──────────┴───────────────────┘
```

### 标记文件机制

- **路径**：`/tmp/atomcode_kb_$(whoami).flag`
- **创建**：`flag-searcher.sh` 在 `search_vault` / `read_note` / `vault_structure` 调用时自动创建
- **检查**：`knowledge-enforcer.sh` 在每次改文件前检查
- **隔离**：按用户名隔离，不同用户互不冲突
- **生命周期**：系统重启后自动清理

---

## 六、故障处理

| 现象 | 原因 | 解决 |
|------|------|------|
| 改了 ATOMCODE.md 但 AI 不遵守 | 上下文压缩导致规则丢失 | 在当前会话中直接提醒 AI 规则内容 |
| 钩子不生效 | hooks.json 格式错误或路径不对 | 检查 `~/.atomcode/hooks.json` 的 JSON 合法性 |
| 提示"找不到脚本" | 脚本无可执行权限或路径不对 | `chmod +x ~/.atomcode/hooks/*.sh` |
| 保险丝感觉太紧（频繁误拦截） | 非知识库项目也被拦截 | 修改 `knowledge-enforcer.sh`，增加项目白名单 |
| 误放行了危险命令 | 危险模式列表不全 | 在 `danger-guard.sh` 的 `DANGER_PATTERNS` 数组中添加新模式 |

---

## 七、自定义与扩展

### 增加危险模式

编辑 `danger-guard.sh` 的 `DANGER_PATTERNS` 数组：

```bash
DANGER_PATTERNS=(
    'rm -rf'
    'git reset --hard'
    # 添加你自己的模式：
    'drop table'
    'shutdown /s'
)
```

### 增加项目白名单（解决误拦截）

编辑 `knowledge-enforcer.sh`：

```bash
# 只有这些项目才强制查知识库
ENFORCED_PROJECTS=(
    'sgy-network'
    'bj-aop'
    # 添加更多项目名
)

CWD="${PWD}"
ENFORCED=false
for proj in "${ENFORCED_PROJECTS[@]}"; do
    if echo "$CWD" | grep -qiF "$proj"; then
        $enforced = $true
        break
    }
}
if (-not $enforced) {
    Write-Output '{"action":"allow"}'
    exit 0
}
```

### 添加 post_tool_use 审计日志

在 `hooks.json` 追加：

```json
"audit-log": {
  "event": "post_tool_use",
  "matcher": "edit_file|write_file|bash",
  "command": "bash -c 'echo \"$(date) $ATOMCODE_TOOL_NAME\" >> $HOME/.atomcode/audit.log'",
  "timeout_ms": 500
}
```

---

## 八、涉及的知识

- AtomCode 配置体系：`~/.atomcode/ATOMCODE.md`（全局）、`.atomcode.md`（项目）、`.atomcode.user.md`（个人覆写）
- 钩子系统：4 种事件（`session_start` / `session_end` / `pre_tool_use` / `post_tool_use`）
- MCP 服务：`dao-distill-mcp` 提供知识库检索接口
- 标记文件 + Shell 脚本实现强制拦截
