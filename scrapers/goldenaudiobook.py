import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
from rich.console import Console

class GoldenAudiobookScraper:
    """
    Scraper for goldenaudiobook.net.
    This site embeds direct MP3 links in <audio> tags on the page.
    """
    
    BASE_URL = "https://goldenaudiobook.net"
    console = Console()

    def fetch_book_data(self, url):
        """
        Fetches all necessary book data from a given goldenaudiobook.net URL.
        """
        self.console.print(f"Fetching data from Golden Audiobook: {url}")
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })

        try:
            response = session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # --- Extract Title and Author ---
            # Title and author are often combined in the <h1> tag.
            title_text = soup.find("h1", class_="title-page").text.strip()
            author, book_title = self._split_author_title(title_text)
            sanitized_title = re.sub(r'[<>:"/\\|?*]', "_", book_title)

            # --- Extract Other Details ---
            cover_url = self._extract_cover_url(soup)
            year = self._extract_year(soup)
            # Narrator is not consistently available on this site
            narrator = None 

            # --- Extract Chapters ---
            chapters = self._extract_chapters(soup)
            
            if not chapters:
                self.console.print("[yellow]Warning: Could not find any chapter links.[/yellow]")
                return None

            return {
                'title': sanitized_title,
                'author': author,
                'narrator': narrator,
                'year': year,
                'cover_url': cover_url,
                'chapters': chapters,
                'site_headers': {
                    "Referer": self.BASE_URL,
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "*/*",
                    "Accept-Encoding": "identity;q=1, *;q=0",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Range": "bytes=0-"
                }
            }

        except Exception as e:
            self.console.print(f"[red]Error occurred while scraping Golden Audiobook: {e}[/red]")
            return None

    def _split_author_title(self, text):
        """Splits text like 'Author - Title Audiobook' into (Author, Title)."""
        author, title = "Unknown", text
        if '–' in text:
            parts = text.split('–', 1)
            author = parts[0].strip()
            title = parts[1].strip()
        
        # Clean up common suffixes
        title = title.replace("Audiobook", "").strip()
        return author, title

    def _extract_cover_url(self, soup):
        """Finds the main cover image URL."""
        # The primary image is often in a <figure> tag
        cover_tag = soup.select_one("figure.wp-caption img")
        if cover_tag and cover_tag.get('src'):
            return cover_tag['src']
        return None

    def _extract_year(self, soup):
        """Extracts the publication year from the <time> tag."""
        time_tag = soup.find("time", class_="entry-date")
        if time_tag and time_tag.get('datetime'):
            # The datetime is in ISO format, e.g., "2017-02-13T12:44:28+00:00"
            return time_tag['datetime'][:4] # Extract the first 4 characters (the year)
        return None

    import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
from rich.console import Console

class GoldenAudiobookScraper:
    """
    Scraper for goldenaudiobook.net.
    This site embeds direct MP3 links in <audio> tags on the page.
    """
    
    BASE_URL = "https://goldenaudiobook.net"
    console = Console()

    def fetch_book_data(self, url):
        """
        Fetches all necessary book data from a given goldenaudiobook.net URL.
        """
        self.console.print(f"Fetching data from Golden Audiobook: {url}")
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })

        try:
            response = session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # --- Extract Title and Author ---
            # Title and author are often combined in the <h1> tag.
            title_text = soup.find("h1", class_="title-page").text.strip()
            author, book_title = self._split_author_title(title_text)
            sanitized_title = re.sub(r'[<>:"/\\|?*]', "_", book_title)

            # --- Extract Other Details ---
            cover_url = self._extract_cover_url(soup)
            year = self._extract_year(soup)
            # Narrator is not consistently available on this site
            narrator = None 

            # --- Extract Chapters ---
            chapters = self._extract_chapters(soup)
            
            if not chapters:
                self.console.print("[yellow]Warning: Could not find any chapter links.[/yellow]")
                return None

            return {
                'site': 'goldenaudiobook.net',
                'title': sanitized_title,
                'author': author,
                'narrator': narrator,
                'year': year,
                'cover_url': cover_url,
                'book_url': url,
                'chapters': chapters,
                'site_headers': {
                    "Referer": "https://goldenaudiobook.net",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "*/*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "identity;q=1, *;q=0",
                    "Range": "bytes=0-"
                }
            }

        except Exception as e:
            self.console.print(f"[red]Error occurred while scraping Golden Audiobook: {e}[/red]")
            return None

    def _split_author_title(self, text):
        """Splits text like 'Author - Title Audiobook' into (Author, Title)."""
        author, title = "Unknown", text
        if '–' in text:
            parts = text.split('–', 1)
            author = parts[0].strip()
            title = parts[1].strip()
        
        # Clean up common suffixes
        title = title.replace("Audiobook", "").strip()
        return author, title

    def _extract_cover_url(self, soup):
        """Finds the main cover image URL."""
        # The primary image is often in a <figure> tag
        cover_tag = soup.select_one("figure.wp-caption img")
        if cover_tag and cover_tag.get('src'):
            return cover_tag['src']
        return None

    def _extract_year(self, soup):
        """Extracts the publication year from the <time> tag."""
        time_tag = soup.find("time", class_="entry-date")
        if time_tag and time_tag.get('datetime'):
            # The datetime is in ISO format, e.g., "2017-02-13T12:44:28+00:00"
            return time_tag['datetime'][:4] # Extract the first 4 characters (the year)
        return None

    def _extract_chapters(self, soup):
        chapters = []
        audio_tags = soup.select("audio.wp-audio-shortcode")

        for i, audio_tag in enumerate(audio_tags, start=1):
            source_tag = audio_tag.find("source")
            if source_tag and source_tag.get('src'):
                src = source_tag['src']

                chapters.append({
                    'url': src,
                    'title': f"Chapter {i:03}"  # zero-padded 3 digits
                })
        return chapters


