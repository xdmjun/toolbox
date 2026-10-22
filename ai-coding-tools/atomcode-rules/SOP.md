# AtomCode 全局规则 + harness 钩子体系 · SOP

> 在任意机器上初始化 AtomCode 的全局规则 + 单入口 harness 钩子体系（危险命令拦截 / 锁文件保护 / 先读后改 / 会话跟踪 / 知识库联动）。
> 作者：AtomCode | 适用平台：macOS / Linux / Windows (Git Bash)，依赖 Node.js >= 18

---

## 一、快速部署（2 分钟）

### 方式 A：一键脚本（推荐）

```bash
# 在 toolbox 仓库中直接运行（脚本从同目录复制 hook.js / hooks.json）
bash ai-coding-tools/atomcode-rules/setup-atomcode-rules.sh
# 然后重启 AtomCode 生效
```

脚本会：写 ATOMCODE.md → 复制 hooks.json → 复制 hook.js → 生成知识库三件套 → `node --check` 校验 hook.js。

### 方式 B：手动逐条

1. 创建目录：
   ```bash
   mkdir -p ~/.atomcode/hooks
   ```
2. 将 `ATOMCODE.md`、`hooks.json`、`hook.js` 和 `hooks/*.sh` 从本目录复制到 `~/.atomcode/`（hook.js 放 `~/.atomcode/hooks/`）
3. （macOS/Linux）设置可执行权限：
   ```bash
   chmod +x ~/.atomcode/hooks/*.sh
   ```
4. 重启 AtomCode

### 方式 C：Git 托管（团队共享）

本目录（`ai-coding-tools/atomcode-rules/`）本身就在 toolbox 仓库中，其他机器 clone 后运行方式 A 即可。

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

### 2.3 确认 Node.js 可用

hook.js 是 harness 主钩子，依赖 Node.js >= 18：

```bash
node --version
```

### 2.4 重启 AtomCode

关闭并重新打开 AtomCode，新的规则和钩子才会加载。session_start 钩子会注入"【harness 守护层已激活】"说明，看到它即代表钩子已挂载。

---

## 三、验证部署

### 验证文件存在

```bash
ls -la ~/.atomcode/ATOMCODE.md                 # 应存在
ls -la ~/.atomcode/hooks.json                  # 应存在
ls -la ~/.atomcode/hooks/hook.js               # 应存在（harness 主钩子）
ls -la ~/.atomcode/hooks/flag-searcher.sh      # 应存在
ls -la ~/.atomcode/hooks/knowledge-enforcer.sh # 应存在
ls -la ~/.atomcode/hooks/danger-guard.sh       # 应存在
```

### 命令行模拟测试（不进 AtomCode 也能测）

```bash
# 1) 锁文件保护：应输出 block + 退出码 2
echo '{"hook_event_name":"pre_tool_use","tool_name":"edit_file","tool_input":{"file_path":"/x/app/package-lock.json"}}' \
  | node ~/.atomcode/hooks/hook.js; echo "exit=$?"

# 2) 先读后改：未读过的文件应被拦截
echo '{"hook_event_name":"pre_tool_use","tool_name":"edit_file","tool_input":{"file_path":"/x/src/main.rs"}}' \
  | node ~/.atomcode/hooks/hook.js; echo "exit=$?"

# 3) 危险命令：根级 rm 应被拦截
echo '{"hook_event_name":"pre_tool_use","tool_name":"bash","tool_input":{"command":"rm -rf /"}}' \
  | node ~/.atomcode/hooks/hook.js; echo "exit=$?"
```

### 验证 ATOMCODE.md 正确加载

在 AtomCode 中输入 `/status`，检查 `ATOMCODE.md` 出现在 "Project instructions" 列表中。

---

## 四、文件清单

