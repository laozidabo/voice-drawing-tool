"""Web UI 后端 — Flask + WebSocket 语音绘图服务器"""

import io
import time
import threading
import base64
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
    COLOR_MAP,
)


class WebApp:
    """Flask Web UI 包装器，复用现有 DrawingCanvas / CommandParser 逻辑。"""

    def __init__(self, use_speech: bool = False):
        self.canvas = DrawingCanvas()
        self.parser = CommandParser()
        self.recognizer = SpeechRecognizer() if use_speech else None
        self.cmd_count = 0
        self.session_start = time.time()
        self.last_feedback = ""
        self.last_speech_text = ""
        self.running = True
        self._pending_confirm = None
        self._pending_confirm_time = 0.0

        self.flask_app = Flask(
            __name__,
            template_folder="templates",
            static_folder="static",
        )
        self.flask_app.config["SECRET_KEY"] = "voice-drawing-tool"
        self.socketio = SocketIO(self.flask_app, cors_allowed_origins="*", async_mode="threading")

        self._register_routes()
        self._start_animation_loop()
        if use_speech:
            self._start_speech_loop()

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
            _, buf = cv2.imencode(".png", img)
            return send_file(io.BytesIO(buf.tobytes()), mimetype="image/png")

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
            if not text:
                return jsonify({"ok": False, "feedback": "空指令"})
            result = self._execute_command(text)
            return jsonify(result)

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
            if text:
                result = self._execute_command(text)
                sio.emit("command_result", result)

    # ── Command execution ───────────────────────────────────────────────

    def _execute_command(self, text: str) -> dict:
        text_lower = text.lower().strip()
        if text_lower in ("exit", "quit", "退出"):
            return {"ok": False, "feedback": "Web 模式下无法退出，请关闭浏览器"}

        cmd = self.parser.parse_command(text, self.canvas.cursor_x, self.canvas.cursor_y)
        if cmd is None:
            from .commands import fix_speech_text, zh_to_en
            fixed = fix_speech_text(text)
            en = zh_to_en(fixed)
            self._set_feedback(f"⚠ {text[:30]} → 未识别")
            return {"ok": False, "feedback": f"⚠ 未识别: {text[:30]}", "translated": en}

        if isinstance(cmd, ClearCanvasCommand):
            self.canvas.clear()
            self.cmd_count += 1
            self._set_feedback("✓ 画布已清空")
            self._broadcast_state()
            return {"ok": True, "feedback": "✓ 画布已清空"}

        result = cmd.execute(self.canvas)
        self.cmd_count += 1
        self.last_speech_text = text

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
            self.canvas.cursor_x = max(0, min(799, self.canvas.cursor_x + cmd.dx))
            self.canvas.cursor_y = max(0, min(599, self.canvas.cursor_y + cmd.dy))
        elif isinstance(cmd, SetCursorCommand):
            self.canvas.cursor_x = max(0, min(799, cmd.x))
            self.canvas.cursor_y = max(0, min(599, cmd.y))
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

        self._set_feedback(f"✓ {text[:30]} → {result}")
        self._broadcast_state()
        return {"ok": True, "feedback": f"✓ {result}", "description": cmd.get_description()}

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
                    canvas_roi = preview[32:32 + 600, :]
                    self.canvas.anim_mgr.update_and_render(dt, canvas_roi, self.canvas.image)
                    _, buf = cv2.imencode(".png", self.canvas.image)
                    b64 = base64.b64encode(buf.tobytes()).decode("ascii")
                    self.socketio.emit("canvas_update", {"image": b64})
                time.sleep(0.033)

        t = threading.Thread(target=loop, daemon=True)
        t.start()

    def _start_speech_loop(self):
        def loop():
            while self.running:
                if not self.recognizer:
                    time.sleep(0.1)
                    continue
                texts = self.recognizer.listen_with_alternatives()
                if texts:
                    best = texts[0].strip().rstrip("。，！？；：,.!?;:")
                    self.last_speech_text = best
                    self.socketio.emit("speech", {"text": best})
                    cmd = self.parser.parse_command(best, self.canvas.cursor_x, self.canvas.cursor_y)
                    if cmd:
                        result = self._execute_command(best)
                        self.socketio.emit("command_result", result)
                time.sleep(0.1)

        t = threading.Thread(target=loop, daemon=True)
        t.start()

    def run(self, host: str = "0.0.0.0", port: int = 5000):
        print(f"\n{'=' * 50}")
        print(f"  🎤 语音绘图工具 - Web UI")
        print(f"  http://localhost:{port}")
        print(f"{'=' * 50}\n")
        self.socketio.run(self.flask_app, host=host, port=port, allow_unsafe_werkzeug=True)
