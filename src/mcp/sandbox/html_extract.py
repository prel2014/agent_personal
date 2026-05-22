from __future__ import annotations

from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin


class _TextExtractor(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.links: list[dict[str, str]] = []
        self._in_title = False
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        normalized = tag.lower()
        if normalized in {"script", "style", "noscript"}:
            self._ignored_depth += 1
            return
        if normalized == "title":
            self._in_title = True
        if normalized == "a":
            attr_map = {name.lower(): value for name, value in attrs if value}
            href = attr_map.get("href")
            if href:
                self.links.append({"url": urljoin(self.base_url, href), "text": ""})

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if normalized in {"script", "style", "noscript"} and self._ignored_depth:
            self._ignored_depth -= 1
            return
        if normalized == "title":
            self._in_title = False
        if normalized in {"p", "div", "section", "article", "br", "li", "tr", "h1", "h2", "h3"}:
            self.text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        cleaned = " ".join(unescape(data).split())
        if not cleaned:
            return
        if self._in_title:
            self.title_parts.append(cleaned)
        self.text_parts.append(cleaned)


def extract_html(html: str, base_url: str, *, max_links: int = 100) -> dict[str, object]:
    parser = _TextExtractor(base_url)
    parser.feed(html)

    title = " ".join(parser.title_parts).strip()
    text = "\n".join(
        line.strip()
        for line in " ".join(parser.text_parts).splitlines()
        if line.strip()
    )

    seen: set[str] = set()
    links: list[dict[str, str]] = []
    for link in parser.links:
        url = link["url"]
        if url in seen:
            continue
        seen.add(url)
        links.append(link)
        if len(links) >= max_links:
            break

    return {"title": title, "text": text, "links": links}
