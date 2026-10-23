"""チャットの盛り上がりから見どころ候補を出し、Claudeで候補を絞り込む。"""
from __future__ import annotations

import json
import statistics
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .subtitles import Cue

# 視聴者のコメントは場面から数秒遅れて流れるので、その分だけ区間を前にずらす
CHAT_LAG_SEC = 8


@dataclass
class Candidate:
    start: float
    end: float
    score: float
    title_ideas: list[str] = field(default_factory=list)
    reason: str = ""
    skip: bool = False  # 歌枠など、ガイドライン上切り抜けない区間
    skip_reason: str = ""


def _zscores(values: list[float]) -> list[float]:
    if len(values) < 2:
        return [0.0] * len(values)
    mean = statistics.fmean(values)
    sd = statistics.pstdev(values) or 1.0
    return [(v - mean) / sd for v in values]


def score_windows(counts: dict[str, list[int]], window: int = 40, step: int = 5) -> list[tuple[int, float]]:
    """window秒の区間ごとに盛り上がりスコアを付ける。戻り値は (区間開始秒, スコア)。"""
    n = len(counts["total"])
    starts = list(range(0, max(n - window, 0) + 1, step))
    sums = {k: [sum(v[s:s + window]) for s in starts] for k, v in counts.items()}
    zt, zl, zs = (_zscores(sums[k]) for k in ("total", "laugh", "surprise"))
    # 笑いは切り抜き向きの場面と相関が強いので重めにする
    return [(s, zt[i] + 1.5 * zl[i] + zs[i]) for i, s in enumerate(starts)]


def pick_candidates(scored: list[tuple[int, float]], window: int = 40, top_k: int = 8,
                    pad_before: int = 20, pad_after: int = 10, duration: float | None = None) -> list[Candidate]:
    """スコアの高い順に、重ならない区間を top_k 件選ぶ。前後に余白を付ける。"""
    chosen: list[Candidate] = []
    for start, score in sorted(scored, key=lambda x: x[1], reverse=True):
        if score <= 0 or len(chosen) >= top_k:
            break
        s = max(0, start - CHAT_LAG_SEC - pad_before)
        e = start - CHAT_LAG_SEC + window + pad_after
        if duration is not None:
            e = min(e, duration)
        if any(s < c.end and e > c.start for c in chosen):
            continue
        chosen.append(Candidate(start=float(s), end=float(e), score=round(score, 2)))
    return sorted(chosen, key=lambda c: c.start)


def transcript_excerpt(cues: list[Cue], start: float, end: float) -> str:
    return "\n".join(f"[{c.start:.0f}s] {c.text}" for c in cues if c.end > start and c.start < end)


def refine_with_claude(candidates: list[Candidate], cues: list[Cue], info: dict,
                       exclude_singing: bool = False) -> list[Candidate]:
    """各候補の文字起こしをClaudeに渡し、区間の微調整・理由・タイトル案を付ける。"""
    import anthropic
    from pydantic import BaseModel

    class Refined(BaseModel):
        index: int
        start: float
        end: float
        reason: str
        title_ideas: list[str]
        is_singing: bool

    class Result(BaseModel):
        clips: list[Refined]

    blocks = []
    for i, c in enumerate(candidates):
        excerpt = transcript_excerpt(cues, c.start - 30, c.end + 30)
        blocks.append(f"## 候補{i} (目安 {c.start:.0f}s〜{c.end:.0f}s, 盛り上がり {c.score})\n{excerpt}")

    prompt = f"""VTuberの配信アーカイブ「{info.get('title', '')}」({info.get('channel', '')})の切り抜き候補です。
チャットが盛り上がった区間と、その前後の文字起こしを渡します。秒数は配信先頭からの位置です。

候補ごとに次を返してください。
- start / end: 切り抜きとして話の流れが分かる区間(秒)。オチの直後で終える。15〜120秒が目安。
- reason: なぜ見どころなのか、一文で。
- title_ideas: 動画タイトル案を3つ。釣りすぎず、内容が伝わるもの。
- is_singing: 歌っている区間なら true。

最終的な構成やツッコミは人が付けるので、候補の良し悪しを正直に書いてください。

{chr(10).join(blocks)}"""

    client = anthropic.Anthropic()
    response = client.messages.parse(
        model="claude-opus-5-5",
        max_tokens=16000,
        output_config={"effort": "medium"},
        messages=[{"role": "user", "content": prompt}],
        output_format=Result,
    )
    if response.stop_reason == "refusal" or response.parsed_output is None:
        return candidates

    for r in response.parsed_output.clips:
        if not 0 <= r.index < len(candidates):
            continue
        c = candidates[r.index]
        if r.end > r.start:
            c.start, c.end = max(0.0, r.start), r.end
        c.reason, c.title_ideas = r.reason, r.title_ideas
        if exclude_singing and r.is_singing:
            c.skip, c.skip_reason = True, "歌枠(事務所ガイドラインで切り抜き禁止)"
    return candidates


def save_candidates(candidates: list[Candidate], path: Path) -> None:
    path.write_text(json.dumps([asdict(c) for c in candidates], ensure_ascii=False, indent=1), encoding="utf-8")


def load_candidates(path: Path) -> list[Candidate]:
    return [Candidate(**d) for d in json.loads(path.read_text(encoding="utf-8"))]
