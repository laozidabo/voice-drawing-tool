import sys
import threading
import time as _time
from .core import VoiceDrawingApp


def main():
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
