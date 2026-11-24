# ChatCut 高网感口播剪辑 Skill

把一条口播原片，用 [ChatCut](https://chatcut.io) 剪成**开头抓人、画面一直在变、字幕干净、能继续改**的竖屏短视频。

这是一个给 AI 剪辑 Agent（**Gemini CLI、Google Antigravity**、Claude Code、Codex、Grok Bot 等支持 Agent Skills 的助手）用的工作流 Skill，Agent 会照着它在 ChatCut 时间线上分轮完成剪辑，最后用脚本给成片做一次“留存节奏体检”。

## 它解决什么问题

口播剪完常见的几个毛病：开头铺垫太长、整段同一个机位、重点没有画面、字幕和花字挤在一起、BGM 盖住人声。这个 Skill 把“网感”拆成能执行、能检查的规则：

- **先排节奏表再开剪**：挑 Hook、定章节，每 2–4 秒安排一个画面变化。
- **推拉镜头打底**：跳推、快推、缓推的参数和使用位置，解决“画面一直不动”。
- **双层花字 + 动画音效对照表**：打字→键盘声、上滑→pop、发光→叮、转场→whoosh。
- **部位示意图 / 画中画 / 章节卡**：说到具体东西就给画面证据。
- **美妆 / 医美 / 健康垂类规则**：哪些话不能放大，什么时候加提示语。
- **留存 QA 脚本**：量化平均画面变化间隔、最长静态段、前 3 秒变化次数、响度和真峰值。

## 实测效果

同一条 184 秒的美容口播，旧流程和本 Skill 剪出的版本对比（数据由 `retention_qa.py` 测得）：

| 指标 | 旧版 | 用本 Skill | 目标 |
| --- | --- | --- | --- |
| 时长 | 111.7 秒 | 95.5 秒 | — |
| 平均多久变一次画面 | 6.21 秒 | 2.65 秒 | ≤ 3.5 秒 |
| 最长不变画面 | 20.9 秒 | 4.4 秒 | ≤ 6 秒 |
| 超过 4 秒不变的时长占比 | 83% | 9% | ≤ 15% |
| 前 3 秒画面变化 | 0 次 | 2 次 | ≥ 2 次 |
| 响度 / 真峰值 | −16.1 LUFS / −2.5 dBTP | −13.6 LUFS / −1.3 dBTP | −16~−13 / ≤ −1 |

完整过程见 [实测案例](skills/chatcut-editing-sop/references/case-brow-glabella.md)。

## 三个主题

| 主题 | 适合 | 风格 |
| --- | --- | --- |
| 明快风（默认） | 知识科普、美妆、教程、种草 | 提速、跳推、金黄双层花字、音效卡点、2–4 秒一个画面变化 |
| 暗调文案风 | 观点、商业认知、创业、个人 IP、文案金句 | 真实场景压暗的低调光、宋体 + 手写体、红金点睛、1.0× 慢节奏留白；纯黑只用于黑场字卡、居中圆形聚光等插入镜头 |
| 贴纸抠像风 | AI / 产品 / 设计方法论、创作者分享、双语干货、清单教程 | 稳定粗白边人像抠像、淡彩方格纸按章节换底、全息珠光模切贴纸、人物居中↔左偏平滑平移、默认无底部滚动字幕、极简克制音效 |

每个主题都规定了画幅、封面、字体（全部是 ChatCut 可渲染字体）、字幕策略、配色、抠像/调色参数、节奏、转场、声音和 QA 标准。暗调文案风详见 [theme-dark-copywriter.md](skills/chatcut-editing-sop/references/theme-dark-copywriter.md)，贴纸抠像风详见 [theme-sticker-collage.md](skills/chatcut-editing-sop/references/theme-sticker-collage.md)。

## 工作流

```
0 节奏蓝图 → 1 语音粗剪锁轴 → 2 字幕与双层花字 → 3 视觉节奏层 → 4 音效混音 → 5 留存 QA 与交付
```

| 轮次 | 做什么 |
| --- | --- |
| 0 节奏蓝图 | 读转写和画面，定 Hook、章节、每 2–4 秒的视觉节拍，不动时间轴 |
| 1 粗剪锁轴 | 去口癖、重录和长停顿，冷开场，倍速，锁定口播时序 |
| 2 字幕花字 | 单行字幕 + 双层关键词花字，在关键词起音帧入场 |
| 3 视觉节奏层 | 推拉镜头、章节卡、示意图、画中画、B-roll，巡检静态段 |
| 4 音效混音 | 按动画入点配音效，BGM 自动闪避，总线限幅 |
| 5 QA 交付 | 导出、跑留存脚本、逐帧检查字幕区，不达标就回到对应轮次 |

## 安装

把 `skills/chatcut-editing-sop` 整个文件夹放到你的 Agent 读取 Skill 的目录，或直接通过 Gemini CLI 扩展安装：

```bash
# Google Antigravity（全局 / 项目级二选一）
cp -R skills/chatcut-editing-sop ~/.gemini/config/skills/
# 或放到项目根目录 .agents/skills/chatcut-editing-sop/

# Gemini CLI（方式一：直接作为 Extension 安装，自动发现 skills/）
gemini extensions install https://github.com/gnipbao/chatcut-high-retention-edit

# Gemini CLI（方式二：手动复制到 Skills 目录）
cp -R skills/chatcut-editing-sop ~/.gemini/skills/
# 或放到项目根目录 .gemini/skills/chatcut-editing-sop/

# Claude Code
cp -R skills/chatcut-editing-sop ~/.claude/skills/

# 其他支持 Agent Skills (SKILL.md) 的 Agent：放进它的 skills 目录即可
```

Agent 需要已经连上 ChatCut（Desktop MCP，或 Web / Grok Bot 插件）。在 Antigravity / Gemini 环境下已兼容 `chatcut-*` 前缀的配套 Skill 与懒加载 `chatcut_desktop` MCP 调用。

## 使用

对 Agent 说一句就行，例如：

- 「用 ChatCut 把这条口播剪得有网感一点」
- 「按高留存的方式精剪当前项目，测试一下效果」
- 「我只有文稿，先给我四轮剪辑提示词」

只给文稿时，Skill 会输出可以分轮复制给 ChatCut 的提示词；有素材和项目时，直接在 ChatCut 里分轮剪。

### 单独使用留存 QA 脚本

只依赖 `ffmpeg` / `ffprobe`：

```bash
python3 skills/chatcut-editing-sop/scripts/retention_qa.py 成片.mp4 --out qa_report \
  --exempt 23.0-28.7,54.6-61.1   # 可选：示意图/演示定格段不计入静态段
```

输出平均画面变化间隔、最长静态段、静态占比、前 3 秒变化、响度和真峰值，以及一张联系表。
- 明快风（默认）：`--profile bright`（平均 ≤ 3.5 秒、最长静态 ≤ 6 秒、> 4 秒静态占比 ≤ 15%、前 3 秒 ≥ 2 次变化）
- 暗调文案风：`--profile cinematic`（平均 ≤ 4.5 秒、最长静态 ≤ 12 秒、> 6 秒静态占比 ≤ 40%、前 3 秒 ≥ 1 次变化）
- 贴纸抠像风：`--profile sticker`（自动切换贴纸微节拍检测阈值，平均 ≤ 3.5 秒、最长静态 ≤ 9 秒、> 5 秒静态占比 ≤ 25%、前 3 秒 ≥ 1 次变化）

## 实测踩过的坑（已写进 Skill）

- `clean_script` 去口癖会把“额头”的“额”当成语气词删掉，中文稿只压停顿。
- 画中画复用口播原片时，即使静音也会多生成一套字幕叠在主字幕上，画中画要用无音轨副本。
- 改倍速不会自动缩短片段，要自己算时长并重排。
- Quick In 推镜头几帧有运动模糊，封面帧用跳推。
- 字号 0.042 时满 12 个字会被挤成两行，0.039 左右更稳。
- 不加总线限幅时真峰值会过 0 dBTP。

## 目录

```
.
├── gemini-extension.json             # Gemini CLI Extension 清单（自动发现 skills/）
└── skills/chatcut-editing-sop/
    ├── SKILL.md                      # 主流程（兼容 Gemini / Antigravity / Claude / Codex）
    ├── references/
    │   ├── retention-playbook.md     # Hook、视觉节拍、花字、动画音效对照
    │   ├── chatcut-execution.md      # ChatCut 工具用法、Gemini 适配与实测踩坑
    │   ├── design-style.md           # 主题 1：明快风视觉规范与版式
    │   ├── theme-dark-copywriter.md  # 主题 2：暗调文案风
    │   ├── theme-sticker-collage.md  # 主题 3：贴纸抠像风
    │   ├── niche-beauty-health.md    # 美妆/医美/健康垂类规则
    │   ├── prompts.md                # 只有文稿时的分轮提示词（含三主题附加指令）
    │   └── case-brow-glabella.md     # 完整实测案例
    └── scripts/
        └── retention_qa.py           # 留存节奏量化体检（bright / cinematic / sticker）
```

## License

[MIT](LICENSE)
