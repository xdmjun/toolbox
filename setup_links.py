#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
setup_links.py — 跨设备把 toolbox 的 skills / MCP 接入各 AI 编程工具。

解决的问题：
    跨设备（Windows ↔ macOS）时，各 AI 工具加载 skills / mcp 的目录位置随 OS 变化
    （如 Win 是 C:/Users/.../.workbuddy/skills，Mac 是 ~/.workbuddy/skills）。
    本脚本读本机配置 toolbox-local.json，把 toolbox 的真源（skills/ 与 mcp/servers.json）
    以「链接」形式接入各工具的目录，避免复制导致漂移。

链接方向：toolbox 是真源，消费层目录（~/.workbuddy/skills 等）变成指向 toolbox 的链接。
    - macOS / Linux：符号链接（symlink）
    - Windows       ：目录 junction（mklink /J，不需要管理员权限，对工具完全透明）

配置（toolbox-local.json，不进 git）：
{
  "ob_wiki": "/abs/path/to/your/ob-wiki",
  "use_dist": false,
  "tools": {
    "workbuddy": {
      "skills_dir": "~/.workbuddy/skills",
      "mcp_config": "~/.workbuddy/mcp.json",
      "mcp_symlink": true
    },
    "claudecode": { "skills_dir": "~/.claude/skills", "mcp_config": "~/.claude.json", "mcp_symlink": false },
    "cursor": { "skills_dir": "~/.cursor/skills", "mcp_config": "~/.cursor/mcp.json", "mcp_symlink": true },
    "windsurf": { "skills_dir": "~/.windsurf/skills", "mcp_config": "~/.windsurf/mcp.json", "mcp_symlink": true },
    "trae": { "skills_dir": "~/.trae/skills", "mcp_config": "~/.trae/mcp.json", "mcp_symlink": true },
    "atomcode": { "skills_dir": "~/.atomcode/skills", "mcp_config": "~/.atomcode/mcp.json", "mcp_symlink": true }
  }
}

mcp_symlink 说明：
    true  = 该工具的 mcp 配置是独立文件（如 workbuddy/mcp.json、cursor/mcp.json），
            直接链接到 toolbox/mcp/servers.json（POSIX 干净；Windows 尝试 mklink，
            失败则提示复制）。
    false = 该工具 mcp 配置嵌在单一 JSON 里（如 Claude Code 的 ~/.claude.json），
            不能直接链接，脚本会提示你手动把 mcpServers 合并进去。

用法：
    python setup_links.py                # 建立全部链接
    python setup_links.py --dry          # 只打印将做什么，不执行
    python setup_links.py --check        # 检查现有链接是否完好
    python setup_links.py --tool workbuddy   # 只处理某个工具
