#!/usr/bin/env python3
"""扫描项目目录，输出简历素材所需的项目事实摘要。

用法:
    python3 scan_project.py <项目路径> [--max-depth 3] [--readme-lines 40]

输出: 技术栈推断 / 目录结构 / README 摘要 / 包管理文件关键字段 / 规模线索
依赖: 仅标准库
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", "out", ".next", "target",
    "__pycache__", ".venv", "venv", "env", ".idea", ".vscode", "coverage",
    ".gradle", "vendor", "bin", "obj", "pkg", ".pytest_cache", ".mypy_cache",
}

TECH_HINTS = {
    "package.json": "Node.js / 前端项目",
    "tsconfig.json": "TypeScript",
    "next.config.js": "Next.js",
    "next.config.mjs": "Next.js",
    "vite.config.ts": "Vite",
    "vite.config.js": "Vite",
    "webpack.config.js": "Webpack",
    "requirements.txt": "Python",
    "pyproject.toml": "Python",
    "Pipfile": "Python",
    "go.mod": "Go",
    "Cargo.toml": "Rust",
    "pom.xml": "Java / Maven",
    "build.gradle": "Java / Gradle",
    "build.gradle.kts": "Kotlin / Gradle",
    "Gemfile": "Ruby",
    "composer.json": "PHP",
    "CMakeLists.txt": "C/C++",
    "Makefile": "C/C++ 或通用构建",
    "docker-compose.yml": "Docker Compose 编排",
    "docker-compose.yaml": "Docker Compose 编排",
    "Dockerfile": "容器化部署",
    "k8s": "Kubernetes",
    "Jenkinsfile": "Jenkins CI",
    ".github/workflows": "GitHub Actions CI",
    ".gitlab-ci.yml": "GitLab CI",
}

MIDDLEWARE_PATTERNS = {
    "Redis": r"\bredis\b",
    "Kafka": r"\bkafka\b",
    "RabbitMQ": r"\brabbitmq\b|\bamqp\b",
    "RocketMQ": r"\brocketmq\b",
    "MySQL": r"\bmysql\b",
    "PostgreSQL": r"\bpostgres|\bpgsql\b",
    "MongoDB": r"\bmongo",
    "Elasticsearch": r"\belasticsearch\b|\bes\b",
    "ClickHouse": r"\bclickhouse\b",
    "etcd": r"\betcd\b",
    "gRPC": r"\bgrpc\b",
    "Nacos": r"\bnacos\b",
    "ZooKeeper": r"\bzookeeper\b",
    "Nginx": r"\bnginx\b",
    "Prometheus": r"\bprometheus\b",
    "Grafana": r"\bgrafana\b",
}

SCALE_FILES = {
    "docker-compose.yml", "docker-compose.yaml", "Dockerfile",
    "kustomization.yaml", "helm", "terraform",
}


def build_tree(root: Path, max_depth: int, limit: int = 120) -> list[str]:
    lines: list[str] = []
    root_depth = len(root.parts)

    def walk(path: Path) -> None:
        if len(lines) >= limit:
            return
        try:
            entries = sorted(
                (e for e in path.iterdir() if e.name not in SKIP_DIRS),
                key=lambda e: (not e.is_dir(), e.name),
            )
        except PermissionError:
            return
        for entry in entries:
            if len(lines) >= limit:
                return
            depth = len(entry.parts) - root_depth
            if depth > max_depth:
                continue
            indent = "  " * depth
            if entry.is_dir():
                lines.append(f"{indent}{entry.name}/")
                walk(entry)
            else:
                lines.append(f"{indent}{entry.name}")

    walk(root)
    return lines


def read_readme(root: Path, max_lines: int) -> str:
    for name in ("README.md", "README.MD", "readme.md", "README.rst", "README.txt", "README"):
        p = root / name
        if p.is_file():
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return ""
            return "\n".join(text.splitlines()[:max_lines])
    return ""


def read_manifest(root: Path) -> dict[str, str]:
    """读取包管理文件的关键字段，裁剪后返回。"""
    out: dict[str, str] = {}

    def grab(rel: str, keys: list[str] | None = None) -> None:
        p = root / rel
        if not p.is_file():
            return
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        if keys:
            picked = []
            for k in keys:
                m = re.search(rf"^{re.escape(k)}\s*=\s*(.+)$", text, re.M)
                if m:
                    picked.append(f"{k} = {m.group(1).strip()}")
            if picked:
                out[rel] = "\n".join(picked)
        else:
            out[rel] = "\n".join(text.splitlines()[:60])

    grab("package.json")
    grab("go.mod")
    grab("Cargo.toml", keys=["name", "edition"])
    grab("pyproject.toml", keys=["name", "requires-python"])
    grab("requirements.txt")
    grab("pom.xml")
    grab("docker-compose.yml")
    return out


def detect_tech(root: Path) -> list[str]:
    found: list[str] = []
    for marker, label in TECH_HINTS.items():
        target = root / marker
        if marker.startswith(".") or "/" in marker:
            if target.exists():
                found.append(label)
        elif target.is_file():
            found.append(label)
    return sorted(set(found))


def detect_middleware(root: Path, max_files: int = 4000) -> list[str]:
    hits: dict[str, int] = {}
    exts = {".py", ".go", ".java", ".ts", ".js", ".tsx", ".jsx", ".yaml",
            ".yml", ".toml", ".json", ".xml", ".properties", ".conf", ".rs"}
    scanned = 0
    for path in root.rglob("*"):
        if scanned >= max_files:
            break
        if not path.is_file() or path.suffix not in exts:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            if path.stat().st_size > 512_000:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            continue
        scanned += 1
        for name, pattern in MIDDLEWARE_PATTERNS.items():
            if re.search(pattern, text):
                hits[name] = hits.get(name, 0) + 1
    return [f"{k}({v} 处引用)" for k, v in sorted(hits.items(), key=lambda x: -x[1])]


def git_stats(root: Path) -> dict[str, object]:
    """统计 git 提交数与作者分布，用于判断个人贡献线索。"""
    git_dir = root / ".git"
    if not git_dir.exists():
        return {}
    import subprocess
    try:
        total = subprocess.run(
            ["git", "-C", str(root), "rev-list", "--count", "HEAD"],
            capture_output=True, text=True, timeout=20,
        ).stdout.strip()
        authors = subprocess.run(
            ["git", "-C", str(root), "shortlog", "-sn", "--all"],
            capture_output=True, text=True, timeout=20,
        ).stdout.strip()
        first = subprocess.run(
            ["git", "-C", str(root), "log", "--reverse", "--format=%ad",
             "--date=short", "--all"],
            capture_output=True, text=True, timeout=20,
        ).stdout.strip().splitlines()
        last = subprocess.run(
            ["git", "-C", str(root), "log", "-1", "--format=%ad", "--date=short"],
            capture_output=True, text=True, timeout=20,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return {}
    return {
        "commits": total,
        "top_authors": authors.splitlines()[:10],
        "first_commit_date": first[0] if first else "",
        "last_commit_date": last,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="扫描项目目录，输出简历素材摘要")
    ap.add_argument("path", help="项目根目录")
    ap.add_argument("--max-depth", type=int, default=3, help="目录树深度，默认 3")
    ap.add_argument("--readme-lines", type=int, default=40, help="README 摘要行数，默认 40")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出")
    args = ap.parse_args()

    root = Path(args.path).expanduser().resolve()
    if not root.is_dir():
        print(f"错误: {root} 不是有效目录", file=sys.stderr)
        return 1

    data = {
        "project": root.name,
        "path": str(root),
        "tech_stack": detect_tech(root),
        "middleware": detect_middleware(root),
        "tree": build_tree(root, args.max_depth),
        "readme": read_readme(root, args.readme_lines),
        "manifest": read_manifest(root),
        "git": git_stats(root),
    }

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0

    print(f"# 项目扫描: {data['project']}")
    print(f"路径: {data['path']}\n")

    print("## 技术栈线索")
    for t in data["tech_stack"]:
        print(f"- {t}")
    if not data["tech_stack"]:
        print("- (未识别到明确标记)")

    print("\n## 中间件 / 存储线索")
    for m in data["middleware"]:
        print(f"- {m}")
    if not data["middleware"]:
        print("- (未在代码中发现明显引用)")

    g = data["git"]
    if g:
        print("\n## Git 线索")
        print(f"- 提交总数: {g['commits']}")
        print(f"- 时间范围: {g['first_commit_date']} ~ {g['last_commit_date']}")
        print("- 提交量 Top 作者:")
        for a in g["top_authors"]:
            print(f"    {a}")

    print(f"\n## 目录结构 (深度 ≤ {args.max_depth})")
    for line in data["tree"]:
        print(line)

    if data["readme"]:
        print(f"\n## README 摘要 (前 {args.readme_lines} 行)")
        print(data["readme"])

    if data["manifest"]:
        print("\n## 包管理 / 编排文件")
        for name, content in data["manifest"].items():
            print(f"\n--- {name} ---")
            print(content)

    print("\n## 下一步")
    print("1. 用上面的线索填写 12 个字段；缺的向用户追问（角色、规模、量化结果）")
    print("2. 精读核心模块源码，确认技术难点")
    print("3. 按 references/writing-guide.md 生成三段式项目经历")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
