# ChatCut 执行与验收

工具名以当前连接的实时定义为准。Desktop 时间轴用成片帧（`startFrame`、`durationFrames`），素材偏移是整数微秒（`sourceIn`）；Web 常用 `fromFrame`、`durationInFrames`、秒单位的源偏移。条目、资产、轨道 ID 一律从工具结果取。

## 选择连接与项目

- 沿用用户指定的连接。Desktop：`get_active_project`；没有或不确定时 `list_projects` → `target_project` → `read_project`。Web/Codex 插件先读 `chatcut-plugin-basics`。
- 素材卡显示 `desktopRegistered:false`、`inspect_asset` 报“no readable local source”时，说明原片没有关联本机文件，取帧和导出都会失败：在磁盘上找到原片（`mdfind -name <文件名>`），用 `push_asset` 重新注册，新时间轴改用新的资产 ID（会自动转写）。背景音乐同理，可用项目里已注册的 `extracted-audio` 资产替代。
- 同名或多个项目无法唯一判断时再问用户。原片是本地文件且项目里没有时，用 Desktop `push_asset` 注册，等转写完成（`track_progress target=transcription wait`）。
- **版本化**：项目已有成片时，用 `manage_timelines action=duplicate`（或 `create` 新时间轴再把原片放上去）开新版本，命名 `v2 高留存` 之类，旧时间轴不动，便于对比。从原片重剪时，新时间轴先放一条完整原片，再走 Script。
- 记录 `projectId` / `timelineId`，每轮开始前确认没有切走。

## 第 0 轮 · 蓝图取证

- `read_script` 读全稿（新时间轴上需先有原片）。`inspect_asset sourceFrameCount: 12` 看人物取景、手势、背景色调。
- 需要精确源时间时用 `inspect_asset transcriptRanges` 或 `find_transcript asset=<id>`。

## 第 1 轮 · 粗剪与锁轴

1. `clean_script`（默认去 `呃/额` 并压停顿到 250ms）。之后**必须重新** `read_script`，用新内容做语义编辑。
   - **中文陷阱（实测）**：`clean_script` 的口癖匹配按单字，会把“额头、额外、金额、名额”里的“额”也删掉（美容稿里“额头”被删成“头”）。先在 `read_script` 全文里搜“额”“呃”：只要“额”出现在词语里，就用 `clean_script only="silence"`，真正的语气词改在 Script 里逐个 `~~额~~`。误删后无法撤回，只能删掉口播片段、重新放入完整原片再剪。
2. 在 `timeline.md` 里：删失败起句和重复论证（`~~...~~` 或删行）；冷开场 = 在正文前插入一条库里的 Hook 原句行（裸 `[sN]` 行，必要时用 `~~` 修掉首尾多余词）；整段重排就移动行。不要改写或补充原话。
3. `apply_script`；校验失败时按诊断修正后再提交。提交后重读，检查听感：缺主语、指代断裂、接得太硬。
4. 变速（实测）：Desktop 字段是 `playbackRate`，`audioPitchMode` 默认 `preservePitch`。改倍速**不会**自动缩短条目，必须同时把每段 `durationFrames` 改为 `floor(源时长秒 × 30 / 倍速)`，并按顺序重排 `startFrame` 首尾相接，否则会多吃后面的源素材或留空隙。先用脚本算好全部片段，再一次性批量 `updates`。其余要点：看 `edit_item` 契约里的速度/保音调字段，先对一段试，确认相邻片段仍首尾相接、无重叠、无黑帧。Script 重建的片段较多时，速度要对所有口播片段统一设置。
5. 用 `preview_timeline views=["timeline","transcript"]` 读回：片段源区间、倍速、口播末帧、Hook/章节/重点词帧位。`find_transcript`（不带 asset）返回成片帧，用于后续锚点。

## 第 2 轮 · 字幕与花字

- `read_captions` → `edit_captions action=template` 列出预设，选干净的中文样式；或 `enable` 后用 `style` 合并字号、描边、位置。中文每行 ≤12 字，必要时 `split_card`/`merge_cards`。字幕 Card 的时间是微秒。
- 逐词出现用 `style.reveal {"mode":"progressive","unit":"word"}`；关键词着色用 `activeToken`。
- 字号与换行（实测）：`fontSize` 0.042 时，满 12 个字会超出 918px 宽的字幕框被挤成两行，看起来像两条字幕叠在一起。用 0.039 左右，个别仍换行的卡手动 `split_card` / `merge_cards`。
- 两个口播片段的源区间有几毫秒重叠时，交界处的字会重复（如“为为什么”），用 `set_card_text` 修正显示文字。
- 交付前把导出片的字幕区按每秒约 1.5 帧截图、拼成大图看一遍：检查是否单行、有无重影、有无压到画中画或花字（`ffmpeg -vf "fps=1.5,crop=1080:200:0:1360,scale=360:-1,tile=4x18"`）。
- ChatCut 升级后 MCP 工具可能要求显式传 `projectId`（报错 “projectId is required”），每次调用都带上即可。
- 双层花字：用 `create-motion-graphics` 做一个可复用的“上下两层关键词” MG（上层文字、下层文字、颜色、入场方式都是可编辑属性），每次放置只改属性；放置用 `edit_item adds:[{type:"motion-graphic", assetId, startFrame, durationFrames, left/top/width/height}]`。先放一个、看合成帧，再批量。
- 花字区默认在人物胸口上方/字幕上方（竖屏约 y 1080–1400），不压嘴和下巴。

## 第 3 轮 · 视觉节奏层

**推拉镜头**（`browse_library category=zoom` 可看预设）：

