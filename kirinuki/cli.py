"""コマンドライン入口。

  kirinuki analyze <URL>          取得 → 文字起こし → 見どころ候補(candidates.json)
  kirinuki draft <作業フォルダ> 1 3 候補1と3の下書き(動画・テロップ・概要欄)を書き出す
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

from . import chat, fetch, guidelines, highlights, transcribe
from .draft import render_clip


def _video_id(url: str) -> str:
    m = re.search(r"(?:v=|youtu\.be/|/live/)([\w-]{11})", url)
    return m.group(1) if m else re.sub(r"\W+", "_", url)[-32:]


def cmd_analyze(args: argparse.Namespace) -> None:
    workdir = Path(args.work) / _video_id(args.url)
    print(f"作業フォルダ: {workdir}")

    if not (workdir / "video.info.json").exists():
        print("1/4 動画とチャットを取得中…")
        info = fetch.fetch(args.url, workdir)
    else:
        info = fetch.load_info(workdir)
    rules = guidelines.agency_rules(guidelines.channel_settings(info.get("channel_id", "")).get("agency"))
    if rules.get("requires_registration"):
        print(f"注意: {rules.get('name')} は切り抜きの事前登録・申請が必要です。投稿前に済ませてください。")

    transcript = workdir / "transcript.json"
    if transcript.exists():
        cues = transcribe.load_cues(transcript)
    else:
        print("2/4 文字起こし中…(GPUなしだと時間がかかります)")
        cues = transcribe.transcribe(fetch.find_video(workdir), workdir, model_size=args.model, device=args.device)

    print("3/4 チャットの盛り上がりを集計中…")
    chat_file = workdir / "video.live_chat.json"
    duration = float(info.get("duration") or (cues[-1].end if cues else 0))
    if not chat_file.exists():
        sys.exit("ライブチャットのリプレイがありません(プレミア公開・チャット無効の配信は未対応です)")
    counts = chat.per_second(chat.parse_live_chat(chat_file), duration)
    scored = highlights.score_windows(counts)
    cands = highlights.pick_candidates(scored, top_k=args.top, duration=duration)

    if args.no_llm:
        print("4/4 Claudeでの絞り込みはスキップしました")
    else:
        print("4/4 Claudeで候補を絞り込み中…")
        cands = highlights.refine_with_claude(cands, cues, info, exclude_singing=rules.get("exclude_singing", False))
    highlights.save_candidates(cands, workdir / "candidates.json")

    print("\n見どころ候補:")
    for i, c in enumerate(cands, 1):
        mark = f" [除外: {c.skip_reason}]" if c.skip else ""
        print(f"  {i}. {_hms(c.start)}〜{_hms(c.end)} (盛り上がり {c.score}){mark}")
        if c.reason:
            print(f"     {c.reason}")
        for t in c.title_ideas:
            print(f"     ・{t}")
    print(f"\n下書きを作るには: kirinuki draft {workdir} 1 2 …")


def cmd_draft(args: argparse.Namespace) -> None:
    workdir = Path(args.workdir)
    info = fetch.load_info(workdir)
    settings = guidelines.channel_settings(info.get("channel_id", ""))
    rules = guidelines.agency_rules(settings.get("agency"))
    cues = transcribe.load_cues(workdir / "transcript.json")
    cands = highlights.load_candidates(workdir / "candidates.json")
    video = fetch.find_video(workdir)

    for n in args.numbers:
        if not 1 <= n <= len(cands):
            print(f"候補{n} はありません")
            continue
        cand = cands[n - 1]
        if cand.skip:
            print(f"候補{n} は {cand.skip_reason} のため書き出しません")
            continue
        outdir = workdir / "drafts" / f"{n:02}"
        render_clip(video, cues, cand, outdir, color=settings.get("color", "FFFFFF"), burn=not args.no_preview)
        title = cand.title_ideas[0] if cand.title_ideas else ""
        desc = guidelines.build_description(info, rules, clip_title=title, start=cand.start)
        (outdir / "description.txt").write_text(desc, encoding="utf-8")
        print(f"候補{n} → {outdir}")


def _hms(t: float) -> str:
    t = int(t)
    return f"{t // 3600}:{t % 3600 // 60:02}:{t % 60:02}"


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="kirinuki", description="VTuber切り抜きの下書き作成ツール")
    sub = p.add_subparsers(required=True)

    a = sub.add_parser("analyze", help="配信を取得して見どころ候補を出す")
    a.add_argument("url")
    a.add_argument("--work", default=os.environ.get("KIRINUKI_WORK", "work"),
                   help="作業フォルダの置き場所(環境変数 KIRINUKI_WORK でも指定可)")
    a.add_argument("--top", type=int, default=8, help="候補の数")
    a.add_argument("--model", default="large-v3-turbo", help="Whisperのモデル")
    a.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"], help="文字起こしに使う装置")
    a.add_argument("--no-llm", action="store_true", help="Claudeでの絞り込みをしない")
    a.set_defaults(func=cmd_analyze)

    d = sub.add_parser("draft", help="選んだ候補の下書きを書き出す")
    d.add_argument("workdir")
    d.add_argument("numbers", type=int, nargs="+")
    d.add_argument("--no-preview", action="store_true", help="テロップ焼き込みの確認動画を作らない")
    d.set_defaults(func=cmd_draft)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
