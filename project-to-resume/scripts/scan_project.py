#!/usr/bin/env python3
"""扫描全栈项目目录，输出简历素材所需的项目事实摘要。

用法:
    python3 scan_project.py <项目路径> [--max-depth 3] [--readme-lines 50] [--json]

输出: 项目地址(git remote) / 开发时间(git 首末提交) / 技术栈线索(标记文件+依赖级框架)
      / 中间件线索 / 目录结构 / README 摘要 / 包管理文件关键字段
依赖: 仅 Python 标准库 + git 命令
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", "out", ".next", "target",
    "__pycache__", ".venv", "venv", "env", ".idea", ".vscode", "coverage",
    ".gradle", "vendor", "bin", "obj", "pkg", ".pytest_cache", ".mypy_cache",
}

# 根目录标记文件 → 技术栈标签（粗粒度，先给出方向）
TECH_HINTS = {
    "package.json": "Node.js",
    "tsconfig.json": "TypeScript",
    "next.config.js": "Next.js",
    "next.config.mjs": "Next.js",
    "next.config.ts": "Next.js",
    "nuxt.config.ts": "Nuxt",
    "nuxt.config.js": "Nuxt",
    "vite.config.ts": "Vite",
    "vite.config.js": "Vite",
    "tailwind.config.js": "Tailwind CSS",
    "tailwind.config.ts": "Tailwind CSS",
    "requirements.txt": "Python",
    "pyproject.toml": "Python",
    "manage.py": "Django",
    "go.mod": "Go",
    "Cargo.toml": "Rust",
    "pom.xml": "Java / Maven",
    "build.gradle": "Java / Gradle",
    "build.gradle.kts": "Kotlin / Gradle",
    "Gemfile": "Ruby",
    "composer.json": "PHP",
    "CMakeLists.txt": "C/C++",
    "docker-compose.yml": "Docker Compose",
    "docker-compose.yaml": "Docker Compose",
    "Dockerfile": "Docker",
    "Jenkinsfile": "Jenkins CI",
    ".github/workflows": "GitHub Actions",
    ".gitlab-ci.yml": "GitLab CI",
    "nginx.conf": "Nginx",
}

# 依赖名 → 框架/库标签（细粒度，从包管理文件里逐条比对）
DEPENDENCY_LABELS = {
    # 前端框架与生态
    "react": "React", "react-dom": "React", "next": "Next.js",
    "vue": "Vue", "nuxt": "Nuxt", "svelte": "Svelte",
    "@angular/core": "Angular", "vite": "Vite", "webpack": "Webpack",
    "tailwindcss": "Tailwind CSS", "element-plus": "Element Plus",
    "antd": "Ant Design", "ant-design-vue": "Ant Design Vue",
    "echarts": "ECharts", "axios": "Axios", "pinia": "Pinia",
    "redux": "Redux", "@tanstack/react-query": "TanStack Query",
    # Node 后端
    "express": "Express", "koa": "Koa", "@nestjs/core": "NestJS",
    "fastify": "Fastify", "egg": "Egg.js", "socket.io": "Socket.IO",
    "ws": "WebSocket",
    # ORM / 数据访问
    "prisma": "Prisma", "@prisma/client": "Prisma", "typeorm": "TypeORM",
    "sequelize": "Sequelize", "mongoose": "Mongoose", "knex": "Knex",
    "mysql2": "MySQL Driver", "pg": "PostgreSQL Driver", "redis": "Redis Client",
    # 任务 / 安全 / 其他
    "jsonwebtoken": "JWT", "passport": "Passport.js", "bcrypt": "bcrypt",
    "multer": "Multer(文件上传)", "bull": "Bull 队列", "bullmq": "BullMQ 队列",
    "amqplib": "RabbitMQ Client", "kafkajs": "Kafka Client",
    # Python
    "django": "Django", "djangorestframework": "DRF", "flask": "Flask",
    "fastapi": "FastAPI", "sqlalchemy": "SQLAlchemy", "celery": "Celery",
    "uvicorn": "Uvicorn", "gunicorn": "Gunicorn", "scrapy": "Scrapy",
    # Go / Rust / Java / PHP
    "github.com/gin-gonic/gin": "Gin", "github.com/beego/beego": "Beego",
    "gorm.io/gorm": "GORM", "go.uber.org/zap": "zap",
    "actix-web": "Actix Web", "axum": "Axum", "rocket": "Rocket", "tokio": "Tokio",
    "laravel/framework": "Laravel", "symfony/framework-bundle": "Symfony",
}
JAVA_HINTS = {
    "spring-boot-starter-web": "Spring Boot",
    "spring-boot-starter-webflux": "Spring WebFlux",
    "spring-cloud": "Spring Cloud",
    "mybatis": "MyBatis", "mybatis-plus": "MyBatis-Plus",
    "spring-boot-starter-data-redis": "Spring Data Redis",
    "spring-boot-starter-security": "Spring Security",
    "spring-boot-starter-data-jpa": "Spring Data JPA",
}

MIDDLEWARE_PATTERNS = {
    "Redis": r"\bredis\b",
    "Kafka": r"\bkafka\b",
    "RabbitMQ": r"\brabbitmq\b|\bamqp\b",
    "RocketMQ": r"\brocketmq\b",
    "MySQL": r"\bmysql\b",
    "PostgreSQL": r"\bpostgres|\bpgsql\b",
    "MongoDB": r"\bmongo",
    "Elasticsearch": r"\belasticsearch\b",
    "ClickHouse": r"\bclickhouse\b",
    "MinIO": r"\bminio\b",
    "Nginx": r"\bnginx\b",
    "Prometheus": r"\bprometheus\b",
    "Docker": r"\bdocker\b",
}


def run_git(root: Path, args: list[str], timeout: int = 20) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True, text=True, timeout=timeout,
        )
        return proc.stdout.strip() if proc.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def git_info(root: Path) -> dict:
    """项目地址 + 开发时间 + 规模线索，全部来自 git。"""
    remote_raw = run_git(root, ["remote", "-v"])
    url = ""
    for line in remote_raw.splitlines():
        parts = line.split()
        if len(parts) >= 2 and "(fetch)" in line:
            url = parts[1]
            break
    if not url and remote_raw:
        url = remote_raw.splitlines()[0].split()[1] if len(remote_raw.splitlines()[0].split()) > 1 else ""

    first = run_git(root, ["log", "--reverse", "--format=%ad", "--date=short"])
    first_date = first.splitlines()[0] if first else ""
    last_date = run_git(root, ["log", "-1", "--format=%ad", "--date=short"])
    commits = run_git(root, ["rev-list", "--count", "HEAD"])
    authors = run_git(root, ["shortlog", "-sn", "HEAD"])

    info = {
        "remote_url": url,
        "first_commit": first_date,
        "last_commit": last_date,
        "commit_count": commits or "0",
        "top_authors": authors.splitlines()[:10],
    }
    if first_date and last_date:
        info["dev_period"] = f"{first_date[:7].replace('-', '.')} ~ {last_date[:7].replace('-', '.')}"
    return info


def build_tree(root: Path, max_depth: int, limit: int = 150) -> list:
    lines: list = []
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


def match_dependencies(deps: list) -> list:
    """依赖名列表 → 去重后的框架标签。"""
    labels = []
    for dep in deps:
        label = DEPENDENCY_LABELS.get(dep.lower())
        if label and label not in labels:
            labels.append(label)
    return labels


def find_manifests(root: Path, filename: str, max_depth: int = 4) -> list:
    """找出根目录及子包里的依赖清单（全栈项目常见前后端分包），跳过 node_modules 等。"""
    found = []
    for path in root.rglob(filename):
        rel = path.relative_to(root)
        if len(rel.parts) > max_depth:
            continue
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        found.append(path)
        if len(found) >= 10:
            break
    return found


def detect_tech(root: Path) -> dict:
    """返回 {粗粒度标记: [...], 依赖级框架: [...]}。"""
    markers = []
    for marker, label in TECH_HINTS.items():
        target = root / marker
        if target.exists():
            markers.append(label)

    frameworks: list = []

    for pkg in find_manifests(root, "package.json"):
        try:
            data = json.loads(pkg.read_text(encoding="utf-8", errors="replace"))
            deps = list(data.get("dependencies", {})) + list(data.get("devDependencies", {}))
            frameworks += match_dependencies(deps)
        except (OSError, json.JSONDecodeError):
            pass

    for req in find_manifests(root, "requirements.txt"):
        try:
            deps = []
            for line in req.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if line and not line.startswith(("#", "-")):
                    deps.append(re.split(r"[<>=~\[]", line)[0].strip().lower())
            frameworks += match_dependencies(deps)
        except OSError:
            pass

    for pyproject in find_manifests(root, "pyproject.toml"):
        try:
            text = pyproject.read_text(encoding="utf-8", errors="replace")
            deps = re.findall(r'"([a-zA-Z0-9_.-]+?)(?:[><=~^][^"]*)?"', text)
            frameworks += match_dependencies([d.lower() for d in deps])
        except OSError:
            pass

    gomod = root / "go.mod"
    if gomod.is_file():
        try:
            deps = re.findall(r"^\s*([\w./-]+)\s+v[\d.]+", gomod.read_text(encoding="utf-8", errors="replace"), re.M)
            frameworks += match_dependencies(deps)
        except OSError:
            pass

    cargo = root / "Cargo.toml"
    if cargo.is_file():
        try:
            text = cargo.read_text(encoding="utf-8", errors="replace")
            deps = re.findall(r"^\s*([\w-]+)\s*=", text.split("[dependencies]", 1)[-1], re.M)
            frameworks += match_dependencies(deps)
        except OSError:
            pass

    composer = root / "composer.json"
    if composer.is_file():
        try:
            data = json.loads(composer.read_text(encoding="utf-8", errors="replace"))
            frameworks += match_dependencies(list(data.get("require", {})))
        except (OSError, json.JSONDecodeError):
            pass

    pom = root / "pom.xml"
    if pom.is_file():
        try:
            text = pom.read_text(encoding="utf-8", errors="replace")
            for hint, label in JAVA_HINTS.items():
                if hint in text and label not in frameworks:
                    frameworks.append(label)
        except OSError:
            pass

    # 去掉被依赖级覆盖的粗粒度标记（如标记说 Node.js，依赖里已细到 Express）
    return {"markers": markers, "frameworks": sorted(set(frameworks))}


def detect_middleware(root: Path, max_files: int = 4000) -> list:
    hits: dict = {}
    exts = {".py", ".go", ".java", ".ts", ".js", ".tsx", ".jsx", ".yaml",
            ".yml", ".toml", ".json", ".xml", ".properties", ".conf", ".env", ".rs"}
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


def read_manifest(root: Path) -> dict:
    """读取包管理/编排文件的关键字段，裁剪后返回。"""
    out: dict = {}

    def grab(rel: str, keys: list = None) -> None:
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
            out[rel] = "\n".join(text.splitlines()[:80])

    grab("package.json", keys=['"name"', '"version"', '"description"'])
    grab("pyproject.toml", keys=["name", "description", "requires-python"])
    grab("go.mod")
    grab("pom.xml")
    grab("docker-compose.yml")
    grab("docker-compose.yaml")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="扫描全栈项目，输出简历素材摘要")
    ap.add_argument("path", help="项目根目录")
    ap.add_argument("--max-depth", type=int, default=3, help="目录树深度，默认 3")
    ap.add_argument("--readme-lines", type=int, default=50, help="README 摘要行数，默认 50")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出")
    args = ap.parse_args()

    root = Path(args.path).expanduser().resolve()
    if not root.is_dir():
        print(f"错误: {root} 不是有效目录", file=sys.stderr)
        return 1

    tech = detect_tech(root)
    data = {
        "project_name": root.name,
        "path": str(root),
        "git": git_info(root),
        "tech_markers": tech["markers"],
        "frameworks": tech["frameworks"],
        "middleware": detect_middleware(root),
        "tree": build_tree(root, args.max_depth),
        "readme": read_readme(root, args.readme_lines),
        "manifest": read_manifest(root),
    }

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0

    g = data["git"]
    print(f"# 项目扫描: {data['project_name']}")
    print(f"路径: {data['path']}\n")

    print("## 项目地址 / 开发时间")
    print(f"- git remote: {g['remote_url'] or '(无 remote，需向用户确认项目地址)'}")
    print(f"- 开发时间: {g.get('dev_period', '(无提交历史，需向用户确认)')}")
    print(f"- 提交数: {g['commit_count']}")
    if g["top_authors"]:
        print("- 提交量分布:")
        for a in g["top_authors"]:
            print(f"    {a}")

    print("\n## 技术栈（标记文件）")
    for t in data["tech_markers"]:
        print(f"- {t}")
    if not data["tech_markers"]:
        print("- (未识别到明确标记)")

    print("\n## 技术栈（依赖级框架）")
    for f in data["frameworks"]:
        print(f"- {f}")
    if not data["frameworks"]:
        print("- (未从依赖清单中识别到已知框架)")

    print("\n## 中间件 / 存储线索")
    for m in data["middleware"]:
        print(f"- {m}")
    if not data["middleware"]:
        print("- (未在代码中发现明显引用)")

    print(f"\n## 目录结构 (深度 ≤ {args.max_depth})")
    for line in data["tree"]:
        print(line)

    if data["readme"]:
        print(f"\n## README 摘要 (前 {args.readme_lines} 行)")
        print(data["readme"])

    if data["manifest"]:
        print("\n## 包管理 / 编排文件关键字段")
        for name, content in data["manifest"].items():
            print(f"\n--- {name} ---")
            print(content)

    print("\n## 下一步")
    print("1. 从目录结构挑 3-6 个核心模块，Read 路由/控制器/服务层/数据模型源码，为每个核心点配对「问题 + 方法」")
    print("2. 填六要素：项目名称 / 项目地址 / 开发时间 / 技术栈 / 核心模块 / 核心点")
    print("3. 缺失信息一次性向用户追问；量化数据无来源时用 [待补充：xxx] 占位符")
    print("4. 按 references/writing-guide.md 的规格生成简洁版 / 均衡版 / 详细版")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
