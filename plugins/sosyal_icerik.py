"""Instagram ve diğer sosyal hesaplar için gönderi metni, hashtag seti ve Reels/story fikri."""
from core import genplug

TOOL = {
    "name": "sosyal_icerik",
    "description": "Sosyal medya gönderi metni, hashtag, Reels/story fikri üretir (taslak; paylaşım yapmaz). tur: post | reels | story | hepsi.",
    "parameters": {"type": "object", "properties": {
        "marka": {"type": "string"}, "konu": {"type": "string", "description": "Ürün, kampanya ya da duyuru"},
        "platform": {"type": "string", "description": "instagram | x | linkedin | tiktok | facebook"},
        "ton": {"type": "string", "description": "samimi, resmi, eğlenceli…"}, "tur": {"type": "string"},
        "adet": {"type": "integer", "description": "Kaç alternatif (varsayılan 3)"}},
        "required": ["marka", "konu"]},
}


def run(p, ctx):
    n = max(1, min(int(p.get("adet", 3)), 8))
    prompt = (f"{p.get('platform', 'instagram')} için {n} alternatif içerik hazırla. Tür: {p.get('tur', 'hepsi')}. Ton: {p.get('ton', 'samimi')}. "
              "Her alternatif: başlık/kanca (ilk cümle), gönderi metni, 8-12 ilgili hashtag, görsel ya da Reels kare fikri, harekete geçirici çağrı. "
              "Platformun karakter sınırına ve biçimine uy. Abartılı vaat verme.\n"
              + genplug.data("veri", f"Marka: {p['marka']}\nKonu: {p['konu']}"))
    return genplug.generate(ctx, "icerik-" + p["marka"], prompt)
