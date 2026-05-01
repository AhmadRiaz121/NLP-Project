# """
# main.py — FastAPI Server for EarningsEdge Dashboard
# REST endpoints + WebSocket for real-time audio analysis streaming.
# """

# import os
# import json
# import asyncio
# import numpy as np
# from typing import Optional
# from contextlib import asynccontextmanager

# from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import FileResponse, JSONResponse
# from dotenv import load_dotenv

# load_dotenv()

# # Local modules
# from data_fetcher import (
#     get_supported_companies, get_company_events, get_transcript_text,
#     get_speakers_with_info, get_word_timestamps, get_prepared_remarks_and_qa,
#     download_audio, download_slides, get_earnings_calendar, SUPPORTED_TICKERS,
# )
# from analysis import (
#     analyze_full_text, analyze_speaker_segments, compute_overall_metrics,
#     analyze_sentiment, detect_hedging, detect_confidence, detect_hesitations,
#     calculate_snr, calculate_audio_snr, analyze_sentiment_batch, split_into_sentences,
# )
# from audio_processor import (
#     load_audio, get_audio_info, chunk_audio, build_timed_segments,
#     compute_chunk_audio_features,
# )
# from slide_analyzer import analyze_slide_deck
# from transcriber import transcribe_audio, build_transcribed_segments, diarize_audio


# # ─── LIFESPAN: Pre-load FinBERT on startup ──────────────────────────────────
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     print("[server] Starting EarningsEdge Backend...")
#     # Pre-load FinBERT model in background
#     from analysis import get_finbert
#     try:
#         get_finbert()
#     except Exception as e:
#         print(f"[server] FinBERT pre-load warning: {e}")
#     print("[server] Ready.")
#     yield
#     print("[server] Shutting down.")


# app = FastAPI(
#     title="EarningsEdge API",
#     description="Real-time earnings call NLP analysis",
#     version="1.0.0",
#     lifespan=lifespan,
# )

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# # ─── REST ENDPOINTS ──────────────────────────────────────────────────────────

# @app.get("/api/companies")
# async def list_companies():
#     """List supported companies."""
#     return get_supported_companies()


# @app.get("/api/events/{ticker}")
# async def list_events(ticker: str):
#     """Get available earnings events for a company."""
#     ticker = ticker.upper()
#     if ticker not in SUPPORTED_TICKERS:
#         raise HTTPException(400, f"Only {list(SUPPORTED_TICKERS.keys())} supported")
#     try:
#         events = get_company_events(ticker)
#         return {"ticker": ticker, "name": SUPPORTED_TICKERS[ticker], "events": events}
#     except Exception as e:
#         raise HTTPException(500, str(e))


# @app.get("/api/analyze/{ticker}/{year}/{quarter}")
# async def analyze_transcript(ticker: str, year: int, quarter: int):
#     """Full transcript analysis with FinBERT sentiment, hedging, SNR."""
#     ticker = ticker.upper()
#     if ticker not in SUPPORTED_TICKERS:
#         raise HTTPException(400, f"Only {list(SUPPORTED_TICKERS.keys())} supported")

#     # Get speakers with info
#     speakers = get_speakers_with_info(ticker, year, quarter)
#     if not speakers:
#         raise HTTPException(404, "No transcript data found")

#     # Run NLP analysis on each speaker
#     speaker_results = analyze_speaker_segments(speakers)

#     # Compute overall metrics
#     overall = compute_overall_metrics(speaker_results)

#     # Get plain transcript for sentence-level timeline
#     transcript_text = get_transcript_text(ticker, year, quarter)
#     sentences = split_into_sentences(transcript_text) if transcript_text else []

#     # Analyze sentences in batches for sentiment timeline
#     timeline = []
#     if sentences:
#         batch_size = 30
#         for i in range(0, min(len(sentences), 150), batch_size):
#             batch = sentences[i:i + batch_size]
#             batch_sentiments = analyze_sentiment_batch(batch)
#             for j, (sent, analysis) in enumerate(zip(batch, batch_sentiments)):
#                 timeline.append({
#                     "index": i + j,
#                     "text": sent[:200],
#                     "sentiment": analysis["score"],
#                     "label": analysis["label"],
#                     "confidence": analysis.get("confidence", 0),
#                 })

#     return {
#         "ticker": ticker,
#         "company": SUPPORTED_TICKERS[ticker],
#         "year": year,
#         "quarter": quarter,
#         "speakers": speaker_results,
#         "overall": overall,
#         "sentiment_timeline": timeline,
#         "total_sentences": len(sentences),
#     }


# @app.get("/api/remarks/{ticker}/{year}/{quarter}")
# async def analyze_remarks(ticker: str, year: int, quarter: int):
#     """Analyze prepared remarks vs Q&A separately."""
#     ticker = ticker.upper()
#     if ticker not in SUPPORTED_TICKERS:
#         raise HTTPException(400, f"Only {list(SUPPORTED_TICKERS.keys())} supported")

#     data = get_prepared_remarks_and_qa(ticker, year, quarter)
#     if not data:
#         raise HTTPException(404, "No remarks/Q&A data found")

#     remarks_text = data.get("prepared_remarks", "")
#     qa_text = data.get("questions_and_answers", "")

#     # Analyze each section
#     remarks_analysis = analyze_full_text(remarks_text) if remarks_text else None
#     qa_analysis = analyze_full_text(qa_text) if qa_text else None

#     # Sentence-level timelines for each
#     remarks_sentences = split_into_sentences(remarks_text)
#     qa_sentences = split_into_sentences(qa_text)

#     remarks_timeline = []
#     if remarks_sentences:
#         sentiments = analyze_sentiment_batch(remarks_sentences[:80])
#         for i, (s, a) in enumerate(zip(remarks_sentences[:80], sentiments)):
#             remarks_timeline.append({"index": i, "text": s[:200], "sentiment": a["score"], "label": a["label"]})

#     qa_timeline = []
#     if qa_sentences:
#         sentiments = analyze_sentiment_batch(qa_sentences[:80])
#         for i, (s, a) in enumerate(zip(qa_sentences[:80], sentiments)):
#             qa_timeline.append({"index": i, "text": s[:200], "sentiment": a["score"], "label": a["label"]})

