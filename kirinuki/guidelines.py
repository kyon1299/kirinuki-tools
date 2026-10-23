"""事務所ごとのガイドライン設定と、概要欄テンプレの生成。"""
from __future__ import annotations

from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def load_yaml(name: str) -> dict:
    path = CONFIG_DIR / name
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def channel_settings(channel_id: str) -> dict:
    """config/channels.yaml からチャンネル設定(事務所・テロップ色)を引く。"""
    return load_yaml("channels.yaml").get("channels", {}).get(channel_id, {})


def agency_rules(agency: str | None) -> dict:
    agencies = load_yaml("guidelines.yaml").get("agencies", {})
    return agencies.get(agency or "", agencies.get("default", {}))


def build_description(info: dict, rules: dict, clip_title: str = "", start: float | None = None) -> str:
    """元動画のタイトルとURL、チャンネル、ガイドライン表記を入れた概要欄の下書き。"""
    url = info.get("webpage_url") or f"https://www.youtube.com/watch?v={info.get('id', '')}"
    if start is not None:
        url += f"&t={int(start)}s"
    lines = []
    if clip_title:
        lines += [clip_title, ""]
    lines += [
        "▼元配信",
        info.get("title", ""),
        url,
        "",
        f"▼{info.get('channel', '')} さんのチャンネル",
        info.get("channel_url", ""),
    ]
    notes = rules.get("description_notes", [])
    if notes:
        lines += [""] + notes
    lines += ["", "※この動画は切り抜きです。ぜひ元配信もご覧ください。"]
    return "\n".join(lines).strip() + "\n"
