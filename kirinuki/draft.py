"""候補区間をカットし、テロップ付きの下書き動画とSRT・概要欄を書き出す。"""
from __future__ import annotations

import subprocess
from pathlib import Path

from .highlights import Candidate
from .subtitles import Cue, clip_cues, read_srt, write_ass, write_srt


def _filter_path(path: Path) -> str:
    # ffmpegのsubtitlesフィルタ用に : と ' と \ をエスケープする
    return str(path).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def render_clip(video: Path, cues: list[Cue], cand: Candidate, outdir: Path,
                color: str = "FF6FA8", burn: bool = True, margin_v: int = 140,
                keep_srt: bool = False, style: dict | None = None) -> dict[str, Path]:
    """1候補分の下書きを outdir に書き出す。

    clip.mp4           カット済みの素材(テロップなし、編集ソフトに読み込む用)
    clip.srt / clip.ass テロップ(編集ソフト読み込み用 / 焼き込み用)
    preview.mp4        テロップ焼き込みの確認用(burn=True のとき)

    keep_srt=True のときは、手で直した clip.srt をそのまま使って焼き込み直す。
    """
    outdir.mkdir(parents=True, exist_ok=True)
    srt, ass = outdir / "clip.srt", outdir / "clip.ass"
    if keep_srt and srt.exists():
        local = read_srt(srt)
    else:
        local = clip_cues(cues, cand.start, cand.end)
        write_srt(local, srt)
    write_ass(local, ass, color=color, margin_v=margin_v, **(style or {}))

    clip = outdir / "clip.mp4"
    duration = cand.end - cand.start
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{cand.start:.2f}", "-i", str(video),
         "-t", f"{duration:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
         "-c:a", "aac", "-b:a", "192k", str(clip)],
        check=True,
    )
    out = {"clip": clip, "srt": srt, "ass": ass}
    if burn:
        preview = outdir / "preview.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(clip),
             "-vf", f"subtitles='{_filter_path(ass)}'", "-c:v", "libx264", "-preset", "veryfast",
             "-crf", "23", "-c:a", "copy", str(preview)],
            check=True,
        )
        out["preview"] = preview
    return out
