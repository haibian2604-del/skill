# 表情目录与参数速查

## 1. ID 分段（对外契约，永不重排）

| 段位 | 分组 | 用途 | 已占用 |
|---|---|---|---|
| `00-09` | `life` 生命周期 | 睡眠 / 唤醒 / 待机 / 休眠 / 停止 | 00-07 |
| `10-29` | `emotion` 情绪反应 | 开心 / 生气 / 害羞 / 惊讶 … | 10-21 |
| `30-49` | `agent` 代理工作状态 | 思考 / 检索 / 出错 / 完成 … | 30-41 |
| `50+` | `custom` 自定义 | 宿主业务专属表情 | 空 |

**组间的空号是扩展预留位**：新增表情占用空号，已有编号的语义永不改变 ——
对接方可以放心硬编码 `'30'`。这是整套协议最重要的工程约定。

## 2. 眼环形状表（`EB.geometry.EYE_SHAPES`）

| 形状 | rx | top | bot | tip | tilt | 语义 | 用于 |
|---|---|---|---|---|---|---|---|
| `calm` | 1.02 | 0.94 | 0.94 | — | — | 平静圆眼 | 待机、好奇、疑惑 |
| `idle` | 1.00 | 0.90 | 0.92 | — | — | 放松 | 待机、思考 |
| `wide` | 1.08 | 1.20 | 1.20 | — | — | 圆睁 | 惊讶、慌张、出错 |
| `smile` | 1.18 | 0.95 | 0.12 | 0.42 | — | 笑眼 ^ | 开心、满意 |
| `happy` | 1.24 | 1.00 | 0.16 | 0.52 | — | 大笑眼（更宽更翘） | 开心、任务完成 |
| `doze` | 1.06 | 0.44 | 0.48 | — | — | 困倦半闭 | 疲惫、失落、发呆 |
| `closed` | 1.12 | 0.10 | 0.14 | 0.06 | — | 闭眼细线 | 睡眠、唤醒、停止 |
| `sly` | 1.02 | 0.88 | 0.88 | — | 16 | 斜眼打量 | 无奈、困惑、拒绝 |
| `glare` | 1.00 | 0.52 | 1.02 | 0.10 | 22 | 怒目（上睑平直） | 生气、专注 |
| `scan` | 1.08 | 0.70 | 0.70 | — | — | 扫读扁眼 | 检索、输出、满意 |
| `listen` | 0.94 | 1.02 | 1.04 | — | — | 聆听竖眼 | 等待输入、复述回忆 |
| `shy` | 0.92 | 0.84 | 1.14 | — | 10 | 羞怯下垂 | 害羞 |

Tilt 右眼自动镜像，无需为左右眼分别配参。加新形状见 `method.md §2.1`：
只需给 `EB.geometry.defineEyeShape('名', {rx, top, bot, tip, tilt, dy})`。

## 3. 32 个内置表情

### 生命周期 `life`

| ID | 名称 | pool | 关键参数 | 记忆点 |
|---|---|---|---|---|
| 00 | 睡眠 | closed, doze | `blinkMs:null` `openness:0.08` `gaze:false` `body.zzz:1` | zzz 字母 + 头微垂 |
| 01 | 唤醒 | closed | `sequence.settle:{next:'02'}` | 睁眼 → 自动进待机 |
| 02 | 待机放空 | calm, idle | `antics:true` `poolMs:[9000,16000]` | 左看看右看看 + 偶发自旋 |
| 03 | 好奇 | wide, calm, scan | `poolMs:[1800,3200]` `rotate:4` | 快轮换 + 歪头 |
| 04 | 发呆 | doze, calm | 两眼 `lookX` 相反 | 双眼各望各的 |
| 05 | 加载苏醒 | calm, idle | 左右眼 `blink` 相位错开 800ms | 交替亮起 |
| 06 | 休眠 | doze, closed | `transition:1200` `openness:0.4` | 近乎静止 |
| 07 | 抖动唤醒 | closed | `jitter` 带 `decay:1600` | 整球轻颤后进待机 |

### 情绪反应 `emotion`

