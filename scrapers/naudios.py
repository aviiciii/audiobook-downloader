"""
Scraper for naudios.com watch pages.
Audio is served as direct MP3 from audio.naudios.com/audios.php?no=N&postID=ID.
"""

import re
import requests
from bs4 import BeautifulSoup


class NaudiosScraper:
    BASE_URL = "https://naudios.com"
    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    def fetch_book_data(self, url: str) -> dict | None:
        """
        Scrape audiobook metadata and chapter (track) URLs from a naudios.com/watch/ page.
        """
        post_id = self._get_post_id(url)
        if not post_id:
            return None

        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": self.USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
        )

        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()
            html = r.text
        except requests.RequestException as e:
            print(f"[!] Error fetching naudios page: {e}")
            return None

        soup = BeautifulSoup(html, "html.parser")

        # Title from h1
        h1 = soup.select_one("h1.fw-bold.mb-3.text-center") or soup.find("h1")
        title = (h1.get_text(strip=True) if h1 else None) or "Unknown Title"

        # Cover from detail thumb
        cover_img = soup.select_one(".detail-thumb") or soup.select_one(".thumb-container img")
        cover_url = None
        if cover_img and cover_img.get("src"):
            cover_url = cover_img["src"]
            if cover_url.startswith("//"):
                cover_url = "https:" + cover_url
            elif cover_url.startswith("/"):
                cover_url = self.BASE_URL.rstrip("/") + cover_url

        # Tracks: .track-item with data-src="https://audio.naudios.com/audios.php?no=N&postID=..."
        track_items = soup.select(".track-item[data-src]")
        chapters = []
        for i, item in enumerate(track_items, start=1):
            src = item.get("data-src")
            if not src or "audios.php" not in src:
                continue
            # Normalize ampersands
            src = src.replace("&amp;", "&")
            label = item.get_text(strip=True) or f"Chapter {i:03d}"
            # Use short chapter title for filename
            chapter_title = f"Chapter {i:03d}"
            chapters.append({"title": chapter_title, "url": src})

        if not chapters:
            print("[!] No audio tracks found on naudios page.")
            return None

        return {
            "site": "naudios.com",
            "title": title,
            "author": None,
            "narrator": None,
            "year": None,
            "cover_url": cover_url,
            "chapters": chapters,
            "site_headers": {
                "User-Agent": self.USER_AGENT,
                "Referer": f"{self.BASE_URL}/",
            },
        }

    @staticmethod
    def _get_post_id(url: str) -> str | None:
        """Extract post ID from .../watch/202602269643 or .../watch/202602269643/"""
        m = re.search(r"naudios\.com/watch/(\d+)", url)
        return m.group(1) if m else None
