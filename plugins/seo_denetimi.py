"""Bir sayfanın temel SEO denetimi. Kural tabanlıdır (model yok): ölçülebilir her şey sayıyla raporlanır."""
import urllib.request
from html.parser import HTMLParser

from core.netguard import check_url

TOOL = {
    "name": "seo_denetimi",
    "description": "Bir sayfanın temel SEO denetimi: başlık, açıklama, H1, görsel alt metinleri, canonical, dil, viewport, Open Graph, bağlantılar. url ya da html ver.",
    "parameters": {"type": "object", "properties": {"url": {"type": "string"}, "html": {"type": "string"}}},
}


class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""; self.in_title = False; self.meta = {}; self.h = []; self.cur_h = None
        self.imgs = 0; self.noalt = 0; self.links = []; self.canonical = ""; self.lang = ""; self.text = []; self.skip = 0

    def handle_starttag(self, tag, a):
        a = dict(a)
        if tag == "html":
            self.lang = a.get("lang", "")
        elif tag == "title":
            self.in_title = True
        elif tag == "meta":
            k = (a.get("name") or a.get("property") or "").lower()
            if k:
                self.meta[k] = a.get("content", "")
        elif tag in ("h1", "h2", "h3"):
            self.cur_h = tag; self.h.append([tag, ""])
        elif tag == "img":
            self.imgs += 1
            if not (a.get("alt") or "").strip():
                self.noalt += 1
        elif tag == "a" and a.get("href"):
            self.links.append(a["href"])
        elif tag == "link" and (a.get("rel") or "").lower() == "canonical":
            self.canonical = a.get("href", "")
        elif tag in ("script", "style"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        elif tag in ("h1", "h2", "h3"):
            self.cur_h = None
        elif tag in ("script", "style") and self.skip:
            self.skip -= 1

    def handle_data(self, d):
        if self.in_title:
            self.title += d
        elif self.cur_h:
            self.h[-1][1] += d
        if not self.skip:
            self.text.append(d)


def audit(markup: str, url: str = "") -> str:
    p = P(); p.feed(markup)
    title, desc = p.title.strip(), p.meta.get("description", "").strip()
    h1 = [t.strip() for tag, t in p.h if tag == "h1"]
    words = len(" ".join(p.text).split())
    ext = [l for l in p.links if l.startswith("http") and url and url.split("/")[2] not in l]
    checks = [
        (bool(title) and 15 <= len(title) <= 65, f"Başlık: {len(title)} karakter" + ("" if 15 <= len(title) <= 65 else " (15-65 arası olmalı)")),
        (bool(desc) and 70 <= len(desc) <= 165, f"Açıklama: {len(desc)} karakter" + ("" if 70 <= len(desc) <= 165 else " (70-165 arası olmalı)")),
        (len(h1) == 1, f"H1 sayısı: {len(h1)}" + ("" if len(h1) == 1 else " (tam 1 olmalı)")),
        (p.noalt == 0, f"Alt metni olmayan görsel: {p.noalt}/{p.imgs}"),
        (bool(p.canonical), "canonical bağlantısı " + ("var" if p.canonical else "yok")),
        (bool(p.lang), f"html lang: {p.lang or 'yok'}"),
        ("viewport" in p.meta, "viewport meta " + ("var" if "viewport" in p.meta else "yok (mobil uyum)")),
        ("og:title" in p.meta and "og:image" in p.meta, "Open Graph (og:title, og:image) " + ("tamam" if "og:title" in p.meta and "og:image" in p.meta else "eksik")),
        (words >= 300, f"Metin: {words} kelime" + ("" if words >= 300 else " (300+ önerilir)")),
        (not url or url.startswith("https://"), "HTTPS " + ("evet" if not url or url.startswith("https://") else "hayır")),
    ]
    passed = sum(1 for ok, _ in checks if ok)
    lines = [f"SEO denetimi: {passed}/{len(checks)} kontrol geçti" + (f" · {url}" if url else "")]
    lines += [("  ✓ " if ok else "  ✗ ") + t for ok, t in checks]
    lines.append(f"  Bağlantılar: {len(p.links)} toplam, {len(ext)} dış" if url else f"  Bağlantılar: {len(p.links)}")
    return "\n".join(lines)


def run(p, ctx):
    if p.get("html"):
        return audit(p["html"])
    url = (p.get("url") or "").strip()
    if not url:
        return "url ya da html ver."
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    err = check_url(url)
    if err:
        return err
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (SiriusSEO)"})
    with urllib.request.urlopen(req, timeout=12) as r:
        body = r.read(1_500_000).decode(r.headers.get_content_charset() or "utf-8", "replace")
    return audit(body, r.geturl())
