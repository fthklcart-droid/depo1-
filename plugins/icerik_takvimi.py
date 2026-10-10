"""Aylık sosyal medya içerik takvimi; sabit tarihli özel günler koddan gelir, uydurulmaz."""
import calendar
import datetime as dt

from core import genplug

FIXED = {(1, 1): "Yılbaşı", (2, 14): "Sevgililer Günü", (3, 8): "Dünya Kadınlar Günü", (3, 18): "Çanakkale Zaferi",
         (4, 23): "Ulusal Egemenlik ve Çocuk Bayramı", (5, 1): "Emek ve Dayanışma Günü", (5, 19): "Atatürk'ü Anma, Gençlik ve Spor Bayramı",
         (7, 15): "Demokrasi ve Milli Birlik Günü", (8, 30): "Zafer Bayramı", (10, 29): "Cumhuriyet Bayramı", (11, 10): "Atatürk'ü Anma Günü",
         (11, 24): "Öğretmenler Günü", (12, 31): "Yılbaşı gecesi"}

AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]

TOOL = {
    "name": "icerik_takvimi",
    "description": "Bir marka için aylık sosyal medya içerik takvimi (gün gün konu, format, kısa fikir). Sabit tarihli özel günleri otomatik ekler; dini bayramları sen belirtirsen eklenir.",
    "parameters": {"type": "object", "properties": {
        "marka": {"type": "string"}, "ay": {"type": "string", "description": "YYYY-AA, varsayılan bu ay"},
        "platformlar": {"type": "string", "description": "ör. instagram, tiktok"}, "haftalik": {"type": "integer", "description": "Haftada kaç paylaşım (varsayılan 4)"},
        "hedef": {"type": "string"}, "ozel_gunler": {"type": "string", "description": "Ek özel günler (dini bayram vb.), serbest metin"}},
        "required": ["marka"]},
}


def special_days(year: int, month: int) -> list[str]:
    out = [f"{d:02d}.{month:02d} {name}" for (m, d), name in sorted(FIXED.items()) if m == month]
    cal = calendar.Calendar()
    sundays = [d for d in cal.itermonthdates(year, month) if d.month == month and d.weekday() == 6]
    if month == 5:
        out.append(f"{sundays[1].day:02d}.05 Anneler Günü")          # second Sunday of May
    if month == 6:
        out.append(f"{sundays[2].day:02d}.06 Babalar Günü")          # third Sunday of June
    return sorted(out)


def run(p, ctx):
    try:
        y, m = map(int, (p.get("ay") or dt.date.today().strftime("%Y-%m")).split("-"))
        first = dt.date(y, m, 1)
    except ValueError:
        return "ay biçimi YYYY-AA olmalı (ör. 2026-11)."
    days = special_days(y, m)
    prompt = (f"{AYLAR[m - 1]} {y} için '{p['marka']}' markasına {p.get('platformlar', 'instagram')} içerik takvimi hazırla. Haftada {p.get('haftalik', 4)} paylaşım. "
              f"Hedef: {p.get('hedef', 'bilinirlik')}. Ay {calendar.monthrange(y, m)[1]} gün çekiyor, ayın 1'i {GUNLER[first.weekday()]}. "
              "Çıktı: Markdown tablo (Tarih | Gün | Platform | Format | Konu/fikir | Kısa metin önerisi). Özel günlere uygun içerikleri yerleştir, "
              "ardışık günlerde aynı formatı tekrarlama.\nÖzel günler (kesin): " + (", ".join(days) or "yok")
              + "\n" + genplug.data("veri", "Ek özel günler: " + p.get("ozel_gunler", "yok")))
    return genplug.generate(ctx, f"takvim-{p['marka']}-{y}-{m:02d}", prompt)
