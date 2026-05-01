"""
analysis.py — NLP Analysis Engine
FinBERT sentiment, hedge detection, confidence scoring, SNR calculation
"""

import re
import math
import numpy as np
from typing import List, Dict, Tuple, Optional
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification

# ─── GLOBALS ──────────────────────────────────────────────────────────────────
_finbert_pipeline = None

# ─── HEDGE / FILLER / CONFIDENCE WORD LISTS ───────────────────────────────────
HEDGE_WORDS = [
    "approximately", "roughly", "around", "about", "possibly", "potentially",
    "might", "may", "could", "subject to", "to some extent", "if conditions permit",
    "at this point", "going forward", "in the range of", "we believe", "we think",
    "we expect", "we anticipate", "somewhat", "fairly", "relatively", "largely",
    "generally", "typically", "usually", "perhaps", "probably", "likely",
    "unlikely", "uncertain", "unclear", "cautious", "cautiously", "moderate",
    "modest", "manageable", "reasonable", "appears", "seems", "suggest",
    "indicate", "estimate", "projected", "forecasted", "preliminary",
]

FILLER_PHRASES = [
    "at the end of the day", "going forward", "as you know", "you know",
    "i mean", "sort of", "kind of", "at this point in time", "in terms of",
    "as i mentioned", "as we discussed", "as i said", "as you can see",
    "having said that", "that being said", "with that said", "needless to say",
    "it goes without saying", "by and large", "all things considered",
    "at the end of the day", "to be honest", "quite frankly",
    "for what it's worth", "if you will", "so to speak",
]

CONFIDENCE_WORDS = [
    "absolutely", "certainly", "definitely", "clearly", "obviously",
    "committed", "guarantee", "confident", "strong", "robust",
    "exceptional", "outstanding", "record", "remarkable", "significant",
    "substantial", "tremendous", "extraordinary", "unequivocally",
    "decisively", "emphatically", "categorically", "undoubtedly",
    "convinced", "assured", "resolute", "unwavering", "steadfast",
]

HESITATION_PATTERNS = [
    r'\buh+\b', r'\bum+\b', r'\bahh?\b', r'\bhmm+\b', r'\berr?\b',
    r'\b(?:you know)\b', r'\b(?:i mean)\b', r'\b(?:sort of)\b',
    r'\b(?:kind of)\b', r'\b(?:like)\b(?:\s+(?:you know|i said))',
    r'\.{3,}', r'\-{2,}',  # Ellipsis and dashes indicating pauses
]


def get_finbert():
    """Lazy-load FinBERT pipeline (downloads model on first call)."""
    global _finbert_pipeline
    if _finbert_pipeline is None:
        print("[analysis] Loading FinBERT model...")
        import torch
        import warnings
        
        # Suppress the sequential GPU warning
        warnings.filterwarnings("ignore", message="You seem to be using the pipelines sequentially on GPU")
        
        # Robust CUDA detection with error handling
        device = -1  # Default to CPU
        try:
            if torch.cuda.is_available():
                device = 0
                print("[analysis] CUDA detected, using GPU")
            else:
                print("[analysis] CUDA not available, using CPU")
        except Exception as e:
            print(f"[analysis] CUDA detection failed, using CPU: {e}")
            device = -1
        
        _finbert_pipeline = pipeline(
            "sentiment-analysis",
            model="ProsusAI/finbert",
            tokenizer="ProsusAI/finbert",
            truncation=True,
            max_length=512,
            device=device,
        )
        device_name = "GPU" if device >= 0 else "CPU"
        print(f"[analysis] FinBERT loaded successfully on {device_name}.")
    return _finbert_pipeline


def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences using regex."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if len(s.strip()) > 10]


