"""YouTube ve harita aramalarını varsayılan tarayıcıda açar. (Fikir: J.A.R.V.I.S 'search youtube' / 'location'; Chrome yolu sabit değil.)"""
import urllib.parse
import webbrowser

TOOLS = []


def _open(url):
    webbrowser.open(url)
    return f"Açıldı: {url}"


def youtube(p, ctx):
    return _open("https://www.youtube.com/results?search_query=" + urllib.parse.quote(p["sorgu"]))


def harita(p, ctx):
    return _open("https://www.openstreetmap.org/search?query=" + urllib.parse.quote(p["yer"]) if p.get("saglayici") == "osm"
                 else "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(p["yer"]))


TOOLS = [
    ({"name": "youtube_ara", "description": "YouTube'da arama sonuçlarını tarayıcıda açar.",
      "parameters": {"type": "object", "properties": {"sorgu": {"type": "string"}}, "required": ["sorgu"]}}, youtube),
    ({"name": "harita_ara", "description": "Bir yeri haritada açar (Google Haritalar; saglayici=osm ile OpenStreetMap).",
      "parameters": {"type": "object", "properties": {"yer": {"type": "string"}, "saglayici": {"type": "string", "enum": ["google", "osm"]}}, "required": ["yer"]}}, harita),
]
