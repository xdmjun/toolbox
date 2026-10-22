#!/usr/bin/env node
'use strict';
/*
 * AtomCode 生命周期 hook —— 分层驾驭的确定性兜底层
 *
 * 设计原则（道 × Harness）：
 *   - 只拦截"零合法用途"的操作（硬红线，战略层刚性约束）
 *   - git 级破坏操作（reset --hard / clean -f / checkout --）交给审批层，不在此拦截
 *   - 失败即放行（fail-open）：hook 自身崩溃绝不阻塞用户会话（审批层仍在）
 *
 * 事件分支（ATOMCODE_HOOK_EVENT 或 stdin JSON 的 hook_event_name 决定，Pascal/snake 均识别）：
 *   pre_tool_use  bash        -> 危险命令拦截（单行 JSON + 退出码 2 + stderr 原因）
 *   pre_tool_use  edit_file   -> 编辑前必须已 read_file 读过（防拿陌生/陈旧上下文动手）
 *   pre_tool_use  write_file  -> 覆盖已存在文件前必须读过（新建放行）
 *   post_tool_use read_file / read_symbol / list_symbols / write_file -> 记录"本会话已知文件"
 *   session_start -> 注入守护说明（纯文本 stdout = additionalContext）
 *   session_end   -> 会话摘要落盘 JSONL（反者道之动：留存数据供复盘）
 *
 * 契约：
 *   - stdin: JSON {session_id, hook_event_name, cwd, tool_name, tool_input}（可能为空，退化为环境变量）
 *   - stdout: 放行 = 静默退出 0；拦截 = 单行 JSON {"action":"block","decision":"block","reason":...}
 *   - 状态: ~/.atomcode/datalog/hook-state/files-<cwdhash>.json（会话->文件->时间戳）
 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const { execFileSync } = require('child_process');

const STATE_DIR = path.join(os.homedir(), '.atomcode', 'datalog', 'hook-state');
const SESSION_LOG = path.join(os.homedir(), '.atomcode', 'datalog', 'hook-sessions.log');
const FRESH_MS = 4 * 3600 * 1000;          // "已读"新鲜度：4 小时，超时视为陈旧上下文
const MAX_FILES = 500;                      // 每会话最多记录文件数
const MAX_SESSION_AGE_MS = 7 * 24 * 3600 * 1000;
const PROTECTED_BRANCHES = new Set(['main', 'master', 'develop', 'release', 'prod', 'production']);
// rm 递归删除的根级目标：/ /* ~ ~/* $HOME /dev /home /Users C:\ 等
const ROOTISH_TARGET = /^(\/*|~\/?|\$HOME\/?|\/dev(\/\S*)?|\/home(\/\S*)?|\/Users(\/\S*)?|[Cc]:\\?)(\s*)$/i;

function pass() { process.exit(0); }

function block(reason) {
  const line = JSON.stringify({ action: 'block', decision: 'block', reason: reason });
  try { process.stdout.write(line + '\n'); } catch (e) {}
  try { process.stderr.write(reason + '\n'); } catch (e) {}
  process.exit(2);
}

/* ---------------- stdin 读取（带超时，防挂起） ---------------- */

function readStdinJson(timeoutMs) {
  return new Promise((resolve) => {
    if (process.stdin.isTTY) return resolve(null);
    let buf = '';
    let done = false;
    const timer = setTimeout(finish, timeoutMs);
    function finish() {
      if (done) return;
      done = true;
      clearTimeout(timer);
      let obj = null;
      if (buf.trim()) { try { obj = JSON.parse(buf); } catch (e) { obj = null; } }
      resolve(obj);
    }
    process.stdin.on('data', (d) => { buf += d.toString('utf8'); });
    process.stdin.on('end', finish);
    process.stdin.on('close', finish);
    process.stdin.on('error', finish);
  });
}

/* ---------------- 事件 / 工具名归一 ---------------- */

