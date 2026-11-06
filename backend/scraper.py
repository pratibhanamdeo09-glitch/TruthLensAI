"""URL se news article ka title aur text nikalta hai."""
import ipaddress
import socket
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TruthLensAI/1.0",
    "Accept-Language": "en-US,en;q=0.9",
}
MAX_BYTES = 5 * 1024 * 1024  # 5 MB se badi page nahi lenge


class ScrapeError(Exception):
    pass


def _check_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ScrapeError("Sahi URL daalo (http:// ya https:// se shuru hona chahiye).")
    # Apne computer / local network ke address block karo (security)
    try:
        for info in socket.getaddrinfo(parsed.hostname, None):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise ScrapeError("Local/private address allowed nahi hai.")
    except socket.gaierror:
        raise ScrapeError("Ye website nahi mili. URL check karo.")


def fetch_article(url: str) -> dict:
    url = url.strip()
    _check_url(url)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12, stream=True)
        resp.raise_for_status()
        raw = resp.raw.read(MAX_BYTES, decode_content=True)
    except requests.RequestException as e:
        raise ScrapeError(f"Page download nahi ho paya: {e.__class__.__name__}")

    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form", "noscript"]):
        tag.decompose()

    title = ""
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        title = og["content"].strip()
    elif soup.title and soup.title.string:
        title = soup.title.string.strip()

    # Pehle <article> ke andar paragraphs dhoondo, warna poore page se
    container = soup.find("article") or soup
    paragraphs = [p.get_text(" ", strip=True) for p in container.find_all("p")]
    paragraphs = [p for p in paragraphs if len(p.split()) >= 8]
    text = "\n".join(paragraphs)

    if len(text.split()) < 40:
        raise ScrapeError("Is page se kaafi article text nahi mila. "
                          "Text manually copy karke 'Text' tab mein paste karo.")
    return {"title": title, "text": text, "url": url}
