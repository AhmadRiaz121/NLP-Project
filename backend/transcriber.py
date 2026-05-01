# """
# transcriber.py — Whisper ASR + Speaker Diarisation
# Replaces static transcript with transcribed audio.
# """

# import os
# import torch
# import numpy as np
# from typing import List, Dict
# from dotenv import load_dotenv

# load_dotenv()

# # ----- Whisper model (lazy load) -----
# _whisper_model = None

# def get_whisper_model(model_size: str = "tiny.en"):
#     """Load faster‑whisper model once."""
#     global _whisper_model
#     if _whisper_model is None:
#         from faster_whisper import WhisperModel
#         device = "cuda" if torch.cuda.is_available() else "cpu"
#         compute_type = "float16" if device == "cuda" else "int8"
#         _whisper_model = WhisperModel(model_size, device=device, compute_type=compute_type)
#         print(f"[whisper] Model loaded: {model_size} on {device}")
#     return _whisper_model


# def transcribe_audio(audio_path: str, language: str = "en") -> List[Dict]:
#     """
#     Transcribe audio file with Whisper.
#     Returns list of segments: {start, end, text}.
#     """
#     model = get_whisper_model()
#     segments, _ = model.transcribe(audio_path, language=language, beam_size=1, word_timestamps=False)
#     result = []
#     for seg in segments:
#         result.append({
#             "start": round(seg.start, 2),
#             "end": round(seg.end, 2),
#             "text": seg.text.strip(),
#         })
#     print(f"[whisper] Transcription produced {len(result)} segments")
#     return result


# # ----- Speaker diarisation (optional) -----
# def diarize_audio(audio_path: str) -> List[Dict]:
#     """
#     Use pyannote.audio to get speaker segments.
#     Returns list of {start, end, speaker}.
#     Requires HUGGINGFACE_TOKEN in .env.
#     """
#     token = os.getenv("HUGGINGFACE_TOKEN")
#     if not token:
#         print("[diarize] No HUGGINGFACE_TOKEN — skipping speaker diarisation")
#         return []

#     try:
#         from pyannote.audio import Pipeline
#         pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1",
#                                             use_auth_token=token)
#         # pyannote expects audio as a waveform and sample rate
#         import librosa
#         audio, sr = librosa.load(audio_path, sr=16000, mono=True)
#         audio_tensor = torch.tensor(audio).unsqueeze(0)
#         diarization = pipeline({"waveform": audio_tensor, "sample_rate": sr})
#         turns = []
#         for turn, _, speaker in diarization.itertracks(yield_label=True):
#             turns.append({
#                 "start": round(turn.start, 2),
#                 "end": round(turn.end, 2),
#                 "speaker": speaker,
#             })
#         print(f"[diarize] Found {len(turns)} speaker turns")
#         return turns
#     except Exception as e:
#         print(f"[diarize] Error: {e}")
#         return []


# def build_transcribed_segments(
#     transcription: List[Dict],
#     diarization: List[Dict] = None,
#     segment_duration: float = 2.0,
# ) -> List[Dict]:
#     """
#     Combine transcription words (with approximate word times) and diarisation
#     into a list of 2‑second segments identical in structure to what the
#     previous `build_timed_segments` returned.
#     """
#     # First, split each transcription segment into words with estimated times.
#     # We'll use a simple method: distribute words evenly across the segment duration.
#     all_words = []
#     for seg in transcription:
#         words = seg["text"].split()
#         if not words:
#             continue
#         dur = seg["end"] - seg["start"]
#         if dur <= 0:
#             dur = 0.01
#         w_dur = dur / len(words)
#         for i, w in enumerate(words):
#             t = seg["start"] + i * w_dur
#             all_words.append({
#                 "word": w,
#                 "start_time": round(t, 2),
#             })

#     if not all_words:
#         return []

#     # Determine speaker for each word if diarisation is available
#     speaker_of_word = ["Unknown"] * len(all_words)
#     if diarization:
#         for turn in diarization:
#             for idx in range(len(all_words)):
#                 if turn["start"] <= all_words[idx]["start_time"] < turn["end"]:
#                     speaker_of_word[idx] = turn["speaker"]

