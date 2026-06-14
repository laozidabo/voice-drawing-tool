# AGENTS.md

## Quick start

```bash
# Install (pip, no venv activation needed if venv/ exists)
pip install -r requirements.txt

# Run tests (custom runner, not pytest discovery)
python test_voice_drawing.py

# Run the app (GUI, requires display)
python -m voice_drawing_tool

# Headless / debug
python -m voice_drawing_tool --no-gui
python -m voice_drawing_tool --debug
```

## Architecture

Single Python package at `src/voice_drawing_tool/` with 4 modules:

| Module | Role |
|--------|------|
| `commands.py` | Command pattern: parser + all Command subclasses + scene decomposition + Chinese→English translation maps |
| `core.py` | `DrawingCanvas` (OpenCV 800x600 BGR image), `SpeechRecognizer` (faster-whisper primary, Google fallback), `VoiceDrawingApp` (main loop) |
| `animation.py` | Particle-based animations (rain, snow, fireworks, aurora, etc.) rendered on canvas overlay |
| `pinyin_matcher.py` | Pinyin fuzzy matching for Chinese homophone correction |

Entry point: `__main__.py` → `VoiceDrawingApp.run()`.

## Key conventions

- **Colors are BGR** (OpenCV convention): `red = (0, 0, 255)`, `blue = (255, 0, 0)`, `green = (0, 255, 0)`. See `COLOR_MAP` in `commands.py:318`.
- **All user-facing commands are Chinese**. English equivalents are internal only, produced by `zh_to_en()` translation.
- **Speech error correction**: `fix_speech_text()` in `commands.py:262` fixes common Whisper misrecognitions before parsing. `_dedup_whisper_text()` in `core.py:599` handles Whisper hallucination repeats.
- **Command parsing pipeline**: Chinese text → `fix_speech_text()` → `zh_to_en()` → regex matching → Command object. Pinyin fuzzy matching (`pinyin_matcher.py`) runs as a fallback for unknown Chinese words.
- **Canvas history**: Full-frame snapshots (each ~1.4MB). `max_history = 100`. `_save_state()` before every draw call.
- **GUI requires main thread** (Linux OpenCV requirement). Speech and stdin run in daemon threads.
- **CJK font**: Required for Chinese text rendering. Lookup order defined in `core.py:32`. Falls back to OpenCV `putText` (ASCII only) if no font found.

## Testing

Tests use plain `assert` statements with a manual runner (no pytest fixtures). Run with:

```bash
python test_voice_drawing.py
```

23 tests covering: canvas state, draw operations, command parsing (shapes, colors, undo/redo, scenes, unrecognized), save/load.

## Adding a new command

1. Add Chinese→English mapping in `_ZH_EN_MAP` (`commands.py:30`)
2. Add regex pattern to `CommandParser._patterns` (search for `_patterns` in `commands.py`)
3. Create a `Command` subclass with `execute(canvas) -> str` and `get_description() -> str`
4. If it's a scene, add a `SceneTemplate` list and register in `CommandDecomposer.templates`

## System dependencies

- `portaudio` (system package) for microphone access
- CJK font (e.g., `noto-fonts-cjk`) for Chinese text on canvas
- faster-whisper downloads ~460MB model on first run
