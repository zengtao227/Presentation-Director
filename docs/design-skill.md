# UI/UX Pro Max 设计支持

全局官方的 `ui-ux-pro-max`（`~/.claude/skills/ui-ux-pro-max`）是本仓库用于 PPT 和可视化页面设计的 skill，仓库不再内置副本。它不是 PPTX 生成器，而是可搜索的设计情报库。新版增加了 `--design-system` 聚合生成器，可以一次性输出行业匹配的风格、语义色板、字体、页面模式、关键效果和反模式。

## 适用场景

- 路演 PPT 视觉重做
- 比赛答辩 PPT 版式优化
- Markdown PPT 的配色与字体方案选择
- 图表页、时间线页、对比页的表达方式选择
- 导出前的可读性、对比度、留白检查

## 推荐检索顺序

优先生成总简报：

```bash
python3 ~/.claude/skills/ui-ux-pro-max/scripts/search.py "<行业 + deck 类型 + 听众>" \
  --design-system \
  --format markdown \
  --project-name "<项目名>"
```

再做定向检索：

```bash
python3 ~/.claude/skills/ui-ux-pro-max/scripts/search.py "<项目类型>" --domain product
python3 ~/.claude/skills/ui-ux-pro-max/scripts/search.py "<风格关键词>" --domain style
python3 ~/.claude/skills/ui-ux-pro-max/scripts/search.py "<字体气质>" --domain typography
python3 ~/.claude/skills/ui-ux-pro-max/scripts/search.py "<中文字体或英文字体>" --domain google-fonts
python3 ~/.claude/skills/ui-ux-pro-max/scripts/search.py "<行业或场景>" --domain color
python3 ~/.claude/skills/ui-ux-pro-max/scripts/search.py "<图表类型>" --domain chart
python3 ~/.claude/skills/ui-ux-pro-max/scripts/search.py "accessibility layout spacing contrast" --domain ux
```

新版可用增量：

- `--design-system`：把 product / style / color / landing / typography 和行业推理规则合并成设计简报。
- `ui-reasoning.csv`：161 条行业规则，能给出 anti-patterns，适合放进 PPTX Prompt 的“禁用项”。
- 扩展色板：`color` 域从简单 primary/secondary/CTA 扩展为 semantic palette，包括 foreground、muted、border、ring 等。
- `google-fonts` 域：可以确认中英文字体、字重和语言 subset，减少 PPTX 字体选择盲区。
- 更多 stack/domain：对需要先做 HTML demo 或网页式可视化原型的材料更有用。

## 路演 PPT 建议默认方向

对于高校竞赛、酒店服务、AI 应用路演这类材料，优先采用：

- 风格：Swiss Modernism 2.0 / Trust & Authority / Minimalism
- 配色：浅色背景、深色正文、蓝绿双主色，少量金色作为强调
- 字体：现代专业型无衬线字体，中文优先保证可读性和稳定导出
- 版式：12 栏网格、充足留白、少装饰、少大面积暗色
- 检查：标题不被线条穿过，正文不低对比，卡片不拥挤，句末标点不破坏标题观感

## 使用原则

设计建议必须服务于内容表达。涉及比赛名称、项目定义、评分权重、学校名称和团队信息时，以项目资料和官方规则为准，不用设计 skill 改写事实。

`--design-system` 输出偏 Web/UI 语境。用于 PPTX 时，不要照搬滚动动画、hover、CTA 页面结构；应把它翻译成版式节奏、视觉层级、图表语法和反模式清单，再交给 Codex `Presentations`。
