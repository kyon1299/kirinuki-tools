"""yt-dlpで配信アーカイブの動画・ライブチャット・メタデータを取得する。"""
from __future__ import annotations

import json
from pathlib import Path


def fetch(url: str, workdir: Path) -> dict:
    """動画を workdir に保存し、メタデータ(info.json の中身)を返す。

    保存されるファイル:
      video.<ext>            動画本体(1080p以下)
      video.live_chat.json   ライブチャットのリプレイ(ある場合)
      video.info.json        タイトル・チャンネルなどのメタデータ
    """
    import yt_dlp

    workdir.mkdir(parents=True, exist_ok=True)
    opts = {
        "format": "bv*[height<=1080]+ba/b[height<=1080]",
        "merge_output_format": "mp4",
        "outtmpl": str(workdir / "video.%(ext)s"),
        "writeinfojson": True,
        "writesubtitles": True,
        "subtitleslangs": ["live_chat"],
        "quiet": True,
        "noprogress": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    return load_info(workdir)


def load_info(workdir: Path) -> dict:
    return json.loads((workdir / "video.info.json").read_text(encoding="utf-8"))


def find_video(workdir: Path) -> Path:
    for ext in ("mp4", "mkv", "webm"):
        path = workdir / f"video.{ext}"
        if path.exists():
            return path
    raise FileNotFoundError(f"{workdir} に動画がありません。先に fetch を実行してください")
