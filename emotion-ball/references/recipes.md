# 场景配方

每种场景只列"必须做的事 + 必须避开的坑"。统一前置：`eb-core.js` → `eb-emotions.js`（顺序不能反）。

---

## 1. 网页里的 AI 状态指示器（最常见）

```html
<div id="bot" style="width:160px;height:160px"></div>
<script src="eb-core.js"></script>
<script src="eb-emotions.js"></script>
<script>
  var ball = EmotionBall.create('#bot', { emotion: '02', idle: true });

  ball.on('change', function (e) { console.log(e.id, e.def.name); });
  ball.on('tips',   function (e) { showText(e.text); });
  ball.on('error',  function (e) { console.warn(e.message); });

  /* 后端 / LLM 只要吐一个 emotionId */
  ws.onmessage = function (ev) { ball.handleAIMessage(ev.data); };
</script>
```

要点：
- AI 侧协议固定为 `{"emotionId":"30","tips":"正在思考"}`，一行接入。
- `error` 事件一定要接：未知 ID / 坏 JSON 会自动回退待机，把提示透出去即可。
- 消息与表情的映射建议固定成表：请求中 `30` 或 `40`、生成中 `39`、完成 `33`、失败 `34`、
  待输入 `35`、拒绝 `38`、停止 `41`。

## 2. 多实例缩略图墙 / 表情选择器

```js
var b = EmotionBall.create(el, { emotion: id, autostart: false });   // 只渲染静态帧
card.onmouseenter = function () { b.setActive(true); };              // 悬停才进循环
card.onmouseleave = function () { b.setActive(false); };
```

- **必须**：视口外的实例用 `IntersectionObserver` 调 `setActive(false)`。
- 所有实例共享同一个 rAF 心跳，数量多了也不会卡（实测 30+ 实例正常）。
- 静态帧不播 `sequence` 第 0 帧，所以缩略图与主舞台观感要按 `hold` 体色规则保持一致性。

## 3. 鼠标注视（全页面跟随）

```js
addEventListener('pointermove', function (e) {
  var r = el.getBoundingClientRect();
  var cx = r.left + r.width / 2, cy = r.top + r.height / 2;
  ball.setGaze(
    Math.max(-1, Math.min(1, (e.clientX - cx) / 300)),
    Math.max(-1, Math.min(1, (e.clientY - cy) / 300))
  );
});
```

- 引擎不监听 DOM，由宿主换算坐标（内部已做球面投影 + 平滑）。
- 滚动 / 布局变化后 `rect` 会变，需要重新取；多实例共用一次 pointermove 分发。
- 点一下自旋是廉价的高回报交互：`el.onclick = function () { ball.spin(2); };`

## 4. 桌面宠物 / Electron 悬浮窗

| 项 | 值 |
|---|---|
| BrowserWindow | `transparent:true, frame:false, alwaysOnTop:true, skipTaskbar:true, resizable:false` |
| 页面 | 背景透明，只留小球容器；`html,body{background:transparent}` |
| 鼠标穿透 | `win.setIgnoreMouseEvents(true, { forwardMouseMove:true })`，仍可驱动 `setGaze` |
| AI 消息 | 主进程 IPC：`ipcRenderer.on('emotion', function (_, msg) { ball.handleAIMessage(msg); })` |
| 小窗尺寸 | ≤120px 用 `{ eyeScale: 1.5, lite: true }` |
| 托盘 | 待机 / 睡眠 / 停止 三个常用状态做菜单项 |
| 退出 | 先 `ball.destroy()` 再关窗（解绑 ticker、清 DOM） |

## 5. 主题色实例（团队小球 / 品牌色）

```js
EmotionBall.create(el, { emotion: '02', color: '#54B9A6', eyeColor: '#FFFFFF' });
```

- 主题色**优先于**表情体色：生气不会变红，而是保持品牌色。
- 眼睛只在"默认黑"时才被主题色覆盖，表情自己指定的眼色（如出错）仍然生效。
- 一页多实例混用不同主题色是安全的（渐变 id 按实例生成）。

## 6. 新增业务专属表情（宿主扩展，不改库）

```js
ball.registerEmotion({
  id: '50', name: '上传中', group: 'custom',
  desc: '扫读眼环 + 底部缓慢起伏',
  pool: ['scan'], poolMs: [2000, 3000], blinkMs: [4000, 7000],
  body: { breathe: 0.01 },
  anims: [{ target: 'body', prop: 'y', type: 'sine', amp: 3, period: 1800 }]
});
```

- `id` 用 `50+` 段，`group: 'custom'`。
- 也可以用 `EmotionBall.config.exportConfig()` 导出全部表情 JSON 存档 / 交付，
  `importConfig(json)` 批量导入（返回 `{ok, added, errors}`，逐条报告失败原因）。
- 校验是硬的：未知动画类型、缺 id/name、非法 group 一律拒绝注册并给出原因。

## 7. 自动巡演（演示 / 开屏）

```js
ball.startTour(['00','10','13','21','30','33','34','40'], 2200);
ball.stopTour();   // 用户交互时停掉，并 resetIdle()
```

## 8. 待机策略（长时间无人操作）

```js
EmotionBall.create(el, {
  emotion: '02',
  idle: { standbyAfter: 60000, sleepAfter: 180000, standbyId: '02', sleepId: '00' }
});
```

任何 `setEmotion(id)`（非 auto）都会重置计时；巡演期间不触发待机。

## 9. 线稿 / 单色风格

```js
ball.setStyle({ sketch: 1 });   // 轮廓描边 + 空心眼睛，浅色页面上也清晰
```

描边颜色由体色自动加深 60% 得到，不需要额外配色。

---

## 尺寸与性能对照

| 容器尺寸 | 建议 |
|---|---|
| ≥ 200px | 默认；可全特效 |
| 120~200px | 默认 |
| 80~120px | `eyeScale: 1.5` |
| ≤ 80px | `eyeScale: 1.5~1.8` + `lite: true`（关彩带/撒花/zzz） |
| 列表 / 墙（>20 个） | `autostart: false` + 悬停 `setActive(true)` |

## 验收清单（交付前逐条跑）

```
- [ ] 未知 emotionId / 坏 JSON / 缺字段 → 不白屏，回退待机且触发 error
- [ ] 连续快速切换 10 次：无报错、无残留彩带、眼睛不飞出身体
- [ ] 自旋一圈：眼睛绕到背面会消失；收尾彩带干净回收
- [ ] 缩略图静态帧与主舞台观感一致（hold 体色规则）
- [ ] 缩略图墙悬停才动，移出停帧（DevTools Performance 里确认无空转 rAF）
- [ ] 小尺寸实例（≤80px）眼睛可读
- [ ] destroy() 后 DOM 清空、无继续运行的 rAF
```
