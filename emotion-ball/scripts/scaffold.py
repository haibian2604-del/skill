#!/usr/bin/env python3
"""把 Emotion Ball 核心脚手架到一个目标目录，并做语法 / 行为校验。

用法：
  python3 scaffold.py <目标目录> [选项]

选项：
  --title "AI 助手状态球"   页面标题
  --emotion 02             初始表情 ID
  --shape blob             身体形状：blob | wedge | gem
  --size 220               容器边长 px
  --theme "#54B9A6"        主题色（体色固定为该色，表情不再改体色）
  --dark                   宿主页面使用暗色背景
  --demo                   同时输出展馆页 demo.html（缩略图墙 + AI 面板）
  --smoke                  同时输出断言测试台 smoke.html，并尝试用 Chrome 跑一遍
  --dry-run                只打印将要做的事，不写文件

退出码：0 成功；1 参数或校验失败；2 行为断言失败
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CORE = os.path.normpath(os.path.join(HERE, '..', 'assets', 'core'))
CHROME_CANDIDATES = [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/usr/bin/google-chrome',
    '/usr/bin/chromium',
]

# smoke.html 里每条断言的期望（key -> 校验函数）
EXPECT = {
    'orbit_trail_paths': lambda v: int(v) >= 1,
    'confetti_nodes': lambda v: int(v) >= 1,
    'confetti_after_decay': lambda v: int(v) == 0,
    'spin_trail_max': lambda v: int(v) >= 1,
    'eye_hidden_on_backspin': lambda v: v == 'true',
    'wake_settle_next': lambda v: v == '02',
    'fallback_errors': lambda v: int(v) == 3,
    'fallback_emotion': lambda v: v == '02',
    'seed_count': lambda v: int(v) >= 20,
    'invalid_anim_rejected': lambda v: v == 'true',
    'import_added': lambda v: int(v) == 1,
    'renderStatic_roundtrip': lambda v: v == 'true',
}


def find_chrome():
    for p in CHROME_CANDIDATES:
        if os.path.exists(p):
            return p
    for name in ('google-chrome', 'chromium', 'chromium-browser'):
        p = shutil.which(name)
        if p:
            return p
    return None


def render_template(text, mapping):
    def sub(m):
        key = m.group(1)
        if key not in mapping:
            raise KeyError('模板占位符未提供：' + key)
        return str(mapping[key])
    return re.sub(r'\{\{(\w+)\}\}', sub, text)


def check_js(path, node):
    """用 node --check 做语法校验；没有 node 时降级跳过。"""
    if not node:
        return None
    r = subprocess.run([node, '--check', path], capture_output=True, text=True)
    return r.returncode == 0, (r.stderr or '').strip()


def run_smoke(out_dir, chrome, timeout=60):
    """headless 跑 smoke.html，抓 RESULT 行并逐条断言。"""
    url = 'file://' + os.path.join(out_dir, 'smoke.html')
    cmd = [chrome, '--headless=new', '--no-sandbox', '--disable-gpu', '--dump-dom',
           '--virtual-time-budget=3000', url]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, {'__timeout__': 'Chrome 运行 smoke 超时'}
    html = r.stdout or ''
    got = {}
    for m in re.finditer(r'RESULT ([A-Za-z_]+)=([^<\s]+)', html):
        got.setdefault(m.group(1), m.group(2))
    failed = []
    for key, fn in EXPECT.items():
        if key not in got:
            failed.append('%s: 未输出结果' % key)
            continue
        try:
            if not fn(got[key]):
                failed.append('%s: 值 %s 不符合预期' % (key, got[key]))
        except Exception as e:  # noqa: BLE001
            failed.append('%s: 断言异常 %s' % (key, e))
    return (not failed), {'results': got, 'failed': failed}


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('out_dir')
    ap.add_argument('--title', default='会表达情绪的小球')
    ap.add_argument('--emotion', default='02')
    ap.add_argument('--shape', default='blob', choices=['blob', 'wedge', 'gem'])
    ap.add_argument('--size', type=int, default=220)
    ap.add_argument('--theme', default=None)
    ap.add_argument('--dark', action='store_true')
    ap.add_argument('--label', default='AI 表情小球')
    ap.add_argument('--demo', action='store_true')
    ap.add_argument('--smoke', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    if not os.path.isdir(CORE):
        print('找不到核心目录：' + CORE, file=sys.stderr)
        return 1
    core_files = ['eb-core.js', 'eb-emotions.js']
    for f in core_files:
        if not os.path.exists(os.path.join(CORE, f)):
            print('核心文件缺失：' + f, file=sys.stderr)
            return 1

    theme_opt = ''
    if args.theme:
        if not re.fullmatch(r'#?[0-9a-fA-F]{3,6}', args.theme):
            print('主题色格式不合法：%s（示例 #54B9A6）' % args.theme, file=sys.stderr)
            return 1
        theme_opt = ",\n      color: '%s'   /* 主题色实例：体色固定为该色，表情不再改体色 */" % (
            args.theme if args.theme.startswith('#') else '#' + args.theme)

    mapping = {
        'TITLE': args.title,
        'EMOTION': args.emotion,
        'SHAPE': args.shape,
        'SIZE': args.size,
        'LABEL': args.label,
        'THEME_OPT': theme_opt,
        'BG': '#141414' if args.dark else '#F7F5F1',
        'INK': '#F2EFEA' if args.dark else '#1F1D1A',
    }

    with open(os.path.join(CORE, 'host-template.html'), encoding='utf-8') as fh:
        host_html = render_template(fh.read(), mapping)

    plan = list(core_files) + ['index.html']
    if args.demo:
        plan.append('demo.html')
    if args.smoke:
        plan.append('smoke.html')
    print('目标目录：%s' % os.path.abspath(args.out_dir))
    print('将生成：%s' % ', '.join(plan))
    if args.dry_run:
        return 0

    os.makedirs(args.out_dir, exist_ok=True)
    for f in core_files:
        shutil.copy2(os.path.join(CORE, f), os.path.join(args.out_dir, f))
    with open(os.path.join(args.out_dir, 'index.html'), 'w', encoding='utf-8') as fh:
        fh.write(host_html)
    if args.demo:
        shutil.copy2(os.path.join(CORE, 'demo.html'), os.path.join(args.out_dir, 'demo.html'))
    if args.smoke:
        shutil.copy2(os.path.join(CORE, 'smoke.html'), os.path.join(args.out_dir, 'smoke.html'))

    # ---- 校验 1：JS 语法 ----
    node = shutil.which('node')
    for f in core_files:
        res = check_js(os.path.join(args.out_dir, f), node)
        if res is None:
            print('[跳过] 未找到 node，跳过语法校验')
            break
        ok, err = res
        print('[%s] 语法校验 %s' % ('通过' if ok else '失败', f))
        if not ok:
            print(err, file=sys.stderr)
            return 1

    print('\n完成。打开方式：')
    print('  python3 -m http.server 8765   # 然后在浏览器打开 http://localhost:8765/index.html')
    print('  （也可直接双击 index.html，但建议走本地服务器以避免浏览器 file:// 限制）')

    # ---- 校验 2：行为断言（可选） ----
    if args.smoke:
        chrome = find_chrome()
        if not chrome:
            print('\n[跳过] 未找到 Chrome / Chromium，跳过行为断言。')
            return 0
        print('\n运行行为断言测试台（%s）…' % os.path.basename(chrome))
        ok, info = run_smoke(args.out_dir, chrome)
        if 'results' in info:
            for k in sorted(info['results']):
                print('  %-24s %s' % (k, info['results'][k]))
        if not ok:
            if '__timeout__' in info:
                print('[失败] ' + info['__timeout__'], file=sys.stderr)
            else:
                for f in info['failed']:
                    print('[失败] ' + f, file=sys.stderr)
            return 2
        print('[通过] 全部行为断言符合预期')
    return 0


if __name__ == '__main__':
    sys.exit(main())