"""
import os
import sys
import json
import argparse
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IS_WINDOWS = sys.platform.startswith("win")


def load_local_config():
    p = os.path.join(SCRIPT_DIR, "toolbox-local.json")
    if not os.path.isfile(p):
        print("[setup_links] 未找到 toolbox-local.json。")
        print("  请复制 toolbox-local.example.json 为 toolbox-local.json，填入本机路径。")
        sys.exit(1)
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[setup_links] 读取配置失败: {e}")
        sys.exit(1)


def expand(p):
    if not p:
        return None
    p = os.path.expanduser(p)
    return os.path.abspath(p)


def _status(target, link):
    """返回 (state, resolved_target)。"""
    if os.path.islink(link):
        try:
            cur = os.path.realpath(link)
        except Exception:
            cur = None
        if cur and os.path.realpath(cur) == os.path.realpath(target):
            return "ok", cur
        return "conflict", cur
    if os.path.isdir(link):
        return "exists-dir", None
    if os.path.isfile(link):
        return "exists-file", None
    if not os.path.exists(target):
        return "missing-target", None
    return "missing-link", None


def make_dir_link(target, link, dry):
    """让 link 成为指向 target 的目录链接（junction / symlink）。"""
    state, _ = _status(target, link)
    if state == "ok":
        print(f"  = 已完好 : {link}")
        return
    if state in ("exists-dir", "exists-file"):
        print(f"  ! 跳过（{link} 已是真实文件/目录且非链接，怕覆盖你的数据）：请手动备份后删除再运行")
        return
    if state == "conflict":
        print(f"  ! 冲突（{link} 指向别处）：请手动检查")
        return
    if state == "missing-target":
        print(f"  ! 目标不存在 : {target}")
        return
    if dry:
        print(f"  ~ 将链接 : {link} -> {target}")
        return
    os.makedirs(os.path.dirname(link), exist_ok=True)
    try:
        if IS_WINDOWS:
            subprocess.run(["cmd", "/c", "mklink", "/J", link, target], check=True, capture_output=True)
        else:
            os.symlink(target, link, target_is_directory=True)
        print(f"  + 已链接 : {link} -> {target}")
    except Exception as e:
        print(f"  ! 链接失败 : {e}")


def make_file_link(target, link, dry):
    """让 link 成为指向 target 的文件链接（用于 mcp 配置文件）。"""
    state, _ = _status(target, link)
    if state == "ok":
        print(f"  = 已完好 : {link}")
        return
    if state in ("exists-dir", "exists-file"):
        print(f"  ! 跳过（{link} 已存在且非链接）：请手动备份后删除再运行")
        return
    if state == "conflict":
        print(f"  ! 冲突（{link} 指向别处）：请手动检查")
        return
    if state == "missing-target":
        print(f"  ! 目标不存在 : {target}")
        return
    if dry:
        print(f"  ~ 将链接 : {link} -> {target}")
        return
    if IS_WINDOWS:
        # Windows 文件符号链接需特权；跨盘符时硬链接也不行。降级提示复制。
        print(f"  ! Windows 下跨盘 mcp 配置建议直接复制 servers.json 内容到：")
        print(f"    {link}")
        print(f"    （或开启开发者模式后用 mklink 手动链接）")
        return
    try:
        os.symlink(target, link)
        print(f"  + 已链接 : {link} -> {target}")
    except Exception as e:
        print(f"  ! 链接失败 : {e}")


def main():
    ap = argparse.ArgumentParser(description="把 toolbox 接入各 AI 工具（跨平台链接）")
    ap.add_argument("--dry", action="store_true", help="只打印，不执行")
    ap.add_argument("--check", action="store_true", help="检查现有链接是否完好")
    ap.add_argument("--tool", default=None, help="只处理指定工具")
    args = ap.parse_args()

    cfg = load_local_config()
    use_dist = cfg.get("use_dist", False)
    skills_src = os.path.join(SCRIPT_DIR, ".dist" if use_dist else "skills")
    mcp_src = os.path.join(SCRIPT_DIR, "mcp", "servers.json")

    tools = cfg.get("tools", {})
    if args.tool:
        tools = {args.tool: tools[args.tool]} if args.tool in tools else {}

    apply = not args.dry and not args.check
    print(f"[setup_links] 源 skills : {skills_src}")
    print(f"[setup_links] 源 mcp    : {mcp_src}")
    print(f"[setup_links] 模式      : {'CHECK' if args.check else ('DRY' if args.dry else 'APPLY')}")

    for name, t in tools.items():
        print(f"\n--- 工具: {name} ---")
        sdir = expand(t.get("skills_dir"))
        if sdir:
            make_dir_link(skills_src, sdir, args.dry or args.check)
        mcfg = expand(t.get("mcp_config"))
        mlink = t.get("mcp_symlink", False)
        if mcfg and mlink:
            make_file_link(mcp_src, mcfg, args.dry or args.check)
        elif mcfg and not mlink:
            st, _ = _status(mcp_src, mcfg)
            if st == "missing-link":
                print(f"  ~ {name} 的 mcp 配置({mcfg}) 不支持直接链接（单一 JSON）。")
                print(f"    请将 toolbox/mcp/servers.json 的 mcpServers 段合并进该文件；")
                print(f"    或使用支持独立 mcp.json 的工具并设 mcp_symlink: true。")

    print("\n[setup_links] 完成。")


if __name__ == "__main__":
    main()
