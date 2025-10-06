# scrapers/__init__.py
from .tokybook import TokybookScraper
from .goldenaudiobook import GoldenAudiobookScraper
from .zaudiobooks import ZaudiobooksScraper
from .fulllengthaudiobooks import FulllengthAudiobooksScraper
from .hdaudiobooks import HDAudiobooksScraper
from .bigaudiobooks import BigAudiobooksScraper

# A dictionary to map domain names to scraper classes
SCRAPER_MAPPING = {
    "tokybook.com": TokybookScraper,
    "goldenaudiobook.net": GoldenAudiobookScraper,
    "zaudiobooks.com": ZaudiobooksScraper,
    "fulllengthaudiobooks.net": FulllengthAudiobooksScraper,
    "hdaudiobooks.net": HDAudiobooksScraper,
    "bigaudiobooks.net": BigAudiobooksScraper,
}


def get_scraper(url: str):
    """
    Factory function to select the correct scraper based on the URL's domain.

    Args:
        url: The URL of the audiobook.

    Returns:
        An instance of the appropriate scraper class, or None if no match is found.
    """
    for domain, scraper_class in SCRAPER_MAPPING.items():
        if domain in url:
            return scraper_class()
    return None