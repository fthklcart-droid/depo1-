"""Ajans hizmetleri için müşteriye gönderilecek fiyat teklifi (sosyal medya, kimlik, katalog, web, baskı, video)."""
from core import genplug

TOOL = {
    "name": "ajans_teklifi",
    "description": "Reklam/tasarım ajansı için müşteriye resmi fiyat teklifi yazar ve dosyaya kaydeder. Fiyatları SEN vermezsen yer tutucu bırakır; uydurmaz.",
    "parameters": {"type": "object", "properties": {
        "musteri": {"type": "string", "description": "Müşteri / firma adı"},
        "isler": {"type": "string", "description": "İstenen işler, serbest metin (ör. logo, 12 post, 2 reels)"},
        "fiyatlar": {"type": "string", "description": "Bilinen fiyatlar ya da bütçe (isteğe bağlı)"},
        "notlar": {"type": "string", "description": "Teslim süresi, ödeme, özel şartlar (isteğe bağlı)"}},
        "required": ["musteri", "isler"]},
}


def run(p, ctx):
    prompt = ("Bir reklam ajansı adına müşteriye gönderilecek resmi, nazik ve net bir HİZMET TEKLİFİ yaz. Bölümler: "
              "Giriş, Kapsam (kalem kalem), Fiyatlandırma tablosu (KDV ayrı belirtilsin), Teslim süresi, Ödeme planı, "
              "Revizyon hakkı, Teklif geçerlilik süresi, Kapanış. Markdown kullan.\n"
              f"Müşteri: {p['musteri']}\n" + genplug.data("veri", f"İşler: {p['isler']}\nFiyatlar: {p.get('fiyatlar', 'verilmedi')}\nNotlar: {p.get('notlar', '')}"))
    return genplug.generate(ctx, "teklif-" + p["musteri"], prompt)
