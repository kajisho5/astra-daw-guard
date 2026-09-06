# mcp-reaper — Reaper 読み取り専用 MCP (v0.2)

astra-daw-guard の ROADMAP.md フェーズ7・v0.2 項目1として追加した、Reaper
プロジェクト状態を**読み取り専用**で公開する最小の MCP サーバーです。
`reapy` (python-reapy) 経由で稼働中の Reaper にライブ接続します。

**書き込み操作は一切実装していません**（トラック追加・削除、テンポ変更、
保存など）。ルートの `policy/deny.txt` / `policy/allow.txt` の境界を
コードでも守るための実装です。

## ⚠️ 動作状況

このセッションには Reaper が無いため、**実機（Reaper が動いている
Windows/Mac 環境）での動作確認はできていません**。以下は確認済み/未確認
です。

- 確認済み: `mcp` SDK は v2 系（`MCPServer`、旧 `FastMCP` は廃止）に対応
  済み。3ツール（`get_tempo` / `get_tracks` / `get_project_info`）は
  reapy オブジェクトのフェイク（スタブ）でロジックを検証済み
- 未確認: 実際の Reaper + reapy の組み合わせでの疎通（`reapy.Project()`
  が本物の Reaper から値を返すかどうか）

現場で最初に使う際は `get_project_info` など軽い呼び出しから確認して
ください。

## 前提条件

- Reaper がインストール済みで、起動していること
- Python 3.10 以上
- `python-reapy` が **一度だけ設定済み**であること（下記セットアップ参照）

## セットアップ

```bash
cd mcp-reaper
pip install -e .

# Reaper を起動した状態で、初回のみ実行
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

## 提供ツール（すべて読み取り専用）

| ツール | 内容 |
|---|---|
| `get_tempo` | BPM と拍子の分子（`bpi`）。reapy の高レベルAPIでは分子しか取れないため分母は返しません |
| `get_tracks` | トラック一覧（index / name / mute / solo / item数 / 色）。マスタートラックは含みません |
| `get_project_info` | プロジェクト名・ディレクトリ・長さ（秒）・トラック数 |

書き込み系ツール（トラック追加、保存、テンポ変更など）は**意図的に実装して
いません**。それらが必要になった場合でも、`policy/deny.txt` に違反しない
範囲かをまず確認してください。

## 参考にした一次情報

- reapy ソースコード（Project / Track クラス）: https://python-reapy.readthedocs.io/en/latest/_modules/reapy/core/project/project.html , https://python-reapy.readthedocs.io/en/latest/_modules/reapy/core/track/track.html
- reapy README（セットアップ手順）: https://github.com/RomeoDespres/reapy
- reapy API guide: https://python-reapy.readthedocs.io/en/latest/api_guide.html

これらは 2026-09-06 時点で確認した内容です。reapy のバージョンが変わると
属性名が変わる可能性があるため、エラーが出た場合はまずこのページの一次
情報を再確認してください。