def analyze_sentiment(text: str) -> Dict:
    """Run FinBERT sentiment analysis on a text segment."""
    finbert = get_finbert()
    if not text or len(text.strip()) < 5:
        return {"label": "neutral", "score": 0.0, "positive": 0.0, "negative": 0.0, "neutral": 1.0}

    # Truncate to avoid token limit issues
    truncated = text[:1500]
    try:
        result = finbert(truncated)[0]
        label = result["label"].lower()
        score = result["score"]

        # Convert to a single sentiment value: -1 (bearish) to +1 (bullish)
        if label == "positive":
            sentiment_value = score
        elif label == "negative":
            sentiment_value = -score
        else:
            sentiment_value = 0.0

        return {
            "label": label,
            "score": sentiment_value,
            "confidence": score,
            "positive": score if label == "positive" else 0.0,
            "negative": score if label == "negative" else 0.0,
            "neutral": score if label == "neutral" else 0.0,
        }
    except Exception as e:
        print(f"[analysis] FinBERT error: {e}")
        return {"label": "neutral", "score": 0.0, "confidence": 0.0,
                "positive": 0.0, "negative": 0.0, "neutral": 1.0}


def analyze_sentiment_batch(texts: List[str]) -> List[Dict]:
    """Batch sentiment analysis for efficiency."""
    finbert = get_finbert()
    if not texts:
        return []

    truncated = [t[:1500] for t in texts if len(t.strip()) > 5]
    if not truncated:
        return [{"label": "neutral", "score": 0.0, "confidence": 0.0} for _ in texts]

    try:
        results = finbert(truncated, batch_size=16)
        output = []
        for r in results:
            label = r["label"].lower()
            score = r["score"]
            if label == "positive":
                sentiment_value = score
            elif label == "negative":
                sentiment_value = -score
            else:
                sentiment_value = 0.0
            output.append({
                "label": label,
                "score": sentiment_value,
                "confidence": score,
            })
        return output
    except Exception as e:
        print(f"[analysis] Batch FinBERT error: {e}")
        return [{"label": "neutral", "score": 0.0, "confidence": 0.0} for _ in texts]


def detect_hedging(text: str) -> Dict:
    """Detect hedge words and compute hedge density."""
    text_lower = text.lower()
    words = text_lower.split()
    word_count = max(len(words), 1)

    hedge_found = []
    for hw in HEDGE_WORDS:
        count = text_lower.count(hw)
        if count > 0:
            hedge_found.extend([hw] * count)

    filler_found = []
    for fp in FILLER_PHRASES:
        count = text_lower.count(fp)
        if count > 0:
            filler_found.extend([fp] * count)

    hedge_density = len(hedge_found) / word_count
    filler_density = len(filler_found) / word_count

    return {
        "hedge_count": len(hedge_found),
        "hedge_words": list(set(hedge_found)),
        "hedge_density": round(hedge_density, 4),
        "filler_count": len(filler_found),
        "filler_phrases": list(set(filler_found)),
        "filler_density": round(filler_density, 4),
        "total_noise_density": round(hedge_density + filler_density, 4),
    }


def detect_confidence(text: str) -> Dict:
    """Detect confidence/definitive language and return a normalized confidence score."""
    text_lower = text.lower()
    words = text_lower.split()
    word_count = max(len(words), 1)

    confidence_found = []
    for cw in CONFIDENCE_WORDS:
        count = text_lower.count(cw)
        if count > 0:
            confidence_found.extend([cw] * count)

    confidence_density = len(confidence_found) / word_count
    assertive_patterns = [
        "we will", "we are confident", "we remain confident", "we continue to",
        "on track", "strong demand", "strong execution", "we delivered",
        "ahead of", "we expect to", "we're pleased", "record",
    ]
    assertive_hits = sum(text_lower.count(p) for p in assertive_patterns)

    # Convert sparse lexical signals into a more interpretable 0-100 score.
    lexical_signal = min(1.0, confidence_density * 40.0)
    assertive_signal = min(1.0, assertive_hits / 6.0)
    confidence_score = (0.65 * lexical_signal + 0.35 * assertive_signal) * 100.0

    return {
        "confidence_word_count": len(confidence_found),
        "confidence_words": list(set(confidence_found)),
        "confidence_density": round(confidence_density, 4),
        "assertive_phrase_count": int(assertive_hits),
        "confidence_score": round(confidence_score, 2),
    }


def detect_hesitations(text: str) -> Dict:
    """Detect hesitation markers in text."""
    text_lower = text.lower()
    hesitation_count = 0
    hesitations_found = []

    for pattern in HESITATION_PATTERNS:
        matches = re.findall(pattern, text_lower)
        hesitation_count += len(matches)
        hesitations_found.extend(matches)

    words = text_lower.split()
    word_count = max(len(words), 1)

    return {
        "hesitation_count": hesitation_count,
        "hesitations": hesitations_found[:20],  # Cap at 20
        "hesitation_density": round(hesitation_count / word_count, 4),
    }


