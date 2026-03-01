"""Unit tests for CLI argument parsing, utility functions, and scraper selection."""

import unittest

from main import build_parser, get_scraper
from utils import sanitize_book_title, parse_chapter_ranges


class TestBuildParser(unittest.TestCase):
    """Tests for the argparse-based CLI."""

    def setUp(self):
        self.parser = build_parser()

    def test_no_args_defaults(self):
        parsed = self.parser.parse_args([])
        self.assertIsNone(parsed.url)
        self.assertIsNone(parsed.output)
        self.assertIsNone(parsed.chapters)
        self.assertIsNone(parsed.title)
        self.assertIsNone(parsed.author)
        self.assertIsNone(parsed.narrator)
        self.assertIsNone(parsed.year)
        self.assertIsNone(parsed.cover_url)

    def test_url_positional(self):
        parsed = self.parser.parse_args(["https://tokybook.com/post/some-book"])
        self.assertEqual(parsed.url, "https://tokybook.com/post/some-book")

    def test_output_short(self):
        parsed = self.parser.parse_args(
            ["https://tokybook.com/post/some-book", "-o", "/tmp/out"]
        )
        self.assertEqual(parsed.output, "/tmp/out")

    def test_output_long(self):
        parsed = self.parser.parse_args(
            ["https://tokybook.com/post/some-book", "--output", "/tmp/out"]
        )
        self.assertEqual(parsed.output, "/tmp/out")

    def test_chapters_short(self):
        parsed = self.parser.parse_args(
            ["https://tokybook.com/post/some-book", "-c", "1-5,8"]
        )
        self.assertEqual(parsed.chapters, "1-5,8")

    def test_chapters_long(self):
        parsed = self.parser.parse_args(
            ["https://tokybook.com/post/some-book", "--chapters", "1-3"]
        )
        self.assertEqual(parsed.chapters, "1-3")

    def test_metadata_overrides(self):
        parsed = self.parser.parse_args(
            [
                "https://tokybook.com/post/some-book",
                "--title",
                "My Title",
                "--author",
                "Author Name",
                "--narrator",
                "Narrator Name",
                "--year",
                "2023",
                "--cover-url",
                "https://example.com/cover.jpg",
            ]
        )
        self.assertEqual(parsed.title, "My Title")
        self.assertEqual(parsed.author, "Author Name")
        self.assertEqual(parsed.narrator, "Narrator Name")
        self.assertEqual(parsed.year, "2023")
        self.assertEqual(parsed.cover_url, "https://example.com/cover.jpg")

    def test_all_options_combined(self):
        parsed = self.parser.parse_args(
            [
                "https://zaudiobooks.com/red-rising/",
                "-o",
                "/tmp/books",
                "-c",
                "1-3,5",
                "--title",
                "Red Rising",
                "--author",
                "Pierce Brown",
            ]
        )
        self.assertEqual(parsed.url, "https://zaudiobooks.com/red-rising/")
        self.assertEqual(parsed.output, "/tmp/books")
        self.assertEqual(parsed.chapters, "1-3,5")
        self.assertEqual(parsed.title, "Red Rising")
        self.assertEqual(parsed.author, "Pierce Brown")


class TestGetScraper(unittest.TestCase):
    """Tests for the scraper factory function."""

    def test_tokybook(self):
        scraper = get_scraper("https://tokybook.com/post/some-book")
        self.assertIsNotNone(scraper)
        self.assertEqual(type(scraper).__name__, "TokybookScraper")

    def test_goldenaudiobook(self):
        scraper = get_scraper("https://goldenaudiobook.net/some-book/")
        self.assertIsNotNone(scraper)
        self.assertEqual(type(scraper).__name__, "GoldenAudiobookScraper")

    def test_zaudiobooks(self):
        scraper = get_scraper("https://zaudiobooks.com/some-book/")
        self.assertIsNotNone(scraper)
        self.assertEqual(type(scraper).__name__, "ZaudiobooksScraper")

    def test_fulllengthaudiobooks(self):
        scraper = get_scraper("https://fulllengthaudiobooks.net/some-book/")
        self.assertIsNotNone(scraper)
        self.assertEqual(type(scraper).__name__, "FulllengthAudiobooksScraper")

    def test_hdaudiobooks(self):
        scraper = get_scraper("https://hdaudiobooks.net/some-book/")
        self.assertIsNotNone(scraper)
        self.assertEqual(type(scraper).__name__, "HDAudiobooksScraper")

    def test_bigaudiobooks(self):
        scraper = get_scraper("https://bigaudiobooks.net/some-book/")
        self.assertIsNotNone(scraper)
        self.assertEqual(type(scraper).__name__, "BigAudiobooksScraper")

    def test_unsupported_url(self):
        self.assertIsNone(get_scraper("https://example.com/not-a-book"))

    def test_empty_string(self):
        self.assertIsNone(get_scraper(""))


class TestSanitizeBookTitle(unittest.TestCase):
    """Tests for the sanitize_book_title utility."""

    def test_normal_title(self):
        self.assertEqual(sanitize_book_title("My Great Book"), "My Great Book")

    def test_colon_replacement(self):
        self.assertEqual(
            sanitize_book_title("Dune: The Machine Crusade"),
            "Dune - The Machine Crusade",
        )

    def test_slash_replacement(self):
        self.assertEqual(
            sanitize_book_title("AC/DC: Highway to Hell"),
            "AC-DC - Highway to Hell",
        )

    def test_special_chars_removed(self):
        result = sanitize_book_title('How to use < > * ? | in Python')
        self.assertNotIn("<", result)
        self.assertNotIn(">", result)
        self.assertNotIn("*", result)
        self.assertNotIn("?", result)
        self.assertNotIn("|", result)

    def test_reserved_windows_name(self):
        result = sanitize_book_title("COM1")
        self.assertNotEqual(result, "COM1")

    def test_extra_spaces(self):
        result = sanitize_book_title("   A book    with    extra     spaces.   ")
        self.assertNotIn("  ", result)

    def test_empty_string(self):
        self.assertEqual(sanitize_book_title(""), "Untitled_Book")

    def test_none_input(self):
        self.assertEqual(sanitize_book_title(None), "Untitled_Book")

    def test_max_length(self):
        long_title = "A" * 300
        result = sanitize_book_title(long_title)
        self.assertLessEqual(len(result), 200)


class TestParseChapterRanges(unittest.TestCase):
    """Tests for the parse_chapter_ranges utility."""

    def test_single_chapter(self):
        self.assertEqual(parse_chapter_ranges("5", 10), [4])

    def test_range(self):
        self.assertEqual(parse_chapter_ranges("1-3", 10), [0, 1, 2])

    def test_mixed(self):
        self.assertEqual(parse_chapter_ranges("1-3, 5, 7-9", 10), [0, 1, 2, 4, 6, 7, 8])

    def test_empty_string(self):
        self.assertEqual(parse_chapter_ranges("", 10), [])

    def test_out_of_range(self):
        self.assertEqual(parse_chapter_ranges("99", 10), [])

    def test_clamping(self):
        result = parse_chapter_ranges("0-15", 10)
        self.assertEqual(result, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9])

    def test_invalid_input(self):
        self.assertEqual(parse_chapter_ranges("abc", 10), [])

    def test_duplicate_removal(self):
        result = parse_chapter_ranges("1, 1, 2, 2", 10)
        self.assertEqual(result, [0, 1])


if __name__ == "__main__":
    unittest.main()
