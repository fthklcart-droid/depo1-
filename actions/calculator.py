"""Safe math (AST-evaluated, no eval) and unit conversion."""
import ast
import math
import operator as op

OPS = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv, ast.Pow: op.pow,
       ast.Mod: op.mod, ast.FloorDiv: op.floordiv, ast.USub: op.neg, ast.UAdd: op.pos}
FUNCS = {k: getattr(math, k) for k in ("sqrt", "sin", "cos", "tan", "log", "log10", "exp", "floor", "ceil", "factorial")}
FUNCS.update(abs=abs, round=round, min=min, max=max)
CONSTS = {"pi": math.pi, "e": math.e}

LENGTH = {"m": 1, "km": 1000, "cm": .01, "mm": .001, "mi": 1609.344, "ft": .3048, "in": .0254, "yd": .9144}
MASS = {"kg": 1, "g": .001, "lb": .45359237, "oz": .028349523}
VOLUME = {"l": 1, "ml": .001, "gal": 3.785411784}
TIME = {"s": 1, "min": 60, "h": 3600, "day": 86400}
GROUPS = [LENGTH, MASS, VOLUME, TIME]

TOOLS = []


def _eval(n):
    if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
        return n.value
    if isinstance(n, ast.Name) and n.id in CONSTS:
        return CONSTS[n.id]
    if isinstance(n, ast.BinOp) and type(n.op) in OPS:
        l, r = _eval(n.left), _eval(n.right)
        if isinstance(n.op, ast.Pow) and abs(r) > 1000:
            raise ValueError("exponent too large")
        return OPS[type(n.op)](l, r)
    if isinstance(n, ast.UnaryOp) and type(n.op) in OPS:
        return OPS[type(n.op)](_eval(n.operand))
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in FUNCS and not n.keywords:
        return FUNCS[n.func.id](*[_eval(a) for a in n.args])
    raise ValueError("unsupported expression")


def calc(params, ctx):
    try:
        return str(_eval(ast.parse(params["expression"].strip(), mode="eval").body))
    except ZeroDivisionError:
        return "Division by zero."
    except Exception as e:  # noqa: BLE001
        return f"Cannot evaluate: {e}"


def convert(params, ctx):
    v, f, t = float(params["value"]), params["from_unit"].lower(), params["to_unit"].lower()
    temps = {"c", "f", "k"}
    if f in temps and t in temps:
        c = v if f == "c" else (v - 32) * 5 / 9 if f == "f" else v - 273.15
        return f"{c if t == 'c' else c * 9 / 5 + 32 if t == 'f' else c + 273.15:.4g} {t.upper()}"
    for g in GROUPS:
        if f in g and t in g:
            return f"{v * g[f] / g[t]:.6g} {t}"
    return f"Cannot convert {f} to {t}."


TOOLS = [
    ({"name": "calculate", "description": "Evaluate a math expression exactly (+ - * / ** %, sqrt, sin, log, pi...). Use instead of mental math.",
      "parameters": {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]}}, calc),
    ({"name": "convert_units", "description": "Convert length (m km cm mm mi ft in yd), mass (kg g lb oz), volume (l ml gal), time (s min h day) or temperature (c f k).",
      "parameters": {"type": "object", "properties": {"value": {"type": "number"}, "from_unit": {"type": "string"},
                                                       "to_unit": {"type": "string"}}, "required": ["value", "from_unit", "to_unit"]}}, convert),
]
