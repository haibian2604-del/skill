# skill

个人 Agent Skills 仓库，存放可复用的 [WorkBuddy](https://www.workbuddy.cn) / CodeBuddy 技能包。

## 目录结构

```
skill/
├── README.md
└── <skill-name>/
    ├── SKILL.md          # 技能入口：描述、触发条件、工作流
    ├── scripts/          # 可执行脚本（可选）
    ├── references/       # 参考文档（可选）
    └── assets/           # 静态资源（可选）
```

## SKILL.md 规范

每个技能目录必须包含 `SKILL.md`，使用 YAML frontmatter：

```markdown
---
name: my-skill
description: 一句话说明技能用途与触发时机
---

# 技能正文
...
```

## 包含技能

| 技能 | 说明 |
|------|------|
| [resume-master](./resume-master/) | 一站式简历编写：HTML 源文件 + 一页式 PDF 导出，支持从零创建与按 JD 改旧简历。参考 [wangyafu/resume-skills](https://github.com/wangyafu/resume-skills) |
| [project-to-resume](./project-to-resume/) | 把代码仓库、README、架构图（图片或 HTML 页面）或口述材料转化为简历项目经历，输出标准版/精简版/深度版三套文案，可选按 JD 定制 |
| [llm-wiki](./llm-wiki/) | 搭建与维护 Karpathy 方法论的 LLM Wiki 知识库（Obsidian vault）：三层架构 00-Raw/01-Wiki/02-Rules、页面模板、分类体系、Obsidian 配色与图谱配置，支持脚手架创建 + ingest/query/lint 维护 |
| [skill-usage](./skill-usage/) | 查询某个已安装 Skill 的用法：定位 SKILL.md 后按固定结构输出作用、触发方式、输入要求、流程、产出物、依赖与坑；也可列出全部已安装技能（含脚本 find_skill.py） |

## 安装方式

将技能目录克隆或复制到 `~/.workbuddy/skills/` 即可全局使用：

```bash
git clone git@github.com:haibian2604-del/skill.git
cp -r skill/<skill-name> ~/.workbuddy/skills/
```

简历技能还需安装 Python 依赖（PDF 拆图与页数统计）：

```bash
pip install pymupdf pypdf
```

## 约定

- 技能命名使用 kebab-case，如 `deploy-to-staging`
- 触发词与使用边界写在 frontmatter 的 `description` 中
- 脚本需在 SKILL.md 中注明前置依赖与运行环境
- **每次新增技能后，必须在同一提交中更新上方「包含技能」表格**：添加新技能的名称、链接与一句作用简介；删除技能时同步移除对应行
