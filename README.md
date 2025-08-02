
# Audiobook Downloader and Tagger

This Python script downloads all chapters of an audiobook from `tokybook.com`, embeds metadata (title, author, narrator, etc.), and attaches cover art.

![Repo Stars](https://img.shields.io/github/stars/aviiciii/tokybook?style=social)
![Python](https://img.shields.io/badge/Python-3.7%2B-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Cross--Platform-009688?logo=windows&logoColor=white)
![License](https://img.shields.io/github/license/aviiciii/tokybook?color=orange)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)
![Issues](https://img.shields.io/github/issues/aviiciii/tokybook?color=informational)


## Features

* Downloads all chapters for a given audiobook URL.
* Prompts the user for audiobook details (URL, cover art, author, etc.).
* Automatically scrapes the book title.
* Embeds essential ID3 tags into each MP3 file for proper organization in media players.
* Saves the organized, tagged files into an `Audiobooks` folder in the script's directory.
* Displays a summary table of all metadata before starting the download.

---

## Setup and Installation

To run this script, you need [Python 3 ](https://www.python.org/downloads/)installed on your system.

### 1. Install Required Packages

First, you need to install the necessary Python libraries. This project includes a `requirements.txt` file that lists all the dependencies.

To install them, open your terminal or command prompt in the project directory and run the following command:

```bash
pip install -r requirements.txt
```

This command will read the `requirements.txt` file and automatically install all the necessary libraries.

## 2. Run the Script

Once the setup is complete, you can run the script from your terminal:

```bash
python main.py
```

The script will then prompt you to enter the following information:

* The Tokybook URL for the audiobook.
* A direct URL for the cover image.
* Optional details like the author, year, and narrator.

After you provide the details, it will display a summary table, and the download will begin with a progress bar for each chapter.

---

## Acknowledgements

This tool was made possible by the developers of the following open-source libraries:

* [SajaDevil/Tokybook-audiobook-downloader](https://github.com/SajaDevil/Tokybook-audiobook-downloader)
* **[Requests](https://requests.readthedocs.io/en/latest/)**
* **[Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)**
* **[Tqdm](https://github.com/tqdm/tqdm)**
* **[Mutagen](https://mutagen.readthedocs.io/en/latest/)**

A special thanks to the team behind `tokybook.com` for providing access to the audiobooks.
