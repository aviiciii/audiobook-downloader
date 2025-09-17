import requests
from bs4 import BeautifulSoup

class ZaudiobooksScraper:
    def fetch_book_data(self, book_url: str) -> dict:
        """
        Scrape audiobook metadata and chapters from a zaudiobooks.com page.
        """
        response = requests.get(book_url, timeout=30)
        response.raise_for_status()
        html = response.text

        # Save raw HTML if needed for debugging
        # with open("website.html", "w", encoding="utf-8") as f:
        #     f.write(html)

        # Extract track info block
        lines = html.splitlines()
        start_index = None
        for i, line in enumerate(lines):
            if "tracks = [" in line:
                start_index = i
                break

        if start_index is None:
            return None

        # Parse the following lines to extract chapters
        chapters = []
        name = None
        base_url = "https://files01.freeaudiobooks.top/audio/"

        for line in lines[start_index:]:
            if "name" in line:
                # Extract and clean name
                name = (
                    line.strip()
                    .replace('"', "")
                    .replace("\\", "")
                    .replace("name: ", "")
                    .rstrip(",")
                    + ".mp3"
                )
            if "chapter_link_dropbox" in line:
                chapter_link = (
                    line.strip()
                    .replace('"', "")
                    .replace("\\", "")
                    .replace("chapter_link_dropbox: ", "")
                    .rstrip(",")
                )
                full_url = base_url + chapter_link
                chapters.append({"title": name.replace(".mp3", ""), "url": full_url})
            if "]," in line:
                break

        # Extract title and cover (optional with BeautifulSoup)
        soup = BeautifulSoup(html, "html.parser")
        title_tag = soup.find("meta", property="og:title")
        cover_tag = soup.find("meta", property="og:image")

        title = title_tag["content"] if title_tag else "Unknown Title"
        cover_url = cover_tag["content"] if cover_tag else None
        print(chapters)
        return {
            "site": "zaudiobooks.com",
            "book_url": book_url,
            "title": title.strip(),
            "author": None,
            "narrator": None,
            "year": None,
            "cover_url": cover_url,
            "chapters": chapters,
        }