def calculate_snr(sentiment_result: Dict, hedge_result: Dict,
                  confidence_result: Dict, hesitation_result: Dict) -> Dict:
    """
    Calculate Signal-to-Noise Ratio for a text segment.

    Signal = meaningful sentiment strength + definitive language
    Noise  = hedge density + filler density + hesitation density + neutrality

    SNR_dB = 10 * log10(signal_power / noise_power)
    """
    # Signal components
    sentiment_strength = abs(sentiment_result.get("score", 0))
    finbert_confidence = sentiment_result.get("confidence", 0.5)
    confidence_density = confidence_result.get("confidence_density", 0)

    # If sentiment is non-neutral and confident, that's strong signal
    is_non_neutral = 1.0 if sentiment_result.get("label", "neutral") != "neutral" else 0.1
    signal_power = (
        sentiment_strength * finbert_confidence * is_non_neutral +
        confidence_density * 2.0 +
        0.01  # Floor to prevent zero
    )

    # Noise components
    hedge_density = hedge_result.get("hedge_density", 0)
    filler_density = hedge_result.get("filler_density", 0)
    hesitation_density = hesitation_result.get("hesitation_density", 0)
    neutrality = 1.0 - finbert_confidence if sentiment_result.get("label") == "neutral" else 0.0

    noise_power = (
        hedge_density * 3.0 +
        filler_density * 2.0 +
        hesitation_density * 2.5 +
        neutrality * 0.5 +
        0.01  # Floor to prevent zero/division
    )

    # SNR in dB
    snr_ratio = signal_power / noise_power
    snr_db = 10 * math.log10(snr_ratio) if snr_ratio > 0 else -20.0

    # Clamp to reasonable range
    snr_db = max(-20.0, min(30.0, snr_db))

    # Qualitative rating
    if snr_db > 15:
        quality = "EXCELLENT"
    elif snr_db > 8:
        quality = "STRONG"
    elif snr_db > 2:
        quality = "MODERATE"
    elif snr_db > -5:
        quality = "WEAK"
    else:
        quality = "POOR"

    return {
        "snr_db": round(snr_db, 2),
        "signal_power": round(signal_power, 4),
        "noise_power": round(noise_power, 4),
        "snr_ratio": round(snr_ratio, 4),
        "quality": quality,
    }


def calculate_audio_snr(audio_samples: np.ndarray, sample_rate: int) -> Dict:
    """
    Calculate audio-level SNR from raw audio samples.
    Measures speech clarity vs background noise.
    """
    if len(audio_samples) == 0:
        return {"audio_snr_db": 0.0, "speech_ratio": 0.0}

    # Normalize
    samples = audio_samples.astype(np.float64)
    if samples.max() > 1.0:
        samples = samples / 32768.0  # 16-bit normalization

    # Compute RMS energy in frames
    frame_length = int(sample_rate * 0.025)  # 25ms frames
    hop_length = int(sample_rate * 0.010)    # 10ms hop

    frames = []
    for i in range(0, len(samples) - frame_length, hop_length):
        frame = samples[i:i + frame_length]
        rms = np.sqrt(np.mean(frame ** 2))
        frames.append(rms)

    if not frames:
        return {"audio_snr_db": 0.0, "speech_ratio": 0.0}

    frames = np.array(frames)

    # Classify frames: speech vs noise using energy threshold
    threshold = np.percentile(frames, 30)  # Bottom 30% is noise
    speech_frames = frames[frames > threshold]
    noise_frames = frames[frames <= threshold]

    if len(noise_frames) == 0 or len(speech_frames) == 0:
        return {"audio_snr_db": 20.0, "speech_ratio": 1.0}

    speech_power = np.mean(speech_frames ** 2)
    noise_power = np.mean(noise_frames ** 2)

    if noise_power < 1e-10:
        noise_power = 1e-10

    audio_snr_db = 10 * math.log10(speech_power / noise_power)
    audio_snr_db = max(-10.0, min(60.0, audio_snr_db))

    speech_ratio = len(speech_frames) / max(len(frames), 1)

    return {
        "audio_snr_db": round(audio_snr_db, 2),
        "speech_ratio": round(speech_ratio, 4),
        "speech_frames": int(len(speech_frames)),
        "noise_frames": int(len(noise_frames)),
    }


