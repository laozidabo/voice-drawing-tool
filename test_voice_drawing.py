import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import numpy as np
from voice_drawing_tool.commands import (
    CommandParser, DrawCircleCommand, DrawLineCommand, DrawRectangleCommand,
    DrawTriangleCommand, DrawEllipseCommand, DrawStarCommand, DrawTextCommand,
    SetColorCommand, SetWidthCommand, ClearCanvasCommand, UndoCommand, RedoCommand,
    SaveCommand
)
from voice_drawing_tool.core import DrawingCanvas, VoiceDrawingApp


def test_initial_state():
    c = DrawingCanvas()
    assert c.image.shape == (900, 1200, 3), f"wrong shape: {c.image.shape}"
    assert tuple(c.image[0, 0]) == (245, 248, 250), "bg should be off-white"
    assert c.pen_color == (0, 0, 255)
    assert c.pen_width == 2
    print("✓ test_initial_state")


def test_clear():
    c = DrawingCanvas()
    c.draw_circle(200, 200, 50)
    assert len(c.history) == 1
    c.clear()
    assert len(c.history) == 2
    assert tuple(c.image[200, 200]) == (245, 248, 250)
    print("✓ test_clear")


def test_undo_redo():
    c = DrawingCanvas()
    c.draw_circle(200, 200, 50)
    before = c.image.copy()
    c.clear()
    assert not np.array_equal(c.image, before)
    assert c.undo()
    assert np.array_equal(c.image, before)
    assert c.redo()
    assert not np.array_equal(c.image, before)
    assert not c.undo() is False
    print("✓ test_undo_redo")


def test_parse_circle():
    p = CommandParser()
    cmd = p.parse_command("draw red circle at 200, 200 radius 50")
    assert cmd is not None, "should parse circle"
    assert isinstance(cmd, DrawCircleCommand)
    assert cmd.x == 200
    assert cmd.y == 200
    assert cmd.radius == 50
    print("✓ test_parse_circle")


def test_parse_filled_circle():
    p = CommandParser()
    cmd = p.parse_command("draw filled red circle at 300, 400 radius 60")
    assert cmd is not None
    from voice_drawing_tool.commands import DrawFilledCircleCommand
    assert isinstance(cmd, DrawFilledCircleCommand)
    assert cmd.x == 300
    assert cmd.y == 400
    assert cmd.radius == 60
    print("✓ test_parse_filled_circle")


def test_parse_line():
    p = CommandParser()
    cmd = p.parse_command("draw blue line from 100,100 to 300,300")
    assert cmd is not None
    assert isinstance(cmd, DrawLineCommand)
    assert cmd.x1 == 100 and cmd.y1 == 100
    assert cmd.x2 == 300 and cmd.y2 == 300
    print("✓ test_parse_line")


def test_parse_rectangle():
    p = CommandParser()
    cmd = p.parse_command("draw green rectangle from 50,50 to 200,200")
    assert cmd is not None
    assert isinstance(cmd, DrawRectangleCommand)
    assert cmd.x1 == 50 and cmd.y1 == 50
    assert cmd.x2 == 200 and cmd.y2 == 200
    print("✓ test_parse_rectangle")


def test_parse_triangle():
    p = CommandParser()
    cmd = p.parse_command("draw purple triangle with points 200,100 100,200 300,200")
    assert cmd is not None
    assert isinstance(cmd, DrawTriangleCommand)
    print("✓ test_parse_triangle")


def test_parse_star():
    p = CommandParser()
    cmd = p.parse_command("draw gold star at 400,300 radius 60")
    assert cmd is not None
    assert isinstance(cmd, DrawStarCommand)
    assert cmd.x == 400
    assert cmd.y == 300
    assert cmd.r == 60
    print("✓ test_parse_star")


def test_parse_ellipse():
    p = CommandParser()
    cmd = p.parse_command("draw orange ellipse at 300,200 rx 80 ry 50")
    assert cmd is not None
    assert isinstance(cmd, DrawEllipseCommand)
    assert cmd.x == 300 and cmd.y == 200
    assert cmd.rx == 80 and cmd.ry == 50
    print("✓ test_parse_ellipse")


