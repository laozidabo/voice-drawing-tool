import sys
import threading
import time as _time


def main():
    if "--web" in sys.argv:
        from .web_server import WebApp
        use_speech = "--speech" in sys.argv
        app = WebApp(use_speech=use_speech)
        port = 5000
        for i, arg in enumerate(sys.argv):
            if arg == "--port" and i + 1 < len(sys.argv):
                port = int(sys.argv[i + 1])
        app.run(port=port)
        return

    from .core import VoiceDrawingApp
    gui = None if "--no-gui" not in sys.argv else False
    app = VoiceDrawingApp(use_speech=True, gui=gui)
    app.running = True

    print("=" * 50)
    print("  语音控制绘图工具 (Voice Drawing Tool)")
    print("=" * 50)
    print("说 'help' 查看可用指令")
    print("说 'exit' 或 'quit' 退出")
    print()

    # GUI 需要在主线程运行（Linux OpenCV 要求）
    try:
        app.run()
    except KeyboardInterrupt:
        pass

    app.running = False
    print("已退出")


if __name__ == "__main__":
    main()
