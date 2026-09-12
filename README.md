# skill

个人 Agent Skills 仓库，存放可复用的 [WorkBuddy](https://www.workbuddy.cn) / CodeBuddy 技能包。

**仓库地址**

| 类型 | 地址 |
|------|------|
| SSH（推荐） | `git@github.com:haibian2604-del/skill.git` |
| HTTPS | `https://github.com/haibian2604-del/skill.git` |
| 网页 | https://github.com/haibian2604-del/skill |

> HTTPS 克隆在本机偶发 502，优先用 SSH。

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

| 技能 | 说明 | 触发词 / 调用 |
|------|------|------|
| [resume-master](./resume-master/) | 一站式简历编写：HTML 源文件 + 一页式 PDF 导出，支持从零创建与按 JD 改旧简历。参考 [wangyafu/resume-skills](https://github.com/wangyafu/resume-skills) | 写简历、改简历、优化简历、导出简历 PDF、根据 JD 改简历 |
| [project-to-resume](./project-to-resume/) | 把代码仓库、README、架构图（图片或 HTML 页面）或口述材料转化为简历项目经历，输出标准版/精简版/深度版三套文案，可选按 JD 定制 | `/project-to-resume`、把项目写成简历经历、项目经历怎么描述、简历项目润色 |
| [llm-wiki](./llm-wiki/) | 搭建与维护 Karpathy 方法论的 LLM Wiki 知识库（Obsidian vault）：三层架构 00-Raw/01-Wiki/02-Rules、页面模板、分类体系、Obsidian 配色与图谱配置，支持脚手架创建 + ingest/query/lint 维护 | LLM Wiki、创建知识库、obsidian 知识库、ingest 摄入资料、lint 知识库 |
| [skill-usage](./skill-usage/) | 查询某个已安装 Skill 的用法：定位 SKILL.md 后按固定结构输出作用、触发方式、输入要求、流程、产出物、依赖与坑；也可列出全部已安装技能（含脚本 find_skill.py） | X 技能怎么用、/xxx 是干什么的、有哪些 skill |

## 安装方式

技能安装到 **用户级**（`~/.workbuddy/skills/`，所有项目可用）或 **项目级**（`<项目>/.workbuddy/skills/`，仅该项目可用）。任选一种：

### 方式一：对话式安装（推荐，最省事）

在 WorkBuddy 里直接对 Agent 说：

```text
帮我安装这个仓库里的 llm-wiki 技能：
git@github.com:haibian2604-del/skill.git
```

或逐个安装：

```text
从 https://github.com/haibian2604-del/skill 安装 resume-master 技能
安装 skill 仓库里的 skill-usage 技能，仓库地址 git@github.com:haibian2604-del/skill.git
```

Agent 会克隆仓库并把对应技能目录复制到 `~/.workbuddy/skills/`。装好后**重启会话**或到「技能管理」面板确认技能已出现。

### 方式二：手动克隆安装

```bash
# 1. 克隆仓库到任意目录
git clone git@github.com:haibian2604-del/skill.git
cd skill

# 2. 复制需要的技能到用户级技能目录（可一次复制多个）
mkdir -p ~/.workbuddy/skills
cp -r resume-master project-to-resume llm-wiki skill-usage ~/.workbuddy/skills/
```

### 方式三：官方推荐市场安装

仅适用于已上架官方市场的技能，在对话里说「帮我安装 XX 技能」即可，Agent 会搜索推荐市场并安装。

### 更新已安装技能

```bash
cd skill && git pull
cp -r resume-master project-to-resume llm-wiki skill-usage ~/.workbuddy/skills/
```

或直接对 Agent 说：「更新 ~/.workbuddy/skills/ 里的 llm-wiki 技能，源仓库是 git@github.com:haibian2604-del/skill.git」。

### 卸载技能

删除对应目录即可：`rm -rf ~/.workbuddy/skills/<skill-name>`，然后在「技能管理」面板刷新。

### 依赖

简历类技能（resume-master / project-to-resume）需要 Python 依赖（PDF 拆图与页数统计）：

```bash
pip install pymupdf pypdf
```

## 约定

- 技能命名使用 kebab-case，如 `deploy-to-staging`
- 触发词与使用边界写在 frontmatter 的 `description` 中
- 脚本需在 SKILL.md 中注明前置依赖与运行环境
- **每次新增技能后，必须在同一提交中更新上方「包含技能」表格**：添加新技能的名称、链接、一句作用简介与触发词；删除技能时同步移除对应行
- 新增或重命名技能后，同步更新「安装方式」里方式一、方式二的示例技能清单