def test_parse_text():
    p = CommandParser()
    cmd = p.parse_command("write 'Hello' at 50,50")
    assert cmd is not None
    assert isinstance(cmd, DrawTextCommand)
    assert cmd.text == 'Hello'
    assert cmd.x == 50 and cmd.y == 50
    print("✓ test_parse_text")


def test_parse_set_color():
    p = CommandParser()
    cmd = p.parse_command("set color to blue")
    assert cmd is not None
    assert isinstance(cmd, SetColorCommand)
    assert cmd.color_name == 'blue'
    print("✓ test_parse_set_color")


def test_parse_set_width():
    p = CommandParser()
    cmd = p.parse_command("set width to 5")
    assert cmd is not None
    assert isinstance(cmd, SetWidthCommand)
    assert cmd.width == 5
    print("✓ test_parse_set_width")


def test_parse_clear():
    p = CommandParser()
    cmd = p.parse_command("clear canvas")
    assert isinstance(cmd, ClearCanvasCommand)
    print("✓ test_parse_clear")


def test_parse_undo_redo():
    p = CommandParser()
    assert isinstance(p.parse_command("undo"), UndoCommand)
    assert isinstance(p.parse_command("redo"), RedoCommand)
    print("✓ test_parse_undo_redo")


def test_execute_commands():
    c = DrawingCanvas()
    p = CommandParser()
    cmd = p.parse_command("draw red circle at 200,200 radius 50")
    r = cmd.execute(c)
    assert "circle" in r
    assert len(c.history) == 1
    cmd2 = p.parse_command("set color to green")
    r = cmd2.execute(c)
    assert c.pen_color == (0, 255, 0)
    print("✓ test_execute_commands")


def test_undo_redo_on_canvas():
    c = DrawingCanvas()
    c.draw_circle(200, 200, 50)
    assert len(c.history) == 1
    c.undo()
    assert len(c.history) == 0
    c.redo()
    assert len(c.history) == 1
    print("✓ test_undo_redo_on_canvas")


def test_save_load():
    c = DrawingCanvas()
    c.draw_circle(200, 200, 50)
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        c.save(f.name)
        assert os.path.getsize(f.name) > 0
        os.unlink(f.name)
    print("✓ test_save_load")


def test_scene_decomposition():
    p = CommandParser()
    cmd = p.parse_command("draw a house")
    assert cmd is not None
    from voice_drawing_tool.commands import CompositeCommand
    assert isinstance(cmd, CompositeCommand)
    print("✓ test_scene_decomposition")


def test_unrecognized_command():
    p = CommandParser()
    cmd = p.parse_command("do something crazy")
    assert cmd is None
    print("✓ test_unrecognized_command")


def test_star_drawing():
    c = DrawingCanvas()
    c.draw_star(400, 300, 80, 5)
    assert len(c.history) == 1
    print("✓ test_star_drawing")


def test_polygon_drawing():
    c = DrawingCanvas()
    c.draw_polygon([100, 50, 200, 100, 150, 200, 50, 150])
    assert len(c.history) == 1
    print("✓ test_polygon_drawing")


def test_text_drawing():
    c = DrawingCanvas()
    c.draw_text(50, 50, "Hello")
    assert len(c.history) == 1
    print("✓ test_text_drawing")


def run_all():
    tests = [
        test_initial_state,
        test_clear,
        test_undo_redo,
        test_parse_circle,
        test_parse_filled_circle,
        test_parse_line,
        test_parse_rectangle,
        test_parse_triangle,
        test_parse_star,
        test_parse_ellipse,
        test_parse_text,
        test_parse_set_color,
        test_parse_set_width,
        test_parse_clear,
        test_parse_undo_redo,
        test_execute_commands,
        test_undo_redo_on_canvas,
        test_save_load,
        test_scene_decomposition,
        test_unrecognized_command,
        test_star_drawing,
        test_polygon_drawing,
        test_text_drawing,
    ]
    for t in tests:
        t()
    print(f"\n✓ All {len(tests)} tests passed!")


if __name__ == "__main__":
    run_all()
