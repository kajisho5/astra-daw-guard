# mcp-ableton — Ableton Live 読み取り専用 MCP (v0.3)

astra-daw-guard の ROADMAP.md には無かった追加項目（v0.2完了後の続き）
として、`mcp-reaper/` と同じ方針で作った、Ableton Live の状態を
**読み取り専用**で公開する最小の MCP サーバーです。

[AbletonOSC](https://github.com/ideoforms/AbletonOSC)（`ideoforms` 氏に
よる、Ableton Live 用の Remote Script。Live Object Model を OSC で公開
する）経由でライブ接続します。**書き込み操作は一切実装していません**
（テンポ変更、ミュート/ソロ切り替え、保存など）。

## ⚠️ 動作状況（正直な報告）

このセッションには Ableton Live が無いため、**実機での動作確認は
できていません**。以下は確認済み/未確認です。

- 確認済み: OSCアドレス（`/live/song/get/tempo` など）は AbletonOSC の
  ソースコード（`abletonosc/song.py` / `abletonosc/track.py`）を直接
  読んで確認したもの。ポート番号（送信11000/受信11001）と
  Ableton側の有効化手順（Preferences > Link / Tempo / MIDI）は
  AbletonOSCのREADMEで確認済み
- 確認済み: このリポジトリのリクエスト/応答ロジック（`osc_client.py`）
  と3ツール（`get_tempo` / `get_song_info` / `get_tracks`）は、
  AbletonOSCの動作を模したダミーUDPサーバーで実際に往復させて検証済み
- **未確認**: 本物の Ableton Live + AbletonOSC との実際の疎通。特に
  トラックプロパティの応答形式（`track_index` を先頭に返すかどうか）は
  ソース読解からの推定で、`_track_property()` はどちらの形式でも
  動くように防御的に書いていますが、実機で最初に確認してください

## 前提条件

- Ableton Live（Live 11 以降。AbletonOSC の対象バージョン）
- [AbletonOSC](https://github.com/ideoforms/AbletonOSC) を Remote Script
  としてインストール済みで、Preferences > Link / Tempo / MIDI の
  Control Surface で選択済みであること
- Python 3.10 以上

AbletonOSC 自体はこのリポジトリの一部ではありません。上記の公式
リポジトリから別途入手・インストールしてください。

## セットアップ

```bash
cd mcp-ableton
pip install -e .
```

Ableton Live 側で AbletonOSC を Control Surface として選択した状態で
起動しておいてください。

## 起動

```bash
python -m ableton_mcp.server
```

MCP クライアント（Claude Code など）の設定で、このコマンドを stdio MCP
サーバーとして登録してください。

## 提供ツール（すべて読み取り専用）

| ツール | 内容 |
|---|---|
| `get_tempo` | BPM |
| `get_song_info` | BPM・曲の長さ（拍）・再生位置（拍）・再生中か・トラック数・シーン数。プロジェクト名/パスはAbletonのOSC APIに無いため含みません |
| `get_tracks` | トラック一覧（index / name / mute / solo / arm / 色）。リターン/マスタートラックは含みません |

書き込み系ツール（テンポ変更、ミュート切り替え、保存など）は**意図的に
実装していません**。

## 参考にした一次情報

- AbletonOSC README（ポート番号、インストール手順、Preferences設定）: https://github.com/ideoforms/AbletonOSC/blob/master/README.md
- AbletonOSC ソースコード（OSCアドレスの確認）: https://github.com/ideoforms/AbletonOSC/blob/master/abletonosc/song.py , https://github.com/ideoforms/AbletonOSC/blob/master/abletonosc/track.py

これらは 2026-09-06 時点で確認した内容です。AbletonOSCのバージョンが
変わるとアドレス構成が変わる可能性があるため、エラーが出た場合は
まずこのページの一次情報を再確認してください。

## その他のAbleton連携ツールについて

`ableton-osc-mcp`（nozomi-koborinai氏）など、AbletonOSCを使った
コミュニティ製MCPサーバーも存在します。これらは**コミュニティ製・
自己責任**であり、多くは書き込み操作（再生、ミュート変更など）も
含むため、このリポジトリの `policy/deny.txt` の範囲外の操作をする
可能性があります。使う場合は内容を確認してください。
