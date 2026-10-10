"""Müşteri görüşme notlarını tasarım ekibine verilecek düzenli bir kreatif brief'e çevirir."""
from core import genplug

TOOL = {
    "name": "kreatif_brief",
    "description": "Dağınık görüşme notu, ses dökümü ya da yazışmadan tasarım ekibi için kreatif brief çıkarır. Eksik bilgileri 'Netleştirilecek sorular' olarak listeler.",
    "parameters": {"type": "object", "properties": {
        "notlar": {"type": "string", "description": "Ham notlar / yazışma"}, "musteri": {"type": "string"}}, "required": ["notlar"]},
}


def run(p, ctx):
    prompt = ("Aşağıdaki notlardan bir KREATİF BRİEF yaz. Bölümler: Müşteri ve iş özeti, Hedef, Hedef kitle, Teslim edilecekler (ölçü/format), "
              "Ton ve stil, Referanslar, Zorunlu öğeler, Yasaklar, Takvim ve bütçe, Netleştirilecek sorular. "
              "Notlarda olmayan bilgiyi doldurma; 'Netleştirilecek sorular'a yaz.\n"
              + genplug.data("veri", f"Müşteri: {p.get('musteri', '')}\n{p['notlar']}"))
    return genplug.generate(ctx, "brief-" + p.get("musteri", "musteri"), prompt)