#     # Group by (primary speaker) per segment – similar to original `build_timed_segments`
#     max_time = all_words[-1]["start_time"] + 0.5
#     num_segments = int(np.ceil(max_time / segment_duration))
#     segments = []

#     for i in range(num_segments):
#         seg_start = i * segment_duration
#         seg_end = seg_start + segment_duration

#         seg_words = [w for w in all_words if seg_start <= w["start_time"] < seg_end]
#         if not seg_words:
#             segments.append({
#                 "index": i,
#                 "start_time": round(seg_start, 2),
#                 "end_time": round(seg_end, 2),
#                 "text": "",
#                 "speakers": [],
#                 "word_count": 0,
#             })
#             continue

#         # Collect words per speaker
#         speaker_words = {}
#         for w, sp in zip(seg_words, speaker_of_word):
#             sp = sp or "Unknown"
#             speaker_words.setdefault(sp, []).append(w["word"])

#         text = " ".join(w["word"] for w in seg_words)

#         # primary speaker = most words
#         primary = max(speaker_words.items(), key=lambda x: len(x[1]))
#         primary_speaker = primary[0]
#         primary_text = " ".join(primary[1])

#         segments.append({
#             "index": i,
#             "start_time": round(seg_start, 2),
#             "end_time": round(seg_end, 2),
#             "text": text,
#             "speakers": [
#                 {"speaker": sp, "name": sp, "title": "", "text": " ".join(words)}
#                 for sp, words in speaker_words.items()
#             ],
#             "word_count": len(seg_words),
#             "primary_speaker": primary_speaker,
#             "primary_speaker_title": "",
#         })

#     return segments


# Deepseek
"""
transcriber.py — Whisper ASR + Speaker Diarisation (optional)
Used only when USE_WHISPER=true in environment.
"""

import os
import torch
import numpy as np
from typing import List, Dict, Iterator
from dotenv import load_dotenv

load_dotenv()

_whisper_model = None

def get_whisper_model(model_size: str = "tiny.en"):
    """Lazy-load faster-whisper model once."""
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        _whisper_model = WhisperModel(model_size, device=device, compute_type=compute_type)
        print(f"[whisper] Model loaded: {model_size} on {device}")
    return _whisper_model


def iter_transcribe_audio(
    audio_path: str,
    language: str = "en",
    chunk_duration: int = 8,
) -> Iterator[Dict]:
    """
    Incrementally transcribe audio using small in-memory chunks.
    Yields:
        {
            "chunk_start": float,
            "chunk_end": float,
            "segments": [{"start": float, "end": float, "text": str}]
        }
    """
    model = get_whisper_model()
    import librosa

    audio, sr = librosa.load(audio_path, sr=16000, mono=True)
    total_duration = len(audio) / sr
    chunk_samples = int(chunk_duration * sr)

    print(f"[whisper] Streaming transcription in {chunk_duration}s chunks (total: {total_duration:.1f}s)")

    for start_sample in range(0, len(audio), chunk_samples):
        end_sample = min(start_sample + chunk_samples, len(audio))
        chunk_audio = audio[start_sample:end_sample]
        chunk_start = start_sample / sr
        chunk_end = end_sample / sr

        if len(chunk_audio) < sr // 2:
            continue

        segments_result: List[Dict] = []
        try:
            # Pass ndarray directly to faster-whisper to avoid temp-file I/O overhead.
            segments, _ = model.transcribe(
                chunk_audio.astype(np.float32),
                language=language,
                beam_size=1,
                word_timestamps=False,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 300, "speech_pad_ms": 200},
                temperature=0.0,
                condition_on_previous_text=False,
            )

            for seg in segments:
                global_start = chunk_start + float(seg.start)
                global_end = chunk_start + float(seg.end)
                segments_result.append(
                    {
                        "start": round(global_start, 2),
                        "end": round(global_end, 2),
                        "text": seg.text.strip(),
                    }
                )
        except Exception as e:
            print(f"[whisper] Error processing chunk {chunk_start:.1f}-{chunk_end:.1f}s: {e}")

        yield {
            "chunk_start": round(chunk_start, 2),
            "chunk_end": round(chunk_end, 2),
            "segments": segments_result,
        }


