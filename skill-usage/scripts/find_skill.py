#!/usr/bin/env python3
"""Locate an installed Skill and print a compact usage-oriented summary.

Usage:
  python find_skill.py --list [--root-only]          # 列出所有已安装 skill
  python find_skill.py --name <关键词> [--all]        # 查某个 skill（模糊匹配）
  python find_skill.py --name <关键词> --json         # 机器可读输出
  python find_skill.py --roots                        # 只看搜索根目录

Design notes:
  - Stdlib only. Frontmatter is parsed with a small YAML-subset reader (no pyyaml).
  - Search roots are ordered by precedence; same-named skills from lower-priority
    roots are reported as shadowed rather than dropped.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

BUILTIN_SKILLS = Path(
    "/Applications/WorkBuddy.app/Contents/Resources/app.asar.unpacked"
    "/resources/plugins/workbuddy-builtin/skills"
)

HOME = Path.home()


def search_roots(cwd: Path | None = None) -> list[tuple[str, Path]]:
    """Return (label, path) roots ordered by lookup precedence."""
    cwd = cwd or Path.cwd()
    roots: list[tuple[str, Path]] = [
        ("project", cwd / ".workbuddy" / "skills"),
        ("user", HOME / ".workbuddy" / "skills"),
    ]
    # Plugin / marketplace cache: <cache>/<source>/<plugin>/<version>/skills
    cache = HOME / ".workbuddy" / "plugins" / "cache"
    if cache.is_dir():
        for src in sorted(p for p in cache.iterdir() if p.is_dir()):
            for plugin in sorted(p for p in src.iterdir() if p.is_dir()):
                versions = sorted((v for v in plugin.iterdir() if v.is_dir()), key=lambda p: p.name)
                if not versions:
                    continue
                # Highest version sorts last; use it, note the shadowed count.
                latest = versions[-1]
                skills_dir = latest / "skills"
                if skills_dir.is_dir():
                    label = f"plugin:{src.name}/{plugin.name}@{latest.name}"
                    if len(versions) > 1:
                        label += f"(+{len(versions) - 1} old)"
                    roots.append((label, skills_dir))
    if BUILTIN_SKILLS.is_dir():
        roots.append(("builtin", BUILTIN_SKILLS))
    for label, extra in (("claude", HOME / ".claude" / "skills"), ("codex", HOME / ".codex" / "skills")):
        if extra.is_dir():
            roots.append((label, extra))
    return roots


def parse_frontmatter(text: str) -> dict[str, str]:
    """Parse a flat YAML frontmatter block (scalars only)."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    block = text[3:end]
    data: dict[str, str] = {}
    key: str | None = None
    for raw in block.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", line)
        if m:
            key = m.group(1)
            value = m.group(2).strip()
            data[key] = value.strip('"').strip("'")
        elif key and line.startswith((" ", "\t")):
            # Continuation of a folded scalar.
            data[key] = (data.get(key, "") + " " + line.strip()).strip()
    return data


def read_skill(skill_md: Path, root_label: str) -> dict:
    text = ""
    try:
        text = skill_md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        pass
    fm = parse_frontmatter(text)
    skill_dir = skill_md.parent
    resources = {}
    for sub in ("scripts", "references", "assets"):
        d = skill_dir / sub
        if d.is_dir():
            resources[sub] = sum(1 for p in d.rglob("*") if p.is_file())
    body_line = next((m.start() for m in re.finditer(r"\n# ", text)), -1)
    return {
        "name": fm.get("name", skill_dir.name),
        "dir_name": skill_dir.name,
        "description": fm.get("description", ""),
        "agent_created": fm.get("agent_created", "").lower() == "true",
        "path": str(skill_md),
        "root": root_label,
        "resources": resources,
        "lines": text.count("\n") + 1,
        "body_offset": body_line,
    }


def discover(cwd: Path | None = None) -> list[dict]:
    found: list[dict] = []
    for label, root in search_roots(cwd):
        if not root.is_dir():
            continue
        for skill_md in sorted(root.glob("*/SKILL.md")):
            found.append(read_skill(skill_md, label))
        # Builtin/plugin caches sometimes nest one level deeper (e.g. plugins/*/skills/<name>).
        for skill_md in sorted(root.glob("*/*/SKILL.md")):
            if skill_md.parent.parent.name == "skills":
                found.append(read_skill(skill_md, label))
    return found


