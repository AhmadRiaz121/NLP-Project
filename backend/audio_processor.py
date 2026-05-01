# """
# audio_processor.py — Audio Chunking for Real-Time Simulation
# Splits audio into timed segments and pairs with word-level timestamps for streaming.
# """

# import os
# import math
# import numpy as np
# from typing import List, Dict, Optional, Generator

# # Add FFmpeg path to environment so pydub can find it without requiring a terminal restart
# ffmpeg_path = r"C:\Users\moham\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin"
# if ffmpeg_path not in os.environ["PATH"]:
#     os.environ["PATH"] += os.pathsep + ffmpeg_path

# from pydub import AudioSegment


# def load_audio(filepath: str) -> Optional[AudioSegment]:
#     """Load an audio file (MP3/WAV)."""
#     if not os.path.exists(filepath):
#         print(f"[audio] File not found: {filepath}")
#         return None
#     try:
#         if filepath.endswith(".mp3"):
#             audio = AudioSegment.from_mp3(filepath)
#         elif filepath.endswith(".wav"):
#             audio = AudioSegment.from_wav(filepath)
#         else:
#             audio = AudioSegment.from_file(filepath)
#         print(f"[audio] Loaded: {len(audio)/1000:.1f}s, {audio.frame_rate}Hz, {audio.channels}ch")
#         return audio
#     except Exception as e:
#         print(f"[audio] Load error: {e}")
#         return None


# def get_audio_info(filepath: str) -> Dict:
#     """Get audio metadata without loading full file."""
#     audio = load_audio(filepath)
#     if not audio:
#         return {}
#     return {
#         "duration_seconds": round(len(audio) / 1000, 2),
#         "sample_rate": audio.frame_rate,
#         "channels": audio.channels,
#         "frame_count": audio.frame_count(),
#     }


# def chunk_audio(audio: AudioSegment, chunk_seconds: float = 3.0) -> List[Dict]:
#     """Split audio into fixed-size chunks with numpy samples."""
#     chunk_ms = int(chunk_seconds * 1000)
#     total_ms = len(audio)
#     chunks = []

#     for start_ms in range(0, total_ms, chunk_ms):
#         end_ms = min(start_ms + chunk_ms, total_ms)
#         segment = audio[start_ms:end_ms]

#         # Convert to numpy array
#         samples = np.array(segment.get_array_of_samples(), dtype=np.float32)
#         if segment.channels == 2:
#             samples = samples.reshape((-1, 2)).mean(axis=1)  # Mono mix

#         chunks.append({
#             "start_time": start_ms / 1000.0,
#             "end_time": end_ms / 1000.0,
#             "duration": (end_ms - start_ms) / 1000.0,
#             "samples": samples,
#             "sample_rate": segment.frame_rate,
#         })

#     return chunks


# def build_timed_segments(
#     word_timestamps: List[Dict],
#     segment_duration: float = 3.0,
#     audio_duration: float = None,
# ) -> List[Dict]:
#     """
#     Group word-level timestamps into timed segments for real-time streaming.
#     Each segment contains the words spoken during that time window.
#     """
#     if not word_timestamps:
#         return []

#     segments = []
#     all_words_flat = []

#     # Flatten all speakers' words into a single timeline
#     for speaker_data in word_timestamps:
#         speaker_id = speaker_data.get("speaker", "Unknown")
#         name = speaker_data.get("name", speaker_id)
#         title = speaker_data.get("title", "")
#         for wt in speaker_data.get("words_with_times", []):
#             all_words_flat.append({
#                 "word": wt["word"],
#                 "start_time": wt["start_time"],
#                 "speaker": speaker_id,
#                 "name": name,
#                 "title": title,
#             })

#     # Sort by start_time
#     all_words_flat.sort(key=lambda x: x["start_time"])

#     if not all_words_flat:
#         return []

#     # Determine total duration
#     max_time = max(w["start_time"] for w in all_words_flat)
#     if audio_duration:
#         max_time = max(max_time, audio_duration)

#     # Group into segments
#     num_segments = math.ceil(max_time / segment_duration)
#     last_speaker_name = "Unknown"
#     last_speaker_title = ""

#     for i in range(num_segments):
#         seg_start = i * segment_duration
#         seg_end = seg_start + segment_duration

#         seg_words = [
#             w for w in all_words_flat
#             if seg_start <= w["start_time"] < seg_end
#         ]

#         if not seg_words:
#             segments.append({
#                 "index": i,
#                 "start_time": round(seg_start, 2),
#                 "end_time": round(seg_end, 2),
#                 "text": "",
#                 "speakers": [],
#                 "word_count": 0,
#                 "primary_speaker": last_speaker_name,
#                 "primary_speaker_title": last_speaker_title,
#             })
#             continue

#         # Group words by speaker within this segment
#         speakers_in_segment = {}
#         for w in seg_words:
#             sp = w["speaker"]
#             if sp not in speakers_in_segment:
#                 speakers_in_segment[sp] = {
#                     "words": [],
#                     "name": w.get("name", sp),
#                     "title": w.get("title", "")
#                 }
#             speakers_in_segment[sp]["words"].append(w["word"])