const EVENT_ALIASES = {
  pretooluse: 'pre_tool_use',
  posttooluse: 'post_tool_use',
  posttoolusefailure: 'post_tool_use',
  sessionstart: 'session_start',
  sessionend: 'session_end',
  userpromptsubmit: 'user_prompt_submit',
  notification: 'notification',
  pre_tool_use: 'pre_tool_use',
  post_tool_use: 'post_tool_use',
  session_start: 'session_start',
  session_end: 'session_end',
  user_prompt_submit: 'user_prompt_submit',
};

function normEvent(e) {
  const key = String(e || '').toLowerCase().replace(/[_-]/g, '');
  return EVENT_ALIASES[key] || '';
}

/* ---------------- 状态（会话已知文件） ---------------- */

function stateFileFor(cwd) {
  const key = crypto.createHash('sha1').update(String(cwd)).digest('hex').slice(0, 12);
  return path.join(STATE_DIR, 'files-' + key + '.json');
}

function loadState(cwd) {
  try { return JSON.parse(fs.readFileSync(stateFileFor(cwd), 'utf8')); }
  catch (e) { return { sessions: {} }; }
}

function saveState(cwd, state) {
  try {
    fs.mkdirSync(STATE_DIR, { recursive: true });
    const f = stateFileFor(cwd);
    const tmp = f + '.tmp.' + process.pid + '.' + Date.now();
    fs.writeFileSync(tmp, JSON.stringify(state));
    fs.renameSync(tmp, f);
  } catch (e) { /* 状态写失败不影响主流程 */ }
}

function prune(state, now) {
  for (const sid of Object.keys(state.sessions)) {
    const s = state.sessions[sid];
    if (now - (s.created || 0) > MAX_SESSION_AGE_MS) { delete state.sessions[sid]; continue; }
    const files = s.files || {};
    const keys = Object.keys(files);
    if (keys.length > MAX_FILES) {
      keys.sort((a, b) => files[a] - files[b]);
      for (const k of keys.slice(0, keys.length - MAX_FILES)) delete files[k];
    }
  }
}

function recordRead(p, cwd, sid) {
  const now = Date.now();
  const state = loadState(cwd);
  if (!state.sessions[sid]) state.sessions[sid] = { created: now, files: {} };
  state.sessions[sid].files[p] = now;
  prune(state, now);
  saveState(cwd, state);
}

// 返回 'fresh' | 'stale' | null(未读)
function readStatus(p, cwd, sid) {
  const state = loadState(cwd);
  const s = state.sessions[sid];
  if (!s || !s.files || !s.files[p]) return null;
  return Date.now() - s.files[p] < FRESH_MS ? 'fresh' : 'stale';
}

function knownFileCount(cwd, sid) {
  const state = loadState(cwd);
  const s = state.sessions[sid];
  return s && s.files ? Object.keys(s.files).length : 0;
}

/* ---------------- 路径归一 ---------------- */

function getFilePath(toolInput) {
  if (!toolInput || typeof toolInput !== 'object') return '';
  return toolInput.file_path || toolInput.path || toolInput.target || '';
}

function normPath(p, cwd) {
  if (!p) return '';
  let abs;
  try { abs = path.isAbsolute(p) ? path.resolve(p) : path.resolve(cwd || process.cwd(), p); }
  catch (e) { return ''; }
  if (process.platform === 'win32') abs = abs.toLowerCase();
  return abs;
}

/* ---------------- 危险命令扫描（只拦零合法用途） ---------------- */

function currentBranch(cwd) {
  try {
    const out = execFileSync('git', ['branch', '--show-current'], {
      cwd: cwd, timeout: 2000, stdio: ['ignore', 'pipe', 'ignore'],
    });
    return String(out).trim() || null;
  } catch (e) { return null; }
}

