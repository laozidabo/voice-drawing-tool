# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick start

```bash
# Install dependencies (includes faster-whisper ~460MB model on first run)
pip install -r requirements.txt

# Run tests (manual runner, 23 tests)
python test_voice_drawing.py

# Desktop GUI (requires display, OpenCV windows)
python -m voice_drawing_tool

# Web UI (Flask server, open http://localhost:5000)
python -m voice_drawing_tool --web

# With server-side speech (faster-whisper on backend)
python -m voice_drawing_tool --web --speech

# Headless / debug
python -m voice_drawing_tool --no-gui
python -m voice_drawing_tool --debug
```

## Architecture

Single Python package at `src/voice_drawing_tool/` with 7 modules:

| Module | Role |
|--------|------|
| `__main__.py` | Entry point: routes `--web` to `WebApp`, otherwise `VoiceDrawingApp` |
| `core.py` | `DrawingCanvas` (OpenCV 800×600 BGR), `SpeechRecognizer` (faster-whisper + Google fallback), `VoiceDrawingApp` (GUI main loop), CJK font rendering via PIL |
| `commands.py` | Command pattern: `CommandParser` (regex + scene decomposition), 30+ `Command` subclasses, Chinese→English translation (`zh_to_en()`), speech error correction (`fix_speech_text()`), `COLOR_MAP` |
| `animation.py` | `Animation` base class + 12 particle/effect animations (rain, snow, fireworks, aurora, bubbles, starfall, sparkle, magic circle, fireflies, grow flower, grow tree) managed by `AnimationManager` |
| `pinyin_matcher.py` | Pinyin fuzzy matching: `build_pinyin_index()` for known commands, `pinyin_fuzzy_match()` via edit distance for homophone correction |
| `web_server.py` | `WebApp`: Flask + Socket.IO server with REST API (`/api/command`, `/api/state`, `/api/canvas`), WebSocket state broadcast, optional server-side speech loop |
| `static/` + `templates/` | Web UI: `index.html` (inline JS — no Socket.IO dependency), `style.css` (dark theme), `app.js` (legacy Socket.IO client, unbundled), `socket.io.min.js` (local bundle) |

### Data flow (desktop)
```
Mic/Keyboard → SpeechRecognizer / stdin → cmd_queue
  → CommandParser.parse_command() → Command.execute(canvas)
    → canvas.get_preview() → cv2.imshow()
```

### Data flow (web)
```
Browser Web Speech API → POST /api/command
  → WebApp._execute_command() → CommandParser → Command.execute()
    → polling /api/preview & /api/state every 2s
```

## Key conventions

- **Colors are BGR** (OpenCV): `red = (0, 0, 255)`, `blue = (255, 0, 0)`. `COLOR_MAP` at `commands.py:337` has 20 colors + `resolve_color()` with difflib fuzzy matching (cutoff=0.6).
- **All user-facing commands are Chinese**. Internal English is produced by `zh_to_en()` (line ~309), which is a regex-based translation map (`_ZH_EN_MAP` at line 30).
- **Command parsing pipeline**: Chinese text → `fix_speech_text()` (Whisper misrecognition fixes, line 281) → `zh_to_en()` → regex matching → Command object. Pinyin fuzzy matching (`pinyin_matcher.py`) falls back for unknown words.
- **Canvas history**: Full-frame snapshots (800×600×3 = ~1.4MB each). `max_history = 100`. `_save_state()` called before every draw.
- **GUI requires main thread** (Linux OpenCV requirement). Speech and keyboard run in daemon threads.
- **CJK font**: Required for Chinese text rendering via PIL. Lookup order in `core.py:32`. Falls back to `cv2.putText` (ASCII only).
- **Web UI**: Browser-side speech via Web Speech API (no server-side whisper by default). Uses polling (fetch every 2s), not WebSockets for canvas updates. Socket.IO is available server-side but unused by current frontend.
- **Animation rendering**: Animations composite onto a preview overlay; `AnimationManager.update_and_render()` merges finished animations into the permanent canvas.

## Testing

Tests use plain `assert` with a manual runner (no pytest). Run:

```bash
python test_voice_drawing.py
```

23 tests: canvas state (1), draw ops (3), undo/redo (2), command parsing (10: circle, filled circle, line, rect, triangle, star, ellipse, text, set color, set width), clear (1), undo/redo parse (1), execution (1), save/load (1), scene decomposition (1), unrecognized (1), star/polygon/text drawing (3).

## Adding a new command

1. Add Chinese→English mapping to `_ZH_EN_MAP` (`commands.py:30`)
2. Add speech fix entries to `_SPEECH_FIX_MAP` (`commands.py:190`) for common Whisper errors
3. Add regex pattern to `CommandParser._register()` (line 1858)
4. Create a `Command` subclass with `execute(canvas) -> str` and `get_description() -> str`
5. If it's a scene, add a `SceneTemplate` list and register in `CommandDecomposer.templates`
6. If it's an animation, subclass `Animation` in `animation.py` and register in `__init__.py` exports

## Git workflow

- **Branch**: single `main` branch, no PRs
- **Commit style**: [Conventional Commits](https://www.conventionalcommits.org/) — `feat:`, `fix:`, `docs:`, `ui:`
- **Remote**: `https://github.com/laozidabo/voice-drawing-tool.git`

## System dependencies

- `portaudio` (system package) for microphone access with faster-whisper
- CJK font (e.g., `noto-fonts-cjk`) for Chinese text on canvas
- faster-whisper downloads ~460MB model (small, int8) on first run

## Tips for AI agents

- **Grounded edits**: `_ZH_EN_MAP`, `_SPEECH_FIX_MAP`, `_patterns`, and scene templates are all large dicts/lists in `commands.py`. When adding a command, touch all four locations.
- **Web UI vs Desktop**: They share `DrawingCanvas` and `CommandParser` but have separate execution loops. Changes to canvas or parser affect both. Web-specific UI state lives in `WebApp` fields.
- **Chinese number parsing**: `zh_number_to_int()` handles Chinese numerals (一二三…百千万). The regex `_ZH_NUM_PAT` in `zh_to_en()` converts them before command matching.
- **Color resolution**: Use `resolve_color()` not direct `COLOR_MAP` lookup — it includes difflib fuzzy matching for pronunciation errors.
- **Position system**: 9-zone grid (左上角, 正中间, …), 5×5 grid (A1-E5), directional offsets (往右, 往上), and absolute coordinates all converge to `(x, y)` during parsing. See `_ZH_EN_MAP` entries for position keywords.
- **History snapshots are expensive**: Each `_save_state()` copies a 800×600×3 uint8 array. Avoid unnecessary saves; batch operations when possible.
- **The `app.js` in `static/` is legacy** — current frontend uses inline JS in `index.html`. If updating web UI, modify the template, not `app.js`.
