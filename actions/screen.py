"""Look at the screen. The frame travels back with the tool result, so the model answers once."""
import io

from core.result import ToolResult

TOOL = {
    "name": "look_at_screen",
    "description": "Capture the screen so you can see it. You have NO sight without this. Call when asked what is on screen or to read/analyze it. Provide the question in 'text'.",
    "parameters": {"type": "object", "properties": {"text": {"type": "string", "description": "What to look for"}}},
}


def run(params, ctx):
    try:
        from PIL import ImageGrab
    except ImportError:
        return "Screen capture needs Pillow: pip install pillow"
    img = ImageGrab.grab()
    img.thumbnail((1600, 1600))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=80)
    return ToolResult("Screen captured and attached. Answer once, from what you actually see.",
                      image=(buf.getvalue(), "image/jpeg"), source="SCREEN CAPTURE")
