#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
install_skills.py — 把 toolbox 的技能安装/初始化到其他项目或 AI 工具，支持平铺模式。

解决的问题：
    其他项目或 AI 编程工具想使用 toolbox 里的 AI 技能时，无需理解 categories 层级。
    本脚本将所有技能「平铺」（flatten）复制到目标目录下，开箱即用。

    兼容主流 AI 编程工具：
      终端 CLI ：Claude Code, Cursor CLI, Workbuddy
      客户端 IDE：Cursor, Windsurf, Claude Desktop

两种安装模式：
    1) 项目安装（默认）：安装到项目的本地目录（如 ./skills/ 或 ./.skills/）
    2) 全局安装（--to / --global）：安装到 AI 工具的全局 skills 目录

用法：
    # ── 项目安装 ──────────────────────────────────────────
    python install_skills.py                         # 安装所有技能到 ./skills/
    python install_skills.py -t ../my-project        # 安装到指定项目
    python install_skills.py -t ../my-project --common    # 常用技能
    python install_skills.py -t ../my-project -i          # 交互式
    python install_skills.py -t ../my-project -c code-quality   # 仅某分类
    python install_skills.py -t ../my-project -s code-reviewer,systematic-debugging  # 指定技能

    # ── 全局安装（AI 工具）─ ──────────────────────────────
    python install_skills.py --to claude --common        # 安装到 Claude Code
    python install_skills.py --to cursor --all           # 安装到 Cursor
    python install_skills.py --global --common            # 自动检测工具
    python install_skills.py --global -i                  # 交互式选择工具+技能
    python install_skills.py --list-tools                 # 列出支持的 AI 工具

    # ── 信息 ────────────────────────────────────────────
    python install_skills.py --list                      # 列出所有可用技能
    python install_skills.py --list-tools                 # 列出支持的 AI 工具

    # ── 其他 ────────────────────────────────────────────
    python install_skills.py -n                          # dry-run 预览

    TOOLBOX_PATH 环境变量：
        如果 install_skills.py 不在 toolbox 根目录，设置 TOOLBOX_PATH 指向 toolbox。
        例如：
            export TOOLBOX_PATH=/path/to/toolbox
            python /anywhere/install_skills.py --to claude --common

注意：
    - 技能以「平铺」方式安装：原 skills/<分类>/<技能名>/  →  目标 <dir>/<技能名>/
    - 已有目录会被跳过（除非 --force 覆盖）