#     return {
#         "ticker": ticker,
#         "year": year,
#         "quarter": quarter,
#         "prepared_remarks": {
#             "text_preview": remarks_text[:500] + "..." if len(remarks_text) > 500 else remarks_text,
#             "analysis": remarks_analysis,
#             "timeline": remarks_timeline,
#             "sentence_count": len(remarks_sentences),
#         },
#         "qa": {
#             "text_preview": qa_text[:500] + "..." if len(qa_text) > 500 else qa_text,
#             "analysis": qa_analysis,
#             "timeline": qa_timeline,
#             "sentence_count": len(qa_sentences),
#         },
#     }


# @app.get("/api/slides/{ticker}/{year}/{quarter}")
# async def analyze_slides_endpoint(ticker: str, year: int, quarter: int):
#     """Download and analyze slide deck with Mistral AI."""
#     ticker = ticker.upper()
#     if ticker not in SUPPORTED_TICKERS:
#         raise HTTPException(400, f"Only {list(SUPPORTED_TICKERS.keys())} supported")

#     filepath = download_slides(ticker, year, quarter)
#     quarter_str = f"Q{quarter} {year}"
#     result = analyze_slide_deck(filepath, SUPPORTED_TICKERS[ticker], quarter_str)
#     return {"ticker": ticker, "year": year, "quarter": quarter, **result}


# @app.get("/api/calendar")
# async def get_calendar_endpoint(date: str = Query(default="2025-01-10")):
#     """Get earnings event calendar."""
#     events = get_earnings_calendar(date)
#     return {"date": date, "events": events}


# @app.get("/api/audio/{ticker}/{year}/{quarter}")
# async def serve_audio(ticker: str, year: int, quarter: int):
#     """Download and serve audio file."""
#     ticker = ticker.upper()
#     filepath = download_audio(ticker, year, quarter)
#     if not filepath or not os.path.exists(filepath):
#         raise HTTPException(404, "Audio file not available")
#     return FileResponse(filepath, media_type="audio/mpeg", filename=os.path.basename(filepath))


# @app.get("/api/audio-info/{ticker}/{year}/{quarter}")
# async def audio_info(ticker: str, year: int, quarter: int):
#     """Get audio file metadata."""
#     ticker = ticker.upper()
#     filepath = download_audio(ticker, year, quarter)
#     if not filepath:
#         raise HTTPException(404, "Audio file not available")
#     info = get_audio_info(filepath)
#     return {"ticker": ticker, "year": year, "quarter": quarter, **info}


# @app.get("/api/timestamps/{ticker}/{year}/{quarter}")
# async def get_timestamps(ticker: str, year: int, quarter: int):
#     """Get word-level timestamps."""
#     ticker = ticker.upper()
#     data = get_word_timestamps(ticker, year, quarter)
#     if not data:
#         raise HTTPException(404, "No timestamp data found")
#     return {"ticker": ticker, "year": year, "quarter": quarter, "speakers": data}


# # ─── WEBSOCKET: Real-Time Audio Analysis Stream ─────────────────────────────

# @app.websocket("/ws/realtime/{ticker}/{year}/{quarter}")
# async def realtime_analysis(websocket: WebSocket, ticker: str, year: int, quarter: int):
#     await websocket.accept()
#     ticker = ticker.upper()

#     try:
#         await websocket.send_json({"type": "status", "message": "Preparing real-time analysis (Whisper)..."})

#         # 1. Download audio – we need it for transcription AND playback
#         audio_path = download_audio(ticker, year, quarter)
#         if not audio_path:
#             await websocket.send_json({"type": "error", "message": "No audio file available"})
#             await websocket.close()
#             return

#         # 2. Transcribe with Whisper
#         segments = None
#         audio_obj = load_audio(audio_path)
#         audio_duration = len(audio_obj) / 1000.0 if audio_obj else 0.0

#         # Try Whisper, fallback to API timestamps
#         transcription = None
#         try:
#             transcription = transcribe_audio(audio_path)
#             print(f"[ws] Whisper transcription: {len(transcription)} segments")
#         except Exception as e:
#             print(f"[ws] Whisper failed: {e}")
#             # Fallback to original word timestamps
#             word_data = get_word_timestamps(ticker, year, quarter)
#             if word_data:
#                 segments = build_timed_segments(word_data, segment_duration=2.0, audio_duration=audio_duration)
#             else:
#                 await websocket.send_json({"type": "error", "message": "Transcription unavailable"})
#                 await websocket.close()
#                 return

#         if transcription and not segments:
#             # 3. Optional speaker diarisation
#             diarization = None
#             try:
#                 diarization = diarize_audio(audio_path)
#             except:
#                 pass

#             # 4. Build 2‑second segments from transcription
#             segments = build_transcribed_segments(transcription, diarization, segment_duration=2.0)

#         if not segments:
#             await websocket.send_json({"type": "error", "message": "No segments generated"})
#             await websocket.close()
#             return

#         await websocket.send_json({
#             "type": "init",
#             "total_segments": len(segments),
#             "total_duration": audio_duration or (segments[-1]["end_time"] if segments else 0),
#             "audio_available": True,
#             "engine": "whisper" if transcription else "api",
#         })

#         # Wait for client "play"
#         while True:
#             msg = await websocket.receive_text()
#             if msg == "play":
#                 break

#         # 5. Real-time streaming
#         cumulative_text_parts = []
#         speaker_text_accum = {}
#         start_time_real = asyncio.get_event_loop().time()
#         audio_chunks = chunk_audio(audio_obj, chunk_seconds=2.0) if audio_obj else []

#         for i, seg in enumerate(segments):
#             # Collect words from this segment
#             text = seg.get("text", "")
#             if text:
#                 cumulative_text_parts.append(text)

#             # Maintain speaker accumulators
#             for sp_data in seg.get("speakers", []):
#                 sp = sp_data["speaker"]
#                 if sp not in speaker_text_accum:
#                     speaker_text_accum[sp] = {"name": sp, "title": "", "words": []}
#                 speaker_text_accum[sp]["words"].extend(sp_data["text"].split())

#             cum_text = " ".join(cumulative_text_parts)

#             # NLP on cumulative text
#             if cum_text and len(cum_text.strip()) > 3:
#                 sentiment = analyze_sentiment(cum_text)
#                 hedging = detect_hedging(cum_text)
#                 confidence = detect_confidence(cum_text)
#                 hesitations = detect_hesitations(cum_text)
#                 snr = calculate_snr(sentiment, hedging, confidence, hesitations)
#             else:
#                 sentiment = {"label": "neutral", "score": 0.0, "confidence": 0.0}
#                 hedging = {"hedge_density": 0.0, "hedge_count": 0, "total_noise_density": 0.0}
#                 confidence = {"confidence_density": 0.0, "confidence_word_count": 0}
#                 hesitations = {"hesitation_count": 0, "hesitation_density": 0.0}
#                 snr = {"snr_db": 0.0, "quality": "N/A", "signal_power": 0, "noise_power": 0}

