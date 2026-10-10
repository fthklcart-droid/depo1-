"""Fast path for everyday commands: no model call, no API key, instant. Anything it does not recognise returns None
and goes to the model as usual. Matching is deliberately strict: a wrong guess costs more than a model call."""
from __future__ import annotations

import datetime as dt
import re

_UNITS = {"dakika": 1, "dk": 1, "saat": 60, "sa": 60}
_OPS = [("çarpı", "*"), ("carpi", "*"), ("kere", "*"), ("artı", "+"), ("arti", "+"), ("eksi", "-"), ("bölü", "/"), ("bolu", "/"), (" x ", "*")]


def norm(text: str) -> str:
    t = text.strip().replace("İ", "i").replace("I", "ı").lower()
    return re.sub(r"\s+", " ", t.strip(" .!?"))


def _num(s: str) -> str:
    return s.replace(",", ".")


def route(text: str):
    """-> (tool, params) or None."""
    t = norm(text)
    if not t:
        return None
    if re.fullmatch(r"(şu an )?saat kaç|saati söyle|saat ne|tarih ne|bugün günlerden ne|bugün ayın kaçı", t):
        return "datetime_info", {}
    if re.fullmatch(r"(bugün|bugünkü) ne var|takvimde ne var|bugün programım ne|programım ne|ajandam", t):
        return "calendar", {"action": "today"}
    if re.fullmatch(r"yarın ne var|yarınki programım ne", t):
        return "calendar", {"action": "list", "date": (dt.date.today() + dt.timedelta(days=1)).isoformat()}
    if re.fullmatch(r"(günaydın|sabah özeti|günün özeti|brifing|bana günü anlat)( ver)?", t):
        return "daily_briefing", {}
    m = re.fullmatch(r"(?:(\w+?)(?:'?(?:da|de|ta|te))? )?hava(?: durumu)?(?: nasıl| ne)?", t)
    if m:
        return "weather", ({"city": m.group(1)} if m.group(1) and m.group(1) not in ("bugün", "şu", "dışarıda", "yarın") else {})
    m = re.fullmatch(r"(?:not al|not et|not düş)[:,]? (.+)", t)
    if m:
        return "notes", {"action": "add", "text": m.group(1), "kind": "note"}
    m = re.fullmatch(r"(?:yapılacak(?:lara)?|görev) (?:ekle|olarak ekle)[:,]? (.+)|yapılacaklara (.+?) ekle", t)
    if m:
        return "notes", {"action": "add", "text": m.group(1) or m.group(2), "kind": "todo"}
    if re.fullmatch(r"yapılacaklar(ım)?|yapılacaklar listesi|notlarım|notları göster", t):
        return "notes", {"action": "list"}
    m = (re.fullmatch(r"(\d+(?:[.,]\d+)?) ?(dakika|dk|saat|sa) sonra (.+?)(?: hatırlat\w*)?", t)
         or re.fullmatch(r"hatırlat\w*[:,]? (\d+(?:[.,]\d+)?) ?(dakika|dk|saat|sa) sonra (.+)", t))
    if m:
        return "reminder", {"action": "set", "message": m.group(3).strip(" ,"), "in_minutes": float(_num(m.group(1))) * _UNITS[m.group(2)]}
    if re.fullmatch(r"geri al|undo|az önceki işlemi geri al|son işlemi geri al", t):
        return "undo", {}
    if re.fullmatch(r"sistem durumu|bilgisayar durumu|pil durumu|ram durumu|bilgisayarım nasıl", t):
        return "system_info", {}
    if re.fullmatch(r"(?:el kontrolü|el hareketleri|el hareketleriyle kontrol|holo|holo paneli)(?:n?[iıuü])? ?(?:aç|başlat)|(?:aç|başlat) (?:el kontrolü|el hareketleri|holo)(?: paneli)?", t):
        return "holo_ac", {}
    m = re.fullmatch(r"(?:aç|başlat|çalıştır) (.+)|(.+?)(?:'?[yı]?[iıuü]|'?[yı]?)? (?:aç|başlat)", t)
    if m:
        target = (m.group(1) or m.group(2) or "").strip()
        if target and len(target) <= 40 and not re.search(r"\b(ve|ile|sonra)\b", target):
            return "open_app", {"target": target}
    m = re.fullmatch(r"(?:internette |web'de |google'da |google )?(?:ara|araştır)[:,]? (.+)|(.+?) (?:diye )?(?:internette |google'da )?ara", t)
    if m and (m.group(1) or m.group(2)):
        return "web_search", {"query": (m.group(1) or m.group(2)).strip()}
    m = re.fullmatch(r"(?:hesapla[:,]? )?([\d\s.,+\-*/()x]+?|[\d\s.,]+(?: (?:çarpı|carpi|kere|artı|arti|eksi|bölü|bolu) [\d\s.,]+)+?)(?: kaç eder| kaçtır| eşittir| nedir)?", t)
    if m and re.search(r"\d", m.group(1)) and (t.startswith("hesapla") or re.search(r"[+\-*/x]|çarpı|carpi|kere|artı|arti|eksi|bölü|bolu|kaç eder|kaçtır", t)):
        expr = f" {m.group(1)} "
        for w, o in _OPS:
            expr = expr.replace(f" {w} " if w.strip() == w else w, f" {o} ")
        return "calculate", {"expression": _num(expr.strip().replace("x", "*"))}
    if re.fullmatch(r"görüşürüz|kapat kendini|asistanı kapat|güle güle", t):
        return "shutdown_assistant", {}
    return None


def run(text: str, registry, ctx):
    """Execute a recognised command. Returns the answer text, or None if the text is not a fast command."""
    hit = route(text)
    if not hit:
        return None
    tool, params = hit
    if tool not in registry.tools:
        return None
    return registry.call(tool, params, ctx).text
