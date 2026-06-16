# AI 图片生成门禁

> 旧版方案只讨论“生成封面/章节背景图”。新版 Presentation Director 将它拆成两个概念：`image_policy` 是 intake 阶段的权限边界；`image_generation_mode` 是 Image Style Gate 阶段的执行方式。

---

## 当前规则

| 字段 | 作用 |
|------|------|
| `image_policy` | 用户授权边界，保留现有值：`none` / `abstract-only` / `cover-section` / `ask-before-use` / `custom` |
| `image_generation_mode` | 执行模式：`none` / `global-background` / `cover-section-auto` / `post-v1-slot-review` / `hybrid` |
| `image-plan.json` | Image Style Gate 写入的 pre-v1 target 和 prompt 草稿 |
| `image-assets.json` | 每个 target 的 attempts[] 与 final_status |
| `image-placement-request.json` | v1 preview 后由用户确认的 post-v1 插图请求 |

`final_status: "success"` 只能由生图记录层在 `output_path` 存在且 `size_bytes > 0` 时写入。API 返回成功但图片文件缺失或为空，仍必须记录为失败或 retrying。

失败策略是 **retry-2-then-stop**：最多 3 次尝试。三次失败后停止流程，不能静默退化成 CSS 渐变、SVG 占位或普通装饰背景。

---

## 适用场景

| 情况 | 建议 |
|------|------|
| design-lock 纯色方案已经足够 | **跳过**，直接生成 PPTX |
| 想要更强的视觉冲击力（路演封面、大赛答辩）| **使用**，生成封面背景图 |
| 需要独一无二的品牌感 | **使用**，生成与内容主题相关的抽象背景 |

---

## 只用于哪些页面

**适合使用背景图：**
- 封面（Cover）
- 章节切换页（Section Divider / Act Divider）

**不适合使用背景图：**
- 内容页（文字/图表/数据）：背景图会降低文字可读性
- 数据大字页（背景干扰数字识别）

---

## 图片类型选择

不要生成写实场景图（风景、人物、建筑），要生成**抽象纹理 / 几何光影**：

| 推荐方向 | 不推荐 |
|---------|-------|
| 抽象几何纹理 | 写实城市图 |
| 颜色渐变光晕 | 人物照片 |
| 纸张/麻布/大理石质感 | 卡通插图 |
| 极简线条构成 | 花卉、动物 |

抽象图像的优势：
- 不和文字抢视觉
- 与 design-lock 颜色系统保持一致
- 加半透明遮罩后文字对比度有保障
- 每次都能生成独一无二的版本

---

## Prompt 构造规则

根据 design-lock 自动构造图片 Prompt：

```text
Abstract [主色调描述] textured background,
[design-lock 风格关键词],
minimal, no text, no people, no faces,
suitable for presentation slide cover,
high resolution, 1920x1080
```

### 各档案对应的 Prompt 模板

**swiss-klein-blue（瑞士国际主义）**
```
Abstract deep blue geometric texture, Swiss modernist grid lines,
Klein Blue tones (#002FA7), minimal construction, no text, no people,
1920x1080 presentation cover background
```

**linear-dark（工程暗色）**
```
Abstract dark background with subtle purple grid lines,
engineering precision aesthetic, near-black (#08090a) with indigo accent,
minimal circuit-like geometry, no text, no people,
1920x1080 presentation cover background
```

**editorial（暖纸叙事）**
```
Warm paper texture with subtle ink wash elements,
editorial minimal, off-white (#f1efea) and ink tones,
no text, no people, soft grain texture,
1920x1080 presentation cover background
```

**academic（靛蓝学术）**
```
Abstract indigo porcelain texture, cool tech aesthetic,
deep blue (#0a1f3d) with subtle cerulean highlights,
minimal, no text, no people,
1920x1080 presentation cover background
```

**notion-warm（暖白极简）**
```
Warm minimal abstract background, soft cream and warm grey tones,
paper texture, gentle geometric elements,
no text, no people, clean and airy,
1920x1080 presentation cover background
```

---

## 图片生成 API 选项

| API | 质量 | 费用 | 适合 |
|-----|------|------|------|
| **DALL-E 3**（OpenAI）| ★★★★ | ~$0.04/张（1024×1024） | 你已有 API Key，推荐优先使用 |
| **Flux.1**（fal.ai）| ★★★★★ | ~$0.003–0.01/张 | 质量更高、更便宜，需注册 fal.ai |
| **Stable Diffusion**（Stability AI）| ★★★ | 有免费额度 | 最可控，适合反复测试 |

**推荐：DALL-E 3**，因为你已有 OpenAI API Key，零额外配置。

---

## 在工作流中的位置

```text
[4] Visual Inspiration Gate
    选择 visual candidate；HTML 输出时同时带 transition / animation / gradient 候选
        ↓
[5] Brief Confirmation Gate
    用户点击确认
        ↓
[5.5] Image Style Gate
    ├─ 选择 image_generation_mode
    ├─ ask-before-use + pre-v1 模式时逐条确认 prompt 草稿
    ├─ 写 image-plan.json
    └─ 如需 pre-v1 图片：生成 → image-asset 记录 → guard
        ↓
[6] 生成 v1
    ├─ pptx → v1/final.pptx + v1/contact-sheet.png
    ├─ html-revealjs → v1/.draft/final.html → finalize → v1/final.html
    └─ both → v1/final.pptx + v1/.draft/final.html → finalize → v1/final.html
        ↓
[6.5] Image Placement Gate（post-v1-slot-review / hybrid）
    基于 v1 preview artifact 确认插图位置，写 image-placement-request.json
        ↓
[7] 生成 v2（如有 post-v1 插图）
```

---

## 给 Codex 的 Prompt 片段（带背景图）

```text
背景图已生成并保存在 PPTX/<task-slug>/assets/images/<target-id>.png，并已记录到 image-assets.json。

封面页和章节切换页：
- 使用已确认 target 的 output_path 作为满铺背景图
- 叠加 50% 不透明度的遮罩，颜色使用 design-lock 的主背景色
- 文字颜色用 design-lock 的反色（浅底用深字，深底用白字）

内容页：
- 不使用背景图
- 按 design-lock 的纯色填充方案
```

---

## 注意事项

1. **遮罩必须加**：背景图直接叠文字会导致对比度不足，遮罩是保障可读性的关键
2. **尺寸要对**：PPT 幻灯片通常是 1920×1080（16:9），生成时指定分辨率
3. **图片不放 Git**：`PPTX/` 和 `assets/` 已被忽略，生成图片不需要版本管理
4. **每次可以重新生成**：如果第一次的图不满意，按 attempts[] 追加记录；第 1 次失败第 2 次成功时，guard 只看最终 `final_status`
5. **不能静默降级**：失败时必须 stderr / guard message 明确说明，不能把 CSS 渐变当作“图片已生成”
