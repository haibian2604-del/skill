#!/usr/bin/env python3
"""从 HTML 架构图页面抽取结构化信息（节点 / 连线 / 分层 / 技术词）。

支持的形态:
  1. draw.io / diagrams.net 导出的 HTML（含 mxfile / mxGraphModel，自动解压）
  2. Mermaid（<div class="mermaid"> 或 mermaid.render 字符串）
  3. ECharts / AntV G6 / X6 的 option 数据（尽力正则提取 name / nodes）
  4. 内联 SVG（提取所有 <text>、<title>、aria-label）
  5. 纯 HTML 布局图（提取可见文本，过滤 script/style）
  6. 页面只是 <img src="xxx.png"> 引用 → 输出图片路径，提示改用 Read 读图

用法:
    python3 extract_diagram.py <html 文件路径> [--json]

依赖: 仅标准库
"""
import argparse
import base64
import html as html_mod
import json
import re
import sys
import urllib.parse
import zlib
from pathlib import Path

MAX_READ = 8 * 1024 * 1024  # 只分析前 8MB，避免巨型 bundle 卡死


def read_text(path: Path) -> str:
    data = path.read_bytes()[:MAX_READ]
    for enc in ("utf-8", "gbk", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


# ---------- draw.io ----------

DRAWIO_HINT = (
    r"<mxfile|mxGraphModel|data-mxgraph|class=\"[^\"]*mxgraph|"
    r"graphXml|diagramXml|Viewer\.createViewer|diagrams\.net|mxClient"
)


def decode_drawio(raw: str) -> str:
    """解压 drawio 的 deflate+base64 图数据，返回 mxGraphModel XML。"""
    out: list[str] = []

    def push(payload: str) -> None:
        xml = _inflate(payload)
        if xml and xml not in out:
            out.append(xml)

    # 1. <diagram ...>payload</diagram>（mxfile 直嵌）
    for m in re.finditer(r"<diagram[^>]*>(.*?)</diagram>", raw, re.S | re.I):
        push(m.group(1).strip())
    # 2. data-mxgraph="{...&quot;xml&quot;:&quot;ENC&quot;...}"（官方导出 HTML）
    for m in re.finditer(r'data-mxgraph\s*=\s*"([^"]*)"', raw, re.I):
        obj = html_mod.unescape(m.group(1))
        for mm in re.finditer(r'"xml"\s*:\s*"([^"]+)"', obj):
            push(urllib.parse.unquote(mm.group(1)))
    # 3. content=ENC 形式的 URL 编码串
    for m in re.finditer(r"content%3D([^&\"'<>]+)", raw, re.I):
        push(urllib.parse.unquote(m.group(1)))
    # 4. JS 变量赋值的压缩串
    for m in re.finditer(
        r"(?:graphXml|diagramXml|xmlData|xml)\s*=\s*['\"]([A-Za-z0-9+/=%\-_]{40,})['\"]", raw
    ):
        push(urllib.parse.unquote(m.group(1)))
    return "\n".join(out)


def _inflate(payload: str) -> str:
    payload = payload.strip()
    if not payload:
        return ""
    if "%3D" in payload.lower() or "%2B" in payload.lower():
        payload = urllib.parse.unquote(payload)
    try:
        raw = base64.b64decode(payload)
    except Exception:
        return ""
    for wbits in (-15, 15, 47):
        try:
            return zlib.decompress(raw, wbits).decode("utf-8", errors="replace")
        except Exception:
            continue
    return ""


def parse_mxgraph(xml: str) -> tuple[list[str], list[tuple[str, str, str]]]:
    """从 mxGraphModel XML 提取节点文本与连线关系。"""
    nodes: dict[str, str] = {}
    for m in re.finditer(r"<mxCell\b([^>]*?)/?>", xml, re.S):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        cid = attrs.get("id", "")
        # 边（有 source/target 或显式 edge）不作为节点
        if attrs.get("source") or attrs.get("target") or attrs.get("edge") == "1":
            continue
        val = html_mod.unescape(attrs.get("value", "") or "")
        val = re.sub(r"<[^>]+>", " ", val).strip()
        if val:
            nodes[cid] = val
    edges = []
    for m in re.finditer(r"<mxCell\b([^>]*?)/?>", xml, re.S):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        src, tgt = attrs.get("source"), attrs.get("target")
        if src and tgt:
            label = html_mod.unescape(attrs.get("value", "") or "")
            label = re.sub(r"<[^>]+>", " ", label).strip()
            edges.append((nodes.get(src, src), nodes.get(tgt, tgt), label))
    return list(nodes.values()), edges


# ---------- Mermaid ----------

# Mermaid 节点：id + 可选标签（[文本] / (文本) / {文本} / [(文本)]），或纯标签
NODE = r"(?:[A-Za-z0-9_\u4e00-\u9fff\.\-]+\s*[\[\(\{][^\]\[\}\{\|]*?[\]\)\}]|[A-Za-z0-9_\u4e00-\u9fff\.\-]+|[\[\(\{][^\]\[\}\{\|]*?[\]\)\}])"
EDGE_RE = re.compile(
    rf"({NODE})\s*(?:-->|---|==>|-\.->|->|-\.-)\s*(?:\|([^|]*)\|)?\s*({NODE})"
)
NODE_DECL_RE = re.compile(rf"^({NODE})\s*$")
SKIP_RE = re.compile(r"^(subgraph|end|flowchart|graph|classDef|class|style|linkStyle|click|direction)\b")


def split_node(s: str) -> tuple[str, str]:
    """'A[订单服务]' -> ('A', '订单服务')；'[(MySQL)]' -> ('', 'MySQL')；'B' -> ('B', '')"""
    s = s.strip()
    m = re.match(r"^([A-Za-z0-9_\u4e00-\u9fff\.\-]+)?\s*[\[\(\{]([^\]\[\}\{\|]*?)[\]\)\}]$", s)
    if m:
        node_id = m.group(1) or ""
        label = m.group(2).strip().strip("()（）").strip()
        return node_id, label
    return s, ""


def parse_mermaid(raw: str) -> tuple[list[str], list[tuple[str, str, str]]]:
    blocks: list[str] = []
    for m in re.finditer(
        r'<div[^>]*class="[^"]*mermaid[^"]*"[^>]*>(.*?)</div>', raw, re.S | re.I
    ):
        blocks.append(html_mod.unescape(m.group(1)))
    # mermaid.render('id', `...`) 或模板字符串
    for m in re.finditer(r"mermaid[\s\S]{0,200}?`([^`]{10,})`", raw):
        blocks.append(m.group(1))
    if not blocks and re.search(r"^\s*(graph|flowchart)\s", raw, re.M):
        blocks.append(raw)

    alias: dict[str, str] = {}
    order: list[str] = []
    edges: list[tuple[str, str, str]] = []

    for block in blocks:
        for line in block.splitlines():
            line = line.strip().rstrip(";")
            if not line or line.startswith("%%") or SKIP_RE.match(line):
                continue
            found = EDGE_RE.search(line)
            if found:
                ids = []
                for token in (found.group(1), found.group(3)):
                    nid, label = split_node(token)
                    if nid and label:
                        alias[nid] = label
                    if nid:
                        ids.append(nid)
                        if nid not in order:
                            order.append(nid)
                    elif label:
                        ids.append(label)
                if len(ids) == 2:
                    edges.append((ids[0], ids[1], (found.group(2) or "").strip()))
                continue
            nm = NODE_DECL_RE.match(line)
            if nm:
                nid, label = split_node(nm.group(1))
                if nid:
                    if label:
                        alias[nid] = label
                    if nid not in order:
                        order.append(nid)

    def disp(x: str) -> str:
        return alias.get(x, x)

    nodes = dedupe([disp(i) for i in order])
    return nodes, [(disp(a), disp(b), lbl) for a, b, lbl in edges]


# ---------- ECharts / G6 / X6 ----------

def parse_chart_data(raw: str) -> tuple[list[str], list[tuple[str, str, str]]]:
    nodes, edges = [], []
    # { name: 'xxx' } / "name": "xxx"
    for m in re.finditer(r"""["']?name["']?\s*:\s*["']([^"'\n]{1,60})["']""", raw):
        nodes.append(m.group(1))
    # source / target 结构
    for m in re.finditer(
        r"""\{\s*["']?source["']?\s*:\s*["']([^"']{1,60})["']\s*,\s*["']?target["']?\s*:\s*["']([^"']{1,60})["']""",
        raw,
    ):
        edges.append((m.group(1), m.group(2), ""))
    # G6/X6 的 nodes 数组
    for m in re.finditer(r"nodes\s*:\s*\[([\s\S]{0,4000}?)\]", raw):
        nodes.extend(re.findall(r"""["'](?:id|label|name)["']\s*:\s*["']([^"']{1,60})["']""", m.group(1)))
    return dedupe(nodes)[:150], edges[:150]


# ---------- SVG ----------

def parse_svg(raw: str) -> tuple[list[str], list[tuple[str, str, str]]]:
    nodes: list[str] = []
    for m in re.finditer(r"<text\b[^>]*>([\s\S]*?)</text>", raw, re.I):
        inner = re.sub(r"<[^>]+>", " ", m.group(1))
        inner = html_mod.unescape(inner).strip()
        if inner:
            nodes.append(inner)
    for m in re.finditer(r"<title>([\s\S]*?)</title>", raw, re.I):
        t = html_mod.unescape(m.group(1)).strip()
        if t:
            nodes.append(t)
    for m in re.finditer(r'aria-label="([^"]{1,80})"', raw):
        nodes.append(html_mod.unescape(m.group(1)))
    return dedupe(nodes), []


# ---------- 纯 HTML ----------

def parse_plain_html(raw: str) -> list[str]:
    body = re.sub(r"<script[\s\S]*?</script>", " ", raw, flags=re.I)
    body = re.sub(r"<style[\s\S]*?</style>", " ", body, flags=re.I)
    body = re.sub(r"<!--[\s\S]*?-->", " ", body)
    texts = re.findall(r">([^<>]{1,80})<", body)
    cleaned = [html_mod.unescape(t).strip() for t in texts]
    return dedupe([t for t in cleaned if t])


def find_images(raw: str) -> list[str]:
    imgs = re.findall(r'<img[^>]+src="([^"]+)"', raw, re.I)
    imgs += re.findall(r'<image[^>]+xlink:href="([^"]+)"', raw, re.I)
    return dedupe([i for i in imgs if not i.startswith("data:")])


def dedupe(seq: list[str]) -> list[str]:
    seen, out = set(), []
    for s in seq:
        s = s.strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="从 HTML 架构图抽取节点与链路")
    ap.add_argument("path", help="HTML 文件路径")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出")
    args = ap.parse_args()

    p = Path(args.path).expanduser().resolve()
    if not p.is_file():
        print(f"错误: {p} 不是有效文件", file=sys.stderr)
        return 1

    raw = read_text(p)
    kind, nodes, edges = "未知", [], []
    imgs = find_images(raw)

    if re.search(DRAWIO_HINT, raw, re.I):
        kind = "draw.io / diagrams.net"
        xml = decode_drawio(raw)
        if xml:
            nodes, edges = parse_mxgraph(xml)
        else:
            nodes, edges = parse_mxgraph(raw)
    elif re.search(r"mermaid", raw, re.I):
        kind = "Mermaid"
        nodes, edges = parse_mermaid(raw)
    elif re.search(r"echarts|ECharts|antv|G6|X6|d3\.", raw):
        kind = "图表库渲染 (ECharts/G6/X6/D3)"
        nodes, edges = parse_chart_data(raw)
        if not nodes:
            nodes, edges = parse_svg(raw)
    elif re.search(r"<svg", raw, re.I):
        kind = "内联 SVG"
        nodes, edges = parse_svg(raw)
    else:
        kind = "纯 HTML 布局"
        nodes = parse_plain_html(raw)

    if not nodes and imgs:
        kind += "（内容在外部图片中，需读图）"

    data = {
        "file": str(p),
        "type": kind,
        "nodes": nodes[:200],
        "edges": edges[:200],
        "images": imgs[:20],
    }

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0

    print(f"# 架构图解析: {p.name}")
    print(f"识别类型: {kind}\n")

    if data["images"]:
        print("## 引用的图片")
        for i in data["images"]:
            print(f"- {i}")
        print()

    print(f"## 节点 / 文本 ({len(data['nodes'])})")
    for n in data["nodes"]:
        print(f"- {n}")
    if not data["nodes"]:
        print("- (未提取到。页面可能依赖 JS 动态渲染 → 用浏览器打开后截图识别)")

    if data["edges"]:
        print(f"\n## 链路关系 ({len(data['edges'])})")
        for a, b, label in data["edges"]:
            print(f"- {a} {label + ' ' if label else ''}→ {b}")

    print("\n## 下一步")
    print("1. 把节点归入：接入层 / 业务层 / 中间件 / 存储层 / 基础设施")
    print("2. 对用户说清：这些是图上识别到的组件，角色与量化数据仍需用户确认")
    print("3. 若页面需 JS 渲染且上面为空，用 agent-browser / playwright 打开并截图后再 Read 读图")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
