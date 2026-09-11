# Wiki 日志 (Log)

> 时间线记录，**append-only**，只允许在末尾追加，绝不改写历史。
> 每次 ingest / query / lint / update 追加一条。
> 可解析性：`grep "^## \[" 01-Wiki/log.md | tail -5` 查看最近 5 条活动。

## 操作类型

| 前缀 | 触发时机 | 内容要点 |
|------|----------|----------|
| `init` | 初始化/重构 | 本次变更概要 |
| `ingest` | 摄入新源 | 源文件名、新增/更新的页面清单、归档位置 |
| `query` | 查询后归档 | 问题、归档的新页面名 |
| `lint` | 健康检查 | 发现的问题数、修复数、遗留缺口 |
| `update` | 页面修订 | 修订的页面、原因（新源反驳/纠错等） |

## 记录格式

```markdown
## [YYYY-MM-DD] 操作 | 简述

- 正文要点（可多行、可嵌套列表）
```

---

## [{{TODAY}}] init | 知识库初始化

- 从 `llm-wiki` 技能脚手架生成：三层架构（00-Raw / 01-Wiki / 02-Rules）+ Obsidian 配色（wiki-colors.css + graph.json 路径兜底组）
- 目录已就绪：`00-Raw/inbox/`（暂存区）、`01-Wiki/{summaries,entities,concepts}/`
- 待办：把第一批源文件放入 `00-Raw/inbox/`，说"处理这个"开始 ingest
