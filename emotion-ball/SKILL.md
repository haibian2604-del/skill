---
name: emotion-ball
agent_created: true
description: 制作「会表达情绪的小球」——纯 SVG + 原生 JS 的零依赖表情引擎（32 种状态表情、一个 emotionId 对接 AI、鼠标注视、自旋彩带、撒花庆祝）。技能内含可运行核心（引擎 + 渲染 + 几何 + 表情配置）、脚手架脚本与行为断言测试台。当用户想 (1) 做一颗会表达情绪的小球 / AI 表情球 / 桌面宠物 / 悬浮助手头像；(2) 给 LLM / Agent 加状态可视化（思考中、检索中、出错、任务完成）；(3) 用 emotionId 协议把 AI 输出接到表情上；(4) 新增 / 调校表情、眼环形状、身体形状、动画原语时使用。触发词：情绪小球、表情球、emotion ball、会表达情绪的小球、AI 表情、桌面宠物、悬浮助手、Agent 状态指示、emotionId。
---

# 会表达情绪的小球

造一颗用 SVG 实时驱动的表情小球：它安静时会呼吸眨眼、左看右看，被注视时会回看你，
思考时头顶拖着一条彩色环带，任务完成会自旋甩彩带并撒花，出错会涨红闪灯。

**一条底层原理**（整技能的地基）：
表情的差异只由**四个自由度**表达 —— 眼环形状、目光方向、身体姿态、体色，
**永不新增图形元素**（没有嘴、眉毛、手）。所以所有表情天然同源、切换永远丝滑。

## 何时用

| 用户意图 | 做法 |
|---|---|
| "做一颗会表达情绪的小球 / AI 表情球" | 走 §1 脚手架，交付可直接打开的页面 |
| "给 Agent 加状态指示 / 表情" | 走 §1 + §3 的 AI 协议接线 |
| "做个桌面宠物 / 悬浮助手" | 走 §1 + `references/recipes.md §4` |
| "加一个 XX 表情 / 表情不对" | 走 §4，只改数据层（`eb-emotions.js`） |
| "小球怎么做出来的 / 讲讲原理" | 讲 `references/method.md`，别改代码 |

## 文件地图

```
emotion-ball/
├── SKILL.md                      本文件：流程与决策
├── scripts/scaffold.py           脚手架：生成可运行页面 + 语法校验 + 行为断言
├── references/
│   ├── method.md                 制作方法总纲（原理、公式、参数调校、三层边界）★核心
│   ├── emotion-catalog.md        32 表情 + 12 眼环形状参数表 + 新增表情工作流 + 常见坑
│   └── recipes.md                场景配方：指示器 / 缩略图墙 / 注视 / 桌面宠物 / 主题色 / 多实例
└── assets/core/                  ★可直接运行的核心（零依赖，两个文件搞定）
    ├── eb-core.js                几何 + 渲染 + 引擎（1390 行，单文件）
    ├── eb-emotions.js            32 个表情配置（纯数据）
    ├── demo.html                 展馆页：缩略图墙 + AI 下发面板 + 巡演
    ├── host-template.html        宿主集成最小页模板（脚手架用，含 {{占位符}}）
    └── smoke.html                行为断言测试台（时间旅行时钟驱动 rAF）
```

## §1 标准流程：从零交付一颗小球

```bash
# 1) 脚手架（会自动做 JS 语法校验；--smoke 再跑一遍行为断言）
python3 <skill>/scripts/scaffold.py <目标目录> --demo --smoke \
        --title "AI 助手状态球" --size 220 --theme "#54B9A6"

# 2) 本地起服务后打开
cd <目标目录> && python3 -m http.server 8765     # → http://localhost:8765/index.html

# 3) 交给用户看效果（截图或预览 index.html / demo.html）
```

产物：`eb-core.js`、`eb-emotions.js`、`index.html`（宿主集成页）、可选 `demo.html` / `smoke.html`。

`scaffold.py` 参数：`--title --emotion --shape{blob|wedge|gem} --size --theme --dark --demo --smoke --dry-run`。
退出码：`0` 成功 / `1` 参数或语法错误 / `2` 行为断言失败。

不跑脚手架、纯手写也完全可以 —— 只需按顺序引入两个文件：

