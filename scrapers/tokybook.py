import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from rich.console import Console


class TokybookScraper:
    """Scraper for tokybook.com. Handles the API call to /player."""
    
    BASE_URL = "https://tokybook.com"
    console = Console()

    def fetch_book_data(self, url):
        """
        Fetches all necessary book data from a given Tokybook URL.

        Args:
            url (str): The URL of the audiobook page.

        Returns:
            dict: A dictionary containing the book's metadata and chapter list,
                  or None if scraping fails.
        """
        self.console.print("[bold cyan]Fetching data from Tokybook...[/bold cyan]")
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })
        try:
            response = session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            book_title = soup.find("h1", class_=re.compile(r"text-4xl")).text.strip()
            sanitized_title = re.sub(r'[<>:"/\\|?*]', "_", book_title)

            details = self._extract_details(soup)
            
            cover_img_tag = soup.select_one("div.md\\:col-span-1 img")
            cover_url = urljoin(self.BASE_URL, cover_img_tag['src']) if cover_img_tag else None

            play_button = soup.find("button", {"data-action": "play-now"})
            book_id = play_button["data-book-id"]
            token = play_button["data-token"]
            
            chapters, headers = self._fetch_player_data(session, url, book_id, token)

            return {
                'title': sanitized_title,
                'author': details.get('author'),
                'narrator': details.get('narrator'),
                'year': details.get('year'),
                'cover_url': cover_url,
                'chapters': chapters,
                'site_headers': headers
            }

        except Exception as e:
            print(f"An error occurred while scraping Tokybook: {e}")
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
            value_element = item.find("span", class_="detail-value-link") or item.find("span", class_="detail-value")

            if value_element:
                value = " ".join(value_element.text.split())
                if "authors:" in label:
                    details["author"] = value
                elif "narrators:" in label:
                    details["narrator"] = value
                elif "release date:" in label:
                    match = re.search(r"\d{4}$", value) # Look for a 4-digit year
                    if match:
                        details["year"] = match.group()
        return details

    def _fetch_player_data(self, session, book_url, book_id, token):
        """Fetches the chapter list from the internal player API."""
        player_url = f"{self.BASE_URL}/player"
        # Tokybook requires these headers for the player API request
        headers = {"Referer": book_url, "X-Audiobook-Id": book_id, "X-Playback-Token": token}
        
        response = session.get(player_url, headers=headers)
        response.raise_for_status()
        player_soup = BeautifulSoup(response.text, "html.parser")

        chapters = []
        for i, item in enumerate(player_soup.find_all("li", class_="playlist-item-hls"), start=1):
            src = item.get("data-track-src")
            if src:
                title = f"Chapter {i:03}"  # 3-digit zero-padded
                chapters.append({
                    'url': urljoin(self.BASE_URL, src),
                    'title': title
                })
        
        # These headers are required by yt-dlp to download the actual audio files
        headers_for_yt_dlp = {
            "Referer": book_url,
            "x-playback-token": token
        }
        return chapters, headers_for_yt_dlp