"""faster-whisperで単語タイムスタンプ付きの文字起こしを作る。"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .subtitles import Cue, write_srt


def transcribe(video: Path, workdir: Path, model_size: str = "large-v3-turbo",
               device: str = "auto") -> list[Cue]:
    """文字起こしして transcript.json と transcript.srt を書き出す。"""
    audio = load_audio(video)
    try:
        segments = _run(audio, model_size, device)
    except (RuntimeError, ValueError, OSError) as e:
        if device == "cpu":
            raise
        # CUDAのライブラリ(cuBLAS / cuDNN)がない環境では、文字起こしの途中で落ちるのでCPUでやり直す
        print(f"GPUで文字起こしできなかったため、CPUで実行します({e})")
        segments = _run(audio, model_size, "cpu")
    cues = [Cue(start=s.start, end=s.end, text=s.text.strip()) for s in segments if s.text.strip()]
    save_cues(cues, workdir / "transcript.json")
    write_srt(cues, workdir / "transcript.srt")
    return cues


def load_audio(video: Path, sampling_rate: int = 16000):
    """ffmpegで音声を16kHzモノラルに変換して読み込む。

    faster-whisper付属の読み込み(PyAV)は版の組み合わせで壊れることがあるので使わない。
    """
    import numpy as np

    out = subprocess.run(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-i", str(video),
         "-vn", "-ac", "1", "-ar", str(sampling_rate), "-f", "s16le", "-"],
        check=True, capture_output=True,
    ).stdout
    return np.frombuffer(out, np.int16).astype(np.float32) / 32768.0


def _run(audio, model_size: str, device: str) -> list:
    from faster_whisper import WhisperModel

    compute_type = "int8" if device == "cpu" else "float16"
    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    segments, info = model.transcribe(audio, language="ja", vad_filter=True, word_timestamps=True)
    # transcribe は遅延評価なので、ここで最後まで回してエラーをこの関数内で出す
    out, last = [], -60.0
    for seg in segments:
        out.append(seg)
        if seg.end - last >= 60:
            last = seg.end
            print(f"  文字起こし {seg.end / 60:.0f}分 / {info.duration / 60:.0f}分", flush=True)
    return out


def save_cues(cues: list[Cue], path: Path) -> None:
    data = [{"start": c.start, "end": c.end, "text": c.text} for c in cues]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def load_cues(path: Path) -> list[Cue]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [Cue(**d) for d in data]
