# 语音控制绘图工具 - 架构设计文档

## 1. 项目概述

### 1.1 项目定位
纯语音控制的绘图工具，用户只能通过语音指令完成绘图创作，不能使用鼠标或键盘。  
对应的比赛议题：七牛云 2026 校招季 · 实战议题五"语音控制电脑"。

### 1.2 核心能力
- 语音指令解析与执行
- 多图形绘制（圆形、矩形、三角形、椭圆、星形、多边形、直线、文本）
- 填充与轮廓模式
- 颜色、线宽设置
- 撤消与重做
- 场景分解（如"画一座房子"自动分解为多个基本图形）
- 画布导出（PNG 格式）

---

## 2. 系统架构

```
┌──────────────────────────────────────────────────────────┐
│  ┌──────────────┐    ┌──────────────┐                    │
│  │  Speech In   │    │  Keyboard In │  ← 输入层          │
│  └──────┬───────┘    └──────┬───────┘                    │
│         │                   │                            │
│         ▼                   ▼                            │
│  ┌─────────────────────────────────────┐                 │
│  │        VoiceDrawingApp              │  ← 控制层       │
│  │  (主循环, 队列调度, 窗口管理)       │                 │
│  └──────┬──────────────────────┬───────┘                 │
│         │                      │                         │
│         ▼                      ▼                         │
│  ┌──────────────┐    ┌──────────────┐                    │
│  │ CommandParser│    │  DrawingCanvas│  ← 核心层        │
│  │ (NLP 解析)   │    │  (OpenCV 绘图)│                    │
│  └──────┬───────┘    └──────────────┘                    │
│         │                                                │
│         ▼                                                │
│  ┌─────────────────────────────────────┐                 │
│  │  Command 模式 (命令对象)            │  ← 命令层       │
│  │  DrawCircle, DrawLine, ...          │                 │
│  └─────────────────────────────────────┘                 │
└──────────────────────────────────────────────────────────┘
```

### 2.1 层次说明

| 层次 | 模块 | 职责 |
|------|------|------|
| 输入层 | SpeechRecognizer | 接收语音输入（支持 real/stub 两种模式） |
| 控制层 | VoiceDrawingApp | 主循环、消息队列、窗口显示、键盘回退 |
| 核心层 | CommandParser | 自然语言指令→命令对象（含场景分解） |
| 核心层 | DrawingCanvas | OpenCV 画布、历史栈、撤销/重做 |
| 命令层 | Command 子类 | 每个具体命令封装 execute + 描述 |

---

## 3. 模块设计

### 3.1 commands.py — 命令解析与命令对象

#### 3.1.1 命令基类
```
Command (ABC)
├── execute(canvas) -> str          # 执行绘图操作
└── get_description() -> str        # 返回人类可读命令描述
```

#### 3.1.2 命令对象一览
| 命令类 | 对应语音指令示例 | 参数 |
|--------|------------------|------|
| DrawCircleCommand | "draw red circle at 200,200 radius 50" | x, y, radius, color, width |
| DrawFilledCircleCommand | "draw filled red circle at 200,200 radius 50" | x, y, radius, color |
| DrawEllipseCommand | "draw orange ellipse at 300,200 rx 80 ry 50" | x, y, rx, ry, color, width |
| DrawLineCommand | "draw blue line from 100,100 to 300,300" | x1, y1, x2, y2, color, width |
| DrawRectangleCommand | "draw green rectangle from 50,50 to 200,200" | x1, y1, x2, y2, color, width, filled |
| DrawTriangleCommand | "draw purple triangle with points 200,100 100,200 300,200" | points, color, width, filled |
| DrawStarCommand | "draw gold star at 400,300 radius 60" | x, y, r, points, color, width |
| DrawPolygonCommand | "draw red polygon with points 100,50 200,100 150,200 50,150" | points, color, width, filled |
| DrawSquareCommand | "draw red square at 400,300 side 200" | x, y, side, color, width, filled |
| DrawRingCommand | "draw red ring at 300,300 outer 60 inner 30" | x, y, radius, inner, color, width |
| DrawRegularPolygonCommand | "draw green hexagon at 400,300 radius 80" | cx, cy, radius, sides, color, width, filled |
| DrawArrowLineCommand | "draw black arrow line from 100,300 to 700,300" | x1, y1, x2, y2, color, width |
| DrawRoundedRectCommand | "draw blue rounded rect from 300,50 to 500,120" | x1, y1, x2, y2, radius, color, width, filled |
| DrawDiamondCommand | "draw black diamond at 400,300 rx 100 ry 60" | cx, cy, rx, ry, color, width, filled |
| DrawTextCommand | "write Hello at 50,50" | x, y, text, size, color |
| SetColorCommand | "set color to blue" | color |
| SetWidthCommand | "set width to 5" | width |
| ClearCanvasCommand | "clear canvas" | — |
| UndoCommand | "undo" | — |
| RedoCommand | "redo" | — |
| SaveCommand | "save drawing.png" | filename |
| SetBackgroundCommand | "set background to gray" | color |
| MoveLastCommand | "shape move right 100" | dx, dy |
| ScaleLastCommand | "shape bigger 2 times" | factor |
| MoveCursorCommand | "cursor move right 50" | dx, dy |
| SetCursorCommand | "cursor set to 400,300" | x, y |
| ConfirmCommand | "confirm" | — |
| CompositeCommand | "draw a house" (场景分解) | commands[], description |

#### 3.1.3 命令解析器 (CommandParser)
**正则模式匹配流程：**
1. 尝试场景分解（"draw a house" → CompositeCommand）
2. 按注册顺序尝试正则匹配
3. 匹配成功后构造对应 Command 对象

