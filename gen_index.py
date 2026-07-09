#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_index.py — 从 SKILL.md frontmatter 自动重建 toolbox 索引，消灭手维护漂移。

零依赖（仅 Python 标准库），跨平台。

为什么需要它：
    toolbox 的索引（根 README、skills-manifest.json、各分类 README）原本靠手维护，
    已经和磁盘实盘对不上（manifest 写 47，实际 48）。唯一可信源是文件系统里
    每个 SKILL.md 的 frontmatter。本脚本扫 frontmatter，一次生成全部索引产物，
    并从根上消除“人维护索引必漂移”的问题。

产物：
    1. skills/skills-manifest.json       机器 / agent / MCP 消费
    2. README.md                         仓库根，GitHub 浏览（人类向）
    3. skills/<cat>/README.md            分类说明（自动列表 + 手写“归类逻辑”块）
    4. Skills-Catalog.md                 toolbox 根，agent 总电话簿
    5. <ob-wiki>/mocs/Skills-Catalog.md  镜像到知识库（--ob-wiki，默认 ../ob-wiki）

手写块策略：
    每个生成文件用 <!-- AUTO-GENERATED-START/END --> 包裹自动内容，
    <!-- HANDWRITTEN-START/END --> 之间保留你写的内容（归类逻辑、项目介绍等）。
    重跑本脚本只重写 AUTO 块，HANDWRITTEN 块原样保留。
    根 README 首次生成时，会把整份旧 README 当作手写块保留，不丢介绍文字。

中文名 / 中文摘要继承：
    SKILL.md 里没有中文显示名，旧 manifest 里有（“AI前沿观察”等二次元数据）。
    解析优先级：frontmatter metadata.zh-name  >  旧 manifest 同名 id  >  slug。
    中文摘要同理。这样首次生成不退化显示，新 skill 自动纳入；
    鼓励你后续把 metadata.zh-name 写进 SKILL.md，让真源彻底归一。

用法：
    python gen_index.py                 # 生成全部
    python gen_index.py --check         # 仅打印与现有 manifest 的差异，不写文件
    python gen_index.py --no-obwiki     # 不镜像到 ob-wiki
    python gen_index.py --ob-wiki E:/dev/project/ob-wiki