#             # Audio features for the corresponding chunk
#             audio_features = {}
#             if i < len(audio_chunks):
#                 chunk = audio_chunks[i]
#                 audio_features = compute_chunk_audio_features(chunk["samples"], chunk["sample_rate"])
#                 audio_features["audio_snr"] = calculate_audio_snr(chunk["samples"], chunk["sample_rate"])

#             # Build speaker list
#             current_speakers = [
#                 {"speaker": sp, "name": info["name"], "title": info["title"], "text": " ".join(info["words"])}
#                 for sp, info in speaker_text_accum.items()
#             ]
#             primary_speaker = seg.get("primary_speaker", "Unknown")
#             primary_info = speaker_text_accum.get(primary_speaker, {"name": primary_speaker, "title": ""})

#             await websocket.send_json({
#                 "type": "segment",
#                 "index": i,
#                 "start_time": seg["start_time"],
#                 "end_time": seg["end_time"],
#                 "text": text,                    # only this segment's new words
#                 "cumulative_text": cum_text[-500:],
#                 "primary_speaker": primary_info.get("name", primary_speaker),
#                 "primary_speaker_title": primary_info.get("title", ""),
#                 "speakers": current_speakers,
#                 "word_count": seg.get("word_count", 0),
#                 "sentiment": sentiment,
#                 "hedging": {
#                     "hedge_density": hedging.get("hedge_density", 0),
#                     "hedge_count": hedging.get("hedge_count", 0),
#                     "total_noise_density": hedging.get("total_noise_density", 0),
#                     "hedge_words": hedging.get("hedge_words", [])[:5],
#                 },
#                 "confidence": {
#                     "confidence_density": confidence.get("confidence_density", 0),
#                     "confidence_word_count": confidence.get("confidence_word_count", 0),
#                 },
#                 "hesitations": {
#                     "hesitation_count": hesitations.get("hesitation_count", 0),
#                     "hesitation_density": hesitations.get("hesitation_density", 0),
#                 },
#                 "snr": snr,
#                 "audio_features": audio_features,
#                 "cumulative": {
#                     "composite_score": round(float(np.mean([s.get("score", 0) for s in [sentiment]])), 4),
#                     "avg_hedge_density": round(float(hedging.get("hedge_density", 0)), 4),
#                     "avg_snr_db": snr.get("snr_db", 0),
#                     "segments_processed": i + 1,
#                 },
#             })

#             # Wait until the segment's end time in real life
#             elapsed = asyncio.get_event_loop().time() - start_time_real
#             sleep_time = seg["end_time"] - elapsed
#             if sleep_time > 0:
#                 try:
#                     msg = await asyncio.wait_for(websocket.receive_text(), timeout=sleep_time)
#                     if msg == "stop":
#                         break
#                 except asyncio.TimeoutError:
#                     pass

#         # Final cumulative summary
#         final_sent = sentiment.get("score", 0) if sentiment else 0
#         final_snr = snr.get("snr_db", 0) if snr else 0
#         final_hedge = hedging.get("hedge_density", 0) if hedging else 0

#         await websocket.send_json({
#             "type": "complete",
#             "final_composite": round(float(final_sent), 4),
#             "final_snr": round(float(final_snr), 2),
#             "final_hedge": round(float(final_hedge), 4),
#         })

#     except WebSocketDisconnect:
#         print(f"[ws] Client disconnected: {ticker} Q{quarter} {year}")
#     except Exception as e:
#         print(f"[ws] Error: {e}")
#         try:
#             await websocket.send_json({"type": "error", "message": str(e)})
#         except:
#             pass


# # ─── HEALTH CHECK ─────────────────────────────────────────────────────────────
# @app.get("/api/health")
# async def health():
#     return {"status": "ok", "service": "EarningsEdge API"}


# # ─── RUN ──────────────────────────────────────────────────────────────────────
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)




# Deepseek
"""
main.py — FastAPI Server for EarningsEdge Dashboard
REST endpoints + WebSocket for real-time audio analysis streaming.
"""

import os
import json
import asyncio
import math
import re
import numpy as np
from typing import Optional, List, Dict
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv

load_dotenv()

# Local modules
from data_fetcher import (
    get_supported_companies, get_company_events, get_transcript_text,
    get_speakers_with_info, get_word_timestamps, get_prepared_remarks_and_qa,
    download_audio, download_slides, get_earnings_calendar, SUPPORTED_TICKERS,
)
from analysis import (
    analyze_full_text, analyze_speaker_segments, compute_overall_metrics,
    analyze_sentiment, detect_hedging, detect_confidence, detect_hesitations,
    calculate_snr, calculate_audio_snr, analyze_sentiment_batch, split_into_sentences,
)
from audio_processor import (
    load_audio, get_audio_info, chunk_audio, build_timed_segments,
    compute_chunk_audio_features,
)
from slide_analyzer import analyze_slide_deck
from transcriber import iter_transcribe_audio, transcribe_audio, build_transcribed_segments

INSIGHTS_CACHE_DIR = os.path.join(os.path.dirname(__file__), ".cache")
os.makedirs(INSIGHTS_CACHE_DIR, exist_ok=True)


def _insights_cache_key(ticker: str, year: int, quarter: int, watchlist: List[str]) -> str:
    wl = "-".join(sorted(set(watchlist)))
    return f"insights_{ticker}_{year}_Q{quarter}_{wl or 'default'}"


