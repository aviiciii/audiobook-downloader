import json
import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from rich.console import Console
import os
from requests.utils import default_user_agent


class TokybookScraper:
    """Scraper for tokybook.com. Handles the API call to /player."""

    BASE_URL = "https://tokybook.com"
    console = Console()

    def fetch_book_data(self, url):
        """
        Fetch book metadata + chapters using the new Tokybook API (2025).
        """

        self.console.print("[bold cyan]Fetching data from Tokybook API...[/bold cyan]")

        session = requests.Session()
        user_agent = os.environ.get("USER_AGENT") or os.environ.get("HTTP_USER_AGENT") or default_user_agent()
        session.headers.update({"User-Agent": user_agent})

        try:
            # ---------------------------------------------------------
            # 1) Extract the dynamicSlugId from the URL
            #    https://tokybook.com/<slug>
            # ---------------------------------------------------------
            slug = url.rstrip("/").split("/")[-1]

            api_details_url = f"{self.BASE_URL}/api/v1/search/post-details"

            payload = {
                "dynamicSlugId": slug,
                "userIdentity": {
                    "ipAddress": "0.0.0.0",
                    "userAgent": session.headers["User-Agent"],
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                },
            }

            headers = {
                "Content-Type": "application/json",
                "Origin": self.BASE_URL,
                "Referer": url,
                "Accept": "*/*",
                
            }

            # ---------------------------------------------------------
            # 2) POST /api/v1/search/post-details
            # ---------------------------------------------------------
            resp = session.post(api_details_url, data=json.dumps(payload), headers=headers)
            resp.raise_for_status()
            info = resp.json()

            # metadata fields
            book_title = info["title"]
            sanitized_title = re.sub(r'[<>:"/\\|?*]', "_", book_title)

            cover_url = info.get("coverImage")
            authors = ", ".join(a["name"] for a in info.get("authors", []))
            narrators = ", ".join(n["name"] for n in info.get("narrators", []))

            audioBookId = info["audioBookId"]
            postDetailToken = info["postDetailToken"]

            # ---------------------------------------------------------
            # 3) Fetch playlist using your existing function
            # ---------------------------------------------------------
            chapters, site_headers = self._fetch_player_data(
                session,
                url,
                audioBookId,
                postDetailToken
            )

            return {
                "title": sanitized_title,
                "author": authors,
                "narrator": narrators,
                "year": None,  # API doesn't include year; remove if needed
                "cover_url": cover_url,
                "chapters": chapters,
                "site_headers": site_headers,
                "site": "tokybook.com",
            }

        except Exception as e:
            print(f"Error in fetch_book_data: {e}")
            return None


    def _extract_details(self, soup):
        """Extracts author, narrator, and year from the details section."""
        details = {}
        detail_items = soup.select("div.detail-item")
        for item in detail_items:
            label_element = item.find("span", class_="font-medium")
            if not label_element:
                continue

            label = label_element.text.strip().lower()
            value_element = item.find("span", class_="detail-value-link") or item.find(
                "span", class_="detail-value"
            )

            if value_element:
                value = " ".join(value_element.text.split())
                if "authors:" in label:
                    details["author"] = value
                elif "narrators:" in label:
                    details["narrator"] = value
                elif "release date:" in label:
                    match = re.search(r"\d{4}$", value)  # Look for a 4-digit year
                    if match:
                        details["year"] = match.group()
        return details

    def _fetch_player_data(self, session, book_url, book_id, token):
        """
        New Tokybook API (2025) playlist fetcher.
        Uses POST /api/v1/playlist instead of HTML player.
        """

        api_url = f"{self.BASE_URL}/api/v1/playlist"

        # Build payload according to browser request
        payload = {
            "audioBookId": book_id,
            "postDetailToken": token,
            "userIdentity": {
                "ipAddress": "0.0.0.0",   # Tokybook accepts any value
                "userAgent": session.headers["User-Agent"],
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            },
        }
        headers = {
            "Content-Type": "application/json",
            "Origin": self.BASE_URL,
            "Accept": "*/*",
        }
        
        
        

        response = session.post(api_url, data=json.dumps(payload), headers=headers)
        response.raise_for_status()

        data = response.json()
        
        

        chapters = []
        
        
        for i, track in enumerate(data.get("tracks", []), start=1):
            src = track.get("src")
            if not src:
                continue

            full_url = urljoin(f"{self.BASE_URL}/api/v1/public/audio/", src)
            xtracksrc = urljoin(f"/api/v1/public/audio/", src)
            title = f"Chapter {i:03}"
            chapters.append({
                "url": full_url,
                "title": title,
                "src": xtracksrc,
            })

        # yt-dlp requires this header (streamToken replaces old playback token)
        headers_for_yt_dlp = {
            "Content-Type": "application/json",
            "Origin": self.BASE_URL,
            "Referer": book_url,
            "x-audiobook-id": data.get("audioBookId"),
            "x-stream-token": data.get("streamToken"),
        }

        return chapters, headers_for_yt_dlp