```
ai-coding-tools/atomcode-rules/          # 本目录（toolbox 仓库托管）
├── setup-atomcode-rules.sh              # 一键部署（复制文件而非 heredoc 生成大文件）
├── ATOMCODE.md                          # 全局规则（Bug 工作流 + 禁止事项 + Git 规范）
├── hooks.json                           # 6 条钩子注册
├── hook.js                              # harness 主钩子（单入口）
├── danger-guard.sh                      # bash 模式兜底（无 node 环境时仍生效）
├── flag-searcher.sh                     # 知识库查询标记
├── knowledge-enforcer.sh                # 改码前强制查知识库
└── SOP.md                               # 本文档

~/.atomcode/                             # 部署目标
├── ATOMCODE.md
├── hooks.json
└── hooks/
    ├── hook.js
    ├── flag-searcher.sh
    ├── knowledge-enforcer.sh
    └── danger-guard.sh
```

---

## 五、架构解读

### 单入口 harness 主钩子（hook.js）

一个 Node 脚本处理全部事件，通过 stdin JSON 的 `hook_event_name`（或 `ATOMCODE_HOOK_EVENT` 环境变量）分发：

| 事件 | 工具 | 行为 |
|------|------|------|
| pre_tool_use | bash | 危险命令拦截：根级 rm、磁盘级操作（dd/mkfs/diskpart）、fork bomb、shutdown、DROP DATABASE、对保护分支 force push |
| pre_tool_use | edit_file | 先读后改：目标文件必须在本会话 read_file 读过；超过 4 小时视为陈旧需重读 |
| pre_tool_use | write_file | 覆盖已存在文件前必须读过；新建文件放行 |
| pre_tool_use | edit_file / write_file / search_replace | **锁文件保护**：15 种锁文件（package-lock.json / yarn.lock / pnpm-lock.yaml / Cargo.lock / go.sum / flake.lock 等）禁止直接编辑，引导改用包管理器 |
| post_tool_use | read_file / read_symbol / list_symbols / write_file | 记录"本会话已知文件"（状态存 `~/.atomcode/datalog/hook-state/`） |
| session_start | — | 注入守护说明（additionalContext） |
| session_end | — | 会话摘要落盘 JSONL（`~/.atomcode/datalog/hook-sessions.log`） |

**协议契约**：

- stdin: `{session_id, hook_event_name, cwd, tool_name, tool_input}`（可能为空，退化为环境变量）
- 放行 = 静默退出 0；拦截 = 单行 JSON `{"action":"block","reason":"..."}` + 退出码 2
- **fail-open**：hook 自身崩溃时退出 0 放行，绝不阻塞用户会话（审批层仍在）

### 三层拦截体系

| 层级 | 机制 | 强度 | 说明 |
|------|------|------|------|
| **L1 规则注入** | ATOMCODE.md 文本 → 上下文 | ⭐⭐ | 告诉 AI"应该怎么做"，随上下文压缩可能丢失 |
| **L2 harness 钩子** | hooks.json → hook.js（主）+ bash 三件套（辅） | ⭐⭐⭐⭐ | **强制执行**，每次工具调用前触发，不可绕过 |
| **L3 持久记忆** | memory 工具 → 跨会话加载 | ⭐⭐⭐ | 补充语境，新会话自动带出偏好 |

### 数据流

```
AI 调用任意工具
    │
    ▼
┌─────────────────────────────────────┐
│ pre_tool_use: knowledge-enforcer.sh │  改码前查知识库标记
├─────────────────────────────────────┤
│ pre_tool_use: hook.js               │  危险命令 / 锁文件 / 先读后改
│   拦截 = block JSON + exit 2        │  （精确扫描，非关键词暴力匹配）
├─────────────────────────────────────┤
│ 工具实际执行                          │
├─────────────────────────────────────┤
│ post_tool_use: hook.js              │  记录已读文件（供下次先读后改判定）
└─────────────────────────────────────┘
```

### 设计取舍（相对旧版三件套的改进）

