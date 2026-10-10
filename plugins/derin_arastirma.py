"""Çok kaynaklı araştırma: sorguları planlar, arar, sayfaları okur, kaynak göstererek sentezler."""
import re

from core import genplug, llm

TOOL = {
    "name": "derin_arastirma",
    "description": "Bir konuyu internette birkaç kaynaktan araştırıp kaynaklı bir rapor yazar (yavaştır, ~30-60 sn). Hızlı bir bilgi için web_search kullan.",
    "parameters": {"type": "object", "properties": {
        "soru": {"type": "string"}, "kaynak_sayisi": {"type": "integer", "description": "Okunacak sayfa sayısı (2-8, varsayılan 5)"}},
        "required": ["soru"]},
}


def run(p, ctx):
    soru, n = p["soru"].strip(), max(2, min(int(p.get("kaynak_sayisi", 5)), 8))
    plan = llm.text("Şu araştırma sorusu için birbirinden farklı 3 kısa web arama sorgusu yaz, her satıra bir tane, başka hiçbir şey yazma:\n" + genplug.data("veri", soru))
    queries = [re.sub(r"^[\-\d.\s*]+", "", q).strip() for q in plan.splitlines() if q.strip()][:4] or [soru]
    urls: list[str] = []
    for q in queries:
        for u in re.findall(r"^\s+(https?://\S+)", ctx.call("web_search", query=q, max_results=4), re.M):
            if u not in urls:
                urls.append(u)
    sources = []
    for u in urls[:n + 3]:
        if len(sources) >= n:
            break
        page = ctx.call("fetch_page", url=u, max_chars=3500)
        body = page.split("\n", 1)[-1] if page.startswith("[UNTRUSTED") else page
        if len(body) > 300:                      # skip error stubs and empty pages
            sources.append((u, body))
    if not sources:
        return "Okunabilir kaynak bulunamadı (ağ erişimi ya da arama sonucu yok)."
    blocks = "\n\n".join(f"[{i}] {u}\n{genplug.data('veri', b)}" for i, (u, b) in enumerate(sources, 1))
    prompt = ("Aşağıdaki numaralı kaynaklara DAYANARAK soruyu yanıtlayan bir araştırma raporu yaz: Özet, Bulgular (her iddiadan sonra [n] ile kaynak), "
              "Çelişkiler ya da belirsizlikler, Sonuç. Kaynaklarda olmayanı yazma; emin değilsen söyle.\nSoru: " + soru + "\n\n" + blocks)
    out = genplug.generate(ctx, "arastirma-" + soru[:30], prompt)
    return out + "\n\nKaynaklar:\n" + "\n".join(f"[{i}] {u}" for i, (u, _) in enumerate(sources, 1))
