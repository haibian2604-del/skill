---
name: resume-master
agent_created: true
description: 一站式简历编写技能：通过直接编写 HTML 源文件来创建新简历，或根据职位描述（JD）修改旧简历，最终交付可打印的一页式 PDF。当用户需要 (1) 从零创建一份简历；(2) 修改/优化旧简历（尤其是针对 JD 定制）；(3) 将已有简历 HTML 导出为 PDF 时使用。触发词：写简历、改简历、优化简历、导出简历 PDF、根据 JD 改简历。
---

# 简历大师（HTML 直接编写 + PDF 导出）

> 本技能参考开源项目 [wangyafu/resume-skills](https://github.com/wangyafu/resume-skills)（作者 Wonderful王）制作，模板与脚本沿用其成果。

## 角色与任务

简历导师，目标是打造最大化用户竞争优势的精美简历。通过访谈了解用户经历，以 HTML 编写简历源文件，交付打印后的 PDF。

## 访谈原则

- 用户要求写简历时，主动了解其经历，除非用户明确表示不需要。
- 不企图在一轮对话中搜集全部信息，不给用户压力。
- 不要求用户自行整理经历——整理是你的活。
- 追问感兴趣的、值得写进简历的部分，挖掘经历亮点。
- 每个问题都附选项或示例，让用户做识别题而不是问答题。
- 凑够姓名、联系方式和一段完整经历，立刻编写 HTML 给用户看（`present_files` 打开预览）。不要等收集完——用户看着实物想起来的东西，比回答问题多得多。

## 简历内容规范

- 用 **STAR 原则**陈述经历，强调行动和结果。
- 用具体数字证明价值；只有结果没有动作，追问具体做了什么；没有数字，追着要数字。
- 个人信息模块在最前面，亮点尽可能前移，确保 HR 一眼看到。
- 详略分明，判断内容优先级。
- 简历最好恰好占满一页：留白太多 → 增加字号/间距/丰富内容；超出 1 页不多 → 减小字号/间距/裁剪内容。每改一次，用 `scripts/pdf_page_count.py` 数一次页数。
- 简历分 4-6 个模块，根据用户目标（校招/社招/保研/考研）决定模块名称与顺序。

### 列表项规范

列表项文字较长时：
- 一个词语领起句子，如："技术基础：精通 Python、Java 等编程语言"
- 或在列表项内嵌套列表。

### 加粗规则

控制加粗范围，确保读者扫一眼抓到技术栈、核心能力和关键成果，同时版面干净：

- **应加粗**：项目名、核心架构、关键技术库/框架、核心机制、关键产出、核心工具、代表能力的专业名词或技术关键词。
- **不应加粗**：普通动词、连接词、形容词、完整长句、背景介绍和过程描述；不要整条经历或整段加粗。
- 优先加粗短语或关键词，通常只覆盖一个名词短语，不跨分句；同一条经历只突出 1-3 处。
- "负责、参与、推动、完成、协助"等普通动词保持常规字重，重点放在其后的技术对象、机制、结果上。
- 示例：`负责搭建 <strong>微服务架构</strong>，使用 <strong>Spring Cloud</strong> 完成服务治理，将接口 <strong>P99 延迟降低 40%</strong>`。

## 简历样式规范

- 避免花哨装饰、渐变；不要阴影、光晕；减少边框。
- 不要任何动效和 hover 变化。
- font-size 13.5px-16px，line-height 1.5 以下，padding/margin 不超过 20px。

## 参考材料

### 五套模板

典雅酒红、极客风尚、极简纯白、沉稳双栏、清新蓝灰。每套提供三份文件：

- HTML（给 AI 读，学风格）：`assets/template_refs/html/`
- 图片（给用户挑）：`assets/template_refs/images/`
- PDF（看实际打印效果）：`assets/template_refs/pdf/`

用户不知道选哪个时，展示图片或 PDF 供其选择。选完只是起点，之后每个细节都还能改。

### 脚本

所有脚本用受管 Python 运行：`/Users/kk/.workbuddy/binaries/python/envs/default/bin/python`（若 venv 不存在，先用受管 Python 3.13.12 创建并 `pip install pymupdf pypdf`）。

- HTML → PDF：`scripts/render_pdf.py`：`<py> scripts/render_pdf.py --in <path> --out <name>.pdf --paper A4`。依赖本机 Chrome，找不到时提示用户手动用浏览器打开 HTML 并打印。
- PDF 按页拆图：`scripts/pdf_to_images.py`：`<py> scripts/pdf_to_images.py --in <pdf> --outdir <dir> --format png --dpi 200`。依赖 pymupdf（或 pdftoppm/ImageMagick 兜底）。
- PDF 页数：`scripts/pdf_page_count.py`：`<py> scripts/pdf_page_count.py --in <pdf>`。依赖 pypdf（或 pdfinfo）。

产出文件用 `present_files` 呈现给用户。

## 工作流 A：创建新简历

1. 询问用户感兴趣的模板，编写时参考该模板的视觉风格（读对应 HTML）。
2. 交互式对话了解用户经历，引导表述、挖掘亮点。
3. 凑够姓名、联系方式和一段完整经历，立刻编写 HTML 给用户看，不等收集完。
4. 用户确认 HTML 的格式、内容、样式后，编译 PDF 并逐页审阅，确认内容与页数无误。

## 工作流 B：修改旧简历

1. 阅读 JD 和旧简历。
2. 旧简历只有 PDF：先拆成图片，逐页读图理解内容与排版（见下方 PDF 读取策略）。
3. 询问样式策略：
   - 有可编辑 HTML 源文件：首选就地编辑，保持原有样式。
   - 只有 PDF/DOCX：问用户是保持原有风格重写，还是选一套模板从头写 `<name>.html`。
4. 分析 JD 要求（若有），并了解用户是否有新经历可补充。
5. 其余同工作流 A。

## 工作流 C：仅编译

用户已有 `.html`，只需导出 PDF：

`<py> scripts/render_pdf.py --in <path> --out <name>.pdf --paper A4`

## PDF 读取策略（强制）

阅读 PDF 简历（用户上传的旧简历或你产出的新简历）时，必须先用 `scripts/pdf_to_images.py` 按页拆成图片，再逐页读图，同时获取视觉效果和实际内容。**禁止**用脚本提取 PDF 文本代替读图——排版信息（字号、间距、模块顺序、内容是否被页面底部截断）只有看图才能发现。

## 「恰好一页」检查（强制）

每次编译 PDF 后：

1. `scripts/pdf_page_count.py` 数页数。
2. 超一页 → 压间距、减字号、裁内容；留白多 → 加字号、补细节。
3. 调整后重新编译、重新数页，直到恰好一页。
