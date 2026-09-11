#!/usr/bin/env python3
"""Scaffold an LLM Wiki vault (Karpathy methodology, Obsidian) from the bundled template.

Usage:
  python scaffold_wiki.py --target /path/to/my-knowledge [--name my-knowledge]
                          [--repo git@github.com:user/repo.git] [--git] [--force]

Behavior:
  - Copies assets/vault-template/ into --target
  - Replaces placeholders: {{VAULT_NAME}}, {{REPO_URL}}, {{TODAY}}
  - Creates empty layer dirs with .gitkeep so git tracks them
  - With --git: git init -b main, optional remote, initial commit
"""
from __future__ import annotations

import argparse
import datetime as _dt
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = SKILL_DIR / "assets" / "vault-template"

TEXT_SUFFIXES = {".md", ".css", ".json", ".gitignore", ""}
PLACEHOLDERS = ("{{VAULT_NAME}}", "{{REPO_URL}}", "{{TODAY}}")


def _run(cmd: list[str], cwd: Path) -> None:
    proc = subprocess.run(
        cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stdout}")


def _substitute(target: Path, mapping: dict[str, str]) -> list[Path]:
    changed: list[Path] = []
    for path in sorted(target.rglob("*")):
        if not path.is_file():
            continue
        if path.name in (".gitkeep",):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if not any(ph in text for ph in PLACEHOLDERS):
            continue
        for key, value in mapping.items():
            text = text.replace(key, value)
        path.write_text(text, encoding="utf-8")
        changed.append(path)
    return changed


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Scaffold an LLM Wiki vault.")
    parser.add_argument("--target", required=True, help="Target vault directory (will be created)")
    parser.add_argument("--name", default="", help="Vault name (default: target dir name)")
    parser.add_argument("--repo", default="", help="Remote git URL (optional)")
    parser.add_argument("--git", action="store_true", help="git init + initial commit")
    parser.add_argument("--force", action="store_true", help="Write into a non-empty target dir")
    args = parser.parse_args(argv)

    if not TEMPLATE_DIR.is_dir():
        raise FileNotFoundError(f"Template not found: {TEMPLATE_DIR}")

    target = Path(args.target).expanduser().resolve()
    name = args.name or target.name
    repo = args.repo or "(未设置)"
    today = _dt.date.today().isoformat()

    if target.exists() and any(target.iterdir()) and not args.force:
        raise SystemExit(
            f"[scaffold_wiki] ERROR: {target} 非空。加 --force 覆盖写入，或换一个目录。"
        )
    target.mkdir(parents=True, exist_ok=True)

    shutil.copytree(TEMPLATE_DIR, target, dirs_exist_ok=True)

    for rel in ("00-Raw/inbox", "01-Wiki/summaries", "01-Wiki/entities", "01-Wiki/concepts"):
        (target / rel).mkdir(parents=True, exist_ok=True)
        (target / rel / ".gitkeep").touch(exist_ok=True)

    changed = _substitute(target, {"{{VAULT_NAME}}": name, "{{REPO_URL}}": repo, "{{TODAY}}": today})

    if args.git:
        if not (target / ".git").exists():
            _run(["git", "init", "-b", "main"], target)
        if args.repo:
            remotes = subprocess.run(
                ["git", "remote"], cwd=str(target), stdout=subprocess.PIPE, text=True,
            ).stdout.split()
            if "origin" in remotes:
                _run(["git", "remote", "set-url", "origin", args.repo], target)
            else:
                _run(["git", "remote", "add", "origin", args.repo], target)
        _run(["git", "add", "-A"], target)
        _run(["git", "commit", "-m", "chore: init LLM Wiki vault"], target)

    print(f"[scaffold_wiki] vault: {target}")
    print(f"[scaffold_wiki] name={name}  repo={repo}  date={today}")
    n_files = sum(1 for p in target.rglob("*") if p.is_file() and ".git/" not in p.as_posix())
    print(f"[scaffold_wiki] files: {n_files}  placeholders filled in {len(changed)} file(s)")
    print("[scaffold_wiki] 下一步：")
    print("  1. 用 Obsidian 打开该文件夹（Open folder as vault）")
    print("  2. 设置 → 外观 → CSS 代码片段 → 启用 wiki-colors")
    print("  3. 安装 Dataview 插件（index.md 的动态表格依赖它）")
    print("  4. 把第一批源文件放入 00-Raw/inbox/，说“处理这个”开始 ingest")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as exc:  # pragma: no cover
        print(f"[scaffold_wiki] ERROR: {exc}", file=sys.stderr)
        raise
