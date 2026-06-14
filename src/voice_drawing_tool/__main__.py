import sys
import webbrowser
import threading


def _check_deps():
    """检查 Web 依赖是否安装，给出友好提示。"""
    missing = []
    for mod in ("flask", "flask_socketio"):
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if missing:
        print("=" * 50)
        print("  ❌ 缺少依赖: " + ", ".join(missing))
        print()
        print("  请先激活虚拟环境并安装依赖:")
        print("    source venv/bin/activate")
        print("    pip install -r requirements.txt")
        print()
        print("  或直接使用 venv 运行:")
        print("    venv/bin/python -m voice_drawing_tool")
        print("=" * 50)
        sys.exit(1)


def main():
    _check_deps()
    from .web_server import WebApp
    use_speech = "--speech" in sys.argv
    port = 5000
    for i, arg in enumerate(sys.argv):
        if arg == "--port" and i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])

    app = WebApp(use_speech=use_speech)

    # 自动打开浏览器
    def _open_browser():
        import time
        time.sleep(1.2)
        webbrowser.open(f"http://localhost:{port}")

    threading.Thread(target=_open_browser, daemon=True).start()
    app.run(port=port)


if __name__ == "__main__":
    main()
