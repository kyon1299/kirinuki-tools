"""yt-dlpが保存したライブチャットのリプレイを読み、盛り上がりを数える。"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

# 「草」「www」「ｗｗ」「笑」「lol」などの笑い反応
LAUGH_RE = re.compile(r"草|[wｗ]{2,}|笑|lol|LOL|ｗ$|w$")
# 「!?」「えぇ」「やばい」などの驚き反応
SURPRISE_RE = re.compile(r"[!！?？]{2,}|えぇ|ええ|やば|ヤバ|まじ|マジ|すご|うま")


@dataclass
class ChatMessage:
    t: float  # 動画先頭からの秒数
    text: str


def parse_live_chat(path: Path) -> list[ChatMessage]:
    messages = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        replay = obj.get("replayChatItemAction", {})
        offset = replay.get("videoOffsetTimeMsec")
        if offset is None:
            continue
        for action in replay.get("actions", []):
            item = action.get("addChatItemAction", {}).get("item", {})
            renderer = item.get("liveChatTextMessageRenderer") or item.get("liveChatPaidMessageRenderer")
            if not renderer:
                continue
            runs = renderer.get("message", {}).get("runs", [])
            text = "".join(r.get("text", "") or _emoji_text(r) for r in runs)
            messages.append(ChatMessage(int(offset) / 1000, text))
    return messages


def _emoji_text(run: dict) -> str:
    emoji = run.get("emoji")
    if not emoji:
        return ""
    shortcuts = emoji.get("shortcuts") or [""]
    return shortcuts[0]


def per_second(messages: list[ChatMessage], duration: float) -> dict[str, list[int]]:
    """1秒ごとのコメント数・笑い数・驚き数。"""
    n = int(duration) + 1
    total, laugh, surprise = [0] * n, [0] * n, [0] * n
    for m in messages:
        i = int(m.t)
        if not 0 <= i < n:
            continue
        total[i] += 1
        if LAUGH_RE.search(m.text):
            laugh[i] += 1
        if SURPRISE_RE.search(m.text):
            surprise[i] += 1
    return {"total": total, "laugh": laugh, "surprise": surprise}
