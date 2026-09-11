# AGENTS.md

本仓库是一个 **LLM Wiki 知识库**（Karpathy 方法论，Obsidian vault）。

**完整规则见 [[02-Rules/AGENTS.md]]，任何 LLM 代理在工作前必须先阅读它。**

要点速览：

- 三层架构：`00-Raw/`（只读源）→ `01-Wiki/`（LLM 维护）→ `02-Rules/`（本 schema）
- 原始资料**内容永不修改**（仅允许在 `00-Raw/` 内移动以分类），且**按知识点分文件夹**存放；出现新知识点则新建文件夹
- Wiki 层由 LLM 全权维护：summaries/entities/concepts 页 + `index.md` + `log.md`
- 工作流：Ingest（摄入）、Query（查询）、Lint（健康检查），详见规则文件
