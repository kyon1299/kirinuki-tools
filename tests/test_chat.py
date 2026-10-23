import json

from kirinuki.chat import parse_live_chat, per_second


def _line(ms, text):
    return json.dumps({"replayChatItemAction": {"videoOffsetTimeMsec": str(ms), "actions": [
        {"addChatItemAction": {"item": {"liveChatTextMessageRenderer": {"message": {"runs": [{"text": text}]}}}}}
    ]}}, ensure_ascii=False)


def test_parse_and_count(tmp_path):
    path = tmp_path / "video.live_chat.json"
    path.write_text("\n".join([_line(1500, "草"), _line(1900, "えぇ!?"), _line(3000, "こんばんは"), "broken"]),
                    encoding="utf-8")
    msgs = parse_live_chat(path)
    assert [m.t for m in msgs] == [1.5, 1.9, 3.0]
    counts = per_second(msgs, duration=4)
    assert counts["total"] == [0, 2, 0, 1, 0]
    assert counts["laugh"][1] == 1
    assert counts["surprise"][1] == 1
