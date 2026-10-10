"""Small precise helpers the model is bad at doing in its head."""
import base64
import hashlib
import json
import re
import secrets
import string
import uuid
import datetime as dt

TOOL = {
    "name": "utilities",
    "description": "Exact helpers: password (length, symbols), uuid, hash (text, algo md5|sha1|sha256), base64_encode, base64_decode, json_format (text), regex_test (pattern, text), random_int (low, high), dice (sides, count), word_count (text), timestamp (value: unix seconds or ISO).",
    "parameters": {"type": "object", "properties": {
        "action": {"type": "string", "enum": ["password", "uuid", "hash", "base64_encode", "base64_decode", "json_format",
                                               "regex_test", "random_int", "dice", "word_count", "timestamp"]},
        "text": {"type": "string"}, "pattern": {"type": "string"}, "algo": {"type": "string"}, "length": {"type": "integer"},
        "symbols": {"type": "boolean"}, "low": {"type": "integer"}, "high": {"type": "integer"}, "sides": {"type": "integer"},
        "count": {"type": "integer"}, "value": {"type": "string"}}, "required": ["action"]},
}


def run(p, ctx):
    a, t = p["action"], p.get("text", "")
    if a == "password":
        alphabet = string.ascii_letters + string.digits + ("!@#$%^&*-_=+" if p.get("symbols", True) else "")
        n = max(8, min(int(p.get("length", 20)), 128))
        while True:
            pw = "".join(secrets.choice(alphabet) for _ in range(n))
            if any(c.islower() for c in pw) and any(c.isupper() for c in pw) and any(c.isdigit() for c in pw):
                return pw
    if a == "uuid":
        return str(uuid.uuid4())
    if a == "hash":
        algo = p.get("algo", "sha256").lower()
        if algo not in ("md5", "sha1", "sha256", "sha512"):
            return "algo must be md5, sha1, sha256 or sha512"
        return hashlib.new(algo, t.encode()).hexdigest()
    if a == "base64_encode":
        return base64.b64encode(t.encode()).decode()
    if a == "base64_decode":
        try:
            return base64.b64decode(t, validate=True).decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            return "Not valid base64."
    if a == "json_format":
        try:
            return json.dumps(json.loads(t), indent=2, ensure_ascii=False)
        except ValueError as e:
            return f"Invalid JSON: {e}"
    if a == "regex_test":
        try:
            ms = [m.group(0) for m in re.finditer(p["pattern"], t)]
        except re.error as e:
            return f"Bad pattern: {e}"
        return f"{len(ms)} matches: {ms[:20]}"
    if a == "random_int":
        lo, hi = int(p.get("low", 1)), int(p.get("high", 100))
        return str(secrets.randbelow(hi - lo + 1) + lo) if hi >= lo else "high must be >= low"
    if a == "dice":
        sides, n = max(2, int(p.get("sides", 6))), max(1, min(int(p.get("count", 1)), 100))
        rolls = [secrets.randbelow(sides) + 1 for _ in range(n)]
        return f"{rolls} total {sum(rolls)}"
    if a == "word_count":
        return f"{len(t.split())} words, {len(t)} characters, {len([l for l in t.splitlines() if l.strip()])} lines"
    if a == "timestamp":
        v = p.get("value", "")
        try:
            if re.fullmatch(r"-?\d+(\.\d+)?", v):
                return dt.datetime.fromtimestamp(float(v), dt.timezone.utc).isoformat()
            return str(int(dt.datetime.fromisoformat(v).timestamp()))
        except (ValueError, OSError, OverflowError):
            return "Could not convert that value."
    return "Unknown action"
