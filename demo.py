import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from voice_drawing_tool.core import DrawingCanvas
from voice_drawing_tool.commands import CommandParser


def demo_canvas():
    print("=== Canvas Demo ===")
    c = DrawingCanvas()
    c.draw_circle(200, 200, 50)
    c.draw_line(100, 100, 300, 300)
    c.draw_rectangle(50, 50, 200, 200)
    c.pen_color = (0, 255, 0)
    c.draw_rectangle(300, 50, 450, 200)
    c.pen_color = (0, 0, 255)
    c.draw_ellipse(400, 400, 80, 50)
    c.draw_star(600, 150, 60, 5)
    c.draw_text(50, 550, "Voice Drawing!")
    c.draw_polygon([100, 450, 200, 420, 250, 480, 150, 500])
    c.save("demo_output.png")
    print("Saved demo_output.png")
    print("✓ Canvas Demo\n")


def demo_parser():
    print("=== Parser Demo ===")
    p = CommandParser()
    tests = [
        "draw red circle at 200,200 radius 50",
        "draw blue line from 100,100 to 300,300",
        "draw green rectangle from 50,50 to 200,200",
        "draw purple triangle with points 200,100 100,200 300,200",
        "draw gold star at 400,300 radius 60",
        "draw orange ellipse at 300,200 rx 80 ry 50",
        "draw filled yellow circle at 500,100 radius 40",
        "write 'Hello' at 50,50",
        "set color to blue",
        "set width to 5",
        "clear canvas",
        "undo",
        "redo",
        "draw a house",
        "draw a tree",
    ]
    for text in tests:
        cmd = p.parse_command(text)
        if cmd:
            print(f"  ✓ {text}")
            print(f"    -> {type(cmd).__name__}: {cmd.get_description()}")
        else:
            print(f"  ✗ {text}")
            print(f"    -> unrecognized")
    print()


def demo_undo():
    print("=== Undo Demo ===")
    c = DrawingCanvas()
    c.draw_circle(200, 200, 50)
    c.draw_rectangle(50, 50, 200, 200)
    print(f"  History size: {len(c.history)}")
    c.undo()
    print(f"  After undo: {len(c.history)}")
    c.redo()
    print(f"  After redo: {len(c.history)}")
    print("✓ Undo Demo\n")


if __name__ == "__main__":
    demo_canvas()
    demo_parser()
    demo_undo()
    print("All demos completed.")