#         text = " ".join(w["word"] for w in seg_words)

#         primary_speaker_id = max(speakers_in_segment.items(), key=lambda x: len(x[1]["words"]))[0]
#         primary_info = speakers_in_segment[primary_speaker_id]
        
#         last_speaker_name = primary_info["name"]
#         last_speaker_title = primary_info["title"]

#         segments.append({
#             "index": i,
#             "start_time": round(seg_start, 2),
#             "end_time": round(seg_end, 2),
#             "text": text,
#             "speakers": [
#                 {
#                     "speaker": sp, 
#                     "name": info["name"], 
#                     "title": info["title"], 
#                     "text": " ".join(info["words"])
#                 }
#                 for sp, info in speakers_in_segment.items()
#             ],
#             "word_count": len(seg_words),
#             "primary_speaker": primary_info["name"],
#             "primary_speaker_title": primary_info["title"],
#         })

#     return segments


# def compute_chunk_audio_features(samples: np.ndarray, sample_rate: int) -> Dict:
#     """Compute audio features for a single chunk (for real-time display)."""
#     if len(samples) == 0:
#         return {"rms": 0, "peak": 0, "zero_crossings": 0, "is_speech": False}

#     # Normalize
#     if np.max(np.abs(samples)) > 0:
#         normalized = samples / np.max(np.abs(samples))
#     else:
#         normalized = samples

#     rms = float(np.sqrt(np.mean(normalized ** 2)))
#     peak = float(np.max(np.abs(normalized)))

#     # Zero crossing rate (indicator of speech vs noise)
#     zero_crossings = int(np.sum(np.abs(np.diff(np.sign(normalized))) > 0))
#     zcr = zero_crossings / max(len(normalized), 1)

#     # Simple speech detection: RMS above threshold
#     is_speech = rms > 0.02

#     # Speaking rate estimate (based on energy variation)
#     frame_size = int(sample_rate * 0.02)  # 20ms frames
#     energy_frames = []
#     for j in range(0, len(normalized) - frame_size, frame_size):
#         frame_energy = np.mean(normalized[j:j + frame_size] ** 2)
#         energy_frames.append(frame_energy)

#     energy_var = float(np.var(energy_frames)) if energy_frames else 0

#     return {
#         "rms": round(rms, 4),
#         "peak": round(peak, 4),
#         "zero_crossing_rate": round(zcr, 4),
#         "is_speech": is_speech,
#         "energy_variance": round(energy_var, 6),
#     }


"""
audio_processor.py — Audio Chunking for Real-Time Simulation
Splits audio into timed segments and pairs with word-level timestamps for streaming.
"""

import os
import math
import numpy as np
from typing import List, Dict, Optional

# Try to locate FFmpeg automatically (cross-platform)
def _find_ffmpeg_bin():
    """Search for ffmpeg/ffprobe in common locations."""
    # Windows: typical winget/choco paths
    for root in [
        r"C:\ffmpeg\bin",
        r"C:\Program Files\ffmpeg\bin",
        r"C:\Program Files (x86)\ffmpeg\bin",
        os.path.expanduser(r"~\AppData\Local\Microsoft\WinGet\Packages\*ffmpeg*\bin"),
    ]:
        if root.endswith("*"):
            import glob
            for d in glob.glob(root):
                if os.path.isfile(os.path.join(d, "ffmpeg.exe")):
                    return d
        elif os.path.isfile(os.path.join(root, "ffmpeg.exe")):
            return root
    # Linux/Mac: assume on PATH
    return ""

_ffmpeg_path = _find_ffmpeg_bin()
if _ffmpeg_path and _ffmpeg_path not in os.environ["PATH"]:
    os.environ["PATH"] += os.pathsep + _ffmpeg_path

from pydub import AudioSegment


def load_audio(filepath: str) -> Optional[AudioSegment]:
    """Load an audio file (MP3/WAV) safely."""
    if not os.path.exists(filepath):
        print(f"[audio] File not found: {filepath}")
        return None
    try:
        if filepath.endswith(".mp3"):
            audio = AudioSegment.from_mp3(filepath)
        elif filepath.endswith(".wav"):
            audio = AudioSegment.from_wav(filepath)
        else:
            audio = AudioSegment.from_file(filepath)
        print(f"[audio] Loaded: {len(audio)/1000:.1f}s, {audio.frame_rate}Hz, {audio.channels}ch")
        return audio
    except Exception as e:
        print(f"[audio] Load error: {e}")
        return None


def get_audio_info(filepath: str) -> Dict:
    audio = load_audio(filepath)
    if not audio:
        return {}
    return {
        "duration_seconds": round(len(audio) / 1000, 2),
        "sample_rate": audio.frame_rate,
        "channels": audio.channels,
        "frame_count": audio.frame_count(),
    }


