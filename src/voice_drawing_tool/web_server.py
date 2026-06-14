"""Web UI 后端 — Flask + WebSocket 语音绘图服务器"""

import io
import time
import threading
import base64
from typing import Optional, List
import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO

from .core import DrawingCanvas, SpeechRecognizer
from .commands import (
    CommandParser, ClearCanvasCommand, UndoCommand, RedoCommand,
    SaveCommand, SetColorCommand, SetWidthCommand, SetBackgroundCommand,
    MoveLastCommand, ScaleLastCommand, CompositeCommand,
    MoveCursorCommand, SetCursorCommand,
    fix_speech_text, zh_to_en,
    COLOR_MAP,
)


class WebApp:
    """Flask Web UI 包装器，复用现有 DrawingCanvas / CommandParser 逻辑。"""

    def __init__(self, use_speech: bool = False):
        self.canvas = DrawingCanvas()
        self.parser = CommandParser()
        # 始终初始化 Whisper 模型（浏览器录音需要后端转写）
        self.recognizer = SpeechRecognizer()
        self._whisper_lock = threading.Lock()  # Whisper 不是线程安全的
        self.cmd_count = 0
        self.session_start = time.time()
        self.last_feedback = ""
        self.last_speech_text = ""
        self.running = True
        self._pending_confirm = None
        self._pending_confirm_time = 0.0
        self._fail_count = 0

        self.flask_app = Flask(
            __name__,
            template_folder="templates",
            static_folder="static",
        )
        self.flask_app.config["SECRET_KEY"] = "voice-drawing-tool"
        self.socketio = SocketIO(self.flask_app, cors_allowed_origins="*", async_mode="threading")

        self._register_routes()
        self._start_animation_loop()
        # 服务端麦克风监听（识别到可用 mic 自动启动；--speech 可强制启用）
        if use_speech or (self.recognizer and self.recognizer._use_real):
            self._start_speech_loop()
            if self.recognizer._whisper_available:
                print("[启动] 服务端语音识别已就绪（对着麦克风说话即可）")
            else:
                print("[启动] 麦克风可用但 Whisper 未加载，仅使用浏览器语音识别")
        else:
            print("[启动] 未检测到可用麦克风，请使用浏览器语音识别或输入文字指令")

    # ── Routes ──────────────────────────────────────────────────────────

    def _register_routes(self):
        app = self.flask_app
        sio = self.socketio

        @app.route("/")
        def index():
            return render_template("index.html")

        @app.route("/api/canvas")
        def api_canvas():
            img = self.canvas.image
            _, buf = cv2.imencode(".png", img)
            return send_file(io.BytesIO(buf.tobytes()), mimetype="image/png")

        @app.route("/api/preview")
        def api_preview():
            dt = 0.05
            img = self.canvas.get_preview(
                feedback_text=self.last_feedback,
                is_listening=False,
                cmd_count=self.cmd_count,
                session_duration=time.time() - self.session_start,
                dt=dt,
            )
            _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
            return send_file(io.BytesIO(buf.tobytes()), mimetype="image/jpeg")

        @app.route("/api/state")
        def api_state():
            return jsonify({
                "pen_color": self.canvas.pen_color_name,
                "pen_color_bgr": list(self.canvas.pen_color),
                "pen_width": self.canvas.pen_width,
                "cursor_x": int(self.canvas.cursor_x),
                "cursor_y": int(self.canvas.cursor_y),
                "shape_count": self.canvas._shape_count,
                "cmd_count": self.cmd_count,
                "history_count": len(self.canvas.history),
                "redo_count": len(self.canvas.redo_stack),
                "session_duration": int(time.time() - self.session_start),
                "feedback": self.last_feedback,
                "last_speech": self.last_speech_text,
            })

        @app.route("/api/colors")
        def api_colors():
            colors = []
            for name, bgr in COLOR_MAP.items():
                colors.append({"name": name, "bgr": list(bgr)})
            return jsonify(colors)

        @app.route("/api/command", methods=["POST"])
        def api_command():
            data = request.get_json(force=True)
            text = data.get("text", "").strip()
            candidates = data.get("candidates", [])
            if not text:
                return jsonify({"ok": False, "feedback": "空指令"})
            result = self._execute_command(text, candidates)
            return jsonify(result)

        @app.route("/api/audio", methods=["POST"])
        def api_audio():
            """接收浏览器录制的 PCM 音频，用 Whisper 本地转写。"""
            if not self.recognizer or not self.recognizer._whisper_available:
                return jsonify({"ok": False, "error": "Whisper 模型未加载"})

            # 从 query 参数获取采样率，默认 16000
            sample_rate = int(request.args.get("rate", "16000"))
            audio_data = request.get_data()
            if len(audio_data) < 1000:
                return jsonify({"ok": False, "error": "音频太短"})

            # Whisper 转写（加锁，模型不是线程安全的）
            # beam_size=1（贪心解码）+ initial_prompt 偏置，绘图命令精度足够
            with self._whisper_lock:
                results = self.recognizer._transcribe_whisper(audio_data, sample_rate)
            if not results:
                return jsonify({"ok": True, "texts": [], "feedback": "未识别到语音"})

            texts = [r["text"] for r in results]
            # 选出能解析的最佳候选
            best = self._pick_best_transcript(texts)
            if best:
                result = self._execute_command(best, texts)
                return jsonify({"ok": True, "texts": texts, "best": best, "result": result})
            else:
                return jsonify({"ok": True, "texts": texts, "best": None, "feedback": f"未识别: {texts[0][:20]}"})

        @app.route("/api/undo", methods=["POST"])
        def api_undo():
            ok = self.canvas.undo()
            if ok:
                self.cmd_count += 1
                self._set_feedback("↩ 已撤销")
                self._broadcast_state()
                return jsonify({"ok": True, "feedback": "↩ 已撤销"})
            return jsonify({"ok": False, "feedback": "没有可撤销的操作"})

        @app.route("/api/redo", methods=["POST"])
        def api_redo():
            ok = self.canvas.redo()
            if ok:
                self.cmd_count += 1
                self._set_feedback("↪ 已重做")
                self._broadcast_state()
                return jsonify({"ok": True, "feedback": "↪ 已重做"})
            return jsonify({"ok": False, "feedback": "没有可重做的操作"})

        @app.route("/api/clear", methods=["POST"])
        def api_clear():
            self.canvas.clear()
            self.cmd_count += 1
            self._set_feedback("✓ 画布已清空")
            self._broadcast_state()
            return jsonify({"ok": True, "feedback": "✓ 画布已清空"})

        @app.route("/api/save", methods=["POST"])
        def api_save():
            path = "/tmp/voice_drawing_web.png"
            self.canvas.save(path)
            self._set_feedback(f"✓ 已保存到 {path}")
            return jsonify({"ok": True, "feedback": f"✓ 已保存到 {path}", "path": path})

        @app.route("/api/download")
        def api_download():
            _, buf = cv2.imencode(".png", self.canvas.image)
            return send_file(
                io.BytesIO(buf.tobytes()),
                mimetype="image/png",
                as_attachment=True,
                download_name="drawing.png",
            )

        @app.route("/api/export_svg")
        def api_export_svg():
            """导出 SVG 文件（画布内容嵌入为 base64 PNG）。"""
            import base64 as b64
            _, buf = cv2.imencode(".png", self.canvas.image)
            png_b64 = b64.b64encode(buf.tobytes()).decode("ascii")
            w, h = self.canvas.WIDTH, self.canvas.HEIGHT
            svg = (
                f'<?xml version="1.0" encoding="UTF-8"?>\n'
                f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'xmlns:xlink="http://www.w3.org/1999/xlink" '
                f'width="{w}" height="{h}" viewBox="0 0 {w} {h}">\n'
                f'  <title>语音绘图 - Voice Drawing</title>\n'
                f'  <image width="{w}" height="{h}" '
                f'href="data:image/png;base64,{png_b64}"/>\n'
                f'</svg>'
            )
            return send_file(
                io.BytesIO(svg.encode("utf-8")),
                mimetype="image/svg+xml",
                as_attachment=True,
                download_name="drawing.svg",
            )

        @app.route("/api/set_color", methods=["POST"])
        def api_set_color():
            data = request.get_json(force=True)
            name = data.get("color", "red")
            from .commands import resolve_color
            self.canvas.pen_color = resolve_color(name)
            self.canvas.pen_color_name = name
            self._set_feedback(f"🎨 颜色: {name}")
            self._broadcast_state()
            return jsonify({"ok": True})

        @app.route("/api/set_width", methods=["POST"])
        def api_set_width():
            data = request.get_json(force=True)
            w = int(data.get("width", 2))
            self.canvas.pen_width = max(1, min(20, w))
            self._set_feedback(f"✏ 线宽: {self.canvas.pen_width}")
            self._broadcast_state()
            return jsonify({"ok": True})

        # ── WebSocket ──

        @sio.on("connect")
        def on_connect():
            self._emit_full_state()

        @sio.on("command")
        def on_command(data):
            text = data.get("text", "").strip()
            candidates = data.get("candidates", [])
            if text:
                result = self._execute_command(text, candidates)
                sio.emit("command_result", result)

    # ── Command execution ───────────────────────────────────────────────

    def _pick_best_transcript(self, candidates: List[str]) -> Optional[str]:
        """遍历候选列表，返回第一个能成功解析的文本。"""
        for t in candidates:
            cleaned = t.strip().rstrip('。，！？；：,.!?;:')
            if not cleaned:
                continue
            cmd = self.parser.parse_command(cleaned,
                                            self.canvas.cursor_x,
                                            self.canvas.cursor_y)
            if cmd is not None:
                return cleaned
        # 所有原始文本都解析失败时，尝试 fix_speech_text 修正后重试
        if candidates:
            from .commands import fix_speech_text, zh_to_en
            t = candidates[0].strip().rstrip('。，！？；：,.!?;:')
            fixed = fix_speech_text(t)
            if fixed != t:
                cmd = self.parser.parse_command(fixed,
                                                self.canvas.cursor_x,
                                                self.canvas.cursor_y)
                if cmd is not None:
                    return fixed
            # 最后尝试：直接英文翻译 + 模糊匹配
            en = zh_to_en(fixed)
            cmd = self.parser.parse_command(en,
                                            self.canvas.cursor_x,
                                            self.canvas.cursor_y)
            if cmd is not None:
                return en
        return None

    def _get_suggestion(self, text: str) -> str:
        """为未识别的指令提供建议。"""
        text_lower = text.lower().strip()
        shape_suggestions = {
            '圆': '试试: 画圆 / 红圆 / 画一个圆',
            '圈': '试试: 画圆 / 画圆环',
            '方': '试试: 画正方形 / 画长方形',
            '三': '试试: 画三角形',
            '星': '试试: 画五角星',
            '线': '试试: 画线 / 画直线',
            '房': '试试: 画房子',
            '树': '试试: 画树',
            '车': '试试: 画车',
            '花': '试试: 画小花',
            '太阳': '试试: 画太阳',
            '山': '试试: 画山',
            '红': '试试: 红圆 / 红方',
            '蓝': '试试: 蓝圆 / 蓝方',
            '绿': '试试: 绿圆 / 绿方',
            '撤销': '试试: 撤销',
            '重做': '试试: 重做',
            '清空': '试试: 清空',
            '保存': '试试: 保存',
        }
        for keyword, suggestion in shape_suggestions.items():
            if keyword in text:
                return suggestion
        if text_lower.startswith('画'):
            return '试试: 画圆 / 画方 / 画三角形 / 画房子'
        return ""

    def _execute_command(self, text: str, candidates: Optional[List[str]] = None) -> dict:
        text_lower = text.lower().strip()
        if text_lower in ("exit", "quit", "退出"):
            return {"ok": False, "feedback": "Web 模式下无法退出，请关闭浏览器"}

        # 如果有多个候选，选第一个能解析的
        chosen = text
        if candidates and len(candidates) > 1:
            best = self._pick_best_transcript(candidates)
            if best:
                chosen = best

        cmd = self.parser.parse_command(chosen, self.canvas.cursor_x, self.canvas.cursor_y)
        if cmd is None:
            fixed = fix_speech_text(chosen)
            en = zh_to_en(fixed)
            suggestion = self._get_suggestion(chosen)
            self._fail_count += 1

            if self._fail_count >= 3:
                msg = f"⚠ 连续未识别，试试简单指令: 画圆 / 红圆 / 画房子"
                self._fail_count = 0
            elif suggestion:
                msg = f"⚠ 未识别: {chosen[:20]}，{suggestion}"
            else:
                msg = f"⚠ 未识别: {chosen[:20]}"

            self._set_feedback(msg)
            return {"ok": False, "feedback": msg, "translated": en}

        # 解析成功，重置失败计数
        self._fail_count = 0

        if isinstance(cmd, ClearCanvasCommand):
            self.canvas.clear()
            self.cmd_count += 1
            self._set_feedback("✓ 画布已清空")
            self._broadcast_state()
            return {"ok": True, "feedback": "✓ 画布已清空", "cmd_count": self.cmd_count}

        result = cmd.execute(self.canvas)
        self.cmd_count += 1
        self.last_speech_text = chosen

        if isinstance(cmd, CompositeCommand):
            self.canvas.last_command_type = CompositeCommand
            self.canvas.last_command_params = {
                "sub_commands": [(type(sub), getattr(sub, "params", {})) for sub in cmd.commands],
            }
            if cmd.commands:
                last = cmd.commands[-1]
                for attr in ("x", "cx", "x1"):
                    if hasattr(last, attr):
                        self.canvas.cursor_x = getattr(last, attr)
                        break
                for attr in ("y", "cy", "y1"):
                    if hasattr(last, attr):
                        self.canvas.cursor_y = getattr(last, attr)
                        break
        elif isinstance(cmd, MoveCursorCommand):
            self.canvas.cursor_x = max(0, min(self.canvas.WIDTH - 1, self.canvas.cursor_x + cmd.dx))
            self.canvas.cursor_y = max(0, min(self.canvas.HEIGHT - 1, self.canvas.cursor_y + cmd.dy))
        elif isinstance(cmd, SetCursorCommand):
            self.canvas.cursor_x = max(0, min(self.canvas.WIDTH - 1, cmd.x))
            self.canvas.cursor_y = max(0, min(self.canvas.HEIGHT - 1, cmd.y))
        elif not isinstance(cmd, (
            MoveLastCommand, ScaleLastCommand,
            SetColorCommand, SetWidthCommand, SetBackgroundCommand,
            UndoCommand, RedoCommand, SaveCommand,
            MoveCursorCommand, SetCursorCommand,
        )):
            self.canvas.last_command_type = type(cmd)
            self.canvas.last_command_params = getattr(cmd, "params", {})
            self.canvas._shape_count += 1
            for attr in ("x", "cx", "x1"):
                if hasattr(cmd, attr):
                    self.canvas.cursor_x = getattr(cmd, attr)
                    break
            for attr in ("y", "cy", "y1"):
                if hasattr(cmd, attr):
                    self.canvas.cursor_y = getattr(cmd, attr)
                    break

        self._set_feedback(f"✓ {chosen[:30]} → {result}")
        self._broadcast_state()
        return {"ok": True, "feedback": f"✓ {result}", "description": cmd.get_description(), "cmd_count": self.cmd_count}

    # ── Helpers ─────────────────────────────────────────────────────────

    def _set_feedback(self, text: str):
        self.last_feedback = text

    def _broadcast_state(self):
        self.socketio.emit("state_update", {
            "pen_color": self.canvas.pen_color_name,
            "pen_color_bgr": list(self.canvas.pen_color),
            "pen_width": self.canvas.pen_width,
            "cursor_x": int(self.canvas.cursor_x),
            "cursor_y": int(self.canvas.cursor_y),
            "shape_count": self.canvas._shape_count,
            "cmd_count": self.cmd_count,
            "history_count": len(self.canvas.history),
            "redo_count": len(self.canvas.redo_stack),
            "session_duration": int(time.time() - self.session_start),
            "feedback": self.last_feedback,
        })

    def _emit_full_state(self):
        self._broadcast_state()
        img = self.canvas.image
        _, buf = cv2.imencode(".png", img)
        b64 = base64.b64encode(buf.tobytes()).decode("ascii")
        self.socketio.emit("canvas_update", {"image": b64})

    def _start_animation_loop(self):
        def loop():
            while self.running:
                if self.canvas.anim_mgr.active_count > 0:
                    dt = 0.033
                    preview = self.canvas.get_preview(
                        feedback_text=self.last_feedback,
                        cmd_count=self.cmd_count,
                        session_duration=time.time() - self.session_start,
                        dt=dt,
                    )
                    BAR_H = 44
                    canvas_roi = preview[BAR_H:BAR_H + self.canvas.HEIGHT, :]
                    self.canvas.anim_mgr.update_and_render(dt, canvas_roi, self.canvas.image)
                    _, buf = cv2.imencode(".png", self.canvas.image)
                    b64 = base64.b64encode(buf.tobytes()).decode("ascii")
                    self.socketio.emit("canvas_update", {"image": b64})
                time.sleep(0.033)

        t = threading.Thread(target=loop, daemon=True)
        t.start()

    def _start_speech_loop(self):
        """后端 Whisper 语音识别循环（仅 --speech 模式）。"""
        def loop():
            while self.running:
                if not self.recognizer:
                    time.sleep(0.1)
                    continue
                texts = self.recognizer.listen_with_alternatives()
                if texts:
                    # 遍历所有候选，选第一个能解析的
                    best = self._pick_best_transcript(texts)
                    if best:
                        self.last_speech_text = best
                        self.socketio.emit("speech", {"text": best})
                        result = self._execute_command(best)
                        self.socketio.emit("command_result", result)
                    else:
                        self.last_speech_text = texts[0]
                        self.socketio.emit("speech", {"text": texts[0]})
                time.sleep(0.1)

        t = threading.Thread(target=loop, daemon=True)
        t.start()

    def run(self, host: str = "0.0.0.0", port: int = 5000):
        print(f"\n{'=' * 50}")
        print(f"  🎤 语音绘图工具")
        print(f"  http://localhost:{port}")
        print(f"{'=' * 50}\n")
        self.socketio.run(self.flask_app, host=host, port=port, allow_unsafe_werkzeug=True)