function scanDangerousCommand(cmd, cwd) {
  if (!cmd || !cmd.trim()) return null;
  const c = cmd.replace(/\r/g, ' ');

  // 1) rm 递归删除根级目标
  const rm = c.match(/\brm\s+((?:-\w+\s+)*)(\S+)/);
  if (rm) {
    const flags = rm[1] || '';
    const target = rm[2];
    if (/\br\b|[rf]/.test(flags) && ROOTISH_TARGET.test(target)) {
      return '拦截：rm ' + flags.trim() + ' ' + target + ' 会递归销毁根级目录，无合法用途。请核对实际目标路径；删除特定子目录请使用明确完整路径，并在执行前向用户确认。';
    }
  }

  // 2) 磁盘级操作
  if (/\b(dd\s+if=|mkfs(\.\w+)?\b|diskpart\b|format\s+[a-z]:\b|fdisk\b|parted\b)/i.test(c)) {
    return '拦截：检测到磁盘级操作（dd/mkfs/diskpart/format/fdisk/parted），破坏性且不可逆，不允许自动执行。如确有需要，请由用户手动在终端执行。';
  }

  // 3) Windows 递归删除磁盘根（del /s /q C:\ 等）
  if (/\b(?:del|rd|rmdir)\b[^|;&]*\b[a-z]:\\?(\s|$)/i.test(c)) {
    return '拦截：检测到对磁盘根目录（如 C:\\）的递归删除，无合法用途。';
  }

  // 4) fork bomb
  if (/:\(\)\s*\{/.test(c)) {
    return '拦截：检测到 fork bomb 模式。';
  }

  // 5) 系统关机/重启
  if (/(^|[|;&]\s*)(shutdown|reboot|poweroff|halt)\b/.test(c)) {
    return '拦截：系统关机/重启命令不允许自动执行。';
  }

  // 6) DROP DATABASE
  if (/\bDROP\s+DATABASE\b/i.test(c)) {
    return '拦截：DROP DATABASE 会销毁整个数据库，必须由用户在数据库客户端手动执行。如只是清理测试数据，请改用表级操作并先向用户确认。';
  }

  // 7) force push 保护分支
  const isGitPush = /\bgit\s+push\b/.test(c);
  const isForce = isGitPush && (
    /--force(?!-with-lease)/.test(c) || /\s-f(\s|$)/.test(c)
  );
  if (isForce) {
    const branch = currentBranch(cwd);
    if (branch && PROTECTED_BRANCHES.has(branch.toLowerCase())) {
      return '拦截：向保护分支 ' + branch + ' 执行 force push 被全局 Git 规范禁止。如用户明确要求，请由用户手动执行；或先推到新的备份分支。';
    }
    if (!branch) {
      return '拦截：force push 但无法确认当前分支（git branch --show-current 失败）。请确认目标分支不是 main/master/develop 等保护分支后重试。';
    }
  }

  return null;
}

// 锁文件只应通过包管理器变更，不允许 AI 直接编辑
const LOCK_FILES = new Set([ // 全小写：win32 下 normPath 会转小写，匹配侧也 toLowerCase()
  'package-lock.json', 'npm-shrinkwrap.json', 'yarn.lock', 'pnpm-lock.yaml',
  'bun.lockb', 'bun.lock', 'cargo.lock', 'poetry.lock', 'pipfile.lock',
  'uv.lock', 'pdm.lock', 'composer.lock', 'gemfile.lock', 'go.sum', 'flake.lock',
]);

/* ---------------- 事件处理 ---------------- */

function handlePre(tool, toolInput, cwd, sid) {
  if (tool === 'bash') {
    const cmd = typeof toolInput.command === 'string' ? toolInput.command : '';
    const danger = scanDangerousCommand(cmd, cwd);
    if (danger) return block(danger);
    return pass();
  }

  // edit_file / write_file / search_replace: 锁文件保护
  if (tool === 'edit_file' || tool === 'write_file' || tool === 'search_replace') {
    const p = normPath(getFilePath(toolInput), cwd);
    if (p) {
      const base = path.basename(p).toLowerCase(); // normPath 在 win32 已转小写，统一用小写匹配
      if (LOCK_FILES.has(base)) {
        return block('锁文件（' + base + '）不允许直接编辑，只能通过包管理器变更（npm/pnpm install、cargo update 等）。请改用对应包管理器命令。');
      }
    }
  }

  if (tool === 'edit_file') {
    const p = normPath(getFilePath(toolInput), cwd);
    if (!p) return pass();
    const st = readStatus(p, cwd, sid);
    if (st === 'fresh') return pass();
    if (st === 'stale') {
      return block('该文件上次读取已超过 4 小时（' + p + '），上下文可能陈旧：请重新 read_file 读取后再编辑。');
    }
    return block('未读取该文件，禁止直接编辑：请先用 read_file 读取 ' + p + '，再进行 edit_file。');
  }

  if (tool === 'write_file') {
    const p = normPath(getFilePath(toolInput), cwd);
    if (!p) return pass();
    if (fs.existsSync(p)) {
      const st = readStatus(p, cwd, sid);
      if (st === 'fresh') return pass();
      if (st === 'stale') {
        return block('目标文件已存在且上次读取超过 4 小时（' + p + '）：请重新 read_file 读取后再覆盖。');
      }
      return block('目标文件已存在且本会话未读取（' + p + '）：如需覆盖请先 read_file 读取；如属新建文件，请检查路径是否拼错。');
    }
    return pass(); // 新建文件放行
  }

  return pass(); // 其他工具不拦
}

function handlePost(tool, toolInput, cwd, sid) {
  const TRACK = { read_file: 1, read_symbol: 1, list_symbols: 1, write_file: 1 };
  if (!TRACK[tool]) return pass();
  const p = normPath(getFilePath(toolInput), cwd);
  if (!p) return pass();
  recordRead(p, cwd, sid);
  return pass();
}

function handleSessionStart() {
  const text = '【harness 守护层已激活】本会话确定性 hooks 生效：① 零合法用途的危险命令（rm -rf 根目录/磁盘、磁盘格式化工具、force push 保护分支、DROP DATABASE、fork bomb、shutdown）会被直接拦截——被拦截后不要换措辞重试同一意图，按拦截原因中的替代方案执行或向用户确认。② edit_file / write_file 覆盖前要求目标文件已在本会话 read_file 读过（超过 4 小时视为陈旧需重读）；新建文件不受限。③ git 级破坏操作（reset --hard / clean -f / checkout --）走审批流程而非 hook。';
  try { process.stdout.write(text + '\n'); } catch (e) {}
  process.exit(0);
}

function handleSessionEnd(cwd, sid) {
  try {
    fs.mkdirSync(path.dirname(SESSION_LOG), { recursive: true });
    const line = JSON.stringify({
      ts: new Date().toISOString(),
      event: 'session_end',
      cwd: cwd,
      session_id: sid,
      known_files: knownFileCount(cwd, sid),
    });
    fs.appendFileSync(SESSION_LOG, line + '\n');
  } catch (e) { /* 落盘失败不影响退出 */ }
  process.exit(0);
}

/* ---------------- main ---------------- */

(async () => {
  let stdinObj = null;
  try { stdinObj = await readStdinJson(300); } catch (e) { stdinObj = null; }

  const event = normEvent(
    process.env.ATOMCODE_HOOK_EVENT || (stdinObj && stdinObj.hook_event_name) || ''
  );
  const tool = String(
    process.env.ATOMCODE_TOOL_NAME || (stdinObj && stdinObj.tool_name) || ''
  ).toLowerCase();

  let toolInput = (stdinObj && stdinObj.tool_input) || {};
  if ((!toolInput || typeof toolInput !== 'object' || !Object.keys(toolInput).length)
      && process.env.ATOMCODE_HOOK_CONTEXT) {
    try {
      const ctx = JSON.parse(process.env.ATOMCODE_HOOK_CONTEXT);
      toolInput = (ctx && (ctx.tool_input || ctx)) || {};
    } catch (e) { toolInput = {}; }
  }

  const cwd = (stdinObj && stdinObj.cwd) || process.cwd();
  const sid = (stdinObj && stdinObj.session_id)
    || process.env.ATOMCODE_SESSION_ID || 'default';

  switch (event) {
    case 'pre_tool_use': return handlePre(tool, toolInput, cwd, sid);
    case 'post_tool_use': return handlePost(tool, toolInput, cwd, sid);
    case 'session_start': return handleSessionStart();
    case 'session_end': return handleSessionEnd(cwd, sid);
    default: return pass();
  }
})().catch((e) => {
  try { process.stderr.write('hook.js error: ' + (e && e.message) + '\n'); } catch (err) {}
  process.exit(0); // fail-open
});