| 旧版（v1，纯 bash 三件套） | 新版（v2，单入口 hook.js） |
|------|------|
| 关键词 grep 匹配（`rm -rf` 连写法变体都拦不住） | 正则语义扫描（根级目标判定、保护分支识别、force-with-lease 放行） |
| 无文件级状态 | 会话级已读状态 + 4 小时新鲜度 |
| 无锁文件保护 | 15 种锁文件硬拦截（Windows 大小写坑已修：集合与匹配统一 toLowerCase） |
| 每个 hook 独立进程/脚本 | 单入口分发，状态可共享 |
| — | session_end 摘要落盘，可复盘 |
| 脚本崩了行为不一 | 统一 fail-open 兜底 |
| setup 用 heredoc 内嵌生成（双份维护漂移） | hook.js / hooks.json 直接复制（单一真相源） |

---

## 六、故障处理

| 现象 | 原因 | 解决 |
|------|------|------|
| 改了 ATOMCODE.md 但 AI 不遵守 | 上下文压缩导致规则丢失 | 在当前会话中直接提醒 AI 规则内容 |
| 钩子不生效 | hooks.json 格式错误或路径不对 | `python -m json.tool ~/.atomcode/hooks.json` 校验 JSON |
| hook.js 完全不触发 | 无 node / node < 18 | `node --version`；此时 danger-guard.sh 仍兜底拦 bash 危险命令 |
| 提示"找不到脚本" | 脚本无可执行权限或路径不对 | `chmod +x ~/.atomcode/hooks/*.sh` |
| 编辑总是要求先 read_file | 先读后改生效（预期行为） | 先 read_file 再 edit；4 小时后需重读 |
| 锁文件被拦 | 锁文件保护生效（预期行为） | 改用 `npm/pnpm install`、`cargo update` 等包管理器命令 |
| 知识库拦截太频繁 | 非知识库项目也被拦 | 编辑 `knowledge-enforcer.sh` 加项目白名单 |
| 拦截提示乱码（Windows） | 终端编码非 UTF-8 | Git Bash 下运行；AtomCode TUI 内正常 |

---

## 七、自定义与扩展

### 在 hook.js 中增加拦截规则

编辑 `handlePre`（事件处理段），参照锁文件保护的模式：

```js
// 新增一种 pre_tool_use 拦截：只拦"零合法用途"的操作
if (tool === 'edit_file') {
    const p = normPath(getFilePath(toolInput), cwd);
    if (p.endsWith('.env')) {
        return block('.env 环境文件不允许 AI 编辑，请用户手动处理。');
    }
}
```

修改后验证：

```bash
node --check hook.js
echo '{"hook_event_name":"pre_tool_use","tool_name":"edit_file","tool_input":{"file_path":"/x/.env"}}' | node hook.js
```

### 增加锁文件类型

编辑 hook.js 顶部 `LOCK_FILES` 集合（**注意保持全小写**——Windows 下路径匹配统一转小写）。

### 知识库白名单（解决误拦截）

编辑 `knowledge-enforcer.sh`，在检查标记前增加项目路径判断，非白名单项目直接 `{"action":"allow"}`。

### 添加 post_tool_use 审计日志

hook.js 已内置 session_end 摘要落盘；如需更细粒度，在 hooks.json 追加独立条目即可（单入口之外仍可并行注册 bash 钩子）。

---

## 八、涉及的知识

- AtomCode 配置体系：`~/.atomcode/ATOMCODE.md`（全局）、`.atomcode.md`（项目）、`.atomcode.user.md`（个人覆写）
- 钩子系统：事件（`session_start` / `session_end` / `pre_tool_use` / `post_tool_use` / `user_prompt_submit`）、matcher 正则、`timeout_ms`
- 钩子 IO 协议：stdin JSON 进，block JSON + exit 2 出，纯文本 stdout = additionalContext
- Windows 坑：路径大小写归一（`Cargo.lock` vs `cargo.lock`）、Git Bash 路径转义
- MCP 服务：`dao-distill-mcp` 提供知识库检索接口
- 借鉴来源：Claude Code 官方 hooks-patterns（格式化/类型检查/敏感保护/锁文件保护四类模式），其中锁文件保护与危险命令保护已落地
