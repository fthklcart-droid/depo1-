"""Copy this file, rename it (no leading underscore), and JARVIS learns a new skill on next launch."""

TOOL = {
    "name": "hello_plugin",
    "description": "Example skill. Replace with what your skill does.",
    "parameters": {
        "type": "object",
        "properties": {"name": {"type": "string", "description": "Who to greet"}},
        "required": ["name"],
    },
}


def run(params, ctx):
    return f"Hello, {params['name']}!"
