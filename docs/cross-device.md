# 跨设备使用指南（Windows ↔ macOS）

toolbox 是 skills 的**唯一真源**（GitHub 管版本），ob-wiki 是知识库。本文件讲清楚
在两台不同 OS 的电脑之间如何无缝切换，以及 ob-wiki 那边的处理。

---

## 一、核心原则

1. **真源单一，派生随处重建**
   - 真源：`skills/<cat>/<skill>/SKILL.md` 的 frontmatter（在 toolbox）
   - 派生：manifest / README / Catalog 全部由 `gen_index.py` 生成，**不手维护、不跨设备复制**
   - 任何设备 clone 后跑一次 `gen_index.py`，索引立即与本地实盘对齐——天然防漂移

2. **本机路径用本地配置，不写死**
   - `toolbox-local.json`（每台机器一份，已被 .gitignore 忽略）记录本机路径
   - `gen_index.py` / `setup_links.py` 都优先读它，之后**零参数运行**

3. **消费层用链接接入，不复制**
   - 各 AI 工具的 skills 目录 → 链接到 `toolbox/skills`（Win 用 junction，Mac 用 symlink）
   - 改 toolbox 一处，所有工具立即可见，永不漂移

---

## 二、新设备初始化（5 分钟）

```bash
# 1. 拉两个仓库（任意位置，不必平级、不必是 dev/project）
git clone <toolbox> ~/任意位置/toolbox
git clone <ob-wiki> ~/另一个任意位置/ob-wiki

# 2. 写本机配置（复制模板，填本机真实路径）
cp toolbox/toolbox-local.example.json toolbox/toolbox-local.json
#   编辑 toolbox-local.json：ob_wiki / tools.*.skills_dir / tools.*.mcp_config

# 3. 接入各 AI 工具（自动建链接，Win=junction / Mac=symlink）
python toolbox/setup_links.py

# 4. 重建全部索引（含 ob-wiki 镜像）
python toolbox/gen_index.py

# 5. 验证
python toolbox/gen_index.py --check     # 应显示 实盘 == manifest，无漂移
python toolbox/setup_links.py --check   # 链接应全部"已完好"
```

---

## 三、日常使用

```bash
# 加了新 skill / 改了 frontmatter 后，一键重建
python toolbox/gen_index.py

# 换设备后同步（<toolbox> / <ob-wiki> 是你本机 clone 的任意实际路径）
git -C <toolbox> pull
git -C <ob-wiki> pull
python <toolbox>/gen_index.py     # 重建索引 + ob-wiki 镜像
```

建议把 `gen_index.py` 挂到 toolbox 的 git pre-commit hook，从此索引永远对得上。

---

## 四、ob-wiki 那边如何处理（关键）

ob-wiki 里的 `mocs/Skills-Catalog.md` **不是真源，是生成镜像**：

- 它由 `gen_index.py` 从 toolbox 的 SKILL.md frontmatter 生成
- 跨仓库相对链接（如 `../.../toolbox/skills/<cat>/<skill>/SKILL.md`，前缀由
  `gen_index.py` 按本机实际目录自动计算）指回 toolbox 真源——**无需平级、无需写死**
- 文件带 Obsidian frontmatter `type: moc`，在 Obsidian 里作为 MOC（Map of Content）导航页

**sync 策略（二选一）：**

| 同步方式 | ob-wiki 的 Catalog 处理 |
|---|---|
| **git 同步 ob-wiki** | 建议把 `mocs/Skills-Catalog.md` 加进 ob-wiki 的 `.gitignore`（派生产物，不进版本库）。每台设备 sync 后跑 `gen_index.py` 重建即可 |
| **Obsidian Sync / iCloud / Syncthing** | Catalog 随 vault 自动同步，但仍是派生产物。改 toolbox 后记得重跑 `gen_index.py`，否则 Catalog 会暂时过期（不影响真源） |

> 无论哪种同步，Catalog 都是「编译产物」而非「源」。真源永远在 toolbox 的 SKILL.md。
> 这与 Karpathy LLM Wiki 哲学一致：wiki 是编译输出，raw 才是源。

**ob-wiki 的 .gitignore 建议加：**
```
# 生成镜像（由 toolbox/gen_index.py 产出，跨设备 sync 后重建）
mocs/Skills-Catalog.md
```

---

## 五、MCP 跨设备

- 单一真源：`toolbox/mcp/servers.json`（标准 `mcpServers` 格式）
- 接入方式（在 `toolbox-local.json` 的 `tools.<name>.mcp_symlink` 控制）：
  - `true`（workbuddy/cursor 的独立 mcp.json）：`setup_links.py` 直接链接到 servers.json
  - `false`（claude 的 `~/.claude.json` 单一 JSON）：脚本提示你手动把 `mcpServers` 段合并进去
- Windows 跨盘符时文件符号链接需特权，`setup_links.py` 会自动降级为「提示复制」并给出路径
- 各 MCP server 的 token 用 `${ENV_VAR}` 引用系统环境变量，**不写进 servers.json**（避免泄露）

---

## 六、路径约定（推荐平级 + 相对路径；不平级也可）

**主推方案：两个仓库平级（兄弟目录），Catalog 用相对路径 `../../toolbox/...`。**
这不算"写死"——相对路径只描述两者之间的位置关系，不绑定任何绝对位置。
只要每台机器上 toolbox 与 ob-wiki 是兄弟目录，无论放在 `D:\repos`、`~/code`
还是 `/Volumes/Sync`，相对链接跨 Win/Mac 都成立，clone 到哪都能用。

```
# 推荐：平级即可，绝对位置任意，不必是 dev/project
<任意位置>/
├── toolbox/     # git 仓库（skills 真源）
└── ob-wiki/     # git 仓库（知识库），与 toolbox 平级
```

**链接前缀怎么来：** `gen_index.py` 生成 ob-wiki 镜像时，用
`os.path.relpath(SCRIPT_DIR, ob_mocs)` 从 toolbox 根**算出**到 `ob-wiki/mocs`
的相对前缀。平级时算出来正好就是 `../../toolbox/`（即你认可的相对路径方案），
代码里没有烤死这串字面；只有在不平级时才会算出不同的前缀，自动兜底。

需要手动覆盖的情况（均写在本机 `toolbox-local.json`，不提交）：

| 字段 | 何时需要 | 填什么 |
|---|---|---|
| `ob_wiki` | 任何非默认情况 | ob-wiki 的**绝对路径**（gen_index 用它定位 `mocs/`） |
| `ob_wiki_link_prefix` | 极少：你想硬编码链接前缀（如用 vault 别名 `[[toolbox/...]]`） | 显式相对/别名前缀；**留空即自动计算** |

> 结论：**无需任何路径约定**。clone 到任意位置 → 填 `toolbox-local.json` → 跑
> `gen_index.py` → 索引与链接自动对齐本机实盘。