| ID | 名称 | pool | 关键参数 | 记忆点 |
|---|---|---|---|---|
| 10 | 开心 | smile, happy | `antics:true` `glance` lookY ±6 | 笑眼 + 上下点头 |
| 11 | 疑惑 | sly, calm | 左眼 1.1 / 右眼 0.9 倍 + `rotate:-8` | 一眼大一眼小 |
| 12 | 失落 | doze, closed | `y:8` `color:#EDEAE3` | 眼睛下沉 + 降饱和 |
| 13 | 惊讶 | wide, calm | `sequence` 0.92→1.45→1.22 `settle:base` | 瞬间放大再回稳 |
| 14 | 害羞 | shy, calm | `sequence` 1.5s 变粉 `settle:hold` | 目光躲开 + 泛粉 |
| 15 | 疲惫 | doze, closed | `openness:0.55` `blinkMs:null` | 半睁 + 目光下沉 |
| 16 | 专注 | glare, calm | 双眼 `x` 内聚 ±4 | 眼神内聚、几乎不动 |
| 17 | 慌张 | wide | `poolMs:[900,1800]` + 三条 jitter | 高频轮换 + 乱晃 + 细颤 |
| 18 | 无奈 | sly | `rotate:10` `lookY:-8` | 头一歪、翻白眼 |
| 19 | 满意 | scan, smile | `sine` lookY ±5 周期 1050 | 节奏性点头 |
| 20 | 困惑 | sly, calm | 两眼缩放 1.16 / 0.8 + 相位差 1.6 | 注视方向对不齐 |
| 21 | 生气 | glare, wide | `sequence` 250ms 涨红 `settle:hold` `color:#E4574A` | 怒目 + 涨红发抖 |

### 代理工作状态 `agent`

| ID | 名称 | pool | 关键参数 | 记忆点 |
|---|---|---|---|---|
| 30 | 思考中 | idle, glare, sly, calm | `body.orbit:1` `lookY:-6` | 头顶常驻环带 |
| 31 | 接收任务 | scan, calm | `sequence` 眨眼放大 `settle:base` | 像点头确认 |
| 32 | 处理中忙碌 | glare, calm | `sine` lookX 6/1200 + lookY 4/900 | 目光小幅循环 |
| 33 | 任务完成 | smile, happy | `ribbons:1` `confetti:0.95` | 自旋甩带 + 撒花 |
| 34 | 出错 | wide | `sequence` 红白闪 4 次 `settle:hold` | 定格警示红 |
| 35 | 等待输入 | listen, scan | `sine` lookY ±6 | 轻轻上下扫读 |
| 36 | 联网加载 | calm, idle | 左右眼 `blink` 相位差 600ms | 信号来回跳 |
| 37 | 复述回忆 | listen, scan | `lookY:-9` `transition:780` | 目光飘向上方 |
| 38 | 拒绝/受限 | sly | `sequence` 摇头 6 帧 `settle:base` `openness:0.6` | 连续摇头 |
| 39 | 输出回复 | scan | `pulse` eyes scale 0.1/680 | 随输出节奏脉动 |
| 40 | 检索资料 | scan, wide, listen, idle | `poolSpeed:10` `poolMs:[1000,1800]` `scan` lookX ±11 | 6 组高速轮换 + 快扫 |
| 41 | 停止终止 | closed, doze | `sequence` 收小半闭 1.5s `settle:hold` `gaze:false` | 慢慢收小定格 |

## 4. 新增一个表情（工作流）

```
- [ ] 选 id：占用本组空号，name/desc/en 双语齐全
- [ ] 从眼环形状表挑 1~4 个形状组成 pool（这就是"它的情绪"）
- [ ] 配 poolMs / poolSpeed / blinkMs / openness / antics / transition / gaze
- [ ] body 至少给 breathe；需要事件效果才给 ribbons / confetti
- [ ] eyes 调姿态（位移 / 缩放 / 朝向）；anims ≤ 3 条，振幅克制
- [ ] 如需"表演"用 sequence；检查 settle 语义与体色一致性规则
- [ ] 验证：静态缩略图可辨识 → 悬停动画正确 → 主舞台切入过渡自然
- [ ] 连续切换两个表情 10 次，确认无白屏、无残留特效、无眼睛飞出身体
```

## 5. 常见坑

| 症状 | 原因 | 修法 |
|---|---|---|
| 切表情时眼睛先弹回圆眼再变形 | 形变起点没冻结 | 按 `method.md §2.2` 冻结当前插值结果 |
| 缩略图和实际观感不一致 | `hold` 序列改了体色，但 base 色没改 | base 色 = 序列终态色 |
| 自旋收尾拖一堆碎带 | 甩带阈值太低 | 只让 `|角速度| ≥ 5` 甩带，`≥0.9` 算"快" |
| 小尺寸下眼睛看不见 | 眼睛占比太小 | `eyeScale: 1.5~1.8` + `lite: true` |
| 掉帧时弹簧爆掉 / 眼睛错位 | 弹簧没分子步 | 子步 1/120 半隐式欧拉 |
| 多实例同时眨眼像机械舞 | 相位没打散 | 相位里混入实例随机种子 |
| 睡眠时眼球还在跟鼠标 | 忘配 `gaze:false` | 睡眠 / 停止类必须关注视 |
| 眼睛越出身体轮廓 | 缺纵向钳制 | `clamp` 到轮廓扫描行范围内 |
