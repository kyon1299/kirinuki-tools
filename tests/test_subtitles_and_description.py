from kirinuki.guidelines import build_description
from kirinuki.subtitles import Cue, ass_escape, clip_cues, srt_time


def test_clip_cues_shifts_and_trims():
    cues = [Cue(5, 9, "前"), Cue(9, 12, "中"), Cue(14, 20, "後")]
    out = clip_cues(cues, 10, 16)
    assert [(c.start, c.end, c.text) for c in out] == [(0, 2, "中"), (4, 6, "後")]


def test_time_formats_and_escape():
    assert srt_time(3723.456) == "01:02:03,456"
    assert ass_escape("{a}\nb") == "\\{a\\}\\Nb"


def test_description_has_source_title_and_url():
    info = {"title": "【雑談】はじめての配信", "webpage_url": "https://www.youtube.com/watch?v=abcdefghijk",
            "channel": "テスト", "channel_url": "https://www.youtube.com/channel/UCx"}
    desc = build_description(info, {"description_notes": ["定型文"]}, clip_title="タイトル案", start=125.7)
    assert "【雑談】はじめての配信" in desc
    assert "https://www.youtube.com/watch?v=abcdefghijk&t=125s" in desc
    assert "定型文" in desc


def test_detect_agency_from_title():
    from kirinuki.guidelines import agency_rules, detect_agency

    info = {"channel_id": "UCnone", "title": "【防災訓練】ご紹介しますのじゃ【ホロライブ/熱千めら】"}
    assert detect_agency(info) == "hololive"
    assert agency_rules(detect_agency({"title": "雑談"}))["name"].startswith("その他")


def test_srt_roundtrip(tmp_path):
    from kirinuki.subtitles import read_srt, write_srt

    path = tmp_path / "clip.srt"
    write_srt([Cue(0, 2.38, "あのー"), Cue(3.26, 4.94, "炎上は危険ですね")], path)
    cues = read_srt(path)
    assert [(c.start, c.end, c.text) for c in cues] == [(0, 2.38, "あのー"), (3.26, 4.94, "炎上は危険ですね")]
