"""Sözlük: yazım hatasını anlayıp öneri verir. (Fikir: J.A.R.V.I.S 'intelligent dictionary'; difflib ile yeniden yazıldı.)
Çevrimdışı için data/sozluk.json ({"kelime": ["tanım", ...]}) kullanılır; yoksa çevrimiçi sözlük API'sine (İngilizce) bakılır."""
import difflib
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "sozluk.json"
UPSTREAM = "https://raw.githubusercontent.com/GauravSingh9356/J.A.R.V.I.S/master/data.json"
_cache = {}

TOOL = {
    "name": "sozluk",
    "description": "Kelime anlamı (İngilizce sözlük). Yazım hatası varsa en yakın kelimeleri önerir. action=indir: çevrimdışı sözlük dosyasını (4,9 MB) bir kez indirir (onay ister).",
    "parameters": {"type": "object", "properties": {"kelime": {"type": "string"}, "action": {"type": "string", "enum": ["ara", "indir"]}}},
}


def local():
    if DATA.exists() and _cache.get("m") != DATA.stat().st_mtime:
        _cache["d"], _cache["m"] = json.loads(DATA.read_text("utf-8")), DATA.stat().st_mtime
    return _cache.get("d") if DATA.exists() else None


def lookup(word: str, data: dict):
    w = word.strip().lower()
    if w in data:
        return w, data[w], []
    return None, None, difflib.get_close_matches(w, data.keys(), n=3, cutoff=0.75)


def online(word: str):
    url = "https://api.dictionaryapi.dev/api/v2/entries/en/" + urllib.parse.quote(word.strip().lower())
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "SiriusAssistant/1.0"}), timeout=10) as r:
        d = json.load(r)
    return [df["definition"] for m in d[0]["meanings"] for df in m["definitions"]][:4]


def run(p, ctx):
    if p.get("action") == "indir":
        if not ctx.confirm("Çevrimdışı sözlük (≈4,9 MB) indirilsin mi?\nKaynak: GauravSingh9356/J.A.R.V.I.S (MIT). Verinin asıl kaynağı belirtilmemiş; kişisel kullanım için indir."):
            return "İndirilmedi."
        with urllib.request.urlopen(UPSTREAM, timeout=60) as r:
            raw = r.read(12_000_000)
        d = json.loads(raw)
        if not isinstance(d, dict) or not all(isinstance(v, list) for v in list(d.values())[:50]):
            return "Beklenen biçimde değil, kaydedilmedi."
        DATA.parent.mkdir(exist_ok=True)
        DATA.write_bytes(raw)
        return f"İndirildi: {len(d)} kelime ({DATA})."
    word = (p.get("kelime") or "").strip()
    if not word:
        return "kelime ver."
    data = local()
    if data is not None:
        w, defs, near = lookup(word, data)
        if defs:
            return f"{w}: " + " | ".join(defs[:4])
        return f"'{word}' bulunamadı." + (f" Şunu mu demek istedin: {', '.join(near)}?" if near else "")
    try:
        return f"{word.lower()}: " + " | ".join(online(word))
    except urllib.error.HTTPError as e:
        return f"'{word}' bulunamadı (çevrimiçi sözlük, yalnızca İngilizce). Yazımı kontrol et." if e.code == 404 else f"Sözlük hatası: {e.code}"
    except (OSError, ValueError, KeyError, IndexError):
        return "Sözlüğe ulaşılamadı. Çevrimdışı kullanmak için sozluk aracını action=indir ile çalıştır."
