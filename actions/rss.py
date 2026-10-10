"""Read RSS/Atom feeds: headlines without a search engine."""
import urllib.request
import xml.etree.ElementTree as ET

FEEDS = {
    "world": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "turkce": "https://feeds.bbci.co.uk/turkce/rss.xml",
    "tech": "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "science": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
    "business": "https://feeds.bbci.co.uk/news/business/rss.xml",
}

TOOL = {
    "name": "rss_feed",
    "description": "Latest headlines from a feed. feed = world | turkce | tech | science | business, or give a full RSS/Atom url.",
    "parameters": {"type": "object", "properties": {"feed": {"type": "string"}, "url": {"type": "string"},
                                                      "limit": {"type": "integer"}}},
}


def parse(xml_text: str, limit: int = 8) -> list[tuple[str, str, str]]:
    root = ET.fromstring(xml_text)
    out = []
    for it in root.iter():
        tag = it.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        g = lambda n: next((c for c in it if c.tag.split("}")[-1] == n), None)  # noqa: E731
        title, link, desc = g("title"), g("link"), g("description")
        if desc is None:   # not `or`: an Element with no children is falsy
            desc = g("summary")
        href = (link.get("href") if link is not None and link.get("href") else (link.text if link is not None else "")) or ""
        out.append(((title.text or "").strip() if title is not None else "", href.strip(),
                    (desc.text or "").strip()[:160] if desc is not None else ""))
        if len(out) >= limit:
            break
    return out


def run(p, ctx):
    url = p.get("url") or FEEDS.get((p.get("feed") or "world").lower())
    if not url or not url.startswith(("http://", "https://")):
        return f"Unknown feed. Use one of {', '.join(FEEDS)} or a url."
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (SiriusAssistant)"})
    with urllib.request.urlopen(req, timeout=10) as r:
        body = r.read(2_000_000).decode("utf-8", "replace")
    items = parse(body, int(p.get("limit", 8)))
    return "\n".join(f"{i}. {t}\n   {l}" + (f"\n   {d}" if d else "") for i, (t, l, d) in enumerate(items, 1)) or "Feed is empty."
