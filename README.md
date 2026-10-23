# kirinuki-tools

VTuberの配信アーカイブから、切り抜き動画の「下書き」を作るツールです。
構成の組み替え、ツッコミテロップ、サムネ、最終チェックは人が仕上げる前提です(収益化審査で量産型と判断されないため)。

## できること

1. 配信の動画・ライブチャット・メタデータを取得(yt-dlp)
2. 文字起こし(faster-whisper large-v3-turbo)
3. チャットの盛り上がり(コメント数・「草」・驚き)から見どころ候補を出す
4. Claudeで候補の区間を整え、見どころの理由とタイトル案を付ける(歌枠の除外にも対応)
5. 選んだ候補をカットし、テロップ(SRT/ASS)と焼き込みの確認動画を書き出す
6. 元配信のタイトルとURLを入れた概要欄の下書きを作る

## 準備

- Python 3.11 以上、ffmpeg
- Deno(yt-dlpがYouTubeを読み込むのに使います。Windowsは `winget install DenoLand.Deno`)
- NVIDIA GPU があると文字起こしが速いです(なくても動きます)。WindowsでGPUを使うときは `pip install -e ".[gpu]"` でCUDAのライブラリも入れてください
- Claude API キー(`ANTHROPIC_API_KEY`)。なくても `--no-llm` で使えます

```sh
python -m venv .venv
source .venv/bin/activate        # Windowsは .venv\Scripts\activate
pip install -e ".[dev]"
cp config/channels.example.yaml config/channels.yaml   # 対象メンバーを書く
```

### 大きいファイルを別ドライブに置く

動画は作業フォルダに、Whisperのモデル(約1.6GB)は Hugging Face のキャッシュに保存されます。
別ドライブに置く場合は、PowerShellで一度だけ次を実行し、PowerShellを開き直してください。

```powershell
setx KIRINUKI_WORK "F:\kirinuki\work"
setx HF_HOME "F:\kirinuki\hf-cache"
```

## 使い方

```sh
# 取得 → 文字起こし → 見どころ候補
kirinuki analyze "https://www.youtube.com/watch?v=XXXXXXXXXXX"

# 候補1と3の下書きを書き出す(clip.srt を手で直したら --keep-srt を付けて焼き込み直す)
kirinuki draft work/XXXXXXXXXXX 1 3   # 作業フォルダを変えた場合はそのパス
```

`work/<動画ID>/drafts/01/` に次のファイルができます。

| ファイル | 用途 |
|---|---|
| clip.mp4 | カット済み素材(テロップなし)。編集ソフトに読み込む |
| clip.srt | テロップ。DaVinci Resolve / Premiere Pro / YMM4 に読み込める |
| clip.ass | 焼き込み用テロップ(メンバーのイメージカラー) |
| preview.mp4 | テロップ焼き込みの確認用 |
| description.txt | 概要欄の下書き(元配信のタイトル・URL・チャンネル) |

## ガイドライン

事務所ごとの設定は `config/guidelines.yaml` にあります。公式ガイドラインは改定されるので、投稿前に必ず最新版を確認してください。

- にじさんじ: 切り抜きは事前登録制(2025-05-23〜)。登録前に投稿しない
- ぶいすぽっ!: 事前申請制、歌枠の切り抜きは禁止
- ホロライブ: 概要欄に元動画のタイトルとURLを記載

## テスト

```sh
pytest
```