**容错设计：**
- `resolve_color()`: 颜色名称模糊匹配（difflib.get_close_matches，cutoff=0.6）
- 多格式支持：`(100, 200)` / `x=100, y=200` / `100, 200` 均有效
- 场景别名映射：`house/hut/cottage/cabin` → house

**定位系统：**
- 3×3 九宫格：左上角/上中/右上角/左中/正中间/右中/左下角/下中/右下角
- 5×5 网格：A1-E5（字母+数字），如"画红圆在B3"
- 偏移修饰：偏左/偏右/偏上/偏下（从基准位置偏移 50px）
- 光标：始终显示灰色十字准星，画图后自动跟随

#### 3.1.4 场景分解 (CommandDecomposer)
将高级指令分解为多个基本指令的组合：
- `"draw a house"` → 棕色矩形(墙体) + 红色三角形(屋顶) + 黄色圆(窗户) + 蓝色矩形(门)
- `"draw a car"` → 蓝色矩形(车身) + 黑色矩形(车顶) + 黑色圆×2(车轮)
- `"draw a tree"` → 棕色矩形(树干) + 绿色圆(树冠)

### 3.2 core.py — 核心应用

#### 3.2.1 DrawingCanvas
OpenCV 画布封装，核心数据结构：

```
DrawingCanvas
├── image: np.ndarray (800×600×3, uint8)
├── pen_color: tuple (BGR)
├── pen_width: int
├── history: List[np.ndarray]    # 撤销栈
└── redo_stack: List[np.ndarray] # 重做栈
```

**关键方法：**
- draw_circle / draw_line / draw_rectangle / draw_ellipse / draw_polygon / draw_star / draw_text
- clear(), undo(), redo(), save(), get_preview()

**撤消/重做机制：**
每次修改前调用 `_save_state()` 将当前 image 快照压入 history 栈，undo 时将 history 弹出恢复到 image，同时将旧状态推入 redo_stack。

#### 3.2.2 SpeechRecognizer
- 支持 real 模式：`speech_recognition` + Google STT API（需网络）
- 支持 stub 模式：无麦克风时返回 None，可配合键盘输入

#### 3.2.3 VoiceDrawingApp
**主循环结构：**
```
while running:
  1. 处理命令队列 (cmd_queue)
  2. 获取画布预览 (带反馈文字)
  3. imshow 刷新窗口
  4. 键盘事件处理 (Esc 退出, u 撤销, r 重做)
```

**语音线程：**
若启用 `--speech`，启动独立线程持续监听麦克风，识别结果送入 cmd_queue。

**键盘回退模式：**
即使无麦克风，用户也可通过 stdin 输入指令调试。

### 3.3 数据流
```
[麦克风/键盘]
     │
     ▼
[VoiceDrawingApp.cmd_queue]
     │
     ▼
[CommandParser.parse_command(text)]
     │ (返回 Command 对象)
     ▼
[Command.execute(canvas)]
     │ (内部调用 canvas.draw_xxx, 自动保存历史)
     ▼
[更新显示 ← canvas.get_preview()]
     │
     ▼
[cv2.imshow 刷新窗口]
```

---

## 4. 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 绘图引擎 | OpenCV | 内置窗口系统、高性能、丰富的图形 API |
| 命令模式 | Command Pattern | 便于撤销/重做、日志记录、组合 |
| NLP 策略 | 正则 + 模糊匹配 | 轻量无依赖、可预测、适合有限指令集 |
| 颜色解析 | difflib 模糊匹配 | 容错"red"→"read"、"blue"→"ble" 等发音近似错误 |
| 历史栈 | 完整帧快照 | 实现简单、撤销操作 O(1)；代价是内存（每帧 ~1.4MB） |
| 语音识别 | speechrecognition + Google STT | 免费、精度高、支持中文 |
| 包结构 | Python 包 (__init__ + __main__) | 可通过 `python -m voice_drawing_tool` 直接运行 |

---

## 5. 项目结构
```
voice-drawing-tool/
├── src/
│   └── voice_drawing_tool/
│       ├── __init__.py          # 包导出
│       ├── __main__.py          # 入口 (支持交互式命令行)
│       ├── commands.py          # 命令解析器 + 全部命令类
│       └── core.py              # 画布、语音识别、主应用
├── test_voice_drawing.py        # 单元测试 (23 项)
├── demo.py                      # 功能演示脚本
├── requirements.txt             # 依赖清单
├── ARCHITECTURE.md              # 本文件
└── README.md                    # 项目简介
```

---

## 6. 测试策略

| 测试类别 | 范围 | 测试方式 |
|---------|------|---------|
| 单元测试 | 命令解析、画布操作、撤销重做 | `python test_voice_drawing.py` |
| 功能演示 | 完整流程（无麦克风） | `python demo.py` |
| 交互测试 | 键盘回退模式 | `python -m voice_drawing_tool` |

测试覆盖：
- 全部 10 种基本命令的解析与执行
- 颜色模糊匹配
- 场景分解（house/tree/car/sun/mountain）
- 撤销/重做机制
- 画布状态管理
- 未识别命令的容错

---

## 7. 未来改进

1. **语音识别**：启用 `speech_recognition` + `pyaudio` 实现真实语音输入，支持中文
2. **NLP 增强**：引入 spaCy/NLTK 进行更灵活的句法分析
3. **画布增强**：多图层、渐变填充、曲线拟合（贝塞尔）
4. **语音反馈**：使用 pyttsx3 或 gTTS 播报执行结果
5. **GUI 增强**：显示指令历史、颜色选择面板、光标位置指示器
6. **手势支持**：结合 MediaPipe 实现手写/手势辅助输入