def analyze_full_text(text: str) -> Dict:
    """Complete NLP analysis of a text segment."""
    sentiment = analyze_sentiment(text)
    hedging = detect_hedging(text)
    confidence = detect_confidence(text)
    hesitations = detect_hesitations(text)
    snr = calculate_snr(sentiment, hedging, confidence, hesitations)

    return {
        "sentiment": sentiment,
        "hedging": hedging,
        "confidence": confidence,
        "hesitations": hesitations,
        "snr": snr,
        "word_count": len(text.split()),
    }


def analyze_speaker_segments(speakers_data: list) -> List[Dict]:
    """Analyze each speaker's text and return detailed results."""
    results = []
    all_texts = [s.get("text", "") for s in speakers_data]

    # Batch sentiment for efficiency
    sentiments = analyze_sentiment_batch(all_texts)

    for i, speaker in enumerate(speakers_data):
        text = speaker.get("text", "")
        sentiment = sentiments[i] if i < len(sentiments) else analyze_sentiment(text)
        hedging = detect_hedging(text)
        confidence = detect_confidence(text)
        hesitations = detect_hesitations(text)
        snr = calculate_snr(sentiment, hedging, confidence, hesitations)

        sentences = split_into_sentences(text)
        sentence_sentiments = analyze_sentiment_batch(sentences) if sentences else []

        results.append({
            "speaker": speaker.get("speaker", "Unknown"),
            "name": speaker.get("name", ""),
            "title": speaker.get("title", ""),
            "text": text[:500] + ("..." if len(text) > 500 else ""),
            "full_text_length": len(text),
            "word_count": len(text.split()),
            "sentiment": sentiment,
            "hedging": hedging,
            "confidence": confidence,
            "hesitations": hesitations,
            "snr": snr,
            "sentence_count": len(sentences),
            "sentence_sentiments": sentence_sentiments[:50],  # Cap
        })

    return results


def compute_overall_metrics(speaker_results: List[Dict]) -> Dict:
    """Compute aggregate metrics across all speakers."""
    if not speaker_results:
        return {}

    all_scores = [r["sentiment"]["score"] for r in speaker_results]
    all_snrs = [r["snr"]["snr_db"] for r in speaker_results]
    all_hedge = [r["hedging"]["hedge_density"] for r in speaker_results]
    all_confidence = [r["confidence"]["confidence_density"] for r in speaker_results]
    all_confidence_scores = [r["confidence"].get("confidence_score", 0) for r in speaker_results]
    total_words = sum(r["word_count"] for r in speaker_results)

    composite_sentiment = np.mean(all_scores) if all_scores else 0.0
    avg_snr = np.mean(all_snrs) if all_snrs else 0.0
    avg_hedge = np.mean(all_hedge) if all_hedge else 0.0
    avg_confidence = np.mean(all_confidence) if all_confidence else 0.0
    avg_confidence_score = np.mean(all_confidence_scores) if all_confidence_scores else 0.0

    # Weighted SNR (by word count)
    weighted_snr = sum(
        r["snr"]["snr_db"] * r["word_count"] for r in speaker_results
    ) / max(total_words, 1)

    return {
        "composite_sentiment": round(float(composite_sentiment), 4),
        "composite_label": (
            "STRONGLY BULLISH" if composite_sentiment > 0.5 else
            "BULLISH" if composite_sentiment > 0.2 else
            "NEUTRAL" if composite_sentiment > -0.2 else
            "BEARISH" if composite_sentiment > -0.5 else
            "STRONGLY BEARISH"
        ),
        "avg_snr_db": round(float(avg_snr), 2),
        "weighted_snr_db": round(float(weighted_snr), 2),
        "avg_hedge_density": round(float(avg_hedge), 4),
        "avg_confidence_density": round(float(avg_confidence), 4),
        "avg_confidence_score": round(float(avg_confidence_score), 2),
        "total_words": total_words,
        "total_speakers": len(speaker_results),
    }
