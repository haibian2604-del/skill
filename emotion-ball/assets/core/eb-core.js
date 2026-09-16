/* ============================================================
 * eb-core.js —— Emotion Ball 单文件核心（几何 + 渲染 + 引擎）
 *
 * 零依赖、零图片、纯 SVG + 原生 JS。引入本文件即可用 window.EmotionBall。
 * 坐标系：viewBox = '-15 -15 259 259'，头部中心 HEAD_C = 114.2705
 *
 * 三层职责（可分别替换）：
 *   EB.geometry  几何层：眼环生成 + 身体轮廓 + 轮廓采样
 *   createBall   渲染层：SVG 骨架、球面投影、彩带、撒花、zzz
 *   Engine       驱动层：rAF 状态机、弹簧、动画原语、表情池、SDK
 *
 * 外部只需消费：EmotionBall.create(el, opts) 与 EmotionBall.config
 * ============================================================ */
(function (global) {
  'use strict';

  var SVGNS = 'http://www.w3.org/2000/svg';
  var TAU = Math.PI * 2;
  var HEAD_C = 114.2705;
  var VIEWBOX = '-15 -15 259 259';
  var EYE_HALF = 21;       /* 眼环基准半高（viewBox 单位） */
  var RING_PTS = 48;       /* 眼环采样点数：形变插值要求全库一致，不可变 */
  var EYE_GAP = 31;        /* 双眼中心相对头心的水平偏移 */
  var EYE_RISE = 13;       /* 双眼中心相对头心的上移量 */
  var FALLBACK_ID = '02';
  var STAR_GOLD = '#f4c34e';
  var CONFETTI_COLORS = ['#f9705c', '#5b95f0', '#3fbe86', '#f5b13f', '#9a72ee', '#35c3bd'];
  var STAR_PATH = (function () {
    var pts = [];
    for (var e = 0; e < 10; e++) {
      var a = -Math.PI / 2 + e * Math.PI / 5;
      var r = e % 2 === 0 ? 1 : 0.42;
      pts.push((Math.cos(a) * r).toFixed(3) + ' ' + (Math.sin(a) * r).toFixed(3));
    }
    return 'M' + pts.join('L') + 'Z';
  })();

  /* ---------------- 基础工具 ---------------- */
  function clamp(v, a, b) { return v < a ? a : (v > b ? b : v); }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function rand(a, b) { return a + Math.random() * (b - a); }
  function r2(v) { return Math.round(v * 100) / 100; }
  function easeInOutCubic(t) {
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  }
  function el(tag, attrs) {
    var n = document.createElementNS(SVGNS, tag);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    return n;
  }
  function shade(hex, amt) {
    var h = String(hex).replace('#', '');
    if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
    var n = parseInt(h, 16);
    var r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
    var target = amt < 0 ? 0 : 255, a = Math.abs(amt);
    r = Math.round(r + (target - r) * a);
    g = Math.round(g + (target - g) * a);
    b = Math.round(b + (target - b) * a);
    return '#' + ((1 << 24) | (r << 16) | (g << 8) | b).toString(16).slice(1);
  }
  function hexToRgb(hex) {
    var h = String(hex).replace('#', '');
    if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
    var n = parseInt(h, 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }
  function rgbToHex(r, g, b) {
    return '#' + [r, g, b].map(function (v) {
      return clamp(Math.round(v), 0, 255).toString(16).padStart(2, '0');
    }).join('');
  }
  function lerpColor(a, b, t) {
    if (!a || a === b) return b;
    var A = hexToRgb(a), B = hexToRgb(b);
    return rgbToHex(lerp(A[0], B[0], t), lerp(A[1], B[1], t), lerp(A[2], B[2], t));
  }

  /* 临界阻尼弹簧（半隐式欧拉；调用方按 1/120 子步推进保证稳定） */
  function spring(v0) { return { x: v0, v: 0, t: v0 }; }
  function springStep(s, w, z, dt) {
    s.v += (-2 * z * w * s.v - w * w * (s.x - s.t)) * dt;
    s.x += s.v * dt;
    if (!isFinite(s.x) || !isFinite(s.v)) { s.x = s.t; s.v = 0; }
  }

  /* ============================================================
   * 几何层
   * ============================================================ */

  /* 眼环形状库：单个形状 = 几个标量，采样成 48 点闭合轮廓。
   *   rx   横向半径系数（1 ≈ EYE_HALF*1.16）
   *   top  上边界高度系数（顶点）/ bot 下边界高度系数（底点）
   *   tip  左右眼角下压量（>0 时眼角低于中线 → 形成 ^ 笑眼；=0 时眼角在中线 → 椭圆）
   *   tilt 倾角（度，右眼自动镜像；越大越"眯/怒"）
   * 命名即语义：新增表达先看能否用现有形状组合出来，再考虑加形状。
   * 关键手法：笑眼 = top 高 + bot 低 + tip 正；闭眼 = top/bot 同小；怒目 = tilt 大 + rx 略窄。 */
  var EYE_SHAPES = {
    calm:   { rx: 1.02, top: 0.94, bot: 0.94 },                      /* 平静圆眼 */
    idle:   { rx: 1.00, top: 0.90, bot: 0.92 },                      /* 放松 */
    wide:   { rx: 1.08, top: 1.20, bot: 1.20 },                      /* 圆睁 */
    smile:  { rx: 1.18, top: 0.95, bot: 0.12, tip: 0.42 },           /* 笑眼 ^ */
    happy:  { rx: 1.24, top: 1.00, bot: 0.16, tip: 0.52 },           /* 大笑眼（更宽更翘） */
    doze:   { rx: 1.06, top: 0.44, bot: 0.48 },                      /* 困倦半闭 */
    closed: { rx: 1.12, top: 0.10, bot: 0.14, tip: 0.06 },           /* 闭眼细线 */
    sly:    { rx: 1.02, top: 0.88, bot: 0.88, tilt: 16 },            /* 斜眼打量 */
    glare:  { rx: 1.00, top: 0.52, bot: 1.02, tip: 0.10, tilt: 22 },  /* 怒目（上睑平直 + 强倾角） */
    scan:   { rx: 1.08, top: 0.70, bot: 0.70 },                      /* 扫读扁眼 */
    listen: { rx: 0.94, top: 1.02, bot: 1.04 },                      /* 聆听竖眼 */
    shy:    { rx: 0.92, top: 0.84, bot: 1.14, tilt: 10, dy: 2 }      /* 羞怯下垂 */
  };

  var ringCache = {};

  /** 生成单只眼的 48 点轮廓环（已含绝对位置与倾角） */
  function eyeRing(shape, side) {
    var key = (typeof shape === 'string' ? shape : JSON.stringify(shape)) + '|' + side;
    if (ringCache[key]) return ringCache[key];
    var s = typeof shape === 'string' ? (EYE_SHAPES[shape] || EYE_SHAPES.calm) : shape;
    var rx = (s.rx == null ? 1 : s.rx) * EYE_HALF * 1.16;
    var top = s.top == null ? 1 : s.top;
    var bot = s.bot == null ? 1 : s.bot;
    var tilt = (s.tilt || 0) * Math.PI / 180 * (side < 0 ? 1 : -1);
    var ca = Math.cos(tilt), sa = Math.sin(tilt);
    var cx = HEAD_C + side * EYE_GAP;
    var cy = HEAD_C - EYE_RISE + (s.dy || 0);
    var out = new Array(RING_PTS);
    for (var k = 0; k < RING_PTS; k++) {
      /* 角度从正上方起、按 SVG 正方向推进：全库相位一致才能逐点插值 */
      var th = TAU * k / RING_PTS - Math.PI / 2;
      var sn = Math.sin(th), cs = Math.cos(th);
      var r = bot + (top - bot) * (1 + sn) / 2;   /* 上下半高平滑过渡，眼角无折角 */
      var x = rx * cs;
      var y = EYE_HALF * r * sn + (s.tip || 0) * EYE_HALF * cs * cs;
      out[k] = [cx + x * ca - y * sa, cy + x * sa + y * ca];
    }
    ringCache[key] = out;
    return out;
  }

  /** 轮廓环 → 闭合折线 path（48 点密度下视觉平滑） */
  function ringPath(ring) {
    var s = 'M';
    for (var i = 0; i < ring.length; i++) {
      s += (i ? 'L' : '') + ring[i][0].toFixed(2) + ' ' + ring[i][1].toFixed(2);
    }
    return s + 'Z';
  }
  function centroid(ring) {
    var x = 0, y = 0;
    for (var i = 0; i < ring.length; i++) { x += ring[i][0]; y += ring[i][1]; }
    return [x / ring.length, y / ring.length];
  }
  /** 两组等点数环逐点插值（形变核心） */
  function lerpRing(a, b, t) {
    var out = new Array(a.length);
    for (var i = 0; i < a.length; i++) {
      out[i] = [a[i][0] + (b[i][0] - a[i][0]) * t, a[i][1] + (b[i][1] - a[i][1]) * t];
    }
    return out;
  }

  /* 身体轮廓：多边形 + Chaikin 切角，得到圆角三角 / 菱形 / 圆胖 */
  function polygonRing(n, rotDeg, radius) {
    var pts = [];
    for (var i = 0; i < n; i++) {
      var a = TAU * i / n - Math.PI / 2 + rotDeg * Math.PI / 180;
      pts.push([HEAD_C + Math.cos(a) * radius, HEAD_C + Math.sin(a) * radius]);
    }
    return pts;
  }
  function chaikin(pts, iter) {
    for (var it = 0; it < iter; it++) {
      var out = [];
      for (var i = 0; i < pts.length; i++) {
        var a = pts[i], b = pts[(i + 1) % pts.length];
        out.push([a[0] * 0.75 + b[0] * 0.25, a[1] * 0.75 + b[1] * 0.25]);
        out.push([a[0] * 0.25 + b[0] * 0.75, a[1] * 0.25 + b[1] * 0.75]);
      }
      pts = out;
    }
    return pts;
  }
  function squircleRing(pow, radius) {
    var pts = [];
    var N = 96;
    for (var i = 0; i < N; i++) {
      var phi = TAU * i / N - Math.PI / 2;
      var c = Math.abs(Math.cos(phi)), s = Math.abs(Math.sin(phi));
      var r = 1 / Math.pow(Math.pow(c, pow) + Math.pow(s, pow), 1 / pow);
      pts.push([HEAD_C + radius * r * Math.cos(phi), HEAD_C + radius * r * Math.sin(phi)]);
    }
    return pts;
  }

  var SHAPES = {
    blob:  { ring: squircleRing(2.6, 114.27), face: { x: 0, y: 0, sx: 1, sy: 1, eye: 1 } },
    wedge: { ring: chaikin(polygonRing(3, 0, 128), 3), face: { x: 0, y: 8, sx: 1, sy: 1, eye: 0.9 } },
    gem:   { ring: chaikin(polygonRing(4, 45, 118), 3), face: { x: 0, y: 2, sx: 1, sy: 1, eye: 0.94 } }
  };

  /* 轮廓采样：每 2px 一行记录 [minX, maxX]，供眼睛贴合任意身体轮廓 */
  function buildSilhouette(ring) {
    var minY = 1e9, maxY = -1e9, i;
    for (i = 0; i < ring.length; i++) {
      if (ring[i][1] < minY) minY = ring[i][1];
      if (ring[i][1] > maxY) maxY = ring[i][1];
    }
    var STEP = 2, rows = [];
    for (var y = minY; y <= maxY; y += STEP) {
      var lo = 1e9, hi = -1e9;
      for (var e = 0; e < ring.length; e++) {
        var a = ring[e], b = ring[(e + 1) % ring.length];
        var y0 = a[1], y1 = b[1];
        if ((y0 <= y && y1 >= y) || (y1 <= y && y0 >= y)) {
          var t = y1 === y0 ? 0 : (y - y0) / (y1 - y0);
          var x = a[0] + (b[0] - a[0]) * t;
          if (x < lo) lo = x;
          if (x > hi) hi = x;
        }
      }
      if (lo > hi) { lo = HEAD_C - 4; hi = HEAD_C + 4; }
      rows.push([lo, hi]);
    }
    return {
      minY: minY, maxY: maxY, step: STEP, rows: rows,
      at: function (y) {
        var r = Math.round((clamp(y, this.minY, this.maxY) - this.minY) / this.step);
        return this.rows[clamp(r, 0, this.rows.length - 1)];
      }
    };
  }

  /* ============================================================
   * 配置注册中心
   * ============================================================ */
  var GROUPS = [
    { key: 'life', name: '生命周期', en: 'Lifecycle' },
    { key: 'emotion', name: '情绪反应', en: 'Emotions' },
    { key: 'agent', name: '代理工作状态', en: 'Agent States' },
    { key: 'custom', name: '自定义', en: 'Custom' }
  ];

  var DEFAULT_BODY = {
    x: 0, y: 0, scale: 1, rotate: 0, color: '#F3F0EA', breathe: 0.01,
    ribbons: 0, confetti: 0, sketch: 0, zzz: 0, orbit: 0
  };
  var DEFAULT_EYE = {
    x: 0, y: 0, scaleX: 1, scaleY: 1, rotate: 0, open: 1,
    color: '#1A1A1A', lookX: 0, lookY: 0
  };

  var ANIM_TYPES = {
    sine: function (a, t) {
      return a.amp * Math.sin(TAU * t / (a.period || 2000) + (a.phase || 0));
    },
    pulse: function (a, t) {
      return a.amp * 0.5 * (1 - Math.cos(TAU * t / (a.period || 1000) + (a.phase || 0)));
    },
    /* 多正弦伪噪声抖动，decay 毫秒内线性衰减到 0 */
    jitter: function (a, t, eng) {
      var s = t / 1000 * (a.speed || 8);
      var v = (Math.sin(s * 3.1 + eng._seed) +
               Math.sin(s * 5.7 + eng._seed * 2.3) +
               Math.sin(s * 9.3 + eng._seed * 4.1)) / 3 * a.amp;
      if (a.decay) v *= clamp(1 - t / a.decay, 0, 1);
      return v;
    },
    /* 三角波快速扫动 */
    scan: function (a, t) {
      var per = a.period || 800;
      var p = ((t + (a.phaseMs || 0)) % per) / per;
      return a.amp * (p < 0.5 ? p * 4 - 1 : 3 - p * 4);
    },
    /* 张望：tanh 平滑方波，两端各停留片刻（左看看右看看/点头） */
    glance: function (a, t) {
      var per = a.period || 3600;
      var ph = TAU * (((t + (a.phaseMs || 0)) % per) / per) + (a.phase || 0);
      return a.amp * Math.tanh(2.8 * Math.sin(ph));
    },
    /* 周期闭合：interval 内前 dur 毫秒闭合再睁开；相位混入实例种子避免多实例同步 */
    blink: function (a, t, eng) {
      var interval = a.interval || 3800, dur = a.dur || 200;
      var p = (t + (a.phaseMs || 0) + (eng ? eng._seed * 97 : 0)) % interval;
      if (p >= dur) return 0;
      return -(a.depth == null ? 1 : a.depth) * Math.sin(Math.PI * (p / dur));
    }
  };

  function defaultPose() {
    return {
      body: Object.assign({}, DEFAULT_BODY),
      left: Object.assign({}, DEFAULT_EYE),
      right: Object.assign({}, DEFAULT_EYE)
    };
  }
  function clonePose(p) {
    return {
      body: Object.assign({}, p.body),
      left: Object.assign({}, p.left),
      right: Object.assign({}, p.right)
    };
  }
  function applySpec(pose, spec) {
    if (!spec) return pose;
    if (spec.body) Object.assign(pose.body, spec.body);
    var e = spec.eyes;
    if (e) {
      if (e.both) { Object.assign(pose.left, e.both); Object.assign(pose.right, e.both); }
      if (e.left) Object.assign(pose.left, e.left);
      if (e.right) Object.assign(pose.right, e.right);
    }
    return pose;
  }
  function lerpPose(a, b, t) {
    var out = defaultPose();
    ['body', 'left', 'right'].forEach(function (part) {
      var pa = a[part], pb = b[part], po = out[part];
      for (var k in pb) {
        var vb = pb[k];
        if (typeof vb === 'number') po[k] = lerp(pa[k] != null ? pa[k] : vb, vb, t);
        else if (k === 'color') po[k] = lerpColor(pa[k] || vb, vb, t);
        else po[k] = vb;
      }
    });
    return out;
  }

  var registry = new Map();
  var order = [];

  function knownGroup(g) { return GROUPS.some(function (x) { return x.key === g; }); }

  function validate(raw) {
    var errs = [];
    if (!raw || typeof raw !== 'object') return ['配置必须是对象'];
    if (typeof raw.id !== 'string' || !raw.id.trim()) errs.push('缺少合法的字符串 id');
    if (typeof raw.name !== 'string' || !raw.name.trim()) errs.push('缺少 name');
    if (!knownGroup(raw.group)) errs.push('group 不合法：' + raw.group);
    if (raw.anims != null) {
      if (!Array.isArray(raw.anims)) errs.push('anims 必须是数组');
      else raw.anims.forEach(function (a, i) {
        if (!a || !ANIM_TYPES[a.type]) errs.push('anims[' + i + '] 未知动画类型：' + (a && a.type));
      });
    }
    if (raw.sequence != null && !Array.isArray(raw.sequence.frames)) {
      errs.push('sequence.frames 必须是数组');
    }
    return errs;
  }

  function normalize(raw) {
    var base = applySpec(defaultPose(), raw);
    var pool = (raw.pool && raw.pool.length ? raw.pool : ['calm']).slice();
    var def = {
      id: raw.id, name: raw.name, group: raw.group,
      desc: raw.desc || '', en: raw.en || null,
      gaze: raw.gaze !== false,
      transition: raw.transition != null ? raw.transition : 500,
      pool: pool,
      poolMs: raw.poolMs || [9000, 16000],
      poolSpeed: raw.poolSpeed || 6,
      blinkMs: raw.blinkMs !== undefined ? raw.blinkMs : [6000, 14000],
      openness: raw.openness != null ? raw.openness : 1,
      antics: !!raw.antics,
      eyeScale: raw.eyeScale || 1,
      base: base,
      anims: (raw.anims || []).map(function (a) { return Object.assign({}, a); }),
      sequence: null,
      raw: raw
    };
    if (raw.sequence) {
      def.sequence = {
        settle: raw.sequence.settle || 'base',
        frames: raw.sequence.frames.map(function (f) {
          return { at: f.at || 0, pose: applySpec(clonePose(base), f) };
        }).sort(function (x, y) { return x.at - y.at; })
      };
    }
    return def;
  }

  function register(raw) {
    var errs = validate(raw);
    if (errs.length) return { ok: false, id: raw && raw.id, errors: errs };
    var def = normalize(raw);
    if (!registry.has(def.id)) order.push(def.id);
    registry.set(def.id, def);
    return { ok: true, id: def.id };
  }

  function importConfig(json) {
    var data;
    try {
      data = typeof json === 'string' ? JSON.parse(json) : json;
    } catch (e) {
      return { ok: false, added: 0, errors: ['JSON 解析失败：' + e.message] };
    }
    var arr = Array.isArray(data) ? data : [data];
    var added = 0, errors = [];
    arr.forEach(function (raw) {
      var r = register(raw);
      if (r.ok) added++;
      else errors.push('[' + ((raw && raw.id) || '?') + '] ' + r.errors.join('；'));
    });
    return { ok: errors.length === 0, added: added, errors: errors };
  }

  /* ============================================================
   * 渲染层
   * ============================================================ */
  var BOUNCE_SEGS = [{ h: 48, d: 0.5 }, { h: 28, d: 0.382 }, { h: 14, d: 0.27 }, { h: 6, d: 0.177 }];
  var BOUNCE_TOTAL = BOUNCE_SEGS.reduce(function (s, q) { return s + q.d; }, 0);

  var uid = 0;
  function createBall(container, opts) {
    opts = opts || {};
    var id = 'eb' + (uid++);
    var lite = !!opts.lite;
    var shape = SHAPES[opts.shape] || SHAPES.blob;
    var face = shape.face;
    var headRing = shape.ring;
    var headPath = ringPath(headRing);
    var sil = buildSilhouette(headRing);

    /* ---- SVG 骨架：背景层 / 身体层 / 前景层，彩带按 z 分插两侧 ---- */
    var svg = el('svg', {
      viewBox: VIEWBOX, width: '100%', height: '100%', role: 'img',
      'aria-label': opts.label || 'AI 表情小球'
    });
    svg.style.display = 'block';
    svg.style.overflow = 'visible';

    var defs = el('defs', {});
    var grad = el('radialGradient', { id: id + 'g', cx: '38%', cy: '32%', r: '75%' });
    var stopA = el('stop', { offset: '0%' });
    var stopB = el('stop', { offset: '62%' });
    var stopC = el('stop', { offset: '100%' });
    grad.appendChild(stopA); grad.appendChild(stopB); grad.appendChild(stopC);
    defs.appendChild(grad);
    svg.appendChild(defs);

    var fxBack = el('g', { 'pointer-events': 'none' });
    svg.appendChild(fxBack);
    var bodyG = el('g', {});
    var head = el('path', { d: headPath, fill: 'url(#' + id + 'g)', stroke: 'none', 'stroke-width': '2' });
    bodyG.appendChild(head);
    var eyeL = newEye(0), eyeR = newEye(1);
    bodyG.appendChild(eyeL.node);
    bodyG.appendChild(eyeR.node);
    svg.appendChild(bodyG);
    var fxFront = el('g', { 'pointer-events': 'none' });
    svg.appendChild(fxFront);
    container.appendChild(svg);

    function newEye(k) {
      var ring = eyeRing('calm', k === 0 ? -1 : 1);
      var node = el('path', { fill: '#1A1A1A', stroke: 'none', 'stroke-width': '1.6' });
      node.setAttribute('d', ringPath(ring));
      return { node: node, ring: ring, c: centroid(ring) };
    }
    var BASE_C = [centroid(eyeRing('calm', -1)), centroid(eyeRing('calm', 1))];

    /* ---- zzz 睡眠粒子 ---- */
    var zzzNodes = null;
    if (!lite) {
      zzzNodes = [];
      for (var zi = 0; zi < 3; zi++) {
        var zn = el('text', {
          x: 0, y: 0, fill: '#A8A296', opacity: '0',
          'font-family': "'Space Grotesk', 'Noto Sans SC', system-ui, sans-serif",
          'font-weight': '700', 'font-style': 'italic', 'text-anchor': 'middle'
        });
        zn.textContent = 'z';
        fxFront.appendChild(zn);
        zzzNodes.push(zn);
      }
    }

    /* ---- 彩带：3D 轨道拖尾（自旋甩带 + 常驻环带共用） ---- */
    var trails = [];
    var plane = null, planeG = 4, baseHue = 0, spawnAt = [], spawnIdx = 0;
    var wasFast = false, prevYaw = 0, prevNow = 0, orbitNextAt = 0;
    var confPieces = [];

    function newPlane() {
      var base = rand(-0.85, 0.85);
      plane = { tilt: rand(0.16, 0.5), roll: base + rand(-0.12, 0.12) };
      planeG = Math.round(rand(3, 5));
      baseHue = rand(0, 360);
      spawnIdx = 0;
    }
    /* 轨道参数 → 屏幕坐标 + z（>0 在球前，<0 绕到球后） */
    function orbitPoint(o, lam) {
      var hx = o.rad * Math.sin(lam);
      var hy = -o.rad * Math.cos(lam) * Math.sin(o.tilt);
      var ca = Math.cos(o.roll), sa = Math.sin(o.roll);
      return {
        x: HEAD_C + hx * ca - hy * sa,
        y: HEAD_C + hx * sa + hy * ca,
        z: Math.cos(lam) * Math.cos(o.tilt),
        l: lam
      };
    }
    function createTrail(cfg) {
      if (trails.length > 8) return;
      var gradEl = el('linearGradient', { id: id + 'tg' + (uid++), gradientUnits: 'userSpaceOnUse' });
      var stops = [];
      for (var s = 0; s < 5; s++) {
        var st = el('stop', { offset: (s / 4).toFixed(3) });
        gradEl.appendChild(st);
        stops.push(st);
      }
      defs.appendChild(gradEl);
      var fill = 'url(#' + gradEl.getAttribute('id') + ')';
      var back = el('path', { stroke: 'none', fill: fill, opacity: '0' });
      var front = el('path', { stroke: 'none', fill: fill, opacity: '0' });
      fxBack.appendChild(back);
      fxFront.appendChild(front);
      trails.push({
        o: cfg.o, r: cfg.r, life: 0, ret: 0, hist: [],
        orbitMode: !!cfg.orbit, hue: cfg.hue,
        hueSpan: rand(45, 95) * (Math.random() < 0.5 ? 1 : -1),
        hueVel: rand(18, 42) * (Math.random() < 0.5 ? 1 : -1),
        gradEl: gradEl, stops: stops, back: back, front: front
      });
    }
    function spawnSpinTrail(lam0, dir) {
      var tierStep = 38 / Math.max(planeG - 1, 1);
      var rw = planeG <= 3 ? rand(8, 10.5) : planeG === 4 ? rand(6.6, 8.6) : rand(5.6, 7.4);
      createTrail({
        o: {
          lam: lam0, lamVel: dir * rand(0.5, 1.1),
          tilt: plane.tilt + rand(-0.04, 0.04),
          roll: plane.roll + rand(-0.05, 0.05),
          rad: 116 + spawnIdx * tierStep + rand(-1.5, 1.5),
          radVel: rand(0, 2.5), follow: rand(0.74, 0.94), carry: 0, arc: rand(2.2, 3.4)
        },
        r: rw,
        hue: baseHue + 360 * spawnIdx / Math.max(planeG, 1) + rand(-14, 14)
      });
      spawnIdx++;
    }
    function spawnOrbit(idx) {
      createTrail({
        orbit: true,
        o: {
          lam: rand(0, TAU), lamVel: (Math.random() < 0.5 ? -1 : 1) * rand(1.7, 2.3),
          tilt: rand(0.1, 0.22), roll: rand(-0.12, 0.12),
          rad: 124 + idx * 16, radVel: 0, follow: 0.8, carry: 0, arc: rand(2.4, 3.2)
        },
        r: rand(5.5, 7), hue: rand(0, 360)
      });
    }
    /* 拖尾轮廓：头宽尾细 + 圆头封口，按 z 正负拆成前后两段 */
    function buildTrail(pts, width) {
      var n = pts.length, nx = [], ny = [], e;
      for (e = 0; e < n; e++) {
        var p0 = pts[e > 0 ? e - 1 : 0], p1 = pts[e < n - 1 ? e + 1 : n - 1];
        var dx = p1.x - p0.x, dy = p1.y - p0.y;
        var h = Math.hypot(dx, dy) || 1;
        dx /= h; dy /= h;
        var d = width * (0.5 + (e / (n - 1)) * 0.5) / 2;
        nx.push(-dy * d); ny.push(dx * d);
      }
      function cap(idx) {
        var hw = Math.max(Math.hypot(nx[idx], ny[idx]), 0.2);
        return 'A' + r2(hw) + ' ' + r2(hw) + ' 0 0 0 ';
      }
      function seg(a, b) {
        var s = '', k;
        for (k = a; k <= b; k++) s += (k === a ? 'M' : 'L') + r2(pts[k].x + nx[k]) + ' ' + r2(pts[k].y + ny[k]);
        s += b === n - 1 ? cap(b) : 'L';
        for (k = b; k >= a; k--) s += (k === b ? '' : 'L') + r2(pts[k].x - nx[k]) + ' ' + r2(pts[k].y - ny[k]);
        if (a === 0) s += cap(0) + r2(pts[0].x + nx[0]) + ' ' + r2(pts[0].y + ny[0]);
        return s + 'Z';
      }
      var front = '', back = '', d0 = 0;
      while (d0 < n) {
        var isF = pts[d0].z >= 0, i2 = d0;
        while (i2 + 1 < n && (pts[i2 + 1].z >= 0) === isF) i2++;
        var a2 = Math.max(d0 - 1, 0), b2 = Math.min(i2 + 1, n - 1);
        if (b2 > a2) {
          var str = seg(a2, b2);
          if (isF) front += str; else back += str;
        }
        d0 = i2 + 1;
      }
      return { front: front, back: back };
    }
    function removeTrail(idx) {
      var rb = trails[idx];
      rb.back.remove(); rb.front.remove(); rb.gradEl.remove();
      trails.splice(idx, 1);
    }

    /* ---- 撒花：一次性物理粒子 ---- */
    function burst(count) {
      if (lite) return;
      count = count || 20;
      for (var i = 0; i < count && confPieces.length < 60; i++) {
        var ang = (i / count) * TAU + rand(-0.35, 0.35);
        var spd = rand(170, 360);
        var star = Math.random() < 0.18;
        var round = !star && Math.random() < 0.3;
        var node;
        if (star) node = el('path', { d: STAR_PATH, fill: STAR_GOLD });
        else if (round) node = el('circle', { r: 1, fill: CONFETTI_COLORS[(Math.random() * CONFETTI_COLORS.length) | 0] });
        else node = el('rect', { x: -0.5, y: -0.5, width: 1, height: 1, rx: 0.24, fill: CONFETTI_COLORS[(Math.random() * CONFETTI_COLORS.length) | 0] });
        fxFront.appendChild(node);
        confPieces.push({
          x: HEAD_C + Math.cos(ang) * rand(96, 116),
          y: HEAD_C + Math.sin(ang) * rand(96, 116),
          vx: Math.cos(ang) * spd, vy: Math.sin(ang) * spd - rand(20, 75),
          life: 0, max: rand(0.45, 0.85),
          r: star ? rand(4, 7) : rand(3.5, 8),
          rot: rand(0, 360), vr: rand(-260, 260),
          stretch: (!star && !round) ? 1.9 : 1, el: node
        });
      }
    }

    /* ---- 身体体色（径向渐变三档 + 线稿描边） ---- */
    var curBodyColor = null, curSketch = -1;
    function setBodyColor(color) {
      if (color === curBodyColor) return;
      curBodyColor = color;
      stopA.setAttribute('stop-color', shade(color, 0.22));
      stopB.setAttribute('stop-color', color);
      stopC.setAttribute('stop-color', shade(color, -0.12));
      if (curSketch > 0.5) head.setAttribute('stroke', shade(color, -0.6));
    }

    /* ---- 眼睛：轮廓形变 + 球面投影 ---- */
    function setEye(eye, pose, k, sketch, yaw) {
      var ring = pose.ring;
      if (ring && ring !== eye.ring) {
        eye.ring = ring;
        eye.node.setAttribute('d', ringPath(ring));
        eye.c = centroid(ring);
      }
      var base = eye.c || BASE_C[k];
      var open = clamp(pose.open, 0.02, 2.4);
      var sy = clamp(pose.scaleY * open * face.eye, 0.02, 2.4);
      var sxBase = pose.scaleX * face.eye;

      /* 纵向：脸部拟合 + 轮廓钳制（眼环不会越出身体） */
      var halfH = EYE_HALF * sy + 2;
      var ey0 = HEAD_C + face.y + (base[1] - HEAD_C) * face.sy + pose.y + pose.lookY;
      ey0 = clamp(ey0, sil.minY + halfH, sil.maxY - halfH);

      var row = sil.at(ey0);
      var cx0 = (row[0] + row[1]) / 2;
      var hw = Math.max((row[1] - row[0]) / 2, 12);

      /* 横向：经度换算（把 x 偏移当成球面经度）+ 自旋偏航 + 余弦压缩 */
      var ox = face.x + (base[0] - HEAD_C) * face.sx + pose.x + pose.lookX;
      var theta = clamp(ox / hw, -1.15, 1.15) + (yaw || 0);
      var cn = Math.cos(theta);
      if (cn <= 0.02) { eye.node.style.display = 'none'; return; }
      eye.node.style.display = '';
      var ex = cx0 + hw * Math.sin(theta) * 0.985;
      var dyN = (ey0 - HEAD_C) / 130;
      var fy = Math.sqrt(1 - dyN * dyN * 0.22);   /* 越靠上下边缘纵向越扁 */

      eye.node.setAttribute('transform',
        'translate(' + r2(ex) + ' ' + r2(ey0) + ')' +
        (pose.rotate ? ' rotate(' + r2(pose.rotate) + ')' : '') +
        ' scale(' + r2(sxBase * cn) + ' ' + r2(sy * fy) + ')' +
        ' translate(' + r2(-base[0]) + ' ' + r2(-base[1]) + ')');

      var fill = sketch > 0.5 ? 'none' : pose.color;
      var stroke = sketch > 0.5 ? pose.color : 'none';
      if (fill !== eye.lastFill) { eye.node.setAttribute('fill', fill); eye.lastFill = fill; }
      if (stroke !== eye.lastStroke) { eye.node.setAttribute('stroke', stroke); eye.lastStroke = stroke; }
    }

    /* ---- 每帧 ---- */
    function applyPose(pose) {
      var b = pose.body;
      var now = performance.now();
      var sketch = b.sketch || 0;

      bodyG.setAttribute('transform',
        'translate(' + r2(HEAD_C + b.x) + ' ' + r2(HEAD_C + b.y) + ')' +
        ' rotate(' + r2(b.rotate || 0) + ')' +
        ' scale(' + r2(b.scale) + ')' +
        ' translate(' + r2(-HEAD_C) + ' ' + r2(-HEAD_C) + ')');
      setBodyColor(b.color);

      if (sketch !== curSketch) {
        curSketch = sketch;
        if (sketch > 0.5) {
          head.setAttribute('fill', 'none');
          head.setAttribute('stroke', shade(b.color, -0.6));
          head.setAttribute('stroke-opacity', '0.85');
        } else {
          head.setAttribute('fill', 'url(#' + id + 'g)');
          head.setAttribute('stroke', 'none');
        }
      }

      var yaw = b.yaw || 0;
      setEye(eyeL, pose.left, 0, sketch, yaw);
      setEye(eyeR, pose.right, 1, sketch, yaw);

      if (lite) return;
      var dt = prevNow ? clamp((now - prevNow) / 1000, 0.001, 0.05) : 1 / 60;
      prevNow = now;

      /* zzz：三枚字母错峰沿右上方向漂浮 */
      if (zzzNodes) {
        var zOn = (b.zzz || 0) > 0;
        for (var z = 0; z < zzzNodes.length; z++) {
          var znode = zzzNodes[z];
          if (!zOn) {
            if (znode.getAttribute('opacity') !== '0') znode.setAttribute('opacity', '0');
            continue;
          }
          var zp = (now * 0.00033 + z / 3) % 1;
          var zo = (zp < 0.18 ? zp / 0.18 : 1 - (zp - 0.18) / 0.82) * 0.8 * b.zzz;
          znode.setAttribute('opacity', zo.toFixed(3));
          znode.setAttribute('font-size', (12 + zp * 11).toFixed(1));
          znode.setAttribute('transform',
            'translate(' + r2(180 + zp * 34 + 4 * Math.sin(zp * 9)) + ' ' + r2(48 - zp * 42) + ')' +
            ' rotate(' + r2(-10 + zp * 14) + ')');
        }
      }

      /* 自旋角速度 → 甩带触发 */
      var dYaw = yaw - prevYaw;
      if (!isFinite(dYaw) || Math.abs(dYaw) > 1.2) dYaw = 0;
      prevYaw = yaw;
      var vel = dYaw / dt;
      var fast = Math.abs(vel) >= 0.9;
      var dir = vel >= 0 ? 1 : -1;

      if (fast && !wasFast) {
        newPlane();
        spawnAt = [];
        for (var q = 0; q < planeG; q++) spawnAt.push(now + q * rand(55, 105));
      }
      if (!fast) spawnAt.length = 0;
      wasFast = fast;
      if (Math.abs(vel) >= 5) {
        while (spawnAt.length && now >= spawnAt[0]) {
          spawnAt.shift();
          spawnSpinTrail(yaw - rand(0, 0.18) * dir, dir);
        }
      }

      /* 常驻环带补给 */
      var orbitWant = (b.orbit || 0) > 0;
      if (orbitWant && now >= orbitNextAt) {
        var orbitCount = 0;
        for (var oc = 0; oc < trails.length; oc++) if (trails[oc].orbitMode) orbitCount++;
        if (orbitCount < 2) spawnOrbit(orbitCount);
        orbitNextAt = now + 700;
      }

      /* 彩带逐帧更新 */
      for (var ti = trails.length - 1; ti >= 0; ti--) {
        var rb = trails[ti];
        rb.life += dt;
        var retract = rb.orbitMode ? !orbitWant : (!fast || rb.life > 5);
        rb.ret = clamp(rb.ret + (retract ? dt / 0.5 : -dt / 0.35), 0, 1);
        if (retract && rb.ret >= 1) { removeTrail(ti); continue; }
        var o = rb.o;
        if (rb.orbitMode) {
          o.lam += o.lamVel * dt + dYaw * o.follow;
        } else if (fast) {
          o.carry = vel * o.follow;
          o.lam += dYaw * o.follow + o.lamVel * dt;
        } else {
          o.lam += (o.carry + o.lamVel) * dt;
          o.carry *= Math.exp(-2.6 * dt);
          o.lamVel *= Math.exp(-2.6 * dt);
        }
        o.rad += o.radVel * dt;

        var hist = rb.hist;
        var lastL = hist.length ? hist[hist.length - 1].l : o.lam - 0.001 * dir;
        var dl = o.lam - lastL;
        var steps = Math.min(Math.ceil(Math.abs(dl) / 0.09), 24);
        for (var st = 1; st <= steps; st++) hist.push(orbitPoint(o, lastL + dl * st / steps));
        if (!hist.length) hist.push(orbitPoint(o, o.lam));

        /* 回缩：smoothstep 弧长收窄 + 首点插值细修 + 上限 48 点 */
        var span = o.arc * (1 - rb.ret * rb.ret * (3 - 2 * rb.ret));
        while (hist.length > 2 && Math.abs(o.lam - hist[0].l) > span) hist.shift();
        var over = Math.abs(o.lam - hist[0].l) - span;
        if (hist.length >= 2 && over > 0) {
          var tl = hist[0].l + (o.lam - hist[0].l >= 0 ? 1 : -1) * over;
          hist[0] = orbitPoint(o, tl);
        }
        if (hist.length > 48) hist.splice(0, hist.length - 48);

        var zHead = Math.cos(o.lam) * Math.cos(o.tilt);
        var pz = 0.72 + 0.28 * clamp(zHead, 0, 1);
        var grow = Math.min(rb.life / 0.34, 1);
        grow = grow * grow * (3 - 2 * grow);
        var width = rb.r * pz * 1.7 * grow * (1 - 0.72 * rb.ret * rb.ret);
        var fade = Math.min(rb.life / 0.26, 1).toFixed(3);

        if (hist.length < 2 || width < 0.5) {
          rb.back.setAttribute('opacity', '0');
          rb.front.setAttribute('opacity', '0');
          continue;
        }
        var dstr = buildTrail(hist, width);
        rb.back.setAttribute('d', dstr.back);
        rb.front.setAttribute('d', dstr.front);
        rb.back.setAttribute('opacity', fade);
        rb.front.setAttribute('opacity', fade);

        var hue = rb.hue + rb.hueVel * rb.life;
        for (var si = 0; si < rb.stops.length; si++) {
          var frac = si / (rb.stops.length - 1);
          var hv = hue + frac * rb.hueSpan;
          rb.stops[si].setAttribute('stop-color',
            'hsl(' + (((hv % 360) + 360) % 360).toFixed(0) + ' 56% ' + (56 + 11 * frac).toFixed(0) + '%)');
        }
        var tail = hist[0], headP = hist[hist.length - 1];
        rb.gradEl.setAttribute('x1', tail.x.toFixed(1));
        rb.gradEl.setAttribute('y1', tail.y.toFixed(1));
        rb.gradEl.setAttribute('x2', headP.x.toFixed(1));
        rb.gradEl.setAttribute('y2', headP.y.toFixed(1));
      }

      /* 撒花：速度衰减 + 微重力 + 缩放淡出 */
      for (var ci = confPieces.length - 1; ci >= 0; ci--) {
        var pc = confPieces[ci];
        pc.life += dt;
        if (pc.life >= pc.max) { pc.el.remove(); confPieces.splice(ci, 1); continue; }
        pc.x += pc.vx * dt; pc.y += pc.vy * dt;
        var drag = Math.pow(0.94, 60 * dt);
        pc.vx *= drag;
        pc.vy = pc.vy * drag + 40 * dt;
        pc.rot += pc.vr * dt;
        var u = pc.life / pc.max;
        var fd = u < 0.1 ? u / 0.1 : Math.pow(1 - (u - 0.1) / 0.9, 1.7);
        var sz = Math.max(pc.r * (1 - 0.4 * u), 0.5);
        pc.el.setAttribute('opacity', fd.toFixed(3));
        pc.el.setAttribute('transform',
          'translate(' + r2(pc.x) + ' ' + r2(pc.y) + ') rotate(' + r2(pc.rot) + ') scale(' + r2(sz) + ' ' + r2(sz * pc.stretch) + ')');
      }
    }

    function destroy() {
      if (svg.parentNode) svg.parentNode.removeChild(svg);
    }
    return { svg: svg, applyPose: applyPose, burst: burst, destroy: destroy };
  }

  /* ============================================================
   * 驱动层
   * ============================================================ */
  var ticker = {
    set: new Set(), raf: 0,
    add: function (e) {
      this.set.add(e);
      if (!this.raf) this.raf = requestAnimationFrame(ticker.loop);
    },
    remove: function (e) { this.set.delete(e); },
    loop: function (now) {
      ticker.raf = 0;
      ticker.set.forEach(function (e) { e._tick(now); });
      if (ticker.set.size) ticker.raf = requestAnimationFrame(ticker.loop);
    }
  };

  function Engine(target, opts) {
    opts = opts || {};
    var el0 = typeof target === 'string' ? document.querySelector(target) : target;
    if (!el0) throw new Error('EmotionBall.create：找不到容器元素');

    this.ball = createBall(el0, Object.assign({}, opts, {
      lite: opts.lite != null ? opts.lite : opts.autostart === false
    }));
    this._seed = Math.random() * 100;
    this._events = {};
    this._gaze = { x: 0, y: 0, tx: 0, ty: 0 };
    this._style = { sketch: 0 };
    this._theme = opts.color ? { body: opts.color, eyes: opts.eyeColor || '#FFFFFF' } : null;
    this._eyeScale = opts.eyeScale || 1;
    this._lastTick = 0;
    this._spin = null;

    /* 眼环形变：src → dst 逐点插值，弹簧进度驱动 */
    this._ringSrc = [eyeRing('calm', -1), eyeRing('calm', 1)];
    this._ringDst = this._ringSrc;
    this._ringCur = this._ringDst;
    this._ringSpring = spring(1);
    this._ringSpeed = 7;
    this._poolKey = null;
    this._poolPos = 0;
    this._poolNext = 0;
    /* 眨眼：开合度弹簧 ω=26 + 关键帧队列 */
    this._open = spring(1);
    this._blinkQ = [];
    this._blinkNext = Infinity;
    this._anticNext = 0;
    this._bounceAt = -1;

    this._def = null;
    this._lastPose = null;
    this._prevPose = null;
    this._transStart = 0;
    this._transDur = 0;
    this._emoStart = 0;
    this._seq = null;
    this._active = false;
    this._touring = false;
    this._tourTimer = 0;
    this._fallbackId = opts.fallbackId || FALLBACK_ID;
    this._lastActivity = performance.now();

    this._idle = opts.idle
      ? Object.assign({ standbyAfter: 60000, sleepAfter: 180000, standbyId: '02', sleepId: '00' },
        opts.idle === true ? {} : opts.idle)
      : null;

    this.setEmotion(opts.emotion || this._fallbackId, { auto: true });
    if (opts.autostart !== false) this.setActive(true);
    else this.renderStatic();
  }

  Engine.prototype = {

    on: function (evt, cb) {
      (this._events[evt] = this._events[evt] || []).push(cb);
      return this;
    },
    off: function (evt, cb) {
      var list = this._events[evt];
      if (list) {
        var i = list.indexOf(cb);
        if (i >= 0) list.splice(i, 1);
      }
      return this;
    },
    _emit: function (evt, payload) {
      (this._events[evt] || []).slice().forEach(function (cb) {
        try { cb(payload); } catch (e) { console.error(e); }
      });
    },

    get emotionId() { return this._def ? this._def.id : null; },
    get touring() { return this._touring; },

    /* ---------- 切换表情（含兜底，永不白屏） ---------- */
    setEmotion: function (id, o) {
      o = o || {};
      var def = registry.get(id);
      if (!def) {
        console.warn('[EmotionBall] 未知表情 ID "' + id + '"，回退到 (' + this._fallbackId + ')');
        this._emit('error', { message: '未知表情 ID "' + id + '"，已回退待机', id: id });
        def = registry.get(this._fallbackId);
        if (!def) return false;
      }
      var now = performance.now();
      var prevId = this._def ? this._def.id : null;
      this._prevPose = this._lastPose ? clonePose(this._lastPose) : null;
      this._def = def;
      this._emoStart = now;
      this._transStart = now;
      this._transDur = this._prevPose ? def.transition : 0;
      this._seq = def.sequence
        ? { frames: def.sequence.frames, settle: def.sequence.settle, done: false }
        : null;

      /* 切入：眼环弹向池内首个形状（兴奋类弹簧更快），并先眨一次眼 */
      this._poolPos = 0;
      this._setPool(0, def.poolSpeed >= 10 ? 10 : 8);
      this._poolNext = now + rand(def.poolMs[0], def.poolMs[1]);
      if (prevId !== null && prevId !== def.id && def.blinkMs) this._blinkNow(now);
      this._blinkNext = def.blinkMs ? now + rand(def.blinkMs[0], def.blinkMs[1]) : Infinity;
      this._anticNext = now + rand(2500, 5000);
      if (!o.auto) this._lastActivity = now;

      this._emit('change', { id: def.id, def: def, auto: !!o.auto });
      /* ribbons / confetti 是进入表情的一次性事件 */
      if (this._active) {
        var fx = def.base.body;
        if (fx.ribbons > 0) this.spin(fx.ribbons >= 1 ? 2 : 1);
        if (fx.confetti > 0) this.burst(20);
      }
      if (!this._active) this.renderStatic();
      return true;
    },

    /** AI 对接入口：接受对象或 JSON 字符串 { emotionId, tips } */
    handleAIMessage: function (msg) {
      var obj = msg;
      if (typeof msg === 'string') {
        try { obj = JSON.parse(msg); }
        catch (e) {
          this._emit('error', { message: 'AI 消息 JSON 解析失败，已回退待机', raw: msg });
          this.setEmotion(this._fallbackId);
          return false;
        }
      }
      if (!obj || typeof obj !== 'object' || typeof obj.emotionId !== 'string') {
        this._emit('error', { message: 'AI 消息缺少 emotionId 字段，已回退待机', raw: msg });
        this.setEmotion(this._fallbackId);
        return false;
      }
      var ok = this.setEmotion(obj.emotionId);
      if (obj.tips) this._emit('tips', { text: String(obj.tips) });
      return ok;
    },

    startTour: function (ids, interval) {
      this.stopTour();
      if (!ids || !ids.length) return;
      interval = interval || 2500;
      this._touring = true;
      var self = this, i = 0;
      this.setEmotion(ids[0], { auto: true });
      this._tourTimer = setInterval(function () {
        i = (i + 1) % ids.length;
        self.setEmotion(ids[i], { auto: true });
      }, interval);
    },
    stopTour: function () {
      if (this._tourTimer) { clearInterval(this._tourTimer); this._tourTimer = 0; }
      this._touring = false;
      this._lastActivity = performance.now();
    },
    resetIdle: function () { this._lastActivity = performance.now(); },

    /* 注视：横向 ±24、纵向 ±15（viewBox 单位），幅度克制 */
    setGaze: function (nx, ny) {
      this._gaze.tx = clamp(nx, -1, 1) * 24;
      this._gaze.ty = clamp(ny, -1, 1) * 15;
      return this;
    },
    clearGaze: function () { this._gaze.tx = 0; this._gaze.ty = 0; return this; },
    setStyle: function (style) {
      Object.assign(this._style, style || {});
      if (!this._active) this.renderStatic();
      return this;
    },

    /* 自旋：弹簧追整数圈，达速后渲染层甩出彩带；进行中不可打断 */
    spin: function (turns, dir) {
      if (this._spin) return this;
      var d = dir || (Math.random() < 0.5 ? -1 : 1);
      this._spin = { x: 0, v: 0, t: Math.max(1, Math.round(turns || 1)) * TAU * d };
      return this;
    },
    burst: function (count) {
      if (this.ball.burst) this.ball.burst(count);
      return this;
    },
    bounce: function () {
      if (this._bounceAt < 0) this._bounceAt = performance.now();
      return this;
    },

    /* 切换眼环：冻结当前插值结果为新起点，弹簧从 0 弹向 1 */
    _setPool: function (pos, speed) {
      var pool = this._def ? this._def.pool : ['calm'];
      var shape = pool[pos % pool.length];
      if (shape === this._poolKey && this._ringSpring.x >= 0.999) return;
      var s = clamp(this._ringSpring.x, 0, 1);
      this._ringSrc = [
        lerpRing(this._ringSrc[0], this._ringDst[0], s),
        lerpRing(this._ringSrc[1], this._ringDst[1], s)
      ];
      this._ringDst = [eyeRing(shape, -1), eyeRing(shape, 1)];
      this._ringSpring.x = 0;
      this._ringSpring.v = 0;
      this._ringSpring.t = 1;
      this._ringSpeed = speed || 7;
      this._poolKey = shape;
    },

    /* 眨眼关键帧：合上 → 停 70ms → 睁到 1.08 过冲 → 300ms 落回 1，14% 连眨 */
    _blinkNow: function (t) {
      this._blinkQ.push(
        { at: t, v: 0.05 }, { at: t + 70, v: 0.05 },
        { at: t + 150, v: 1.08 }, { at: t + 300, v: 1 }
      );
      if (Math.random() < 0.14) this._blinkQ.push({ at: t + 370, v: 0.05 }, { at: t + 480, v: 1 });
    },

    registerEmotion: function (raw) { return register(raw); },

    setActive: function (on) {
      if (on === this._active) return;
      this._active = on;
      if (on) ticker.add(this); else ticker.remove(this);
    },
    replay: function () { if (this._def) this.setEmotion(this._def.id, { auto: true }); },
    /** 静态渲染一帧：缩略图用基础姿态，弹簧直接置终值 */
    renderStatic: function () {
      this._transDur = 0;
      this._ringSpring.x = 1;
      this._ringSpring.v = 0;
      this._open.x = this._def ? this._def.openness : 1;
      this._open.v = 0;
      var seq = this._seq;
      this._seq = null;
      this._tick(performance.now());
      this._seq = seq;
    },
    getSVG: function () { return this.ball.svg; },
    destroy: function () {
      this.stopTour();
      this.setActive(false);
      this._events = {};
      this.ball.destroy();
    },

    /* ---------- 每帧 ---------- */
    _tick: function (now) {
      this._dt = this._lastTick ? clamp((now - this._lastTick) / 1000, 0.001, 0.05) : 1 / 60;
      this._lastTick = now;
      if (this._idle && !this._touring) this._checkIdle(now);
      var pose = this._compose(now, 0);
      this.ball.applyPose(pose);
      this._lastPose = pose;
    },

    _checkIdle: function (now) {
      var idle = this._idle;
      var elapsed = now - this._lastActivity;
      var cur = this.emotionId;
      if (elapsed >= idle.sleepAfter) {
        if (cur !== idle.sleepId) this.setEmotion(idle.sleepId, { auto: true });
      } else if (elapsed >= idle.standbyAfter) {
        if (cur !== idle.standbyId && cur !== idle.sleepId) this.setEmotion(idle.standbyId, { auto: true });
      }
    },

    /** 合成当前帧姿态：base → sequence → anims → 池轮换 → 眨眼 → 弹簧 → 注视 → 过渡 */
    _compose: function (now, depth) {
      var def = this._def;
      var t = now - this._emoStart;
      var pose;

      if (this._seq) {
        var res = this._seqPose(t, now);
        if (res === 'switch') {
          return depth < 4 ? this._compose(now, depth + 1) : clonePose(this._def.base);
        }
        pose = res || clonePose(def.base);
      } else {
        pose = clonePose(def.base);
      }

      /* 内置呼吸：相位用绝对时间，切换表情不跳变 */
      var br = pose.body.breathe || 0;
      if (br) {
        var ph = TAU * now / 3600;
        pose.body.scale += br * Math.sin(ph);
        pose.body.y += br * 55 * Math.sin(ph + 0.6);
      }

      for (var i = 0; i < def.anims.length; i++) applyAnim(pose, def.anims[i], t, this);
      pose.body.sketch = Math.max(pose.body.sketch || 0, this._style.sketch || 0);

      var dt = this._dt || 1 / 60;

      /* 表情池轮换：间隔到点在池内换一个眼环形状 */
      if (this._active && now >= this._poolNext) {
        if (def.pool.length > 1) {
          this._poolPos = (this._poolPos + 1 + Math.floor(rand(0, def.pool.length - 1))) % def.pool.length;
          this._setPool(this._poolPos, def.poolSpeed);
        }
        this._poolNext = now + rand(def.poolMs[0], def.poolMs[1]);
      }

      /* 眨眼调度 */
      if (this._active && def.blinkMs && now >= this._blinkNext) {
        this._blinkNow(now);
        this._blinkNext = now + rand(def.blinkMs[0], def.blinkMs[1]);
      }
      var openKey = null;
      while (this._blinkQ.length && now >= this._blinkQ[0].at) {
        openKey = this._blinkQ[0].v;
        this._blinkQ.shift();
      }
      this._open.t = openKey != null ? openKey : (this._blinkQ.length ? this._open.t : def.openness);

      /* 待机小动作：9~18s 随机自旋 / 弹跳 / 连眨 */
      if (this._active && def.antics && now >= this._anticNext) {
        if (!this._spin && this._bounceAt < 0) {
          var pick = Math.random();
          if (pick < 0.45) this.spin(1);
          else if (pick < 0.8) this.bounce();
          else this._blinkNow(now);
        }
        this._anticNext = now + rand(9000, 18000);
      }

      /* 弹簧整步：子步 1/120 保数值稳定 */
      var steps = Math.max(1, Math.ceil(dt / (1 / 120)));
      var j = dt / steps;
      for (var si = 0; si < steps; si++) {
        springStep(this._ringSpring, this._ringSpeed, 1, j);
        springStep(this._open, 26, 1, j);
        if (this._spin) {
          springStep(this._spin, 6.2, 1, j);
          if (Math.abs(this._spin.t - this._spin.x) < 0.01 && Math.abs(this._spin.v) < 0.05) this._spin = null;
        }
      }
      pose.body.yaw = this._spin ? this._spin.x : 0;

      /* 弹跳：4 段递减抛物线 */
      if (this._bounceAt >= 0) {
        var be = (now - this._bounceAt) / 1000;
        if (be >= BOUNCE_TOTAL) {
          this._bounceAt = -1;
        } else {
          var acc = 0, bi = 0;
          while (bi < BOUNCE_SEGS.length && be >= acc + BOUNCE_SEGS[bi].d) { acc += BOUNCE_SEGS[bi].d; bi++; }
          var seg = BOUNCE_SEGS[Math.min(bi, BOUNCE_SEGS.length - 1)];
          var bn = (be - acc) / seg.d;
          pose.body.y += -4 * seg.h * bn * (1 - bn);
        }
      }

      /* 当前眼环：形变中逐点插值，静止后复用目标引用（跳过 path 重建） */
      if (this._ringSpring.x < 0.999 || Math.abs(this._ringSpring.v) > 0.001) {
        var rs = clamp(this._ringSpring.x, 0, 1.35);
        this._ringCur = [
          lerpRing(this._ringSrc[0], this._ringDst[0], rs),
          lerpRing(this._ringSrc[1], this._ringDst[1], rs)
        ];
      } else if (this._ringCur !== this._ringDst) {
        this._ringCur = this._ringDst;
      }
      pose.left.ring = this._ringCur[0];
      pose.right.ring = this._ringCur[1];

      /* 鼠标注视：帧率无关指数平滑（60fps 下每帧收敛约 9%） */
      var k = 1 - Math.exp(-5.66 * dt);
      var gx = def.gaze !== false ? this._gaze.tx : 0;
      var gy = def.gaze !== false ? this._gaze.ty : 0;
      this._gaze.x += (gx - this._gaze.x) * k;
      this._gaze.y += (gy - this._gaze.y) * k;
      pose.left.lookX += this._gaze.x;
      pose.right.lookX += this._gaze.x;
      pose.left.lookY += this._gaze.y;
      pose.right.lookY += this._gaze.y;

      /* 常驻眼神微漂移：两相位错开，永不完全静止 */
      if (def.gaze !== false) {
        var w = now / 1000;
        pose.left.lookX += 1.4 * Math.sin(0.42 * w) + 0.5 * Math.sin(1.0 * w);
        pose.right.lookX += 1.4 * Math.sin(0.42 * w + 1) + 0.5 * Math.sin(1.0 * w + 2);
        pose.left.lookY += 0.9 * Math.sin(0.58 * w);
        pose.right.lookY += 0.9 * Math.sin(0.58 * w + 1);
      }

      /* 小尺寸实例放大眼睛占比（≤80px 建议 1.5~1.8） */
      var es = this._eyeScale * (def.eyeScale || 1);
      if (es !== 1) {
        pose.left.scaleX *= es; pose.left.scaleY *= es;
        pose.right.scaleX *= es; pose.right.scaleY *= es;
      }

      /* 主题色实例：体色恒为主题色，眼睛仅覆盖默认黑 */
      if (this._theme) {
        pose.body.color = this._theme.body;
        if (pose.left.color === DEFAULT_EYE.color) pose.left.color = this._theme.eyes;
        if (pose.right.color === DEFAULT_EYE.color) pose.right.color = this._theme.eyes;
      }

      /* 开合度 = 配置基础值 × 眨眼弹簧（可过冲到 1.08） */
      var openS = clamp(this._open.x, 0.02, 1.5);
      pose.left.open = clamp(pose.left.open, 0, 1.3) * openS;
      pose.right.open = clamp(pose.right.open, 0, 1.3) * openS;
      pose.left.scaleX = Math.max(pose.left.scaleX, 0.05);
      pose.left.scaleY = Math.max(pose.left.scaleY, 0.05);
      pose.right.scaleX = Math.max(pose.right.scaleX, 0.05);
      pose.right.scaleY = Math.max(pose.right.scaleY, 0.05);

      /* 表情切换过渡插值 */
      var tt = now - this._transStart;
      if (this._transDur > 0 && tt < this._transDur && this._prevPose) {
        pose = lerpPose(this._prevPose, pose, easeInOutCubic(tt / this._transDur));
      }
      return pose;
    },

    /** sequence 采样；播完按 settle 处理（hold 定格 / base 回落 / next 换表情） */
    _seqPose: function (t, now) {
      var seq = this._seq, frames = seq.frames, last = frames[frames.length - 1];
      if (t >= last.at) {
        if (!seq.done) {
          seq.done = true;
          var s = seq.settle;
          if (s === 'base') {
            this._prevPose = this._lastPose ? clonePose(this._lastPose) : clonePose(last.pose);
            this._transStart = now;
            this._transDur = this._def.transition || 500;
            this._seq = null;
            return null;
          }
          if (s && typeof s === 'object' && s.next) {
            this.setEmotion(s.next, { auto: true });
            return 'switch';
          }
        }
        return clonePose(last.pose);
      }
      if (t <= frames[0].at) return clonePose(frames[0].pose);
      for (var i = 0; i < frames.length - 1; i++) {
        var a = frames[i], b = frames[i + 1];
        if (t >= a.at && t < b.at) {
          return lerpPose(a.pose, b.pose, easeInOutCubic((t - a.at) / (b.at - a.at)));
        }
      }
      return clonePose(last.pose);
    }
  };

  function applyAnim(pose, a, t, eng) {
    var fn = ANIM_TYPES[a.type];
    if (!fn) return;
    var v = fn(a, t, eng);
    var targets =
      a.target === 'eyes' ? [pose.left, pose.right] :
      a.target === 'body' ? [pose.body] :
      a.target === 'left' ? [pose.left] :
      a.target === 'right' ? [pose.right] : [];
    for (var i = 0; i < targets.length; i++) {
      var tg = targets[i];
      if (a.prop === 'scale') {
        if (tg === pose.body) tg.scale += v;
        else { tg.scaleX += v; tg.scaleY += v; }
      } else if (a.prop in tg) {
        tg[a.prop] += v;
      }
    }
  }

  /* ============================================================
   * 对外入口
   * ============================================================ */
  var EB = global.EmotionBall = global.EmotionBall || {};
  EB.create = function (target, opts) { return new Engine(target, opts); };
  EB.version = '1.0.0';
  EB.geometry = {
    HEAD_C: HEAD_C, EYE_HALF: EYE_HALF, RING_PTS: RING_PTS,
    EYE_SHAPES: EYE_SHAPES, SHAPES: SHAPES,
    eyeRing: eyeRing, ringPath: ringPath, centroid: centroid, lerpRing: lerpRing,
    /** 注册自定义眼环形状：{ rx, top, bot, tilt, dy } */
    defineEyeShape: function (name, spec) {
      EYE_SHAPES[name] = spec;
      delete ringCache[name + '|-1'];
      delete ringCache[name + '|1'];
      return this;
    }
  };
  EB.animTypes = ANIM_TYPES;
  EB.config = {
    register: register,
    get: function (id) { return registry.get(id) || null; },
    list: function (group) {
      return order.map(function (id) { return registry.get(id); })
        .filter(function (d) { return !group || d.group === group; });
    },
    ids: function () { return order.slice(); },
    groups: function () {
      return Object.keys(GROUPS).map(function (i) {
        return { key: GROUPS[i].key, name: GROUPS[i].name, en: GROUPS[i].en };
      });
    },
    exportConfig: function () {
      return JSON.stringify(order.map(function (id) { return registry.get(id).raw; }), null, 2);
    },
    importConfig: importConfig
  };

  /* 载入种子配置（emotions 数据文件在本文件之后加载，用 seed() 补注册） */
  EB.seed = function (arr) {
    var bad = [];
    (arr || []).forEach(function (raw) {
      var r = register(raw);
      if (!r.ok) bad.push(r.id + ': ' + r.errors.join('；'));
    });
    if (bad.length) console.warn('[EmotionBall] 种子配置无效：', bad);
    return bad;
  };
  if (Array.isArray(global.EB_EMOTION_SEED)) EB.seed(global.EB_EMOTION_SEED);
})(typeof window !== 'undefined' ? window : this);
