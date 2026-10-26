# Creative Intelligence Toolkit

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-Multimodal-8E75B2.svg)](https://ai.google.dev/)
[![Playwright](https://img.shields.io/badge/Playwright-Automated%20Browser-2EAD33.svg)](https://playwright.dev/)
[![yt-dlp](https://img.shields.io/badge/yt--dlp-Media%20Scraper-red.svg)](https://github.com/yt-dlp/yt-dlp)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

An extensible, general-purpose Python pipeline designed to programmatically discover, download, analyze, and alert on digital advertising creatives using **Playwright**, **`yt-dlp`**, and Google's **Gemini models** (via Vertex AI or Google AI Studio).

This repository is structured into modular, brand-agnostic packages:
1. **`social_asset_downloader`**: High-performance scraping and downloading clients for YouTube, Facebook, Instagram, and TikTok.
2. **`creative_ai_analyzer`**: Multi-threaded, structured AI analysis on visual and textual creatives using Gemini.
3. **`social_intel_sources`**: Specialized wrappers for extracting Google Alerts RSS feeds and social media posts via Apify actors.
4. **`data_sinks`**: Generic export & alerting sinks for local CSV generation and Microsoft Teams / Slack webhooks.

---

## Folder Structure

```text
creative-intelligence-toolkit/
├── social_asset_downloader/          # Downloading module
│   ├── base.py                       # Abstract BaseDownloader
│   ├── yt_dlp.py                     # YtDlpDownloader (General/YouTube)
│   ├── playwright.py                 # IgFbDownloader (Instagram/Facebook via stealth Playwright)
│   └── snaptik.py                    # TtShopDownloader (TikTok via Snaptik)
│
├── creative_ai_analyzer/             # AI Analysis module
│   └── analyzer.py                   # CreativeAnalyzer (Gemini multi-threaded structured analysis)
│
├── social_intel_sources/             # Extraction Sources
│   ├── base.py                       # BaseSource
│   ├── rss.py                        # GoogleAlertsSource
│   └── apify.py                      # Apify platform scrapers (FB, IG, TikTok, YouTube)
│
├── data_sinks/                       # Export and alert sinks
│   ├── base.py                       # BaseSink
│   ├── local.py                      # LocalCSVSink
│   ├── teams.py                      # TeamsAlertSink
│   └── slack.py                      # SlackAlertSink
│
├── examples/                         # End-to-end and module demo scripts
│   ├── example_downloader.py         # Testing individual media downloaders
│   ├── example_analyzer.py           # Testing Gemini multimodal analysis
│   └── example_pipeline.py           # Testing complete extraction -> download -> analyze -> alert flow
│
├── tests/                            # Automated test suite (pytest)
├── downloaded_assets/                # Staging folder for downloaded media assets
├── reports/                          # Staging folder for generated CSV and JSON reports
├── pyproject.toml                    # Modern project configuration
├── requirements.txt                  # Direct dependency list
├── .env.example                      # Environment credentials template
└── LICENSE                           # Apache License, Version 2.0
```

---

## Quickstart & Installation

### 1. Prerequisites
- Python 3.10+
- (Optional but recommended) [`uv`](https://docs.astral.sh/uv/) for blazing-fast package management

### 2. Install Dependencies

Using `uv`:
```bash
uv sync --all-extras
```

Or using standard `pip`:
```bash
pip install -r requirements.txt
```

For downloaders using Playwright (Instagram, Facebook, TikTok), install the headless browser dependencies:
```bash
playwright install chromium
```

### 3. Configuration

Copy the environment template and configure your credentials:

```bash
cp .env.example .env
```

Open `.env` and fill in:
- `GEMINI_API_KEY`: For Google AI Studio (easiest way to test Gemini analysis).
- `APIFY_TOKEN`: For scraping social handles and hashtag feeds via Apify actors.
- `TEAMS_WEBHOOK_URL` / `SLACK_WEBHOOK_URL`: Optional webhooks for instant alert dispatching.

---

## Package Overview

### 1. Social Asset Downloader (`social_asset_downloader`)
Exposes downloading strategies conforming to `BaseDownloader` that fetch media files asynchronously:
- **`YtDlpDownloader`**: Uses `yt-dlp` to download video streams.
- **`IgFbDownloader`**: Uses Playwright in headless mode to render Instagram/Facebook pages and extract raw media URLs.
- **`TtShopDownloader`**: Automates Snaptik.app via Playwright to download TikTok videos without watermarks.

### 2. Creative AI Analyzer (`creative_ai_analyzer`)
Processes DataFrame records using Gemini:
- **Automatic Uploads**: Uploads local or remote HTTP files to the Gemini Files API and cleans them up after generation.
- **Robust Fallbacks**: Gracefully falls back to text-only analysis if a video or image URL is blocked/undownloadable.
- **Concurrency**: Leverages ThreadPools and deduplicates unique assets prior to analysis.

### 3. Social Intelligence Sources (`social_intel_sources`)
Ingests data from feeds and actor APIs:
- **`GoogleAlertsSource`**: Ingests Google Alerts RSS feeds mapped to markets/labels.
- **`ApifyInstagramSource` / `ApifyTikTokSource` / `ApifyFacebookSource` / `ApifyYouTubeSource`**: Parameterized Apify scrapers to query profiles, hashtags, or channels.

### 4. Data Sinks (`data_sinks`)
Handles downstream exports and notifications:
- **`LocalCSVSink`**: Saves structured results as timestamped CSVs in `reports/`.
- **`TeamsAlertSink` / `SlackAlertSink`**: Generates markdown digests and fires Webhooks to notify Teams/Slack channels.

---

## Testing & Verification

Run the automated pytest suite:

```bash
pytest tests/
```

Or run individual interactive example workflows in `examples/`:
1. **Test Media Downloading**:
   ```bash
   python examples/example_downloader.py
   ```
2. **Test Gemini Multimodal AI Analysis**:
   ```bash
   python examples/example_analyzer.py
   ```
3. **Test Full Pipeline (Extract $\to$ Download $\to$ Analyze $\to$ Alert)**:
   ```bash
   python examples/example_pipeline.py
   ```

---

## 📜 License
Licensed under the [Apache License, Version 2.0](LICENSE).
