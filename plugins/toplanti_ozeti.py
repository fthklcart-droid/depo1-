"""Toplantı notundan karar ve aksiyonları çıkarır; istersen aksiyonları yapılacaklar listene ekler."""
from core import genplug, llm

TOOL = {
    "name": "toplanti_ozeti",
    "description": "Toplantı notu ya da dökümünden özet, kararlar ve aksiyon maddeleri çıkarır. yapilacaklara_ekle=true ise aksiyonlar notes yapılacaklarına eklenir.",
    "parameters": {"type": "object", "properties": {
        "not": {"type": "string"}, "yapilacaklara_ekle": {"type": "boolean"}}, "required": ["not"]},
}


def run(p, ctx):
    raw = llm.text("Toplantı notundan şu üç bölümü yaz: 'ÖZET:' (3-5 cümle), 'KARARLAR:' (her satır '- '), 'AKSİYONLAR:' (her satır '- kim: ne, ne zamana kadar'; bilinmeyeni [belirsiz] yaz). "
                   "Notta olmayan hiçbir şeyi ekleme.\n" + genplug.data("veri", p["not"])).strip()
    added = 0
    if p.get("yapilacaklara_ekle") and "AKSİYONLAR:" in raw:
        for line in raw.split("AKSİYONLAR:", 1)[1].splitlines():
            line = line.strip()
            if line.startswith("-") and len(line) > 3:
                ctx.call("notes", action="add", text=line.lstrip("- ").strip(), kind="todo")
                added += 1
    return raw + (f"\n\n{added} aksiyon yapılacaklara eklendi." if added else "")