def chunk_audio(audio: AudioSegment, chunk_seconds: float = 3.0) -> List[Dict]:
    """Split audio into fixed-size chunks with numpy samples."""
    if not audio:
        return []
    chunk_ms = int(chunk_seconds * 1000)
    total_ms = len(audio)
    chunks = []

    for start_ms in range(0, total_ms, chunk_ms):
        end_ms = min(start_ms + chunk_ms, total_ms)
        segment = audio[start_ms:end_ms]
        samples = np.array(segment.get_array_of_samples(), dtype=np.float32)
        if segment.channels == 2:
            samples = samples.reshape((-1, 2)).mean(axis=1)  # Mix to mono
        chunks.append({
            "start_time": start_ms / 1000.0,
            "end_time": end_ms / 1000.0,
            "duration": (end_ms - start_ms) / 1000.0,
            "samples": samples,
            "sample_rate": segment.frame_rate,
        })
    return chunks


def build_timed_segments(
    word_timestamps: List[Dict],
    segment_duration: float = 3.0,
    audio_duration: float = None,
) -> List[Dict]:
    """Group word-level timestamps into timed segments for real-time streaming."""
    if not word_timestamps:
        return []

    all_words_flat = []
    for speaker_data in word_timestamps:
        speaker_id = speaker_data.get("speaker", "Unknown")
        name = speaker_data.get("name", speaker_id)
        title = speaker_data.get("title", "")
        for wt in speaker_data.get("words_with_times", []):
            all_words_flat.append({
                "word": wt["word"],
                "start_time": wt["start_time"],
                "speaker": speaker_id,
                "name": name,
                "title": title,
            })

    all_words_flat.sort(key=lambda x: x["start_time"])
    if not all_words_flat:
        return []

    max_time = max(w["start_time"] for w in all_words_flat)
    if audio_duration:
        max_time = max(max_time, audio_duration)

    num_segments = math.ceil(max_time / segment_duration)
    last_speaker_name = "Unknown"
    last_speaker_title = ""
    segments = []

    for i in range(num_segments):
        seg_start = i * segment_duration
        seg_end = seg_start + segment_duration

        seg_words = [w for w in all_words_flat if seg_start <= w["start_time"] < seg_end]
        if not seg_words:
            segments.append({
                "index": i,
                "start_time": round(seg_start, 2),
                "end_time": round(seg_end, 2),
                "text": "",
                "speakers": [],
                "word_count": 0,
                "primary_speaker": last_speaker_name,
                "primary_speaker_title": last_speaker_title,
            })
            continue

        speakers_in_segment = {}
        for w in seg_words:
            sp = w["speaker"]
            if sp not in speakers_in_segment:
                speakers_in_segment[sp] = {
                    "words": [],
                    "name": w.get("name", sp),
                    "title": w.get("title", "")
                }
            speakers_in_segment[sp]["words"].append(w["word"])

        text = " ".join(w["word"] for w in seg_words)
        primary_speaker_id = max(speakers_in_segment.items(), key=lambda x: len(x[1]["words"]))[0]
        primary_info = speakers_in_segment[primary_speaker_id]
        last_speaker_name = primary_info["name"]
        last_speaker_title = primary_info["title"]

        segments.append({
            "index": i,
            "start_time": round(seg_start, 2),
            "end_time": round(seg_end, 2),
            "text": text,
            "speakers": [
                {
                    "speaker": sp,
                    "name": info["name"],
                    "title": info["title"],
                    "text": " ".join(info["words"])
                }
                for sp, info in speakers_in_segment.items()
            ],
            "word_count": len(seg_words),
            "primary_speaker": primary_info["name"],
            "primary_speaker_title": primary_info["title"],
        })

    return segments


def compute_chunk_audio_features(samples: np.ndarray, sample_rate: int) -> Dict:
    """Compute audio features for a single chunk."""
    if len(samples) == 0:
        return {"rms": 0, "peak": 0, "zero_crossings": 0, "is_speech": False}

    if np.max(np.abs(samples)) > 0:
        normalized = samples / np.max(np.abs(samples))
    else:
        normalized = samples

    rms = float(np.sqrt(np.mean(normalized ** 2)))
    peak = float(np.max(np.abs(normalized)))
    zero_crossings = int(np.sum(np.abs(np.diff(np.sign(normalized))) > 0))
    zcr = zero_crossings / max(len(normalized), 1)

    is_speech = rms > 0.02

    frame_size = int(sample_rate * 0.02)
    energy_frames = []
    for j in range(0, len(normalized) - frame_size, frame_size):
        frame_energy = np.mean(normalized[j:j + frame_size] ** 2)
        energy_frames.append(frame_energy)

    energy_var = float(np.var(energy_frames)) if energy_frames else 0

    return {
        "rms": round(rms, 4),
        "peak": round(peak, 4),
        "zero_crossing_rate": round(zcr, 4),
        "is_speech": is_speech,
        "energy_variance": round(energy_var, 6),
    }