```json
{"type":"pixel-effect","assetId":"builtin:effect-zoom","targetItemId":"<口播片段>",
 "startFrame":<可选，片段内局部范围>,"durationFrames":<可选>,
 "propertyOverrides":{"magnification":1.15,"shape":"instant","direction":"in",
   "focalPointY":0.34,"easeInDurationInSeconds":0,"easeOutDurationInSeconds":0}}
```

- `shape`：`instant`（跳推）、`spring-focused`（Quick In/Out，`easeIn/OutDurationInSeconds` 控制速度）、`slow-push` / `slow-pull`（持续缓推拉）。
- 片段被 Script 拆成多段时，在每段上交替“无推/推近”，即可形成跳切 + 推拉节奏；一段内需要局部推近就用 `startFrame/durationFrames`。
- `spring-focused`（Quick In）带速度相关的运动模糊，入场头几帧会糊：**第 0 帧（封面帧）和花字入场帧不要用 Quick In**，开头用 `instant`；Quick In 放在句中强调处。
- 放大前看源画面：人物头顶余量小时 `magnification` ≤1.15，`focalPointY` 跟随眼睛高度（约 0.30–0.38）。

**章节卡与转场**：章卡 MG（可编辑编号与标题）放在顶部安全区（y≈120–220），持续到下一章；换章用 `browse_library category=transitions`（Flash、Clean Line Wipe、Luma Blend）或短扫光 MG。`pixel-transition` 只能放在相邻条目之间。

**示意图 / 整屏卡片**：用 `create-motion-graphics`；部位示意图通常是整屏不透明 MG + 内嵌口播小窗：口播小窗继承源区间与倍速，`borderRadius` 24–36。

**画中画会重复生成字幕（实测踩坑）**：画中画复用口播原片时，即使设了 `muted:true`，ChatCut 也会为它的联动音频再生成一整套字幕，和主字幕叠在同一位置，看起来就是字幕重影。新版本里这套多余的字幕还会锁住整条字幕（编辑时报 “Caption projection conflicts”）。正确做法是**画中画一律用无音轨副本**：

```bash
ffmpeg -i 原片.mp4 -an -c:v copy 原片-画中画无音轨.mp4   # 只复制视频流，画质不变、几秒完成
```

然后 `push_asset` 注册，画中画都用这个资产。放好画中画后用 `read_captions` 检查 `tracks` 只有口播这一条；如果已经出现第二条，删除画中画也清不掉残留卡，只能新建时间轴重新搭。

**抠像破框 / 文字在人物后**：复制口播片段到上层轨，加 `{"type":"pixel-effect","assetId":"builtin:effect-ai-portrait-matte","targetItemId":"<复制层>"}`；大字 MG 放在原口播层与抠像层之间。首次使用会下载模型并生成蒙版缓存，先在短段验证头发和手的边缘。不稳定时退回圆形/圆角窗。

**B-roll**：优先项目内素材；需要外部素材用 `search_stock_media` → 下载 → `push_asset`。竖屏用 `fit:"cover"` 前先比较长宽比（见 talking-head-guide 的 b-roll 规则）。补镜静音。

每次批量放置后，用 `preview_timeline viewerFrames=[...]` 一次看 10–20 个关键帧（入场前一帧、定格帧、退场帧）。

## 第 4 轮 · 音效与混音

- `browse_library category=sound-effects query="typing"` 等找音效；放置 `{"type":"audio","assetId":"library:sound:<id>","fromFrame":<动画首帧>}`，`fromFrame` 是编辑锚点，工具会对齐音头。音效放独立轨。
- 背景音乐放独立轨：`edit_track action=update` 口播轨 `{"audioDucking":{"role":"anchor"}}`、音乐轨 `{"audioDucking":{"role":"follower"}}`；音乐基础增益保持自然，淡入淡出用帧数字段（Desktop：`fadeInDurationFrames`/`fadeOutDurationFrames`），裁到内容末帧。
- 口播片段之间的接缝：`smooth_audio trackIds=[口播轨] crossfadeDurationFrames=2`。
- 总线限幅：`{"type":"audio-effect","assetId":"builtin:audio-effect-limiter","target":"master","propertyOverrides":{"ceilingDb":-1.5}}`。它限的是采样峰值，真峰值会比 ceiling 高约 0.5 dB，所以 ceiling 取 −1.5 才能让真峰值 ≤ −1 dBTP（实测：不加时真峰值 +0.1 dBTP，加上后为 −1.3）。
- 放在条目局部范围内的效果，`edit_item` 返回的 `startFrame` 是**相对条目起点**的帧；传入时用时间轴帧即可。
- `split_item` 会把遮罩效果一起切开，但切出来的效果带了局部范围，再用 `updates` 改 `mask` 会报 “Mask requires targetItemId for one complete … clip”。要给切出的片段换遮罩（如人像遮罩改圆形聚光），先 `deletes` 旧效果，再 `adds` 一个 `targetItemId` 指向新片段的遮罩。
- 切分片段或改字幕分页后，字幕 Card ID 会变；之前用 `set_card_style` 隐藏的卡样式会保留，但后续编辑要重新 `read_captions` 取 ID（用 `fromFrame/toFrame` 小范围读，整轨读一次输出很大）。

## 第 5 轮 · 导出与 QA

- `export format=video resolution=1080p timelineId=<新版>` → `track_progress target=export action=wait`。
- 运行本 Skill 的 `scripts/retention_qa.py <导出文件>`，看报告和联系表；与旧版成片（如有）同样跑一次做对比。
- WARN 处理：静态段 → 在该段语义点补推拉/花字/示意图；前 3 秒不足 → 首帧大字 + 0.8–1.5 秒处跳推；响度偏低 → 提升口播轨增益或检查音乐闪避；真峰值过高 → 降低音效。
- 交付：项目、时间轴、成片路径、QA 数据、未验证项（例如没有实际试听、抠像边缘需人工看）。
