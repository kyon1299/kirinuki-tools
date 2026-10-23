import shutil
import subprocess

import pytest

from kirinuki.draft import render_clip
from kirinuki.highlights import Candidate
from kirinuki.subtitles import Cue


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpegが必要")
def test_render_clip(tmp_path):
    video = tmp_path / "video.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=640x360:rate=30",
                    "-f", "lavfi", "-i", "sine=frequency=440", "-t", "6", "-c:v", "libx264", "-c:a", "aac",
                    str(video)], check=True)
    cues = [Cue(2.0, 4.0, "テストのテロップ")]
    out = render_clip(video, cues, Candidate(start=1.0, end=5.0, score=1.0), tmp_path / "draft")
    for key in ("clip", "srt", "ass", "preview"):
        assert out[key].exists() and out[key].stat().st_size > 0
    assert "00:00:01,000 --> 00:00:03,000" in out["srt"].read_text(encoding="utf-8")