def _get_insights_cached(key: str) -> Optional[dict]:
    path = os.path.join(INSIGHTS_CACHE_DIR, f"{key}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _set_insights_cache(key: str, data: dict) -> None:
    path = os.path.join(INSIGHTS_CACHE_DIR, f"{key}.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        print(f"[insights] cache write failed: {e}")


def enhance_with_speaker_names(
    segments: List[Dict],
    word_timestamps: List[Dict],
) -> List[Dict]:
    """Map Whisper segments to real speaker names using timestamp overlap."""
    if not word_timestamps:
        return segments

    words = []
    for speaker_data in word_timestamps:
        speaker_id = speaker_data.get("speaker", "Unknown")
        name = speaker_data.get("name", speaker_id)
        title = speaker_data.get("title", "")
        for wt in speaker_data.get("words_with_times", []):
            t = wt.get("start_time")
            if isinstance(t, (int, float)):
                words.append(
                    {
                        "start_time": float(t),
                        "speaker": speaker_id,
                        "name": name,
                        "title": title,
                    }
                )

    if not words:
        return segments

    words.sort(key=lambda x: x["start_time"])

    for seg in segments:
        seg_start = seg.get("start_time", 0.0)
        seg_end = seg.get("end_time", seg_start + 2.0)
        seg_words = [w for w in words if seg_start <= w["start_time"] < seg_end]
        if not seg_words:
            continue

        speaker_counts = {}
        speaker_info = {}
        for w in seg_words:
            key = w["speaker"]
            speaker_counts[key] = speaker_counts.get(key, 0) + 1
            speaker_info[key] = {"name": w["name"], "title": w["title"]}

        primary_speaker = max(speaker_counts.items(), key=lambda x: x[1])[0]
        primary_info = speaker_info[primary_speaker]

        seg["primary_speaker"] = primary_info["name"]
        seg["primary_speaker_title"] = primary_info["title"]
        seg["speakers"] = [
            {
                "speaker": spk,
                "name": info["name"],
                "title": info["title"],
                "text": seg.get("text", ""),
            }
            for spk, info in speaker_info.items()
        ]

    return segments


def _flatten_timestamp_words(word_timestamps: List[Dict]) -> List[Dict]:
    words = []
    for speaker_data in word_timestamps:
        speaker_id = speaker_data.get("speaker", "Unknown")
        name = speaker_data.get("name", speaker_id)
        title = speaker_data.get("title", "")
        for wt in speaker_data.get("words_with_times", []):
            t = wt.get("start_time")
            w = wt.get("word", "")
            if isinstance(t, (int, float)) and w:
                words.append(
                    {
                        "word": w,
                        "start_time": float(t),
                        "speaker": speaker_id,
                        "name": name,
                        "title": title,
                    }
                )
    words.sort(key=lambda x: x["start_time"])
    return words


def _build_segments_from_transcription_chunk(
    chunk_transcription_segments: List[Dict],
    segment_duration: float = 2.0,
) -> List[Dict]:
    """Create 2s real-time segments from a single Whisper chunk result."""
    timeline_words = []
    for seg in chunk_transcription_segments:
        text = seg.get("text", "").strip()
        words = text.split()
        if not words:
            continue
        seg_start = float(seg.get("start", 0.0))
        seg_end = float(seg.get("end", seg_start))
        dur = max(seg_end - seg_start, 0.01)
        per_word = dur / len(words)
        for i, word in enumerate(words):
            timeline_words.append(
                {
                    "word": word,
                    "start_time": seg_start + (i * per_word),
                }
            )

    if not timeline_words:
        return []

    grouped = {}
    for w in timeline_words:
        seg_index = int(w["start_time"] // segment_duration)
        grouped.setdefault(seg_index, []).append(w)

    out = []
    for seg_index in sorted(grouped.keys()):
        seg_words = grouped[seg_index]
        seg_start = seg_index * segment_duration
        seg_end = seg_start + segment_duration
        out.append(
            {
                "index": seg_index,
                "start_time": round(seg_start, 2),
                "end_time": round(seg_end, 2),
                "text": " ".join(w["word"] for w in seg_words),
                "speakers": [],
                "word_count": len(seg_words),
                "primary_speaker": "Unknown",
                "primary_speaker_title": "",
            }
        )
    return out


def _attach_speakers_for_segments(segments: List[Dict], timestamp_words: List[Dict]) -> List[Dict]:
    if not timestamp_words:
        return segments

    for seg in segments:
        seg_start = seg.get("start_time", 0.0)
        seg_end = seg.get("end_time", seg_start + 2.0)
        words = [w for w in timestamp_words if seg_start <= w["start_time"] < seg_end]
        if not words:
            continue

        speaker_counts = {}
        speaker_info = {}
        speaker_words = {}
        for w in words:
            sp = w["speaker"]
            speaker_counts[sp] = speaker_counts.get(sp, 0) + 1
            speaker_info[sp] = {"name": w["name"], "title": w["title"]}
            speaker_words.setdefault(sp, []).append(w["word"])

        primary_id = max(speaker_counts.items(), key=lambda x: x[1])[0]
        primary_info = speaker_info[primary_id]
        seg["primary_speaker"] = primary_info["name"]
        seg["primary_speaker_title"] = primary_info["title"]
        seg["speakers"] = [
            {
                "speaker": sp,
                "name": info["name"],
                "title": info["title"],
                "text": " ".join(speaker_words.get(sp, [])) or seg.get("text", ""),
            }
            for sp, info in speaker_info.items()
        ]

    return segments


def _extract_metrics(text: str) -> Dict:
    dollar_values = re.findall(r"\$[\d,.]+(?:\s?(?:billion|million|B|M))?", text, flags=re.IGNORECASE)
    percentages = re.findall(r"\b\d+(?:\.\d+)?%", text)
    guidance_lines = [
        s.strip() for s in split_into_sentences(text)
        if any(k in s.lower() for k in ["guidance", "outlook", "expect", "forecast", "next quarter", "full year"])
    ][:15]
    return {
        "dollar_values": dollar_values[:30],
        "percentages": percentages[:30],
        "guidance_mentions": guidance_lines,
    }


def _extract_questions(qa_text: str) -> List[str]:
    if not qa_text:
        return []
    chunks = re.split(r"(?<=[?])\s+", qa_text)
    questions = [c.strip() for c in chunks if "?" in c and len(c.strip()) > 20]
    return questions[:40]


def _question_quality(question: str) -> Dict:
    q_lower = question.lower()
    specificity = min(len(question.split()) / 30.0, 1.0)
    has_numbers = 1.0 if re.search(r"\d", question) else 0.0
    strategic_terms = ["margin", "guidance", "capex", "ai", "growth", "demand", "pricing", "outlook", "risk"]
    strategic_hits = sum(1 for t in strategic_terms if t in q_lower)
    directness = 1.0 if q_lower.startswith(("why", "how", "what", "when", "can you")) else 0.6
    score = (0.35 * specificity) + (0.25 * has_numbers) + (0.25 * min(strategic_hits / 3.0, 1.0)) + (0.15 * directness)
    return {
        "question": question,
        "score": round(float(score), 3),
        "label": "high" if score > 0.72 else "medium" if score > 0.48 else "low",
    }


def _build_key_moments(transcript_text: str, total_duration: float, timestamp_words: List[Dict]) -> List[Dict]:
    # Prefer timestamp-aligned windows for accurate timeline placement.
    windows = []
    if timestamp_words:
        window_sec = 20.0
        max_t = max((w.get("start_time", 0.0) for w in timestamp_words), default=0.0)
        t = 0.0
        while t <= max_t:
            chunk = [w for w in timestamp_words if t <= w.get("start_time", -1) < (t + window_sec)]
            if chunk:
                windows.append(
                    {
                        "time_sec": round(t, 2),
                        "text": " ".join(w.get("word", "") for w in chunk if w.get("word", "")),
                    }
                )
            t += window_sec

    if not windows:
        sentences = split_into_sentences(transcript_text)[:140]
        if not sentences:
            return []
        denom = max(len(sentences), 1)
        windows = [
            {
                "time_sec": round((idx / denom) * max(total_duration, 1), 2),
                "text": sentence,
            }
            for idx, sentence in enumerate(sentences)
        ]

    texts = [w["text"] for w in windows]
    sentiments = analyze_sentiment_batch(texts)
    moments = []
    for window, sent in zip(windows, sentiments):
        sentence = window["text"]
        hedge = detect_hedging(sentence)
        conf = detect_confidence(sentence)
        risk_words = sum(sentence.lower().count(k) for k in ["risk", "uncertain", "pressure", "headwind"])
        is_event = (
            abs(sent.get("score", 0)) >= 0.72
            or hedge.get("hedge_density", 0) >= 0.08
            or conf.get("confidence_density", 0) >= 0.04
            or risk_words > 0
        )
        if not is_event:
            continue
        time_sec = window["time_sec"]
        moments.append(
            {
                "time_sec": time_sec,
                "time_label": f"{int(time_sec // 60):02d}:{int(time_sec % 60):02d}",
                "text": sentence[:260],
                "sentiment": sent.get("score", 0),
                "hedge_density": hedge.get("hedge_density", 0),
                "confidence_density": conf.get("confidence_density", 0),
                "event_type": (
                    "risk" if risk_words > 0 else
                    "positive_spike" if sent.get("score", 0) > 0.7 else
                    "negative_spike" if sent.get("score", 0) < -0.7 else
                    "uncertainty_spike" if hedge.get("hedge_density", 0) >= 0.08 else
                    "confidence_spike"
                ),
            }
        )
    return moments[:40]


# ─── LIFESPAN: Pre-load FinBERT on startup ──────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[server] Starting EarningsEdge Backend...")
    from analysis import get_finbert
    try:
        get_finbert()
    except Exception as e:
        print(f"[server] FinBERT pre-load warning: {e}")
    print("[server] Ready.")
    yield
    print("[server] Shutting down.")


app = FastAPI(
    title="EarningsEdge API",
    description="Real-time earnings call NLP analysis",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── REST ENDPOINTS ──────────────────────────────────────────────────────────

@app.get("/api/companies")
async def list_companies():
    return get_supported_companies()


@app.get("/api/events/{ticker}")
async def list_events(ticker: str):
    ticker = ticker.upper()
    if ticker not in SUPPORTED_TICKERS:
        raise HTTPException(400, f"Only {list(SUPPORTED_TICKERS.keys())} supported")
    try:
        events = get_company_events(ticker)
        return {"ticker": ticker, "name": SUPPORTED_TICKERS[ticker], "events": events}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/analyze/{ticker}/{year}/{quarter}")
async def analyze_transcript(ticker: str, year: int, quarter: int):
    ticker = ticker.upper()
    if ticker not in SUPPORTED_TICKERS:
        raise HTTPException(400, f"Only {list(SUPPORTED_TICKERS.keys())} supported")

    speakers = get_speakers_with_info(ticker, year, quarter)
    if not speakers:
        raise HTTPException(404, "No transcript data found")

    speaker_results = analyze_speaker_segments(speakers)
    overall = compute_overall_metrics(speaker_results)

    transcript_text = get_transcript_text(ticker, year, quarter)
    sentences = split_into_sentences(transcript_text) if transcript_text else []

    timeline = []
    if sentences:
        batch_size = 30
        for i in range(0, min(len(sentences), 150), batch_size):
            batch = sentences[i:i + batch_size]
            batch_sentiments = analyze_sentiment_batch(batch)
            for j, (sent, analysis) in enumerate(zip(batch, batch_sentiments)):
                timeline.append({
                    "index": i + j,
                    "text": sent[:200],
                    "sentiment": analysis["score"],
                    "label": analysis["label"],
                    "confidence": analysis.get("confidence", 0),
                })

    return {
        "ticker": ticker,
        "company": SUPPORTED_TICKERS[ticker],
        "year": year,
        "quarter": quarter,
        "speakers": speaker_results,
        "overall": overall,
        "sentiment_timeline": timeline,
        "total_sentences": len(sentences),
    }


@app.get("/api/remarks/{ticker}/{year}/{quarter}")
async def analyze_remarks(ticker: str, year: int, quarter: int):
    ticker = ticker.upper()
    if ticker not in SUPPORTED_TICKERS:
        raise HTTPException(400, f"Only {list(SUPPORTED_TICKERS.keys())} supported")

    data = get_prepared_remarks_and_qa(ticker, year, quarter)
    if not data:
        raise HTTPException(404, "No remarks/Q&A data found")

    remarks_text = data.get("prepared_remarks", "")
    qa_text = data.get("questions_and_answers", "")

    remarks_analysis = analyze_full_text(remarks_text) if remarks_text else None
    qa_analysis = analyze_full_text(qa_text) if qa_text else None

    remarks_sentences = split_into_sentences(remarks_text)
    qa_sentences = split_into_sentences(qa_text)

    remarks_timeline = []
    if remarks_sentences:
        sentiments = analyze_sentiment_batch(remarks_sentences[:80])
        for i, (s, a) in enumerate(zip(remarks_sentences[:80], sentiments)):
            remarks_timeline.append({"index": i, "text": s[:200], "sentiment": a["score"], "label": a["label"]})

    qa_timeline = []
    if qa_sentences:
        sentiments = analyze_sentiment_batch(qa_sentences[:80])
        for i, (s, a) in enumerate(zip(qa_sentences[:80], sentiments)):
            qa_timeline.append({"index": i, "text": s[:200], "sentiment": a["score"], "label": a["label"]})

    return {
        "ticker": ticker,
        "year": year,
        "quarter": quarter,
        "prepared_remarks": {
            "text_preview": remarks_text[:500] + "..." if len(remarks_text) > 500 else remarks_text,
            "analysis": remarks_analysis,
            "timeline": remarks_timeline,
            "sentence_count": len(remarks_sentences),
        },
        "qa": {
            "text_preview": qa_text[:500] + "..." if len(qa_text) > 500 else qa_text,
            "analysis": qa_analysis,
            "timeline": qa_timeline,
            "sentence_count": len(qa_sentences),
        },
    }


@app.get("/api/slides/{ticker}/{year}/{quarter}")
async def analyze_slides_endpoint(ticker: str, year: int, quarter: int):
    ticker = ticker.upper()
    if ticker not in SUPPORTED_TICKERS:
        raise HTTPException(400, f"Only {list(SUPPORTED_TICKERS.keys())} supported")

    filepath = download_slides(ticker, year, quarter)
    quarter_str = f"Q{quarter} {year}"
    result = analyze_slide_deck(filepath, SUPPORTED_TICKERS[ticker], quarter_str)
    return {"ticker": ticker, "year": year, "quarter": quarter, **result}


@app.get("/api/calendar")
async def get_calendar_endpoint(date: str = Query(default="2025-01-10")):
    events = get_earnings_calendar(date)
    return {"date": date, "events": events}


@app.get("/api/audio/{ticker}/{year}/{quarter}")
async def serve_audio(ticker: str, year: int, quarter: int):
    ticker = ticker.upper()
    filepath = download_audio(ticker, year, quarter)
    if not filepath or not os.path.exists(filepath):
        raise HTTPException(404, "Audio file not available")
    return FileResponse(filepath, media_type="audio/mpeg", filename=os.path.basename(filepath))


@app.get("/api/audio-info/{ticker}/{year}/{quarter}")
async def audio_info(ticker: str, year: int, quarter: int):
    ticker = ticker.upper()
    filepath = download_audio(ticker, year, quarter)
    if not filepath:
        raise HTTPException(404, "Audio file not available")
    info = get_audio_info(filepath)
    return {"ticker": ticker, "year": year, "quarter": quarter, **info}


@app.get("/api/timestamps/{ticker}/{year}/{quarter}")
async def get_timestamps(ticker: str, year: int, quarter: int):
    ticker = ticker.upper()
    data = get_word_timestamps(ticker, year, quarter)
    if not data:
        raise HTTPException(404, "No timestamp data found")
    return {"ticker": ticker, "year": year, "quarter": quarter, "speakers": data}


@app.get("/api/insights/{ticker}/{year}/{quarter}")
async def insights(
    ticker: str,
    year: int,
    quarter: int,
    watchlist: str = Query(default="AAPL,MSFT"),
):
    """
    Unified advanced analytics endpoint:
    key moments, alerts, Q&A quality, consistency, guidance diff, metric extraction.
    """
    ticker = ticker.upper()
    if ticker not in SUPPORTED_TICKERS:
        raise HTTPException(400, f"Only {list(SUPPORTED_TICKERS.keys())} supported")
    watchlist_tickers = [t.strip().upper() for t in watchlist.split(",") if t.strip()]
    watchlist_tickers = [t for t in watchlist_tickers if t in SUPPORTED_TICKERS]
    if not watchlist_tickers:
        watchlist_tickers = ["AAPL", "MSFT"]

    cache_key = _insights_cache_key(ticker, year, quarter, watchlist_tickers)
    cached = _get_insights_cached(cache_key)
    if cached:
        return cached

    transcript_text = get_transcript_text(ticker, year, quarter) or ""
    remarks_data = get_prepared_remarks_and_qa(ticker, year, quarter) or {}
    prepared_text = remarks_data.get("prepared_remarks", "")
    qa_text = remarks_data.get("questions_and_answers", "")
    timestamp_data = get_word_timestamps(ticker, year, quarter) or []
    speakers_data = get_speakers_with_info(ticker, year, quarter) or []

    if not transcript_text and not prepared_text and not qa_text:
        raise HTTPException(404, "No text data available for insights.")

    max_ts = 0.0
    for sp in timestamp_data:
        for w in sp.get("words_with_times", []):
            t = w.get("start_time")
            if isinstance(t, (int, float)):
                max_ts = max(max_ts, float(t))
    total_duration = max_ts if max_ts > 0 else 3600.0

    base_text = transcript_text or f"{prepared_text}\n{qa_text}"
    timestamp_words = _flatten_timestamp_words(timestamp_data)
    key_moments = _build_key_moments(base_text, total_duration, timestamp_words)
    alerts = [
        m for m in key_moments
        if m["event_type"] in {"negative_spike", "risk", "uncertainty_spike"}
    ][:20]

    prepared_analysis = analyze_full_text(prepared_text) if prepared_text else None
    qa_analysis = analyze_full_text(qa_text) if qa_text else None
    qa_delta = {}
    if prepared_analysis and qa_analysis:
        qa_delta = {
            "sentiment_shift": round(qa_analysis["sentiment"]["score"] - prepared_analysis["sentiment"]["score"], 4),
            "snr_shift_db": round(qa_analysis["snr"]["snr_db"] - prepared_analysis["snr"]["snr_db"], 2),
            "hedge_shift": round(qa_analysis["hedging"]["hedge_density"] - prepared_analysis["hedging"]["hedge_density"], 4),
            "confidence_shift": round(qa_analysis["confidence"]["confidence_density"] - prepared_analysis["confidence"]["confidence_density"], 4),
        }

    questions = _extract_questions(qa_text)
    question_quality = [_question_quality(q) for q in questions]

    speaker_analysis = analyze_speaker_segments(speakers_data) if speakers_data else []
    speaker_heatmap = [
        {
            "speaker": s.get("name") or s.get("speaker", "Unknown"),
            "sentiment": s.get("sentiment", {}).get("score", 0),
            "snr_db": s.get("snr", {}).get("snr_db", 0),
            "hedge_density": s.get("hedging", {}).get("hedge_density", 0),
            "confidence_density": s.get("confidence", {}).get("confidence_density", 0),
        }
        for s in speaker_analysis
    ]

    current_metrics = _extract_metrics(base_text)

    # Consistency tracker + guidance diff (vs most recent prior event)
    consistency = {"history": [], "trend_summary": "Not enough historical events."}
    guidance_diff = {"current": current_metrics["guidance_mentions"][:8], "previous": [], "new_items": [], "removed_items": []}
    try:
        events = get_company_events(ticker)
        prior_events = [e for e in events if (e["year"], e["quarter"]) < (year, quarter)]
        prior_events = sorted(prior_events, key=lambda x: (x["year"], x["quarter"]), reverse=True)[:3]
        history = []
        for ev in prior_events:
            t = get_transcript_text(ticker, ev["year"], ev["quarter"]) or ""
            if not t:
                continue
            a = analyze_sentiment(t)
            m = _extract_metrics(t)
            history.append({
                "year": ev["year"],
                "quarter": ev["quarter"],
                "sentiment": a.get("score", 0),
                "guidance_mentions": len(m.get("guidance_mentions", [])),
                "percentages": len(m.get("percentages", [])),
            })

        if history:
            consistency["history"] = history
            avg_hist = float(np.mean([h["sentiment"] for h in history]))
            curr_sent = analyze_sentiment(base_text).get("score", 0)
            delta = curr_sent - avg_hist
            consistency["trend_summary"] = (
                "Tone is stronger vs prior quarters." if delta > 0.12
                else "Tone is weaker vs prior quarters." if delta < -0.12
                else "Tone is broadly consistent vs prior quarters."
            )

            latest_prev = history[0]
            prev_text = get_transcript_text(ticker, latest_prev["year"], latest_prev["quarter"]) or ""
            prev_metrics = _extract_metrics(prev_text)
            guidance_diff["previous"] = prev_metrics["guidance_mentions"][:8]
            guidance_diff["new_items"] = [g for g in guidance_diff["current"] if g not in guidance_diff["previous"]][:8]
            guidance_diff["removed_items"] = [g for g in guidance_diff["previous"] if g not in guidance_diff["current"]][:8]
    except Exception as e:
        print(f"[insights] history compare error: {e}")

    # Watchlist snapshot (multi-company quick compare)
    watchlist_cards = []
    for tk in watchlist_tickers:
        try:
            evs = get_company_events(tk)
            if not evs:
                continue
            latest = sorted(evs, key=lambda x: (x["year"], x["quarter"]), reverse=True)[0]
            txt = get_transcript_text(tk, latest["year"], latest["quarter"]) or ""
            sa = analyze_sentiment(txt) if txt else {"score": 0, "label": "neutral"}
            watchlist_cards.append({
                "ticker": tk,
                "year": latest["year"],
                "quarter": latest["quarter"],
                "sentiment": sa.get("score", 0),
                "label": sa.get("label", "neutral"),
            })
        except Exception:
            continue

    alpha_signal = {
        "score": round(
            float(
                (analyze_sentiment(base_text).get("score", 0) * 0.45)
                - (np.mean([m["hedge_density"] for m in key_moments]) if key_moments else 0) * 2.2
                + (np.mean([m["confidence_density"] for m in key_moments]) if key_moments else 0) * 2.0
                - (len(alerts) / max(len(key_moments), 1)) * 0.3
            ),
            4,
        )
    }
    alpha_signal["label"] = (
        "Bullish" if alpha_signal["score"] > 0.2 else
        "Bearish" if alpha_signal["score"] < -0.2 else
        "Neutral"
    )

    result = {
        "ticker": ticker,
        "year": year,
        "quarter": quarter,
        "watchlist": watchlist_tickers,
        "key_moments": key_moments,
        "alerts": alerts,
        "qa_vs_remarks": {
            "prepared": prepared_analysis,
            "qa": qa_analysis,
            "delta": qa_delta,
        },
        "question_quality": question_quality,
        "consistency_tracker": consistency,
        "entity_metrics": current_metrics,
        "guidance_diff": guidance_diff,
        "speaker_heatmap": speaker_heatmap,
        "watchlist_snapshot": watchlist_cards,
        "alpha_signal": alpha_signal,
    }
    _set_insights_cache(cache_key, result)
    return result


# ─── WEBSOCKET: Real-Time Audio Analysis Stream ─────────────────────────────

@app.websocket("/ws/realtime/{ticker}/{year}/{quarter}")
async def realtime_analysis(websocket: WebSocket, ticker: str, year: int, quarter: int):
    await websocket.accept()
    ticker = ticker.upper()

    try:
        await websocket.send_json({"type": "status", "message": "Preparing real-time analysis..."})

        # 1. Get audio for playback (optional)
        audio_path = download_audio(ticker, year, quarter)
        audio_obj = None
        audio_duration = 0.0
        if audio_path:
            try:
                audio_obj = load_audio(audio_path)
                if audio_obj:
                    audio_duration = len(audio_obj) / 1000.0
            except Exception as e:
                print(f"[ws] Audio loading failed: {e}")
                audio_obj = None

        # 2. Decide how to get segments based on USE_WHISPER
        use_whisper = os.getenv("USE_WHISPER", "false").lower() == "true"
        segments = None
        seg_source = "api"

        # Get level-3 timestamps so Whisper segments can be mapped to real speakers by time.
        timestamp_speakers = get_word_timestamps(ticker, year, quarter) or []
        timestamp_words = _flatten_timestamp_words(timestamp_speakers)
        
        if use_whisper and audio_obj:
            seg_source = "whisper"

        # Fallback to API if Whisper failed or not enabled
        if not segments and seg_source != "whisper":
            seg_source = "api"
            word_data = get_word_timestamps(ticker, year, quarter)
            if word_data:
                segments = build_timed_segments(word_data, segment_duration=2.0, audio_duration=audio_duration)

        if not segments and seg_source != "whisper":
            await websocket.send_json({"type": "error", "message": "No segments available"})
            await websocket.close()
            return

        estimated_total_segments = (
            int(math.ceil(audio_duration / 2.0)) if audio_duration > 0 else len(segments or [])
        )
        await websocket.send_json({
            "type": "init",
            "total_segments": estimated_total_segments,
            "total_duration": audio_duration or ((segments[-1]["end_time"] if segments else 0) if seg_source != "whisper" else 0),
            "audio_available": audio_obj is not None,
            "engine": seg_source,
        })

        # Wait for client "play"
        while True:
            msg = await websocket.receive_text()
            if msg == "play":
                break

        # 4. Real-time streaming
        cumulative_text_parts = []
        speaker_text_accum = {}
        start_time_real = asyncio.get_event_loop().time()
        audio_chunks = chunk_audio(audio_obj, chunk_seconds=2.0) if audio_obj else []
        processed_count = 0
        sent_segment_indices = set()
        sentiment = {"label": "neutral", "score": 0.0, "confidence": 0.0}
        hedging = {"hedge_density": 0.0, "hedge_count": 0, "total_noise_density": 0.0, "hedge_words": []}
        confidence = {"confidence_density": 0.0, "confidence_word_count": 0}
        hesitations = {"hesitation_count": 0, "hesitation_density": 0.0}
        snr = {"snr_db": 0.0, "quality": "N/A", "signal_power": 0, "noise_power": 0}

        async def emit_segment(seg: Dict):
            nonlocal processed_count, sentiment, hedging, confidence, hesitations, snr

            i = int(seg.get("index", processed_count))
            text = seg.get("text", "")
            if text:
                cumulative_text_parts.append(text)

            for sp_data in seg.get("speakers", []):
                sp = sp_data["speaker"]
                if sp not in speaker_text_accum:
                    speaker_text_accum[sp] = {
                        "name": sp_data.get("name", sp),
                        "title": sp_data.get("title", ""),
                        "words": [],
                    }
                elif sp_data.get("name"):
                    speaker_text_accum[sp]["name"] = sp_data.get("name", speaker_text_accum[sp]["name"])
                    speaker_text_accum[sp]["title"] = sp_data.get("title", speaker_text_accum[sp]["title"])
                speaker_text_accum[sp]["words"].extend(sp_data["text"].split())

            cum_text = " ".join(cumulative_text_parts)

            # NLP on the latest segment text (faster for near real-time updates)
            analysis_text = text if text and len(text.strip()) > 3 else cum_text[-250:]
            if analysis_text and len(analysis_text.strip()) > 3:
                sentiment = analyze_sentiment(analysis_text)
                hedging = detect_hedging(analysis_text)
                confidence = detect_confidence(analysis_text)
                hesitations = detect_hesitations(analysis_text)
                snr = calculate_snr(sentiment, hedging, confidence, hesitations)

            # Audio features for corresponding chunk
            audio_features = {}
            if i < len(audio_chunks):
                chunk = audio_chunks[i]
                audio_features = compute_chunk_audio_features(chunk["samples"], chunk["sample_rate"])
                audio_features["audio_snr"] = calculate_audio_snr(chunk["samples"], chunk["sample_rate"])

            current_speakers = [
                {"speaker": sp, "name": info["name"], "title": info["title"], "text": " ".join(info["words"])}
                for sp, info in speaker_text_accum.items()
            ]
            primary_speaker = seg.get("primary_speaker", "Unknown")
            primary_info = speaker_text_accum.get(primary_speaker, {"name": primary_speaker, "title": ""})
            processed_count += 1

            await websocket.send_json({
                "type": "segment",
                "index": i,
                "start_time": seg["start_time"],
                "end_time": seg["end_time"],
                "text": text,
                "cumulative_text": cum_text[-500:],
                "primary_speaker": primary_info.get("name", primary_speaker),
                "primary_speaker_title": primary_info.get("title", ""),
                "speakers": current_speakers,
                "word_count": seg.get("word_count", 0),
                "sentiment": sentiment,
                "hedging": {
                    "hedge_density": hedging.get("hedge_density", 0),
                    "hedge_count": hedging.get("hedge_count", 0),
                    "total_noise_density": hedging.get("total_noise_density", 0),
                    "hedge_words": hedging.get("hedge_words", [])[:5],
                },
                "confidence": {
                    "confidence_density": confidence.get("confidence_density", 0),
                    "confidence_word_count": confidence.get("confidence_word_count", 0),
                },
                "hesitations": {
                    "hesitation_count": hesitations.get("hesitation_count", 0),
                    "hesitation_density": hesitations.get("hesitation_density", 0),
                },
                "snr": snr,
                "audio_features": audio_features,
                "cumulative": {
                    "composite_score": round(float(sentiment.get("score", 0)), 4),
                    "avg_hedge_density": round(float(hedging.get("hedge_density", 0)), 4),
                    "avg_snr_db": snr.get("snr_db", 0),
                    "segments_processed": processed_count,
                },
            })

        if seg_source == "whisper":
            await websocket.send_json({"type": "status", "message": "Whisper streaming started..."})
            for chunk_payload in iter_transcribe_audio(audio_path, chunk_duration=6):
                chunk_segments = _build_segments_from_transcription_chunk(chunk_payload.get("segments", []), segment_duration=2.0)
                chunk_segments = _attach_speakers_for_segments(chunk_segments, timestamp_words)
                for seg in chunk_segments:
                    seg_idx = int(seg.get("index", -1))
                    if seg_idx < 0 or seg_idx in sent_segment_indices:
                        continue
                    sent_segment_indices.add(seg_idx)

                    # Keep updates aligned with playback clock.
                    elapsed = asyncio.get_event_loop().time() - start_time_real
                    sleep_time = seg["end_time"] - elapsed
                    if sleep_time > 0:
                        try:
                            msg = await asyncio.wait_for(websocket.receive_text(), timeout=sleep_time)
                            if msg == "stop":
                                raise WebSocketDisconnect()
                        except asyncio.TimeoutError:
                            pass

                    await emit_segment(seg)
        else:
            for seg in segments:
                await emit_segment(seg)

                # Wait until the segment's end time in real life
                elapsed = asyncio.get_event_loop().time() - start_time_real
                sleep_time = seg["end_time"] - elapsed
                if sleep_time > 0:
                    try:
                        msg = await asyncio.wait_for(websocket.receive_text(), timeout=sleep_time)
                        if msg == "stop":
                            break
                    except asyncio.TimeoutError:
                        pass

        # Final summary
        final_sent = sentiment.get("score", 0) if sentiment else 0
        final_snr = snr.get("snr_db", 0) if snr else 0
        final_hedge = hedging.get("hedge_density", 0) if hedging else 0

        await websocket.send_json({
            "type": "complete",
            "final_composite": round(float(final_sent), 4),
            "final_snr": round(float(final_snr), 2),
            "final_hedge": round(float(final_hedge), 4),
        })

    except WebSocketDisconnect:
        print(f"[ws] Client disconnected: {ticker} Q{quarter} {year}")
    except Exception as e:
        print(f"[ws] Error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass


# ─── HEALTH CHECK ─────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "EarningsEdge API"}


# ─── RUN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)