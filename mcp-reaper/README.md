# mcp-reaper — Reaper MCP (v0.2 読み取り専用 + Issue #44 書き込みツール)

astra-daw-guard の ROADMAP.md フェーズ7・v0.2 項目1として追加した、Reaper
プロジェクト状態を公開する MCP サーバーです。`reapy` (python-reapy) 経由で
稼働中の Reaper にライブ接続します。

読み取り専用ツール3つに加えて、Issue [#44](https://github.com/kajisho5/astra-daw-guard/issues/44)
で3つの書き込みツール（トラック作成・MIDI書き込み・Save As）を追加
しました。書き込みツールは全て`enforcement.enforce()`経由で
Policy Engine（`policy_engine/rules.py`）のALLOW/ASK/DENY判定を必ず
先に通してからしか実行されません。上書き保存（`mode=overwrite`）は
`policy/deny.txt`により常にDENYで、そもそもツール側でそのActionを
表現する手段自体がありません。

## ⚠️ 動作状況

このセッションには Reaper が無いため、**実機（Reaper が動いている
Windows/Mac 環境）での動作確認はできていません**。以下は確認済み/未確認
です。

- 確認済み: `mcp` SDK は v2 系（`MCPServer`、旧 `FastMCP` は廃止）に対応
  済み。読み取り3ツール（`get_tempo` / `get_tracks` / `get_project_info`）は
  reapy オブジェクトのフェイク（スタブ）でロジックを検証済み
- 確認済み: 書き込み3ツール（`create_track` / `write_generated_midi` /
  `save_project_as`）のPolicy Engineゲート部分（DENY/未承認ASKなら
  reapyを一切呼ばない、ALLOW/承認済みASKなら呼ぶ）は`tests/test_reaper_write_tools.py`
  でfakeのProject/Track/Item/Takeを使って検証済み。`save_project_as`が
  reapy自身の`Project.save(force_save_as=True)`ではなく生の
  `reascript_api.Main_SaveProjectEx`を使う理由（前者はインタラクティブな
  Save Asダイアログを開いてしまい、無人実行できないことをreapyの
  ソースコードで確認済み）も同ファイルに記載
- 未確認: 実際の Reaper + reapy の組み合わせでの疎通（`reapy.Project()`
  が本物の Reaper から値を返すか、書き込みツールが実際にトラック・MIDI・
  ファイルを作るか）はいずれも未検証

現場で最初に使う際は `get_project_info` など軽い呼び出しから確認して
ください。

## 前提条件

- Reaper がインストール済みで、起動していること
- Python 3.10 以上
- `python-reapy` が **一度だけ設定済み**であること（下記セットアップ参照）

## セットアップ

Reaper を起動した状態で:

```bash
cd mcp-reaper
python3 install.py
```

`pip install -e .` と `reapy.configure_reaper()` をまとめて実行します。
終わったら **Reaper を再起動**してください（reapy 側の要求で、これだけは
自動化できません）。

手動でやりたい場合、`install.py` の中身は以下と同じです。

```bash
pip install -e .
python -c "import reapy; reapy.configure_reaper()"
# Reaper を再起動する（reapy 側の要求）
```

再起動後、外部の Python プロセスから `import reapy` するだけで Reaper に
接続できます（reapy 内部で REAPER 側の ReaScript ブリッジと通信します）。

## 起動

```bash
python -m reaper_mcp.server
```

MCP クライアント（Claude Code など）の設定で、このコマンドを stdio MCP
サーバーとして登録してください。

## 提供ツール

読み取り専用:

| ツール | 内容 |
|---|---|
| `get_tempo` | BPM と拍子の分子（`bpi`）。reapy の高レベルAPIでは分子しか取れないため分母は返しません |
| `get_tracks` | トラック一覧（index / name / mute / solo / item数 / 色）。マスタートラックは含みません |
| `get_project_info` | プロジェクト名・ディレクトリ・長さ（秒）・トラック数 |

書き込み（Issue #44、全てPolicy Engineでゲート済み）:

| ツール | 内容 | ゲート |
|---|---|---|
| `create_track(name, approved=False)` | トラックを1つ作成 | `name`が`GEN-`で始まれば自動ALLOW、それ以外はASK（`approved=True`が必要） |
| `write_generated_midi(track_name, notes, approved=False)` | 既存トラックへMIDIノートを書き込み | `track_name`が`GEN-`で始まる場合のみALLOW、それ以外は常にDENY（承認しても不可） |
| `save_project_as(filename, user_requested_this_turn=False, approved=False)` | 別名で保存（上書き保存は不可） | `user_requested_this_turn=True`なら自動ALLOW、それ以外はASK |

いずれもPolicy Engineの判定を通さずreapyを呼ぶ経路は存在しません。判定
ロジック自体は`policy_engine/rules.py`に既存（`CREATE_GEN_TRACK` /
`CREATE_OTHER_TRACK` / `GENERATED_MIDI_INTO_GEN_TRACK` /
`GENERATED_MIDI_INTO_OTHER_TRACK` / `SAVE_AS_APPROVED` /
`SAVE_AS_UNCONFIRMED`）で、今回は既存ルールに実際の書き込み処理を
繋いだだけです。

## 参考にした一次情報

- reapy ソースコード（Project / Track / Take クラス）: https://python-reapy.readthedocs.io/en/latest/_modules/reapy/core/project/project.html , https://python-reapy.readthedocs.io/en/latest/_modules/reapy/core/track/track.html
- reapy README（セットアップ手順）: https://github.com/RomeoDespres/reapy
- reapy API guide: https://python-reapy.readthedocs.io/en/latest/api_guide.html
- REAPER ReaScript API（`Main_SaveProjectEx`のシグネチャ確認）: https://www.reaper.fm/sdk/reascript/reascripthelp.html

これらは 2026-09-06〜09-07 時点で確認した内容です。reapy のバージョンが
変わると属性名が変わる可能性があるため、エラーが出た場合はまずこのページの
一次情報を再確認してください。
