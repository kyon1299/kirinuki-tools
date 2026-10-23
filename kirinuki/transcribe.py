"""faster-whisperで単語タイムスタンプ付きの文字起こしを作る。"""
from __future__ import annotations

import json
from pathlib import Path

from .subtitles import Cue, write_srt


def transcribe(video: Path, workdir: Path, model_size: str = "large-v3-turbo",
               device: str = "auto") -> list[Cue]:
    """文字起こしして transcript.json と transcript.srt を書き出す。"""
    try:
        segments = _run(video, model_size, device)
    except (RuntimeError, ValueError, OSError) as e:
        if device == "cpu":
            raise
        # CUDAのライブラリ(cuBLAS / cuDNN)がない環境では、文字起こしの途中で落ちるのでCPUでやり直す
        print(f"GPUで文字起こしできなかったため、CPUで実行します({e})")
        segments = _run(video, model_size, "cpu")
    cues = [Cue(start=s.start, end=s.end, text=s.text.strip()) for s in segments if s.text.strip()]
    save_cues(cues, workdir / "transcript.json")
    write_srt(cues, workdir / "transcript.srt")
    return cues


def _run(video: Path, model_size: str, device: str) -> list:
    from faster_whisper import WhisperModel

    compute_type = "int8" if device == "cpu" else "float16"
    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    segments, _ = model.transcribe(str(video), language="ja", vad_filter=True, word_timestamps=True)
    # transcribe は遅延評価なので、ここで最後まで回してエラーをこの関数内で出す
    return list(segments)


def save_cues(cues: list[Cue], path: Path) -> None:
    data = [{"start": c.start, "end": c.end, "text": c.text} for c in cues]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def load_cues(path: Path) -> list[Cue]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [Cue(**d) for d in data]
