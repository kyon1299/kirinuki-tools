"""テロップ(SRT / ASS)の書き出し。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Cue:
    start: float
    end: float
    text: str


def clip_cues(cues: list[Cue], start: float, end: float) -> list[Cue]:
    """区間 [start, end] に重なるテロップを、区間先頭を0秒として切り出す。"""
    out = []
    for c in cues:
        if c.end <= start or c.start >= end:
            continue
        out.append(Cue(max(c.start, start) - start, min(c.end, end) - start, c.text))
    return out


def srt_time(t: float) -> str:
    ms = round(t * 1000)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def ass_time(t: float) -> str:
    cs = round(t * 100)
    h, cs = divmod(cs, 360_000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"


def write_srt(cues: list[Cue], path: Path) -> None:
    lines = []
    for i, c in enumerate(cues, 1):
        lines += [str(i), f"{srt_time(c.start)} --> {srt_time(c.end)}", c.text, ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def ass_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}").replace("\n", "\\N")


def _ass_color(rgb: str, alpha: str = "00") -> str:
    """RRGGBB を ASS の &HAABBGGRR に変換する。"""
    return f"&H{alpha}{rgb[4:6]}{rgb[2:4]}{rgb[0:2]}".upper()


def _darken(rgb: str, factor: float = 0.45) -> str:
    return "".join(f"{int(int(rgb[i:i + 2], 16) * factor):02X}" for i in (0, 2, 4))


def write_ass(cues: list[Cue], path: Path, color: str = "FF6FA8",
              font: str = "Noto Sans JP", width: int = 1920, height: int = 1080,
              margin_v: int = 140, size: int = 92, text_color: str = "FFFFFF") -> None:
    """切り抜き向けのテロップを画面下部に置くASSを書き出す。

    白文字をメンバーのイメージカラーで縁取り、その外側を白で囲む二重縁にする。
    color はイメージカラー(RRGGBB)、text_color は文字色、size は文字の大きさ(px)。
    margin_v は画面下からの余白。配信画面の下に帯がある場合は大きくする。
    """
    text = _ass_color(text_color)
    accent = _ass_color(color)
    shadow = _ass_color(_darken(color), "60")
    common = f"-1,0,0,0,100,100,2,0,1"
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Outer,{font},{size},&H00FFFFFF,&H000000FF,&H00FFFFFF,{shadow},{common},14,4,2,60,60,{margin_v},1
Style: Default,{font},{size},{text},&H000000FF,{accent},&H00000000,{common},5,0,2,60,60,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for c in cues:
        t0, t1, body = ass_time(c.start), ass_time(c.end), ass_escape(c.text)
        events.append(f"Dialogue: 0,{t0},{t1},Outer,,0,0,0,,{body}")
        events.append(f"Dialogue: 1,{t0},{t1},Default,,0,0,0,,{body}")
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


def _parse_srt_time(t: str) -> float:
    hms, ms = t.strip().split(",")
    h, m, sec = hms.split(":")
    return ((int(h) * 3600 + int(m) * 60 + int(sec)) * 1000 + int(ms)) / 1000


def read_srt(path: Path) -> list[Cue]:
    """手で直した SRT を読み込む。"""
    cues = []
    for block in path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").split("\n\n"):
        lines = [l for l in block.strip().split("\n") if l.strip()]
        if len(lines) < 2 or "-->" not in lines[1]:
            continue
        start, end = (_parse_srt_time(x) for x in lines[1].split("-->"))
        cues.append(Cue(start, end, "\n".join(lines[2:])))
    return cues
