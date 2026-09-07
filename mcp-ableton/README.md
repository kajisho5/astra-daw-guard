# mcp-ableton — Ableton Live MCP (v0.3 読み取り専用 + Issue #44 書き込みツール)

astra-daw-guard の ROADMAP.md には無かった追加項目（v0.2完了後の続き）
として、`mcp-reaper/` と同じ方針で作った、Ableton Live の状態を
公開する MCP サーバーです。

[AbletonOSC](https://github.com/ideoforms/AbletonOSC)（`ideoforms` 氏に
よる、Ableton Live 用の Remote Script。Live Object Model を OSC で公開
する）経由でライブ接続します。

読み取り専用ツール3つに加えて、Issue [#44](https://github.com/kajisho5/astra-daw-guard/issues/44)
で2つの書き込みツール（トラック作成・MIDI書き込み）を追加しました。
Save/Export用のOSCアドレスはAbletonOSC自体に存在しないことをソース
コードで確認済みのため（下記「動作状況」参照）、保存ツールはありません
（mcp-ardourにテンポ取得ツールが無いのと同じ理由の「無いものは無いと
書く」判断です）。書き込みツールは全て`enforcement.enforce()`経由で
Policy Engine（`policy_engine/rules.py`）のALLOW/ASK/DENY判定を必ず
先に通してからしか実行されません。

## ⚠️ 動作状況（正直な報告）

このセッションには Ableton Live が無いため、**実機での動作確認は
できていません**。以下は確認済み/未確認です。

- 確認済み: OSCアドレス（`/live/song/get/tempo` など）は AbletonOSC の
  ソースコード（`abletonosc/song.py` / `abletonosc/track.py`）を直接
  読んで確認したもの。ポート番号（送信11000/受信11001）と
  Ableton側の有効化手順（Preferences > Link / Tempo / MIDI）は
  AbletonOSCのREADMEで確認済み
- 確認済み: このリポジトリのリクエスト/応答ロジック（`osc_client.py`）
  と読み取り3ツール（`get_tempo` / `get_song_info` / `get_tracks`）は、
  AbletonOSCの動作を模したダミーUDPサーバーで実際に往復させて検証済み
- 確認済み: `/live/song/create_midi_track` / `/live/clip/add/notes` の
  ハンドラ実装（`abletonosc/handler.py`の`_call_method` /
  `abletonosc/clip.py`の`clip_add_notes`）をソースコードで読み、
  **どちらもOSC応答を一切返さない**ことを確認済み。そのため
  `osc_client.py`に新設した`send()`（応答を待たない片方向送信）を
  書き込みに使い、結果は`get`系クエリ（トラック名の読み直し、
  `/live/clip/get/notes`でのノート数照合）で確認する設計にした。
  何度か再試行しても確認できなかった場合は、成功したかのように
  誤った結果を返すのではなく`AbletonWriteUnconfirmed`例外を投げる
  （最初の実装ではこの確認漏れがあり、独立レビューで指摘されて
  修正した — `create_track`/`write_generated_midi`の実装・
  `tests/test_ableton_write_tools.py`参照）
- 確認済み: Save/ExportにあたるOSCアドレスがAbletonOSCに1つも存在しない
  ことをソースコード全体の確認で判断（保存ツールを実装していない理由）
- **未確認**: 本物の Ableton Live + AbletonOSC との実際の疎通（読み取り・
  書き込みとも）。特にトラックプロパティの応答形式（`track_index` を
  先頭に返すかどうか）はソース読解からの推定で、`_track_property()` は
  どちらの形式でも動くように防御的に書いていますが、実機で最初に確認
  してください。書き込み系ツールは応答が無いため、書き込み直後の
  読み直しタイミング（`_wait_until`の再試行間隔）が実機で十分かどうかも
  未検証です

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
python3 install.py
```

`pip install -e .` に加えて、AbletonOSC を `git clone` で Ableton の
Remote Scripts フォルダ（OS別の正しい場所を自動判定）に配置します。

これで自動化できるのはここまでです。**残り2つの手動操作**は
Ableton の外からは実行できません:

1. Ableton Live を再起動する
2. Preferences > Link/Tempo/MIDI > Control Surface で **AbletonOSC** を選ぶ

手動でやりたい場合、`install.py` がやっているのは「AbletonOSCを
`git clone`してRemote Scriptsフォルダに置く」だけです。OS別の配置先は
[AbletonOSCのREADME](https://github.com/ideoforms/AbletonOSC)を参照して
ください。

## 起動

```bash
python -m ableton_mcp.server
```

MCP クライアント（Claude Code など）の設定で、このコマンドを stdio MCP
サーバーとして登録してください。

## 提供ツール

読み取り専用:

| ツール | 内容 |
|---|---|
| `get_tempo` | BPM |
| `get_song_info` | BPM・曲の長さ（拍）・再生位置（拍）・再生中か・トラック数・シーン数。プロジェクト名/パスはAbletonのOSC APIに無いため含みません |
| `get_tracks` | トラック一覧（index / name / mute / solo / arm / 色）。リターン/マスタートラックは含みません |

書き込み（Issue #44、全てPolicy Engineでゲート済み）:

| ツール | 内容 | ゲート |
|---|---|---|
| `create_track(name, approved=False)` | MIDIトラックを1つ作成し名前を設定 | `name`が`GEN-`で始まれば自動ALLOW、それ以外はASK（`approved=True`が必要） |
| `write_generated_midi(track_name, notes, clip_index=0, approved=False)` | 既存トラックにクリップを作成しMIDIノートを書き込み | `track_name`が`GEN-`で始まる場合のみALLOW、それ以外は常にDENY（承認しても不可） |

保存ツールはありません（AbletonOSCにSave用アドレスが無いため、上記
「動作状況」参照）。判定ロジック自体は`policy_engine/rules.py`に既存
（`CREATE_GEN_TRACK` / `CREATE_OTHER_TRACK` /
`GENERATED_MIDI_INTO_GEN_TRACK` / `GENERATED_MIDI_INTO_OTHER_TRACK`）で、
今回は既存ルールに実際の書き込み処理を繋いだだけです。

## 参考にした一次情報

- AbletonOSC README（ポート番号、インストール手順、Preferences設定）: https://github.com/ideoforms/AbletonOSC/blob/master/README.md
- AbletonOSC ソースコード（OSCアドレスの確認、書き込みハンドラの応答有無）: https://github.com/ideoforms/AbletonOSC/blob/master/abletonosc/song.py , https://github.com/ideoforms/AbletonOSC/blob/master/abletonosc/track.py , https://github.com/ideoforms/AbletonOSC/blob/master/abletonosc/clip.py , https://github.com/ideoforms/AbletonOSC/blob/master/abletonosc/handler.py

これらは 2026-09-06〜09-07 時点で確認した内容です。AbletonOSCのバージョンが
変わるとアドレス構成が変わる可能性があるため、エラーが出た場合は
まずこのページの一次情報を再確認してください。

## その他のAbleton連携ツールについて

`ableton-osc-mcp`（nozomi-koborinai氏）など、AbletonOSCを使った
コミュニティ製MCPサーバーも存在します。これらは**コミュニティ製・
自己責任**であり、多くは書き込み操作（再生、ミュート変更など）も
含むため、このリポジトリの `policy/deny.txt` の範囲外の操作をする
可能性があります。使う場合は内容を確認してください。
