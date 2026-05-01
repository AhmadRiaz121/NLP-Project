"""
data_fetcher.py — EarningsCall API Wrapper
Fetches transcripts, speakers, audio, slides, and calendar data for Apple & Microsoft.
Includes caching to minimize API calls.
"""

import os
import json
import hashlib
from datetime import datetime, date
from typing import Optional, Dict, List
from earningscall import get_company, get_calendar

# ─── CACHE ────────────────────────────────────────────────────────────────────
CACHE_DIR = os.path.join(os.path.dirname(__file__), ".cache")
os.makedirs(CACHE_DIR, exist_ok=True)

AUDIO_DIR = os.path.join(os.path.dirname(__file__), ".audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

SLIDES_DIR = os.path.join(os.path.dirname(__file__), ".slides")
os.makedirs(SLIDES_DIR, exist_ok=True)

SUPPORTED_TICKERS = {"AAPL": "Apple Inc.", "MSFT": "Microsoft Corp."}


def _cache_key(prefix: str, ticker: str, year: int, quarter: int, level: int = 1) -> str:
    return f"{prefix}_{ticker}_{year}_Q{quarter}_L{level}"


def _get_cached(key: str) -> Optional[dict]:
    path = os.path.join(CACHE_DIR, f"{key}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _set_cache(key: str, data: dict):
    path = os.path.join(CACHE_DIR, f"{key}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, default=str)


def get_supported_companies() -> List[Dict]:
    """Return list of supported companies."""
    return [
        {"ticker": "AAPL", "name": "Apple Inc."},
        {"ticker": "MSFT", "name": "Microsoft Corp."},
    ]


def get_company_events(ticker: str) -> List[Dict]:
    """Get all available earnings events for a company."""
    ticker = ticker.upper()
    if ticker not in SUPPORTED_TICKERS:
        raise ValueError(f"Only {list(SUPPORTED_TICKERS.keys())} are supported (free tier)")

    cache_key = f"events_{ticker}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    print(f"[data_fetcher] Fetching events for {ticker}...")
    company = get_company(ticker)
    events = []

    for event in company.events():
        # Skip future events
        if datetime.now().timestamp() < event.conference_date.timestamp():
            continue
        events.append({
            "year": event.year,
            "quarter": event.quarter,
            "conference_date": event.conference_date.isoformat(),
        })

    # Sort by date descending (most recent first)
    events.sort(key=lambda x: x["conference_date"], reverse=True)

    # Cache events list
    _set_cache(cache_key, events)
    return events


def get_transcript_text(ticker: str, year: int, quarter: int) -> Optional[str]:
    """Get plain transcript text (level=1)."""
    ticker = ticker.upper()
    cache_key = _cache_key("transcript", ticker, year, quarter, level=1)
    cached = _get_cached(cache_key)
    if cached:
        return cached.get("text")

    print(f"[data_fetcher] Fetching transcript for {ticker} Q{quarter} {year}...")
    company = get_company(ticker)
    transcript = company.get_transcript(year=year, quarter=quarter)

    if transcript and transcript.text:
        data = {"text": transcript.text}
        _set_cache(cache_key, data)
        return transcript.text
    return None


def get_speakers_with_info(ticker: str, year: int, quarter: int) -> List[Dict]:
    """Get transcript broken down by speaker with names and titles (level=2)."""
    ticker = ticker.upper()
    cache_key = _cache_key("speakers", ticker, year, quarter, level=2)
    cached = _get_cached(cache_key)
    if cached:
        return cached

    print(f"[data_fetcher] Fetching speakers for {ticker} Q{quarter} {year}...")
    company = get_company(ticker)
    transcript = company.get_transcript(year=year, quarter=quarter, level=2)

    if not transcript or not transcript.speakers:
        return []

    speakers = []
    for sp in transcript.speakers:
        speaker_data = {
            "speaker": getattr(sp, "speaker", "Unknown"),
            "text": getattr(sp, "text", ""),
        }
        # Try to get speaker info (name and title)
        if hasattr(sp, "speaker_info") and sp.speaker_info:
            speaker_data["name"] = getattr(sp.speaker_info, "name", "")
            speaker_data["title"] = getattr(sp.speaker_info, "title", "")
        else:
            speaker_data["name"] = speaker_data["speaker"]
            speaker_data["title"] = ""
        speakers.append(speaker_data)

    _set_cache(cache_key, speakers)
    return speakers


def get_word_timestamps(ticker: str, year: int, quarter: int) -> List[Dict]:
    """Get word-level timestamps (level=3)."""
    ticker = ticker.upper()
    cache_key = _cache_key("timestamps", ticker, year, quarter, level=3)
    cached = _get_cached(cache_key)
    if cached:
        return cached

    print(f"[data_fetcher] Fetching word timestamps for {ticker} Q{quarter} {year}...")
    company = get_company(ticker)
    transcript = company.get_transcript(year=year, quarter=quarter, level=3)

    if not transcript or not transcript.speakers:
        return []

    speakers_data = []
    for sp in transcript.speakers:
        words = list(getattr(sp, "words", []))
        start_times = list(getattr(sp, "start_times", []))

        words_with_times = []
        for w, t in zip(words, start_times):
            words_with_times.append({"word": w, "start_time": t})

        speaker_name = getattr(sp, "speaker", "Unknown")
        name = speaker_name
        title = ""
        if hasattr(sp, "speaker_info") and sp.speaker_info:
            name = getattr(sp.speaker_info, "name", speaker_name)
            title = getattr(sp.speaker_info, "title", "")

        speakers_data.append({
            "speaker": speaker_name,
            "name": name,
            "title": title,
            "words_with_times": words_with_times,
        })

    _set_cache(cache_key, speakers_data)
    return speakers_data


def get_prepared_remarks_and_qa(ticker: str, year: int, quarter: int) -> Optional[Dict]:
    """Get prepared remarks and Q&A sections (level=4)."""
    ticker = ticker.upper()
    cache_key = _cache_key("remarks_qa", ticker, year, quarter, level=4)
    cached = _get_cached(cache_key)
    if cached:
        return cached

    print(f"[data_fetcher] Fetching remarks & Q&A for {ticker} Q{quarter} {year}...")
    company = get_company(ticker)
    transcript = company.get_transcript(year=year, quarter=quarter, level=4)

    if not transcript:
        return None

    data = {
        "prepared_remarks": getattr(transcript, "prepared_remarks", "") or "",
        "questions_and_answers": getattr(transcript, "questions_and_answers", "") or "",
    }

    _set_cache(cache_key, data)
    return data


def download_audio(ticker: str, year: int, quarter: int) -> Optional[str]:
    """Download audio file and return its local path."""
    ticker = ticker.upper()
    filename = f"{ticker}-Q{quarter}-{year}.mp3"
    filepath = os.path.join(AUDIO_DIR, filename)

    if os.path.exists(filepath):
        print(f"[data_fetcher] Audio already cached: {filepath}")
        return filepath

    print(f"[data_fetcher] Downloading audio for {ticker} Q{quarter} {year}...")
    company = get_company(ticker)
    try:
        result = company.download_audio_file(year=year, quarter=quarter, file_name=filepath)
        if result and os.path.exists(filepath):
            return filepath
        # Sometimes the API returns the path differently
        if result and os.path.exists(str(result)):
            return str(result)
    except Exception as e:
        print(f"[data_fetcher] Audio download failed: {e}")
    return None


def download_slides(ticker: str, year: int, quarter: int) -> Optional[str]:
    """Download slide deck PDF and return its local path."""
    ticker = ticker.upper()
    filename = f"{ticker}-Q{quarter}-{year}-Slides.pdf"
    filepath = os.path.join(SLIDES_DIR, filename)

    if os.path.exists(filepath):
        print(f"[data_fetcher] Slides already cached: {filepath}")
        return filepath

    print(f"[data_fetcher] Downloading slides for {ticker} Q{quarter} {year}...")
    company = get_company(ticker)
    try:
        result = company.download_slide_deck(year=year, quarter=quarter, file_name=filepath)
        if result and os.path.exists(filepath):
            return filepath
        if result and os.path.exists(str(result)):
            return str(result)
    except Exception as e:
        print(f"[data_fetcher] Slides download failed: {e}")
    return None


def get_earnings_calendar(target_date: str) -> List[Dict]:
    """Get earnings event calendar for a specific date."""
    cache_key = f"calendar_{target_date}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    print(f"[data_fetcher] Fetching calendar for {target_date}...")
    try:
        dt = date.fromisoformat(target_date)
        calendar = get_calendar(dt)
        events = []
        for event in calendar:
            events.append({
                "company_name": getattr(event, "company_name", ""),
                "quarter": getattr(event, "quarter", 0),
                "year": getattr(event, "year", 0),
                "conference_date": str(getattr(event, "conference_date", "")),
                "transcript_ready": getattr(event, "transcript_ready", False),
            })
        _set_cache(cache_key, events)
        return events
    except Exception as e:
        print(f"[data_fetcher] Calendar fetch failed: {e}")
        return []