"""
import os
import sys
import json
import shutil
import argparse
import platform

# ── 路径 ──────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLBOX_HOME = os.environ.get("TOOLBOX_PATH") or _SCRIPT_DIR

SKILLS_ROOT = os.path.join(_TOOLBOX_HOME, "skills")
MANIFEST_PATH = os.path.join(SKILLS_ROOT, "skills-manifest.json")
IS_WINDOWS = platform.system() == "Windows"


# ── 支持的 AI 工具清单 ─────────────────────────────────────
# 每个工具：id, 显示名, 全局 skills 目录（按平台）
TOOL_DEFS = [
    {
        "id": "claudecode",
        "name": "Claude Code",
        "dir": ".claude",
        "desc": "Anthropic Claude Code CLI（终端）",
    },
    {
        "id": "cursor",
        "name": "Cursor",
        "dir": ".cursor",
        "desc": "Cursor IDE（终端 + 客户端），支持 skills 目录",
    },
    {
        "id": "workbuddy",
        "name": "Workbuddy",
        "dir": ".workbuddy",
        "desc": "Workbuddy CLI 工具",
    },
    {
        "id": "windsurf",
        "name": "Windsurf",
        "dir": ".windsurf",
        "desc": "Windsurf IDE（Codeium 出品）",
    },
    {
        "id": "trae",
        "name": "Trae",
        "dir": ".trae",
        "desc": "Trae AI IDE（字节跳动出品）",
    },
    {
        "id": "atomcode",
        "name": "AtomCode",
        "dir": ".atomcode",
        "desc": "AtomCode AI 编码 Agent（AtomGit）",
    },
    {
        "id": "codex",
        "name": "Codex CLI",
        "dir": ".agents",
        "desc": "OpenAI Codex CLI（终端）",
    },
]

# 常用的技能 ID（用于 --common）
COMMON_SKILLS = [
    # 代码质量
    "code-reviewer",
    "systematic-debugging",
    "verification-before-completion",
    "test-driven-development",
    # 开发流程
    "brainstorming",
    "executing-plans",
    "planning-with-files",
    "writing-plans",
    "dispatching-parallel-agents",
    "subagent-driven-development",
    # 架构
    "architecture-analyzer",
    "architect-thinking",
    # AI 效率
    "using-superpowers",
    "writing-skills",
]


# ── 工具函数 ──────────────────────────────────────────────

def _home_dir() -> str:
    """跨平台获取用户 home 目录"""
    if IS_WINDOWS:
        return os.environ.get("USERPROFILE", os.path.expanduser("~"))
    return os.path.expanduser("~")


def get_tool_global_dir(tool_id: str) -> str:
    """返回 AI 工具的全局 skills 目录"""
    for t in TOOL_DEFS:
        if t["id"] == tool_id:
            return os.path.join(_home_dir(), t["dir"], "skills")
    return None


def detect_installed_tools() -> list:
    """检测本机安装了哪些 AI 工具（按其全局目录是否存在）"""
    installed = []
    for t in TOOL_DEFS:
        base = os.path.join(_home_dir(), t["dir"])
        if os.path.isdir(base):
            installed.append(t)
    return installed


def load_manifest() -> dict:
    """加载技能清单，返回 {skill_id: {name, category, path, description}}"""
    if not os.path.isfile(MANIFEST_PATH):
        print(f"[install_skills] 错误：未找到技能清单")
        print(f"  期望路径: {MANIFEST_PATH}")
        print(f"  请确保在 toolbox 根目录运行，或设置 TOOLBOX_PATH 环境变量")
        sys.exit(1)

    with open(MANIFEST_PATH, encoding="utf-8") as f:
        manifest = json.load(f)

    skills = {}
    for cat in manifest.get("categories", []):
        cat_id = cat["id"]
        for sk in cat.get("skills", []):
            sk_id = sk["id"]
            skill_path = os.path.join(SKILLS_ROOT, sk["path"])
            skills[sk_id] = {
                "id": sk_id,
                "name": sk.get("name", sk_id),
                "category": cat_id,
                "category_name": cat.get("name", cat_id),
                "path": skill_path,
                "description": sk.get("description", ""),
            }
    return skills


def print_skills_table(skills: dict, category: str = None):
    """打印技能列表（按分类分组）"""
    cats = {}
    for sid, info in skills.items():
        if category and info["category"] != category:
            continue
        c = info["category_name"]
        cats.setdefault(c, []).append(info)

    for cname, items in cats.items():
        print(f"\n  {cname} ({len(items)}):")
        for sk in sorted(items, key=lambda x: x["id"]):
            desc = sk["description"][:60] + "..." if len(sk["description"]) > 60 else sk["description"]
            print(f"    {sk['id']:40s}  {desc}")


def prompt_yes_no(prompt: str, default: bool = True) -> bool:
    """交互式 yes/no 提示"""
    hint = "Y/n" if default else "y/N"
    ans = input(f"{prompt} [{hint}] ").strip().lower()
    if ans == "":
        return default
    return ans.startswith("y")


def copy_skill(src: str, dst: str, dry_run: bool, force: bool) -> bool:
    """复制单个技能，返回是否成功"""
    if not os.path.isdir(src):
        if dry_run:
            print(f"  ! 源目录不存在: {src}")
        return False

    if os.path.exists(dst):
        if not force:
            print(f"  - 已存在（跳过）: {dst}")
            return True
        shutil.rmtree(dst)

    if dry_run:
        print(f"  ~ 将复制: {src}  ->  {dst}")
        return True

    try:
        shutil.copytree(src, dst, dirs_exist_ok=force,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        print(f"  + 已安装: {os.path.basename(src)}")
        return True
    except Exception as e:
        print(f"  ! 复制失败: {e}")
        return False


# ── 选择技能（根据命令行参数） ─────────────────────────────

def select_skills(all_skills: dict, args) -> list:
    """根据命令行参数确定要安装的技能列表"""
    selected_ids = set()

    if args.skills:
        requested = [s.strip() for s in args.skills.split(",") if s.strip()]
        for sid in requested:
            if sid not in all_skills:
                print(f"[install_skills] 警告：未知技能 '{sid}'，跳过")
            else:
                selected_ids.add(sid)
    elif args.category:
        for sid, info in all_skills.items():
            if info["category"] == args.category:
                selected_ids.add(sid)
        if not selected_ids:
            print(f"[install_skills] 错误：未找到分类 '{args.category}'")
            available = sorted(set(info["category"] for info in all_skills.values()))
            print(f"  可用分类: {', '.join(available)}")
            sys.exit(1)
    elif args.interactive:
        print(f"[install_skills] 交互式选择技能（按分类）")
        cats = {}
        for sid, info in all_skills.items():
            cats.setdefault(info["category"], []).append(sid)

        for cat_id in sorted(cats.keys()):
            cat_name = next(
                (info["category_name"] for info in all_skills.values()
                 if info["category"] == cat_id),
                cat_id,
            )
            print(f"\n--- {cat_name} ({cat_id}) ---")
            for sid in sorted(cats[cat_id]):
                info = all_skills[sid]
                desc = info["description"][:60] + "..." if len(info["description"]) > 60 else info["description"]
                print(f"  {sid:40s}  {desc}")

            if prompt_yes_no(f"\n安装「{cat_name}」分类下的所有技能？", default=False):
                for sid in cats[cat_id]:
                    selected_ids.add(sid)

        if not selected_ids:
            print("[install_skills] 未选择任何技能，退出")
            return None
    elif args.common:
        for sid in COMMON_SKILLS:
            if sid in all_skills:
                selected_ids.add(sid)
        if not selected_ids:
            print("[install_skills] 错误：常用技能清单中的技能均未找到，请检查 manifest")
            sys.exit(1)
    else:
        # 默认：所有技能
        selected_ids = set(all_skills.keys())

    return [all_skills[sid] for sid in sorted(selected_ids)]


# ── 安装执行（复制） ──────────────────────────────────────

def install_skills(selected: list, target_dir: str, dry_run: bool, force: bool):
    """执行安装：复制选中的技能到目标目录"""
    print(f"[install_skills] 源       : {SKILLS_ROOT}")
    print(f"[install_skills] 目标     : {target_dir}")
    print(f"[install_skills] 技能数   : {len(selected)}")
    print(f"[install_skills] 模式     : {'dry-run' if dry_run else 'apply'}")
    print(f"[install_skills] 平铺     : 是（去除分类层级，技能目录直接放在目标目录下）")

    if not dry_run:
        os.makedirs(target_dir, exist_ok=True)

    success = 0
    failed = 0
    for sk in selected:
        src = sk["path"]
        dst = os.path.join(target_dir, sk["id"])
        ok = copy_skill(src, dst, dry_run, force)
        if ok and not dry_run and os.path.exists(dst):
            success += 1
        elif not ok:
            failed += 1

    # dry-run 下也算成功（预览）
    if dry_run:
        success = len(selected)

    if not dry_run:
        print(f"\n[install_skills] 完成：{success} 个安装成功", end="")
        if failed:
            print(f"，{failed} 个失败", end="")
        print()

    return success, failed


# ── 入口 ──────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="从 toolbox 安装/初始化技能到项目或 AI 工具（平铺模式）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
示例：
  # 项目安装
  python install_skills.py -t ../my-project --common
  python install_skills.py -t ../my-project --category code-quality
  python install_skills.py -t ../my-project -i

  # 全局安装（AI 工具）
  python install_skills.py --to claude --common
  python install_skills.py --to cursor --all
  python install_skills.py --global --common
  python install_skills.py --global -i

  # 信息
  python install_skills.py --list
  python install_skills.py --list-tools

详情见 README.md 或运行 --help。""",
    )
    # ── 安装位置 ──
    pos = ap.add_argument_group("安装位置")
    pos.add_argument("--target", "-t", default=None,
                     help="目标项目目录（默认：当前目录）")
    pos.add_argument("--dir", "-d", default="skills",
                     help="目标目录名（默认：skills），仅 --target 模式有效")
    pos.add_argument("--to", default=None, dest="tool",
                     help=f"安装到 AI 工具全局目录：{', '.join(t['id'] for t in TOOL_DEFS)}")
    pos.add_argument("--global", "-g", action="store_true", dest="global_mode",
                     help="自动检测本机已安装的 AI 工具并安装")

    # ── 技能选择 ──
    sel = ap.add_argument_group("技能选择（互斥，默认安装所有）")
    sel.add_argument("--category", "-c", default=None,
                     help="只安装指定分类（按 ID，如 code-quality）")
    sel.add_argument("--skills", "-s", default=None,
                     help="只安装指定技能（逗号分隔的 ID 列表）")
    sel.add_argument("--common", action="store_true",
                     help="安装常用技能（14 个核心开发技能）")
    sel.add_argument("--interactive", "-i", action="store_true",
                     help="交互式选择要安装的技能")

    # ── 信息 ──
    info = ap.add_argument_group("信息")
    info.add_argument("--list", "-l", action="store_true",
                      help="列出所有可用技能")
    info.add_argument("--list-tools", action="store_true",
                      help="列出支持的 AI 工具及检测状态")

    # ── 行为 ──
    beh = ap.add_argument_group("行为")
    beh.add_argument("--force", "-f", action="store_true",
                     help="覆盖已有目录")
    beh.add_argument("--dry-run", "-n", action="store_true",
                     help="预览操作，不实际复制")
    args = ap.parse_args()

    # ── --list 模式 ──
    all_skills = load_manifest()
    if args.list:
        print(f"[install_skills] toolbox: {_TOOLBOX_HOME}")
        print(f"[install_skills] 可用技能（共 {len(all_skills)} 个）：")
        print_skills_table(all_skills)
        print()
        return

    # ── --list-tools 模式 ──
    if args.list_tools:
        print(f"[install_skills] 支持的 AI 编程工具：")
        print()
        print(f"  {'工具 ID':<20s} {'显示名':<30s} {'状态':<12s} 全局 Skills 目录")
        print(f"  {'-'*20} {'-'*30} {'-'*12}  {'-'*30}")
        for t in TOOL_DEFS:
            gdir = get_tool_global_dir(t["id"])
            installed = os.path.isdir(os.path.join(_home_dir(), t["dir"]))
            status = "✓ 已安装" if installed else "  未检测到"
            print(f"  {t['id']:<20s} {t['name']:<30s} {status:<12s} {gdir}")
        print()
        print("提示：使用 --to <工具ID> 安装到指定工具，或用 --global 自动检测。")
        return

    # ── 确定目标目录 ──
    target_dir = None
    install_mode = ""

    if args.tool:
        # 全局安装：安装到指定 AI 工具
        tool_info = None
        for t in TOOL_DEFS:
            if t["id"] == args.tool:
                tool_info = t
                break
        if not tool_info:
            print(f"[install_skills] 错误：不支持的 AI 工具 '{args.tool}'")
            print(f"  支持的工具有：{', '.join(t['id'] for t in TOOL_DEFS)}")
            print(f"  使用 --list-tools 查看详情")
            sys.exit(1)

        gdir = get_tool_global_dir(args.tool)
        tool_base = os.path.join(_home_dir(), tool_info["dir"])
        if not os.path.isdir(tool_base):
            print(f"[install_skills] 警告：{tool_info['name']} 的目录不存在")
            print(f"  期望路径: {tool_base}")
            print(f"  请先安装 {tool_info['name']}，或手动创建该目录")
            if not args.dry_run:
                if not prompt_yes_no("仍然继续？（将创建目录）", default=False):
                    print("[install_skills] 已取消")
                    return

        target_dir = gdir
        install_mode = f"全局 → {tool_info['name']} ({tool_info['id']})"

    elif args.global_mode:
        # 自动检测已安装的工具
        installed = detect_installed_tools()
        if not installed:
            print("[install_skills] 未检测到已安装的 AI 工具。")
            print(f"  当前支持的工具有：{', '.join(t['id'] for t in TOOL_DEFS)}")
            print(f"  请先安装目标 AI 工具，或使用 --to <工具ID> 指定。")
            print(f"  也可使用 -t <项目目录> 安装到项目中。")
            sys.exit(1)

        if len(installed) == 1:
            t = installed[0]
            target_dir = get_tool_global_dir(t["id"])
            install_mode = f"全局 → {t['name']} ({t['id']})"
            print(f"[install_skills] 检测到：{t['name']}")
        else:
            # 多个工具，让用户选择
            print(f"[install_skills] 检测到多个 AI 工具：")
            for i, t in enumerate(installed, 1):
                print(f"  {i}. {t['name']} ({t['id']})")
            print()
            try:
                choice = int(input("请选择要安装到的工具编号 [1]: ").strip() or "1")
                t = installed[choice - 1]
            except (ValueError, IndexError):
                print("[install_skills] 无效选择")
                sys.exit(1)
            target_dir = get_tool_global_dir(t["id"])
            install_mode = f"全局 → {t['name']} ({t['id']})"
    else:
        # 项目安装
        target_base = os.path.abspath(args.target) if args.target else os.getcwd()
        target_dir = os.path.join(target_base, args.dir)
        install_mode = f"项目 → {target_dir}"

    # ── 选择技能 ──
    selected = select_skills(all_skills, args)
    if selected is None:
        return

    # ── 执行安装 ──
    print(f"[install_skills] 模式     : {install_mode}")
    install_skills(selected, target_dir, args.dry_run, args.force)

    if not args.dry_run:
        print()
        if args.tool or args.global_mode:
            print(f"提示：技能已安装到 AI 工具目录，重启工具即可生效。")
        else:
            print(f"提示：请在 AI 工具中将 skills 目录指向：")
            print(f"  {target_dir}")


if __name__ == "__main__":
    main()
