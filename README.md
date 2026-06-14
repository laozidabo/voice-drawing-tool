# Voice-Controlled Drawing Tool / 语音绘图工具

[English](#english) | [中文](#chinese)

---

<a name="english"></a>

## English

A Chinese voice-controlled drawing application. Speak commands in Chinese to create shapes, scenes, and artwork on a canvas. Runs fully offline using faster-whisper speech recognition with pinyin-based fuzzy matching for robust command parsing.

### Demo

Demo video: [bilibili](https://www.bilibili.com/video/BV_PLACEHOLDER) | [GitHub Release](https://github.com/laozidabo/voice-drawing-tool/releases/download/v1.0.0/demo.mp4)

### Quick Start

```bash
pip install -r requirements.txt

# System dependencies (Arch Linux)
sudo pacman -S portaudio noto-fonts-cjk

# Web UI (browser-based speech or type commands)
python -m voice_drawing_tool

# With server-side mic (auto-detected if available)
python -m voice_drawing_tool --speech
```

Open http://localhost:5000 in your browser.

### Features

- **Offline Speech Recognition**: faster-whisper base model (~142MB), fully local
- **Pinyin Fuzzy Matching**: Homophone correction via edit distance (e.g. "元" → "圆")
- **30+ Chinese Voice Commands**: Shapes, colors, positions, scenes, animations
- **Scene Templates**: Single command draws complete scenes (house, tree, sun, car, flower, mountain, smiley)
- **Grid & Zone Positioning**: 5×5 grid (A1-E5), 9-zone positions, directional offsets
- **Multi-Command Pipeline**: Chain commands with "和" / "然后"
- **Undo/Redo**: Up to 100 states with full history stack
- **Animations**: Rain, snow, fireworks, aurora, bubbles, starfall, sparkle, magic circle, fireflies, growing flower/tree
- **Web UI + Desktop GUI**: Flask web interface with browser Web Speech API, or OpenCV desktop window
- **CJK Text Rendering**: PIL + Noto CJK font for Chinese text on canvas

### Voice Commands

| Category | Examples |
|----------|----------|
| Shapes | 画圆, 画正方形, 画三角形, 画五角星, 画椭圆, 画线, 画圆环, 画六边形, 画菱形 |
| Color+Shape | 红圆, 蓝方, 绿三角, 黄星, 紫圆环 |
| Positioning | 左上角, 正中间, 右下角, 画红圆在B3, 往右画圆 |
| Scenes | 画房子, 画树, 画车, 画太阳, 画小花, 画山, 画笑脸 |
| Animations | 下雨, 下雪, 烟花, 极光, 气泡, 流星, 萤火虫, 魔法阵, 开花, 长树, 停止动画 |
| Styles | 填充, 空心, 粗一点, 细一点 |
| Operations | 撤销, 重做, 清空, 保存, 帮助, 退出 |
| Advanced | 弧线, 曲线(贝塞尔), 渐变矩形, 画流程图, 重复, 再画一个 |

### Design Document / Design Notes

#### Planned Command Capabilities

| Category | Planned | Implemented | Notes |
|----------|---------|-------------|-------|
| Basic shapes (circle, square, triangle, star, ellipse, line, ring, hexagon, diamond, polygon, arrow, rounded rect) | 12 | 12 | All implemented |
| Color support (20+ named colors, difflib fuzzy matching) | ✓ | ✓ | COLOR_MAP with fuzzy name resolution |
| Positioning (9-zone grid, 5×5 grid A1-E5, directional offsets, absolute coordinates) | ✓ | ✓ | Resolved via `_find_position()` |
| Scene templates (house, tree, car, sun, flower, mountain, smiley, flowchart) | 8 | 8 | CompositeCommand decomposition |
| Animations (rain, snow, fireworks, aurora, bubbles, starfall, sparkle, magic circle, fireflies, grow flower, grow tree) | 11 | 11 | Full AnimationManager system |
| Multi-command (and/then chaining) | ✓ | ✓ | `_parse_multi()` splits on and/then |
| Undo/Redo | ✓ | ✓ | 100-state history stack |
| Speech recognition (faster-whisper offline) | ✓ | ✓ | base model, int8 quantization |
| Pinyin fuzzy matching (homophone correction) | ✓ | ✓ | `pinyin_matcher.py` with edit distance |
| Speech error correction (Whisper hallucination fixes) | ✓ | ✓ | `_SPEECH_FIX_MAP` + `_dedup_whisper_text` |
| Google Speech API fallback | ✓ | ✓ | Optional, requires network |
| Arc / Bezier curve / Gradient rect | 3 | 3 | Late addition, full support |
| Web UI | ✓ | ✓ | Flask + Socket.IO + inline JS |
| Desktop GUI (OpenCV) | ✓ | ✓ | Via `VoiceDrawingApp` |
| Text rendering (CJK via PIL) | ✓ | ✓ | Noto CJK / SourceHanSerif font |
| Cursor move / Shape move & scale | ✓ | ✓ | `MoveCursorCommand`, `MoveLastCommand`, `ScaleLastCommand` |
| Repeat last command with variation | ✓ | ✓ | `RepeatLastWithVariationCommand` |
| Save/Load | ✓ | ✓ | PNG export, auto-save to /tmp |
| Voice feedback (TTS via pyttsx3) | ✓ | ✓ | Optional, async thread |
| Scene description (natural language) | ✓ | ✓ | `SceneDescriptionCommand` decomposes "左边一棵树右边一座山" |
| Background color | ✓ | ✓ | `SetBackgroundCommand` |

#### Issues Encountered & Resolutions

| Issue | Root Cause | Resolution |
|-------|-----------|------------|
| Simple commands not recognized | Whisper confidence threshold too strict (`-1.5`) | Relaxed to `-2.5` + fixed `_is_garbage` to keep drawing keywords |
| Speech completely undetected | SOCKS proxy env var broke httpx; `speech_recognition`/`pyaudio` not installed | Cleared proxy in `_init_whisper()`; uncommented deps in `requirements.txt` |
| Speech loop not starting | Only started with `--speech` flag, users didn't know | Auto-detect mic and start loop automatically |
| "你好" misparsed as confirm | `'好': 'confirm'` in `_ZH_EN_MAP` | Removed overspecific mapping |
| No-coordinate commands failed regex | `_parse_single` patterns required coords | Added 10 short-form patterns without coordinate requirement |
| Whisper hallucination artifacts | Repeated phrases, homophone errors | `_dedup_whisper_text` + expanded fix maps |

#### Unfinished / Known Limitations

| Feature | Status | Reason |
|---------|--------|--------|
| Multi-turn conversation context | Not implemented | Scope limitation; commands are stateless per utterance |
| Continuous dictation mode | Not implemented | Drawing domain is command-based, not free-form text |
| GPU acceleration for Whisper | Not tested | Relies on `device="auto"`; CPU-only env for compatibility |
| Real-time streaming transcription | Not implemented | `phrase_time_limit=6` gives ~6s latency; streaming would need WebSocket audio |
| Shape selection / editing (select existing shape, move/resize by voice) | Partial | `MoveLastCommand` / `ScaleLastCommand` works for last shape only |
| SVG export | Partial | PNG export only; SVG stub exists but embeds base64 PNG |
| Multi-language support (English commands) | Not planned | Chinese-first design; English in internal pipeline only |
| Mobile browser microphone | Not tested | Web Speech API varies by mobile browser |
| Model download behind proxy | Works after fix | Clears SOCKS proxy env var before loading |

---

<a name="chinese"></a>

## 中文

AI 语音绘图工具 — 用中文语音指令在画布上绘图。基于 faster-whisper 离线语音识别 + 拼音模糊匹配，全程无需网络。

### 快速开始

```bash
pip install -r requirements.txt

# 系统依赖
sudo pacman -S portaudio noto-fonts-cjk

# 启动 Web 界面（浏览器语音识别或打字输入）
python -m voice_drawing_tool

# 启用服务端麦克风
python -m voice_drawing_tool --speech
```

打开浏览器访问 http://localhost:5000

### 功能特性

- **离线语音识别**：faster-whisper base 模型（~142MB），本地运行
- **拼音模糊匹配**：同音字自动纠错（如 "元" → "圆"）
- **30+ 中文语音指令**：形状、颜色、位置、场景、动画
- **场景模板**：一句话画出完整场景（房子、树、太阳、车、花、山、笑脸）
- **网格 & 区域定位**：5×5 网格（A1-E5）、九宫格位置、方向偏移
- **多指令串联**：用"和"/"然后"连接多个指令
- **撤销/重做**：最多 100 步历史记录
- **动画效果**：下雨、下雪、烟花、极光、气泡、流星、萤火虫、魔法阵、开花、长树
- **Web UI + 桌面 GUI**：Flask Web 界面 + OpenCV 桌面窗口
- **中文文字渲染**：PIL + Noto CJK 字体

### 语音指令一览

| 分类 | 示例 |
|------|------|
| 基本形状 | 画圆、画正方形、画三角形、画五角星、画椭圆、画线、画圆环、画六边形、画菱形 |
| 颜色+形状 | 红圆、蓝方、绿三角、黄星、紫圆环 |
| 位置 | 左上角、正中间、右下角、画红圆在B3、往右画圆 |
| 场景 | 画房子、画树、画车、画太阳、画小花、画山、画笑脸 |
| 动画 | 下雨、下雪、烟花、极光、气泡、流星、萤火虫、魔法阵、开花、长树、停止动画 |
| 样式 | 填充、空心、粗一点、细一点 |
| 操作 | 撤销、重做、清空、保存、帮助、退出 |
| 高级 | 弧线、曲线(贝塞尔)、渐变矩形、画流程图、重复、再画一个 |

### 设计文档

#### 指令能力规划 vs 实现

| 类别 | 规划 | 实现 | 说明 |
|------|------|------|------|
| 基本形状（圆、方、三角、星、椭圆、线、环、六边、菱、箭头、圆角矩形） | 12 | 12 | 全部完成 |
| 颜色（20+ 颜色名，difflib 模糊匹配） | ✓ | ✓ | COLOR_MAP + resolve_color() |
| 定位（九宫格、5×5网格、方向偏移、绝对坐标） | ✓ | ✓ | `_find_position()` 统一解析 |
| 场景模板（房子、树、太阳、车、花、山、笑脸、流程图） | 8 | 8 | CompositeCommand 场景分解 |
| 动画（雨雪烟花极光气泡流星萤火虫魔法阵开花长树） | 11 | 11 | AnimationManager 完整系统 |
| 多指令串联（and/then） | ✓ | ✓ | `_parse_multi()` 拆分 |
| 撤销/重做 | ✓ | ✓ | 100 步历史栈 |
| 语音识别（faster-whisper 离线） | ✓ | ✓ | base 模型 int8 量化 |
| 拼音模糊匹配（同音字纠错） | ✓ | ✓ | `pinyin_matcher.py` 编辑距离 |
| 语音纠错（Whisper 幻觉修复） | ✓ | ✓ | `_SPEECH_FIX_MAP` + `_dedup_whisper_text` |
| Google 语音回退 | ✓ | ✓ | 可选，需网络 |
| 弧线 / 贝塞尔曲线 / 渐变矩形 | 3 | 3 | 后期追加，完整支持 |
| Web UI | ✓ | ✓ | Flask + Socket.IO |
| 桌面 GUI（OpenCV） | ✓ | ✓ | `VoiceDrawingApp` |
| 中文文字渲染（PIL + CJK字体） | ✓ | ✓ | Noto CJK / SourceHanSerif |
| 光标移动 / 图形移动缩放 | ✓ | ✓ | MoveCursorCommand / MoveLastCommand / ScaleLastCommand |
| 重复上次命令（带变体） | ✓ | ✓ | RepeatLastWithVariationCommand |
| 保存 | ✓ | ✓ | PNG 导出，自动保存到 /tmp |
| 语音反馈（TTS） | ✓ | ✓ | pyttsx3 异步播报 |
| 场景描述（自然语言） | ✓ | ✓ | "左边一棵树右边一座山" 分解为多步绘图 |
| 背景颜色 | ✓ | ✓ | SetBackgroundCommand |

#### 已解决问题

| 问题 | 根因 | 解决方式 |
|------|------|----------|
| 简单指令无法识别 | Whisper 置信度阈值过严（`-1.5`） | 放宽至 `-2.5`；`_is_garbage` 加入绘图关键词白名单 |
| 完全检测不到语音 | SOCKS 代理阻塞 httpx；`speech_recognition`/`pyaudio` 未安装 | `_init_whisper()` 清除代理变量；取消 `requirements.txt` 注释 |
| 语音循环不启动 | 仅 `--speech` 模式启动，用户不知道此参数 | 自动检测麦克风并启动 |
| "你好"被误解析为确认 | `'好': 'confirm'` 映射过于宽泛 | 移除该映射 |
| 无坐标指令正则匹配失败 | `_parse_single` 模式要求坐标 | 新增 10 条无坐标简写模式 |
| Whisper 幻觉产物 | 重复短语、同音错字 | `_dedup_whisper_text` + 扩充纠错映射表 |

#### 未完成 & 已知限制

| 功能 | 状态 | 原因 |
|------|------|------|
| 多轮对话上下文 | 未实现 | 指令设计为无状态单句，非对话式 |
| 连续听写模式 | 未实现 | 绘图领域基于指令而非自由文本 |
| GPU 加速 | 未测试 | `device="auto"` 自动选择；兼容性优先 |
| 实时流式转录 | 未实现 | `phrase_time_limit=6` 约 6s 延迟；流式需 WebSocket 音频 |
| 图形选择/编辑（选中已有图形，语音移动/缩放） | 部分 | `MoveLastCommand`/`ScaleLastCommand` 仅对最后图形有效 |
| SVG 导出 | 部分 | 仅 PNG 导出；SVG 存根存在但嵌入 base64 PNG |
| 多语言支持（英文指令） | 未规划 | 中文优先设计；英文仅存在于内部解析管道 |
| 移动端浏览器麦克风 | 未测试 | Web Speech API 兼容性因浏览器而异 |
| 代理环境下模型下载 | 已修复 | 加载前清除 SOCKS 代理环境变量 |

### 工程架构

```
src/voice_drawing_tool/
├── __main__.py        # 入口：Web UI（默认）或桌面 GUI
├── core.py            # DrawingCanvas（画布）、SpeechRecognizer（语音识别）、VoiceDrawingApp（桌面主循环）
├── commands.py        # CommandParser（30+ 正则模式）、30+ Command 子类、_ZH_EN_MAP（中英翻译）、_SPEECH_FIX_MAP（纠错）
├── animation.py       # Animation 基类 + 12 种粒子/特效动画（雨雪烟花极光气泡流星萤火虫魔法阵开花长树）
├── pinyin_matcher.py  # 拼音模糊匹配：编辑距离同音字纠错
├── web_server.py      # WebApp：Flask + Socket.IO 服务器，REST API，WebSocket 状态广播
├── templates/         # index.html（Web UI 前端，内联 JS，Web Speech API）
└── static/            # style.css、socket.io.min.js
```

### 数据流

```
麦克风/浏览器 → SpeechRecognizer → CommandParser.parse_command()
  → fix_speech_text() → zh_to_en() → _parse_single() / _fuzzy_fallback()
    → Command.execute(canvas) → 画布更新 → WebSocket/HTTP 推送
```

### 注意事项

- **CJK 字体**：中文文字渲染需要 Noto CJK 字体
- **第一次运行**：faster-whisper 自动下载 base 模型（~142MB）
- **端口**：默认 5000，`--port 8080` 可修改
- **调试**：`--debug` 输出语音识别详细日志

### License / 许可证

Part of the Qiniu Cloud 2026 competition (题目二：AI 语音绘图工具) project by laozidabo.
