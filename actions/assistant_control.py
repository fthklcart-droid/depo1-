"""Tools that act on the assistant itself."""

TOOL = {
    "name": "shutdown_assistant",
    "description": "Shut the assistant down. Call when the user says goodbye or asks you to quit, in any language.",
    "parameters": {"type": "object", "properties": {}},
}


def run(params, ctx):
    ctx.shutdown()
    return "Shutting down after this reply."
