import shutil
import subprocess

import pytest

from kirinuki.transcribe import load_audio


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpegが必要")
def test_load_audio_is_16k_mono_float(tmp_path):
    video = tmp_path / "video.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000",
                    "-ac", "2", "-t", "2", "-c:a", "aac", str(video)], check=True)
    audio = load_audio(video)
    assert audio.dtype.name == "float32"
    assert abs(len(audio) - 32000) < 1600
    assert 0 < abs(audio).max() <= 1.0
