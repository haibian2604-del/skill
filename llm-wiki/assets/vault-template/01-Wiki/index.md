# Wiki 索引 (Index)

> 内容目录。每次 ingest / lint 后必须更新。
> 回答查询时先读本文件定位页面，再深入阅读。
> 条目格式：`- [[链接]] — 一句话摘要（YYYY-MM-DD，来源 ×N）`
> 分类规则见 [[02-Rules/分类体系]]：每个页面必标 `domain`（主题领域）+ `tags`（细分主题）。

## 📌 概览

本 wiki 采用 Karpathy LLM Wiki 三层架构：`00-Raw`（只读源）→ `01-Wiki`（LLM 维护）→ `02-Rules`（schema）。
完整规则见 [[02-Rules/AGENTS.md]]。

```dataview
TABLE domain AS 领域, type AS 类型, status AS 状态, date(updated) AS 更新于
FROM "01-Wiki"
WHERE type
SORT domain, updated DESC
```

## 🗂️ 按主题领域浏览 (By Domain)

> 领域词表见 [[02-Rules/分类体系]]（tech / product / business / academic / life / reading / other）。

```dataview
TABLE rows.file.link AS 页面
FROM "01-Wiki"
WHERE type AND domain
GROUP BY domain
```

## 📚 摘要 (Summaries) — `01-Wiki/summaries/`

_暂无_

## 🏛️ 实体 (Entities) — `01-Wiki/entities/`

_暂无_

## 💡 概念 (Concepts) — `01-Wiki/concepts/`

_暂无_

## 📋 待办与缺口 (Open Questions)

> Lint 发现的缺口、用户想深挖的问题，处理完后移出本区。

_暂无_

## 维护约定

1. 添加/更新页面后：在对应分类下增改一行条目，格式见文件头
2. 条目必须含：wikilink、一句话摘要、日期、来源数
3. 同步更新 `log.md`；本文件分类与 `02-Rules/AGENTS.md` 保持一致
4. 页面删除时同步删除对应条目，避免死链
