# Voice-Controlled Drawing Tool (语音绘图工具)

A Chinese voice-controlled drawing application. Speak commands in Chinese to create shapes, scenes, and artwork on an 800x600 canvas. Runs fully offline using Whisper speech recognition with pinyin-based fuzzy matching for robust command parsing.

## Features

- **Offline Speech Recognition**: Uses [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (small model, ~460MB) for fully local, offline Chinese speech recognition -- no internet required
- **Pinyin Fuzzy Matching**: Automatically corrects homophone errors (e.g. "元" to "圆") using pinyin distance matching
- **Chinese Voice Commands**: All commands are in Chinese -- say shapes, colors, positions, and actions naturally
- **Scene Templates**: Single voice commands draw complete scenes (house, tree, car, sun, mountain, flower, smiley face, flowcharts)
- **Grid Positioning**: Place shapes using a 5x5 grid (A1-E5) or 9-zone positions (left-top, center, right-bottom, etc.)
- **Multi-Command Support**: Chain commands with "和" (and) or "然后" (then)
- **Undo/Redo**: Full undo/redo history (up to 100 states)

## Installation

```bash
pip install -r requirements.txt
```

System dependencies (for microphone access):

```bash
# Arch Linux
sudo pacman -S portaudio

# Ubuntu/Debian
sudo apt-get install python3-dev portaudio19-dev

# macOS
brew install portaudio
```

A Chinese-capable font is required for rendering Chinese text on the canvas. The tool looks for:
- `/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc`
- `/home/suki/.local/share/fonts/zhcn/SourceHanSerifSC-Regular.otf`

Install Noto CJK fonts if missing:
```bash
# Arch Linux
sudo pacman -S noto-fonts-cjk

# Ubuntu/Debian
sudo apt-get install fonts-noto-cjk
```

## Usage

```bash
# With GUI (default)
python -m voice_drawing_tool

# Headless mode (no window)
python -m voice_drawing_tool --no-gui

# With debug output
python -m voice_drawing_tool --debug
```

You can also type commands directly into the terminal -- keyboard input works alongside voice.

## Voice Commands

All commands are spoken in Chinese. Below are the main categories.

### Basic Shapes
| Command | Description |
|---------|-------------|
| 画圆 / 画一个圆 | Draw a circle |
| 画正方形 | Draw a square |
| 画长方形 | Draw a rectangle |
| 画三角形 | Draw a triangle |
| 画五角星 | Draw a star |
| 画椭圆 | Draw an ellipse |
| 画线 | Draw a line |
| 画圆环 | Draw a ring |
| 画六边形 | Draw a hexagon |
| 画菱形 | Draw a diamond |

### Color + Shape (Shorthand)
| Command | Description |
|---------|-------------|
| 红圆 | Red circle |
| 蓝方 | Blue square |
| 绿三角 | Green triangle |
| 黄星 | Yellow star |
| 紫圆环 | Purple ring |

### Positioning
| Command | Description |
|---------|-------------|
| 左上角 / 左上 | Top-left area |
| 上中 | Top-center |
| 右上角 / 右上 | Top-right area |
| 左中 | Middle-left |
| 正中间 / 居中 | Center (400, 300) |
| 右中 | Middle-right |
| 左下角 / 左下 | Bottom-left area |
| 下中 | Bottom-center |
| 右下角 / 右下 | Bottom-right area |
| 画红圆在B3 | Place at grid cell B3 (A1-E5) |
| 往右画圆 | Offset 50px to the right |
| 往上画蓝圆 | Offset 50px upward |

### Scenes
| Command | Description |
|---------|-------------|
| 画房子 | Draw a house (body, roof, window, door) |
| 画树 | Draw a tree (trunk, crown) |
| 画车 | Draw a car (body, roof, wheels) |
| 画太阳 | Draw a sun |
| 画小花 | Draw a flower (petals, stem) |
| 画山 | Draw mountains |
| 画笑脸 | Draw a smiley face |
| 画流程图 | Draw a flowchart |

### Multi-Command
- 红圆和蓝方 -- Draw red circle and blue square
- 画红圆然后画绿圆在左边 -- Draw red circle then green circle on the left

### Styles
| Command | Description |
|---------|-------------|
| 填充 | Filled shape |
| 空心 | Hollow shape |
| 粗一点 | Thicker lines (width 6) |
| 细一点 | Thinner lines (width 2) |

### Operations
| Command | Description |
|---------|-------------|
| 撤销 / 不对 / 错了 | Undo last action |
| 重做 | Redo |
| 清空 | Clear canvas (requires confirmation) |
| 保存 | Save drawing to `drawing.png` |
| 帮助 | Show help overlay |
| 退出 | Exit (requires confirmation) |

### Repeat
After drawing a shape, say 再画一个 / 再来一个 / 重复 to repeat the last command.

## Keyboard Controls

Type any command directly into the terminal. Keyboard and voice input share the same command queue.

## Technical Details

### Speech Recognition Pipeline
1. **faster-whisper** (primary): Local Whisper small model with int8 quantization. Uses an initial prompt of drawing-domain vocabulary to improve accuracy. Anti-hallucination filters remove repeated phrases and apply common error corrections.
2. **Google Speech API** (fallback, optional): Requires internet and `speechrecognition` + `pyaudio` packages.
3. **Noise filtering**: Garbage utterances (< 2 chars, repeated characters, common filler words) are discarded before command parsing.

### Command Parsing Pipeline
1. **Speech error correction**: Common misrecognitions are fixed (e.g. "话" to "画", "园" to "圆")
2. **Pinyin fuzzy matching**: Unknown Chinese words are matched to known commands by pinyin edit distance
3. **Chinese-to-English translation**: Chinese text is translated to internal English representation
4. **Regex pattern matching**: Exact and fuzzy regex patterns match shapes and parameters
5. **Scene decomposition**: Scene keywords (房子, 树, etc.) expand to multi-shape composite commands

### Canvas
- 800x600 pixel canvas rendered with OpenCV
- Chinese text rendering via PIL + Noto CJK font
- Real-time cursor crosshair with color indicator
- Top bar: title, last command, current color/width
- Bottom bar: listening status, feedback text, cursor position
- Subtle 5x5 grid overlay with 9-zone position labels

## Troubleshooting

### No microphone detected / PyAudio errors
Ensure `portaudio` is installed at the system level, then reinstall pyaudio:
```bash
pip install --force-reinstall pyaudio
```

### Whisper model download fails
The first run downloads the `small` model (~460MB). If it fails, check your internet connection or pre-download:

```bash
python -c "from faster_whisper import WhisperModel; WhisperModel('small', device='auto', compute_type='int8')"
```
### Chinese characters not rendering on canvas
Install a CJK font:
```bash
# Arch Linux
sudo pacman -S noto-fonts-cjk
# Ubuntu/Debian
sudo apt-get install fonts-noto-cjk
```
The tool looks for `NotoSansCJK-Regular.ttc` in `/usr/share/fonts/noto-cjk/`.

### Commands not recognized
- Speak clearly in Chinese
- Use simple, direct commands: 红圆, 画房子, 撤销
- Say 帮助 to see all available commands
- Check debug output: `python -m voice_drawing_tool --debug`
- Common Whisper fixes are applied automatically (e.g. "画三角行" becomes "画三角形")

### GUI window not opening
If running in a headless environment (SSH, container, WSL without display), use:
```bash
python -m voice_drawing_tool --no-gui
```

## License

Part of the Qiniu Cloud 2026 competition project by Suki.