```html
<div id="bot" style="width:220px;height:220px"></div>
<script src="eb-core.js"></script>
<script src="eb-emotions.js"></script>   <!-- 顺序不能反：core 先定义注册中心 -->
<script>
  var ball = EmotionBall.create('#bot', { emotion: '02', shape: 'blob', idle: true });
</script>
```

## §2 必做的验收（不能跳过）

**跑断言，别只看截图。** 无头浏览器在长虚拟时钟下会丢失动画中的 SVG 图层
（`--virtual-time-budget` > 3s 时截图可能整个球都不见了，但 DOM 状态其实是对的），
所以验证以 `--dump-dom` 抓 `RESULT` 行为准：

```bash
python3 <skill>/scripts/scaffold.py /tmp/eb-check --smoke     # 自动跑，全绿才算通过
```

覆盖的断言（13 条）：常驻环带生成、撒花出现与耗尽、自旋甩带、绕背面眼睛隐藏、
`sequence.settle:{next}` 自动换表情、三条失败路径兜底、眨眼开合区间、静态渲染可用、
种子数量、配置校验拒绝非法动画、JSON 导入。
另外必须人工确认三条：**静态缩略图可辨识** / **悬停动画正确** / **切入过渡自然**。

## §3 AI 对接协议（宿主侧只有这一行）

```js
ball.handleAIMessage('{"emotionId":"30","tips":"正在思考用户问题"}');   // 对象或 JSON 字符串均可
```

- 未知 `emotionId`、JSON 解析失败、缺字段 → 发 `error` 事件 + 回退待机（`fallbackId`，默认 `'02'`），**永不白屏**。
- 事件：`change`（`{id, def, auto}`）/ `tips`（`{text}`）/ `error`（`{message}`）。
- 建议的消息→表情映射：请求中 `30`、检索 `40`、生成中 `39`、完成 `33`、失败 `34`、待输入 `35`、拒绝 `38`、停止 `41`。
- 可见性：`setActive(false)` 停帧省电、`renderStatic()` 出静态帧、
  小尺寸加 `{ eyeScale: 1.5, lite: true }`、缩略图墙用 `{ autostart: false }` + 悬停 `setActive(true)`。
- ID 分段是**对外契约**：`00-09` 生命周期 / `10-29` 情绪 / `30-49` 代理状态 / `50+` 自定义，
  已有编号永不重排，新增只占空号 —— 对接方可以安全硬编码。

## §4 改造与扩展（改对层，别乱动基座）

| 想做什么 | 只改这里 |
|---|---|
| 加 / 调表情 | `eb-emotions.js` 加一条配置（零代码），或运行时 `ball.registerEmotion({...})` |
| 加眼环形状 | `EmotionBall.geometry.defineEyeShape('名', {rx, top, bot, tip, tilt, dy})` |
| 加动画原语 | `EmotionBall.animTypes` 加纯函数 `(a, t, eng) => 值` |
| 加身体形状 | `EmotionBall.geometry.SHAPES` 加轮廓环 + face 参数 |
| 换身体 / 主题色 | 创建选项 `shape` / `color` / `eyeColor` |

**驱动层与渲染层是稳定基座，不要为了一个表情去改它们。**
参数语义、调校区间、`sequence.settle` 三态语义、缩略图一致性规则见
`references/method.md` 与 `references/emotion-catalog.md`；
踩坑对照表（眼睛飞出身体 / 缩略图不一致 / 碎带残留 / 弹簧爆掉）在同文件的「常见坑」一节。

## §5 合规与出处

- 本技能核心为**独立重实现**（参数化眼环生成，替代原项目 25 组手绘环数据），
  方法论与视觉语言参考开源项目 **emotion-ball**（`README.md` 中的 Emotion Ball / 表情馆，
  在线预览 `emotion-balls.vercel.app`）。原项目 **仅供学习与技术交流，禁止商业用途**，
  商用请自行联系原作者授权；本技能沿用同一约束。
- 若用户本地有原项目（如 `~/code/other/emotion-ball-main`），可用它做**高保真对照**：
  原项目是 25 组手绘 48 点眼环 + `js/ball.js` / `js/engine.js` 分离的三文件结构，
  其 `.cursor/skills/` 下另有「表情设计」「集成实践」两份规范，可交叉参考。
- 字体：核心不依赖任何字体（zzz 用 `font-family` 兜底 system-ui）；
  展馆页若要 Space Grotesk 自行引入，**不要**让核心依赖外部字体。