def transcribe_audio(audio_path: str, language: str = "en", chunk_duration: int = 8) -> List[Dict]:
    """
    Transcribe audio with Whisper using chunked processing to avoid memory errors.
    Processes audio in chunks of chunk_duration seconds (increased to 60s for speed).
    Returns list of segments: {start, end, text}.
    """
    result: List[Dict] = []
    for chunk_payload in iter_transcribe_audio(
        audio_path=audio_path,
        language=language,
        chunk_duration=chunk_duration,
    ):
        result.extend(chunk_payload["segments"])

    print(f"[whisper] Transcription produced {len(result)} segments")
    return result


def diarize_audio(audio_path: str) -> List[Dict]:
    """
    Use pyannote.audio for speaker diarization (optional).
    Requires HUGGINGFACE_TOKEN in .env.
    """
    token = os.getenv("HUGGINGFACE_TOKEN")
    if not token:
        print("[diarize] No HUGGINGFACE_TOKEN — skipping")
        return []

    try:
        from pyannote.audio import Pipeline
        pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1",
                                            use_auth_token=token)
        import librosa
        audio, sr = librosa.load(audio_path, sr=16000, mono=True)
        audio_tensor = torch.tensor(audio).unsqueeze(0)
        diarization = pipeline({"waveform": audio_tensor, "sample_rate": sr})
        turns = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            turns.append({
                "start": round(turn.start, 2),
                "end": round(turn.end, 2),
                "speaker": speaker,
            })
        print(f"[diarize] Found {len(turns)} speaker turns")
        return turns
    except Exception as e:
        print(f"[diarize] Error: {e}")
        return []


def build_transcribed_segments(
    transcription: List[Dict],
    diarization: List[Dict] = None,
    segment_duration: float = 2.0,
) -> List[Dict]:
    """Combine Whisper words with optional diarization into timed segments."""
    all_words = []
    for seg in transcription:
        words = seg["text"].split()
        if not words:
            continue
        dur = seg["end"] - seg["start"]
        if dur <= 0:
            dur = 0.01
        w_dur = dur / len(words)
        for i, w in enumerate(words):
            t = seg["start"] + i * w_dur
            all_words.append({"word": w, "start_time": round(t, 2)})

    if not all_words:
        return []

    # Assign speaker per word if diarization available
    for w in all_words:
        w["speaker"] = "Unknown"
    if diarization:
        for turn in diarization:
            for idx in range(len(all_words)):
                if turn["start"] <= all_words[idx]["start_time"] < turn["end"]:
                    all_words[idx]["speaker"] = turn["speaker"]

    max_time = all_words[-1]["start_time"] + 0.5
    num_segments = int(np.ceil(max_time / segment_duration))
    segments = []

    for i in range(num_segments):
        seg_start = i * segment_duration
        seg_end = seg_start + segment_duration

        seg_words = [w for w in all_words if seg_start <= w["start_time"] < seg_end]
        if not seg_words:
            segments.append({
                "index": i,
                "start_time": round(seg_start, 2),
                "end_time": round(seg_end, 2),
                "text": "",
                "speakers": [],
                "word_count": 0,
            })
            continue

        speaker_words = {}
        for w in seg_words:
            sp = w.get("speaker") or "Unknown"
            speaker_words.setdefault(sp, []).append(w["word"])

        text = " ".join(w["word"] for w in seg_words)
        primary = max(speaker_words.items(), key=lambda x: len(x[1]))
        primary_speaker = primary[0]
        primary_text = " ".join(primary[1])

        segments.append({
            "index": i,
            "start_time": round(seg_start, 2),
            "end_time": round(seg_end, 2),
            "text": text,
            "speakers": [
                {"speaker": sp, "name": sp, "title": "", "text": " ".join(words)}
                for sp, words in speaker_words.items()
            ],
            "word_count": len(seg_words),
            "primary_speaker": primary_speaker,
            "primary_speaker_title": "",
        })

    return segments