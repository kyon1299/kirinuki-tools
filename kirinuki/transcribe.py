"""faster-whisperで単語タイムスタンプ付きの文字起こしを作る。"""
from __future__ import annotations

import json
from pathlib import Path

from .subtitles import Cue, write_srt


def transcribe(video: Path, workdir: Path, model_size: str = "large-v3-turbo",
               device: str = "auto") -> list[Cue]:
    """文字起こしして transcript.json と transcript.srt を書き出す。"""
    from faster_whisper import WhisperModel

    compute_type = "float16" if device in ("cuda", "auto") else "int8"
    try:
        model = WhisperModel(model_size, device=device, compute_type=compute_type)
    except (RuntimeError, ValueError):
        # GPUが使えない環境ではCPUに切り替える
        model = WhisperModel(model_size, device="cpu", compute_type="int8")

    segments, _ = model.transcribe(
        str(video),
        language="ja",
        vad_filter=True,
        word_timestamps=True,
    )
    cues = [Cue(start=s.start, end=s.end, text=s.text.strip()) for s in segments if s.text.strip()]
    save_cues(cues, workdir / "transcript.json")
    write_srt(cues, workdir / "transcript.srt")
    return cues


def save_cues(cues: list[Cue], path: Path) -> None:
    data = [{"start": c.start, "end": c.end, "text": c.text} for c in cues]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def load_cues(path: Path) -> list[Cue]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [Cue(**d) for d in data]