"""
import os
import re
import sys
import json
import datetime
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_DIR = os.path.join(SCRIPT_DIR, "skills")
MANIFEST_PATH = os.path.join(SKILLS_DIR, "skills-manifest.json")
DEFAULT_OBWIKI = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "ob-wiki"))

# 分类中文名（fallback；若 skills/<cat>/README.md 有 frontmatter title 则优先用那个）
CATEGORY_NAMES = {
    "ai-productivity": "AI 效率",
    "architecture-design": "架构设计",
    "code-quality": "代码质量",
    "content-processing": "内容处理",
    "dev-tools": "开发工具",
    "development-workflow": "开发流程",
    "social-publish": "社交发布",
    "visual-creation": "视觉创作",
    "web-scraping": "网页抓取",
}

AUTO_S, AUTO_E = "<!-- AUTO-GENERATED-START -->", "<!-- AUTO-GENERATED-END -->"
HW_S, HW_E = "<!-- HANDWRITTEN-START -->", "<!-- HANDWRITTEN-END -->"


# ------------------------- 容错 YAML frontmatter 解析 -------------------------
def extract_frontmatter(raw: str) -> dict:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?", raw, re.DOTALL)
    if not m:
        return {}
    return _parse_simple_yaml(m.group(1))


def _strip_inline(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def _ind(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _parse_simple_yaml(block: str) -> dict:
    """覆盖 toolbox 实测的 frontmatter 写法：
    - key: "value" / key: value（字符串，带或不带引号）
    - key: |  或 key: >  （块标量，保留 / 折叠换行）
    - key: 换行后跟 - item          （列表）
    - key: 换行后跟裸缩进文本        （裸多行 plain，折叠成空格）
    - key: 换行后跟 subkey: val     （一层嵌套，如 metadata）
    """
    lines = block.split("\n")
    n = len(lines)

    def parse_block(start: int, base_ind: int):
        container = None
        i = start
        while i < n:
            line = lines[i]
            if line.strip() == "":
                i += 1
                continue
            cur = _ind(line)
            if cur <= base_ind:
                break
            content = line.strip()
            if content.startswith("- "):
                if container is None:
                    container = []
                item = content[2:].strip()
                if i + 1 < n and _ind(lines[i + 1]) > cur:
                    val, i = parse_block(i + 1, cur)
                    container.append(val)
                else:
                    container.append(_strip_inline(item))
                    i += 1
            else:
                if ":" not in content:
                    i += 1
                    continue
                k, _, v = content.partition(":")
                k = k.strip()
                v = v.strip()
                if container is None:
                    container = {}
                if v == "":
                    if i + 1 < n and _ind(lines[i + 1]) > cur:
                        nxt = lines[i + 1].strip()
                        if nxt.startswith("- "):
                            val, i = parse_block(i + 1, cur)
                            container[k] = val
                        elif re.match(r"^[A-Za-z0-9_\-]+:", nxt):
                            val, i = parse_block(i + 1, cur)
                            container[k] = val
                        else:
                            # 裸多行 plain：折叠换行成空格
                            tl, j = [], i + 1
                            while j < n and (lines[j].strip() == "" or _ind(lines[j]) > cur):
                                if lines[j].strip() != "":
                                    tl.append(lines[j].strip())
                                j += 1
                            container[k] = " ".join(tl)
                            i = j
                    else:
                        container[k] = ""
                        i += 1
                elif v.startswith("|") or v.startswith(">"):
                    tl, j = [], i + 1
                    while j < n and (lines[j].strip() == "" or _ind(lines[j]) > cur):
                        if lines[j].strip() != "":
                            tl.append(lines[j].strip())
                        j += 1
                    container[k] = (" " if v.startswith(">") else "\n").join(tl)
                    i = j
                else:
                    container[k] = _strip_inline(v)
                    i += 1
        if container is None:
            container = {}
        return container, i

    result, _ = parse_block(0, -1)
    return result if isinstance(result, dict) else {}


# ------------------------------- 加载与继承 -------------------------------
def load_legacy(manifest_path: str):
    if not os.path.isfile(manifest_path):
        return {}, {}
    try:
        with open(manifest_path, encoding="utf-8") as f:
            m = json.load(f)
        names, descs = {}, {}
        for c in m.get("categories", []):
            for s in c.get("skills", []):
                names[s["id"]] = s.get("name", "")
                descs[s["id"]] = s.get("description", "")
        return names, descs
    except Exception:
        return {}, {}


def load_skills(skills_dir: str):
    cats = {}
    for cat in sorted(os.listdir(skills_dir)):
        cpath = os.path.join(skills_dir, cat)
        if not os.path.isdir(cpath):
            continue
        skill_files = []
        for name in sorted(os.listdir(cpath)):
            spath = os.path.join(cpath, name, "SKILL.md")
            if os.path.isfile(spath):
                skill_files.append((name, spath))
        if not skill_files:
            continue
        skills = []
        for sname, spath in skill_files:
            try:
                with open(spath, encoding="utf-8") as f:
                    raw = f.read()
            except Exception:
                raw = ""
            fm = extract_frontmatter(raw)
            meta = fm.get("metadata", {}) or {}
            if not isinstance(meta, dict):
                meta = {}
            desc = fm.get("description", "") or ""
            tags = meta.get("tags", []) or []
            if isinstance(tags, str):
                tags = [tags]
            at = fm.get("allowed-tools", []) or []
            if isinstance(at, str):
                at = [x.strip() for x in at.split(",") if x.strip()]
            skills.append({
                "id": sname,
                "slug": fm.get("name", sname),
                "version": str(fm.get("version", "")),
                "description": desc,
                "tags": tags,
                "allowed_tools": at,
                "user_invocable": fm.get("user-invocable", None),
                "argument_hint": fm.get("argument-hint", ""),
                "requires_mcp": meta.get("requires_mcp", []) or [],
                "zh_name": meta.get("zh-name", "") or "",
                "cat": cat,
                "rel": f"skills/{cat}/{sname}/SKILL.md",
            })
        cats[cat] = skills
    return cats


def short(d: str, n: int = 56) -> str:
    d = re.sub(r"\s+", " ", d).strip()
    return d[:n] + ("…" if len(d) > n else "")


# ------------------------------- 手写块保留 -------------------------------
def render_with_handwritten(path: str, auto_content: str, hw_placeholder: str = "") -> str:
    hw = ""
    if os.path.isfile(path):
        old = ""
        try:
            with open(path, encoding="utf-8") as f:
                old = f.read()
        except Exception:
            old = ""
        m = re.search(re.escape(HW_S) + r"(.*?)" + re.escape(HW_E), old, re.DOTALL)
        if m:
            hw = m.group(1).strip()
        elif AUTO_S not in old:
            # 旧文件无标记（如原始手维护 README）→ 整份当作手写保留
            hw = old.strip()
    if not hw:
        hw = hw_placeholder
    return f"{AUTO_S}\n{auto_content}\n{AUTO_E}\n\n{HW_S}\n{hw}\n{HW_E}\n"


def write_if_changed(path: str, content: str, dry: bool) -> bool:
    # 统一用 LF，避免 Windows 上 CRLF 导致每次重跑都判定“变更”（破坏幂等）
    content = content.replace("\r\n", "\n")
    existed = os.path.isfile(path)
    old = ""
    if existed:
        try:
            with open(path, encoding="utf-8", newline="") as f:
                old = f.read().replace("\r\n", "\n")
        except Exception:
            old = ""
    if old == content:
        print(f"  = 未变更 : {os.path.relpath(path, SCRIPT_DIR)}")
        return False
    if dry:
        print(f"  ~ 将更新 : {os.path.relpath(path, SCRIPT_DIR)}")
        return True
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print(f"  + {'新建' if not existed else '更新'} : {os.path.relpath(path, SCRIPT_DIR)}")
    return True


# ------------------------------- 各产物渲染 -------------------------------
def render_manifest(cats, legacy_names, legacy_descs, today):
    categories = []
    for cat, skills in cats.items():
        sk = []
        for s in skills:
            zh = s["zh_name"] or legacy_names.get(s["id"]) or s["slug"]
            md = legacy_descs.get(s["id"]) or short(s["description"], 48)
            sk.append({
                "id": s["id"],
                "name": zh,
                "path": f"{cat}/{s['id']}",
                "description": md,
            })
        categories.append({
            "id": cat,
            "name": CATEGORY_NAMES.get(cat, cat),
            "path": cat,
            "skills": sk,
        })
    return {
        "version": "1.0.0",
        "updated": today,
        "totalSkills": sum(len(v) for v in cats.values()),
        "categories": categories,
    }


def render_root_readme(cats, today):
    total = sum(len(v) for v in cats.values())
    lines = [
        f"# Toolbox · AI Skills 仓库",
        "",
        f"> 自动生成于 {today} · 共 **{total}** 个技能 / **{len(cats)}** 个分类。",
        "> 本文件目录部分为自动生成（AUTO 块），下方介绍为手写，请勿在 AUTO 块内手改。",
        "",
        "## 分类索引",
        "",
        "| 分类 | 中文名 | 技能数 |",
        "|------|--------|--------|",
    ]
    for cat in sorted(cats):
        cn = CATEGORY_NAMES.get(cat, cat)
        lines.append(f"| [{cat}](skills/{cat}/README.md) | {cn} | {len(cats[cat])} |")
    lines += [
        "",
        "## 全部技能（按分类）",
        "",
    ]
    for cat in sorted(cats):
        cn = CATEGORY_NAMES.get(cat, cat)
        lines.append(f"### {cn}（`{cat}`）")
        lines.append("")
        lines.append("| 技能 | 中文名 | 说明 |")
        lines.append("|------|--------|------|")
        for s in cats[cat]:
            zh = s.get("display", s["id"])
            lines.append(f"| [{s['id']}]({s['rel']}) | {zh} | {short(s['description'], 40)} |")
        lines.append("")
    return "\n".join(lines) + "\n"


def render_category_readme(cat, skills):
    cn = CATEGORY_NAMES.get(cat, cat)
    lines = [
        f"# {cn}（`{cat}`）",
        "",
        f"> 本分类共 **{len(skills)}** 个技能。下方“技能列表”为自动生成，",
        "> “归类逻辑”为手写块，请在此说明本分类的边界与归类理由。",
        "",
        "## 技能列表（自动）",
        "",
        "| 技能 | 中文名 | 说明 | 标签 |",
        "|------|--------|------|------|",
    ]
    for s in skills:
        cn = s.get("display", s["id"])
        cn = cn if cn != s["id"] else "—"
        tags = ", ".join(s["tags"]) if s["tags"] else "—"
        lines.append(f"| [{s['id']}]({s['rel']}) | {cn} | {short(s['description'], 40)} | {tags} |")
    lines.append("")
    return "\n".join(lines)


def render_catalog(cats, today, link_prefix: str, with_frontmatter: bool = False) -> str:
    total = sum(len(v) for v in cats.values())
    out = []
    if with_frontmatter:
        out += [
            "---",
            "title: Skills Catalog",
            f"updated: {today}",
            "type: moc",
            "---",
            "",
        ]
    out += [
        "# Skills Catalog（技能总索引）",
        "",
        f"> 自动生成于 {today} · 共 **{total}** 个技能 / **{len(cats)}** 个分类。",
        "> 本文件由 `gen_index.py` 生成，**请勿手改**；归类逻辑请写到各 `skills/<cat>/README.md`。",
        "> 这是 agent 的“电话簿”：开发时按场景匹配技能，再读对应 SKILL.md。",
        "",
        "## 按场景速查",
        "",
    ]
    # 简单场景分组（基于分类）
    scene_map = {
        "ai-productivity": "AI 提效 / 创业 / 写作",
        "architecture-design": "架构 / 数据库 / UI-UX",
        "code-quality": "代码审查 / 调试 / TDD",
        "content-processing": "Markdown / 翻译 / 摘要",
        "dev-tools": "开发工具 / 浏览器 / Git",
        "development-workflow": "开发流程 / 计划 / 并行 Agent",
        "social-publish": "发布到 微信 / 微博 / X / 小红书",
        "visual-creation": "配图 / 漫画 / 信息图 / 幻灯片",
        "web-scraping": "网页 / YouTube / X 抓取转 Markdown",
    }
    for cat in sorted(cats):
        scene = scene_map.get(cat, cat)
        out.append(f"- **{scene}** → 见 [{CATEGORY_NAMES.get(cat, cat)}]({link_prefix}skills/{cat}/README.md)")
    out += ["", "## 全量清单", ""]
    for cat in sorted(cats):
        cn = CATEGORY_NAMES.get(cat, cat)
        out.append(f"### {cn}（`{cat}`）")
        out.append("")
        for s in cats[cat]:
            zh = s.get("display", s["id"])
            tags = f"  ·  `{', '.join(s['tags'])}`" if s["tags"] else ""
            mcp = f"  ·  需 MCP: `{', '.join(s['requires_mcp'])}`" if s["requires_mcp"] else ""
            out.append(f"- [{s['id']}]({link_prefix}{s['rel']}) — {zh}{tags}{mcp}")
        out.append("")
    return "\n".join(out) + "\n"


# ------------------------------- 主流程 -------------------------------
def main():
    ap = argparse.ArgumentParser(description="从 SKILL.md frontmatter 自动重建 toolbox 索引")
    ap.add_argument("--check", action="store_true", help="仅检查差异，不写文件")
    ap.add_argument("--no-obwiki", action="store_true", help="不镜像到 ob-wiki")
    ap.add_argument("--ob-wiki", default=DEFAULT_OBWIKI, help="ob-wiki 仓库路径")
    args = ap.parse_args()

    today = datetime.date.today().isoformat()
    dry = args.check

    print(f"[gen_index] 扫描 {os.path.relpath(SKILLS_DIR, SCRIPT_DIR)} ...")
    cats = load_skills(SKILLS_DIR)
    total = sum(len(v) for v in cats.values())
    legacy_names, legacy_descs = load_legacy(MANIFEST_PATH)
    print(f"[gen_index] 实盘技能数: {total}  分类数: {len(cats)}")
    # 解析展示名：frontmatter metadata.zh-name > 旧 manifest 中文名 > slug
    for skills in cats.values():
        for s in skills:
            s["display"] = s["zh_name"] or legacy_names.get(s["id"]) or s["id"]

    if dry:
        old_total = len(legacy_names)
        print(f"[gen_index] 现有 manifest 技能数: {old_total}")
        if old_total != total:
            print(f"[gen_index] ⚠ 漂移: manifest 声称 {old_total}，实盘 {total}（差 {total - old_total}）")
        # 列出 manifest 有但磁盘无 / 磁盘有但 manifest 无
        disk_ids = {s["id"] for sk in cats.values() for s in sk}
        man_ids = set(legacy_names.keys())
        missing = disk_ids - man_ids
        ghost = man_ids - disk_ids
        if missing:
            print(f"[gen_index] 磁盘新增未入 manifest: {sorted(missing)}")
        if ghost:
            print(f"[gen_index] manifest 残留已删技能: {sorted(ghost)}")
        for cat in sorted(cats):
            for s in cats[cat]:
                zh = s["zh_name"] or legacy_names.get(s["id"]) or s["slug"]
                md = legacy_descs.get(s["id"]) or short(s["description"], 48)
                print(f"    {cat}/{s['id']:<28} -> {zh}  | {md}")
        print("[gen_index] --check 完成，未写入任何文件。")
        return

    # 1) manifest
    manifest = render_manifest(cats, legacy_names, legacy_descs, today)
    write_if_changed(MANIFEST_PATH, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", dry)

    # 2) 根 README
    root_auto = render_root_readme(cats, today)
    root_hw = "# Toolbox\n\n> 在这里写你的项目介绍 / 使用说明（手写块，重生成不会被覆盖）。\n"
    root_md = render_with_handwritten(os.path.join(SCRIPT_DIR, "README.md"), root_auto, root_hw)
    write_if_changed(os.path.join(SCRIPT_DIR, "README.md"), root_md, dry)

    # 3) 各分类 README
    for cat in sorted(cats):
        cpath = os.path.join(SKILLS_DIR, cat, "README.md")
        cauto = render_category_readme(cat, cats[cat])
        chw = (
            "## 归类逻辑（手写，保留）\n\n"
            "在此写本分类解决哪类问题、与相邻分类的边界。\n"
            "例如：code-quality 只审不流，流程编排见 development-workflow。\n"
        )
        cmd = render_with_handwritten(cpath, cauto, chw)
        write_if_changed(cpath, cmd, dry)

    # 4) toolbox 根 Skills-Catalog
    cat_box = render_catalog(cats, today, link_prefix="")
    cat_box_full = render_with_handwritten(
        os.path.join(SCRIPT_DIR, "Skills-Catalog.md"),
        cat_box.strip(),
        "# Skills Catalog\n\n> 手写备注区（一般留空，本文件以 AUTO 块为主）。\n",
    )
    write_if_changed(os.path.join(SCRIPT_DIR, "Skills-Catalog.md"), cat_box_full, dry)

    # 5) 镜像到 ob-wiki
    if not args.no_obwiki:
        ob = args.ob_wiki
        ob_mocs = os.path.join(ob, "mocs")
        if os.path.isdir(ob_mocs):
            link_prefix = "../../toolbox/"
            cat_wiki = render_catalog(cats, today, link_prefix=link_prefix, with_frontmatter=True)
            write_if_changed(os.path.join(ob_mocs, "Skills-Catalog.md"), cat_wiki, dry)
        else:
            print(f"  ! 跳过 ob-wiki 镜像: 未找到 {ob_mocs}")

    print(f"[gen_index] 完成。共 {total} 技能 / {len(cats)} 分类。")


if __name__ == "__main__":
    main()
