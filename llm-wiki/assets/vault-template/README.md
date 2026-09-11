# {{VAULT_NAME}} · LLM Wiki

> 个人知识库：以 Karpathy LLM Wiki 方法论搭建的 **Obsidian vault**。
> 原始资料冻结存档，Wiki 页由 LLM 全权维护，分类规则写入 schema 层。

- **源文件**：0 篇（0 个知识点文件夹）
- **Wiki 页面**：0 页（0 摘要 / 0 实体 / 0 概念）
- **远端仓库**：`{{REPO_URL}}`

---

## 一、三层架构

```
{{VAULT_NAME}}/                  # Obsidian vault = 一个普通文件夹
├── 00-Raw/                      # RAW 层：内容不可变，只读；按知识点分文件夹
│   ├── inbox/                   #   新源文件暂存区，ingest 前放这里
│   ├── <knowledge-point>/       #   知识点文件夹（见下表）
│   └── README.md                #   本层使用说明 + 目录清单
├── 01-Wiki/                     # WIKI 层：LLM 全权维护
│   ├── index.md                 #   内容索引（回答查询先读这里）
│   ├── log.md                   #   时间日志（append-only）
│   ├── summaries/               #   来源摘要：每个源一篇
│   ├── entities/                #   实体页：人 / 组织 / 产品 / 项目
│   └── concepts/                #   概念页：理论 / 术语 / 方法
├── 02-Rules/                    # SCHEMA 层：LLM 的纪律来源
│   ├── AGENTS.md                #   维护手册（工作流 + 页面模板）
│   └── 分类体系.md              #   分类规则（domain 词表 + 知识点目录 + 配色）
└── AGENTS.md                    # 代理入口速览
```

**铁律**

1. `00-Raw/` 源文件**内容永不修改**（唯一允许的写操作：在层内移动以分类）
2. Wiki 层完全由 LLM 维护，用户只读浏览
3. 好答案（对比 / 分析 / 发现的联系）必须归档回 Wiki，不能消失在对话里
4. 每个页面必标 `domain` + `tags`，不得自创游离标签

---

## 二、00-Raw 知识点目录

不同知识点的源文件放入不同文件夹；出现**全新知识点**则新建文件夹并登记到 [[02-Rules/分类体系]] §9。

| 文件夹 | 知识点 | 篇数 |
|--------|--------|:---:|
| `inbox/` | 暂存区（未分类） | — |

---

## 三、工作流

| 流程 | 触发 | 动作 |
|------|------|------|
| **Ingest** | 新源放入 `00-Raw/inbox/` 并说"处理这个" | 读源 → 写摘要 → 更新 `index.md` → 联动实体/概念页 → 记 `log.md` → 按知识点归档 + 同步改链 |
| **Query** | 向 LLM 提问 | 先读 `index.md` 定位 → 深入阅读 → 答案引用来源 → 有价值的答案归档为新页 |
| **Lint** | 定期健康检查 | 查矛盾 / 过期声明 / 孤儿页 / 缺失页 / 数据缺口 → 产出修复清单 |

> 详细步骤与页面模板见 [[02-Rules/AGENTS.md]]。

---

## 四、分类体系

- **domain（一级主题，必填且唯一）**：`tech` / `product` / `business` / `academic` / `life` / `reading` / `other`
- **tags（细分主题，1-3 个）**：小写英文连字符（如 `rag`、`mcp`），从词表选取
- **status（成熟度）**：`seedling` → `growing` → `mature`

「两层各用各的维度」：`01-Wiki/` 目录按**页面类型**组织、主题靠 frontmatter；`00-Raw/` 目录按**知识点**组织。完整规则见 [[02-Rules/分类体系]]。

---

## 五、可视化约定

- **颜色片段**：`.obsidian/snippets/wiki-colors.css`，需在「设置 → 外观 → CSS 代码片段」启用 `wiki-colors`
- **类型配色**：摘要🟠 / 实体🔵 / 概念🟢 / 规则🟣
- **图谱配色**：`.obsidian/graph.json` 双层策略 —— 子域标签组（按 `#tag` 着色）在前，路径兜底组在后
- **Dataview**：`index.md` 顶部含动态查询块，需安装 Dataview 插件

---

## 六、仓库与协作

```bash
# 克隆
git clone {{REPO_URL}}

# 日常
git add -A && git commit -m "..." && git push
```

- `.gitignore` 排除：`.DS_Store`、`.obsidian/workspace.json`（易变的 UI 状态）、`.workbuddy/`（工具内部记忆）
- 每次会话的工作成果 ≈ 一次 commit；`log.md` 记录每次 Ingestion / Query / Lint

---

## 七、给 LLM 代理

**开始工作前必须阅读 [[02-Rules/AGENTS.md]]**（维护手册）与 [[02-Rules/分类体系]]（分类规则）。

要点：源不可改但可移动分类 · Wiki 全权维护 · 分类必标 `domain` + `tags` · 移动文件后必须同步更新 `[[00-Raw/...]]` 链接。

_创建于 {{TODAY}}_
