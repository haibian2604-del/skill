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

## 安装方式

将技能目录克隆或复制到 `~/.workbuddy/skills/` 即可全局使用：

```bash
git clone git@github.com:haibian2604-del/skill.git
cp -r skill/<skill-name> ~/.workbuddy/skills/
```

## 约定

- 技能命名使用 kebab-case，如 `deploy-to-staging`
- 触发词与使用边界写在 frontmatter 的 `description` 中
- 脚本需在 SKILL.md 中注明前置依赖与运行环境
