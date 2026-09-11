---
name: llm-wiki
agent_created: true
description: 搭建与维护 Karpathy 方法论的个人知识库（LLM Wiki，Obsidian vault）：三层架构 00-Raw（只读源）/ 01-Wiki（LLM 维护）/ 02-Rules（分类 schema），含页面模板、分类体系、Obsidian 配色与图谱配置。当用户想 (1) 从零创建一个 LLM Wiki / 个人知识库 / Obsidian 知识库；(2) 把资料「摄入」进已有知识库（ingest）；(3) 在知识库中查询、或做健康检查（lint）；(4) 复刻 / 迁移 / 对齐某知识库的三层结构与规则时使用。触发词：LLM Wiki、知识库搭建、创建知识库、obsidian 知识库、ingest、摄入资料、lint 知识库、卡帕西 wiki。
---

# LLM Wiki 知识库

搭建一个「原始资料冻结 + LLM 全权维护理解」的知识库，或接手维护已有的同款知识库。
方法论来源：Karpathy LLM Wiki（三层架构 + schema 层写死纪律）。

## 铁律（不可违背）

1. **`00-Raw/` 源文件内容永不修改**。唯一允许的写操作是在 `00-Raw/` **内部移动**（归档分类）。发现源里有错，只在 wiki 层标注，不回改源。
2. **Wiki 层（`01-Wiki/`）由 LLM 全权维护**，用户只读浏览。
3. **每个页面必标 `domain` + `tags`**，从词表选，不自创游离标签。
4. **好答案必须归档回 wiki**（对比、分析、发现的联系），不能消失在对话里。
5. **移动源文件后必须同步更新所有 `[[00-Raw/...]]` 链接**，死链是高发错误。

## 三层架构

```
<vault>/
├── 00-Raw/          # RAW：内容不可变；按「知识点」分文件夹（inbox/ 为暂存区）
├── 01-Wiki/         # WIKI：LLM 维护；index.md / log.md / summaries / entities / concepts
├── 02-Rules/        # SCHEMA：AGENTS.md（手册）+ 分类体系.md（taxonomy）
└── AGENTS.md        # 代理入口速览
```

- `01-Wiki/` 目录按**页面类型**组织，主题靠 frontmatter → 「目录管类型，标签管主题」
- `00-Raw/` 目录按**知识点**组织（原始资料无 frontmatter，只能靠文件夹分类）
- 三类页面：`summaries`（每篇源一篇）· `entities`（人/组织/产品/项目）· `concepts`（理论/术语/方法）

## 工作流 1：从零创建知识库

1. 向用户确认三件事：**知识库目录路径**、**名称**、**是否需要 git 远端**（可选）。
2. 运行脚手架（自动复制模板 + 替换占位符 + 建空目录 + 可选 git init）：

```bash
/Users/kk/.workbuddy/binaries/python/envs/default/bin/python \
  <skill_dir>/scripts/scaffold_wiki.py \
  --target <目标目录> --name <库名> [--repo <远端URL>] [--git]
```

3. 告知用户后续手工动作（Obsidian 侧无法脚本化）：
   - 用 Obsidian「Open folder as vault」打开该目录
   - 设置 → 外观 → CSS 代码片段 → 启用 `wiki-colors`
   - 安装 **Dataview** 插件（`index.md` 的动态表格依赖它；未装则手工条目仍有效）
4. 验证产出：`00-Raw/inbox/`、`01-Wiki/{summaries,entities,concepts}/`、`02-Rules/` 齐全，`.md/.json/.css` 中无残留 `{{...}}` 占位符。
5. 引导第一次 ingest（见工作流 2）。

模板内容清单见 `assets/vault-template/`；各文件作用与设计取舍见 `references/设计说明.md`。

## 工作流 2：Ingest（摄入资料）

用户把源文件放进 `00-Raw/inbox/` 并说"处理这个"时：

1. **读源全文**（PDF 先转文本或转图阅读；网页剪藏先查 frontmatter 有没有串号）
2. **与用户确认要点**（单篇：1-3 个问题，附选项；批量可跳过）
3. **写摘要页** `01-Wiki/summaries/<源标题>.md`（模板见 `<vault>/02-Rules/AGENTS.md` §2.5）
4. **更新 `01-Wiki/index.md`**，加一行条目
5. **联动新建/更新** entities 与 concepts 页，加双向链接；命中已有页时**补内容**而不只加链接
6. **追加 `01-Wiki/log.md`**：`## [YYYY-MM-DD] ingest | 标题`
7. **归档源文件**：判定知识点 → 从 `inbox/` 移入 `00-Raw/<知识点>/`；无匹配则新建文件夹并登记到 `分类体系.md` §9.1 + `00-Raw/README.md` + 根 `README.md`
8. **改链**：移动后全局搜索旧路径，更新所有 `sources:` 中的 `[[00-Raw/...]]`
9. `git add -A && git commit -m "ingest: <标题>"`

## 工作流 3：Query 与 Lint

- **Query**：先读 `index.md` 定位 → 深入页面 → 需要时回溯 `00-Raw/`。答案必须引用来源；有价值的答案问用户是否归档为新页。
- **Lint**：检查矛盾 / 过期声明 / 孤儿页 / 缺失页 / 死链 / 数据缺口 → 产出修复清单，**先与用户确认再改**。

详细步骤、扩展规则（新 domain / tag / 知识点文件夹的登记位置）、常见坑见 `references/工作流与维护.md`。

## 进入已有知识库时先做

按顺序读：`02-Rules/AGENTS.md` → `02-Rules/分类体系.md` → `01-Wiki/index.md`；
再看 `git log --oneline -3`、`grep "^## \[" 01-Wiki/log.md | tail -5`、`ls 00-Raw/inbox/`。

**该库自己的 `02-Rules/AGENTS.md` 优先级高于本技能**——若两者冲突，以库内规则为准，并按需建议用户把本技能的改进回写到库内规则。

## 参考文件

| 文件 | 何时读 |
|------|--------|
| `assets/vault-template/` | 脚手架模板（三层文件 + Obsidian 配置），脚本自动复制 |
| `references/工作流与维护.md` | 执行 ingest / query / lint、扩展词表、排查问题 |
| `references/设计说明.md` | 需要向用户解释设计取舍，或为新领域做适配 |

依赖：仅需 Python 标准库；Obsidian 客户端为可选（用于浏览与可视化）。
