#!/usr/bin/env python3
"""Render an SVG to multiple-size PNGs for logo acceptance checks.

Tries renderers in order: rsvg-convert -> inkscape -> qlmanage (macOS)
-> headless Chrome. Prints the PNG paths written, exits non-zero if
nothing could be rendered.

Usage: render_check.py <logo.svg> [--outdir DIR] [--sizes 512,64,32,16]
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RENDERERS = ["rsvg-convert", "inkscape", "qlmanage"]


def find_chrome():
    for name in ("chromium", "chrome", "google-chrome",
                 "Google Chrome", "Chromium"):
        path = shutil.which(name)
        if path:
            return path
    # macOS app bundles
    for app in ("Google Chrome", "Chromium", "Microsoft Edge"):
        cand = Path(f"/Applications/{app}.app/Contents/MacOS/{app}")
        if cand.exists():
            return str(cand)
    return None


def render(svg: Path, outdir: Path, sizes):
    results = []
    for size in sizes:
        out = outdir / f"{svg.stem}-{size}.png"
        if render_one(svg, size, out):
            results.append(out)
    return results


def render_one(svg: Path, size: int, out: Path) -> bool:
    for tool in RENDERERS:
        if not shutil.which(tool):
            continue
        if tool == "rsvg-convert":
            cmd = ["rsvg-convert", "-w", str(size), "-h", str(size),
                   "-o", str(out), str(svg)]
        elif tool == "inkscape":
            cmd = ["inkscape", str(svg), "--export-type=png",
                   f"--export-filename={out}",
                   f"--export-width={size}", f"--export-height={size}"]
        else:  # qlmanage only does thumbnails at one size per call
            cmd = ["qlmanage", "-t", "-s", str(size),
                   "-o", str(out.parent), str(svg)]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=60)
        except (subprocess.SubprocessError, OSError):
            continue
        if tool == "qlmanage":  # emits <full-filename>.png, rename
            produced = out.parent / f"{svg.name}.png"
            if not produced.exists():
                continue
            produced.replace(out)
        if out.exists() and out.stat().st_size > 0:
            return True
    chrome = find_chrome()
    if chrome:
        html = (out.parent / f"_{svg.stem}-{size}.html")
        html.write_text(
            f'<body style="margin:0"><img src="file://{svg.resolve()}" '
            f'width="{size}" height="{size}"></body>')
        try:
            subprocess.run(
                [chrome, "--headless", "--disable-gpu",
                 "--screenshot", str(out),
                 f"--window-size={size},{size}", str(html)],
                check=True, capture_output=True, timeout=60)
        except (subprocess.SubprocessError, OSError):
            pass
        finally:
            html.unlink(missing_ok=True)
        if out.exists() and out.stat().st_size > 0:
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("svg", type=Path)
    ap.add_argument("--outdir", type=Path, default=None)
    ap.add_argument("--sizes", default="512,64,32,16")
    args = ap.parse_args()

    if not args.svg.exists():
        sys.exit(f"not found: {args.svg}")
    outdir = args.outdir or (args.svg.parent / "logo-preview")
    outdir.mkdir(parents=True, exist_ok=True)
    sizes = [int(s) for s in args.sizes.split(",") if s.strip()]

    results = render(args.svg.resolve(), outdir.resolve(), sizes)
    if not results:
        sys.exit("no renderer available (tried: "
                 + ", ".join(RENDERERS) + ", headless chrome)")
    for p in results:
        print(p)


if __name__ == "__main__":
    main()