def dedupe(skills: list[dict]) -> list[dict]:
    """First occurrence wins (roots are ordered); later ones get a shadowed_by marker."""
    seen: dict[str, dict] = {}
    out: list[dict] = []
    for s in skills:
        key = s["dir_name"]
        if key in seen:
            out.append({**s, "shadowed_by": seen[key]["path"]})
            continue
        seen[key] = s
        out.append(s)
    return out


def score(skill: dict, query: str) -> int:
    q = query.lower().strip()
    name = skill["dir_name"].lower()
    if name == q:
        return 100
    s = 0
    if q in name:
        s = max(s, 60)
    if q in skill["name"].lower():
        s = max(s, 55)
    if q in skill["description"].lower():
        s = max(s, 30)
    # Token overlap for multi-word / Chinese queries.
    tokens = [t for t in re.split(r"[\s，,、/]+", q) if t]
    if tokens:
        hits = sum(1 for t in tokens if t in name or t in skill["description"].lower())
        s = max(s, 10 * hits)
    return s


def fmt_line(s: dict, width: int = 26) -> str:
    desc = s["description"].replace("\n", " ")
    if len(desc) > 150:
        desc = desc[:147] + "..."
    tag = "*" if s["agent_created"] else " "
    return f"{tag} {s['dir_name']:<{width}} {desc}"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Locate an installed Skill and summarize it.")
    ap.add_argument("--name", default="", help="Skill name or keyword (fuzzy)")
    ap.add_argument("--list", action="store_true", help="List all installed skills")
    ap.add_argument("--roots", action="store_true", help="Print search roots only")
    ap.add_argument("--all", action="store_true", help="Include shadowed duplicates")
    ap.add_argument("--json", action="store_true", help="JSON output")
    args = ap.parse_args(argv)

    roots = search_roots()

    if args.roots:
        for label, path in roots:
            mark = "ok " if path.is_dir() else "-- "
            print(f"{mark}[{label}] {path}")
        return 0

    skills = dedupe(discover())

    if args.list or not args.name:
        if args.json:
            print(json.dumps(skills, ensure_ascii=False, indent=2))
            return 0
        print(f"共 {len(skills)} 个已安装 skill（* = agent_created，可被 SkillManage 修改）\n")
        by_root: dict[str, list[dict]] = {}
        for s in skills:
            by_root.setdefault(s["root"], []).append(s)
        for label, _ in roots:
            group = [s for s in by_root.get(label, []) if "shadowed_by" not in s or args.all]
            if not group:
                continue
            print(f"## {label}")
            for s in sorted(group, key=lambda x: x["dir_name"]):
                print(fmt_line(s))
            print()
        return 0

    ranked = sorted(skills, key=lambda s: (-score(s, args.name), s["dir_name"]))
    ranked = [s for s in ranked if score(s, args.name) > 0]
    if not args.all:
        ranked = [s for s in ranked if "shadowed_by" not in s]

    if args.json:
        print(json.dumps(ranked, ensure_ascii=False, indent=2))
        return 0

    if not ranked:
        print(f"未找到匹配 “{args.name}” 的本地 skill。", file=sys.stderr)
        print("建议：跑 --list 看全量；或用 marketplace 搜索（workbuddy_marketplace_skill action=search）。", file=sys.stderr)
        return 1

    for s in ranked:
        res = ", ".join(f"{k}×{v}" for k, v in s["resources"].items()) or "无附加资源"
        print(f"name: {s['name']}")
        print(f"dir : {s['dir_name']}  (root: {s['root']})")
        print(f"path: {s['path']}")
        print(f"desc: {s['description']}")
        print(f"size: {s['lines']} 行 SKILL.md；资源：{res}"
              + ("；agent_created=true" if s["agent_created"] else ""))
        if s.get("shadowed_by"):
            print(f"note: 被更高优先级同名 skill 遮蔽 → {s['shadowed_by']}")
        print()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as exc:  # pragma: no cover
        print(f"[find_skill.py] ERROR: {exc}", file=sys.stderr)
        raise
