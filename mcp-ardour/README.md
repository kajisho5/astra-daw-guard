# mcp-ardour — Ardour 読み取り専用 MCP (v0.4)

astra-daw-guard の `mcp-reaper/` / `mcp-ableton/` と同じ方針で、Ardour の
状態を**読み取り専用**で公開する最小の MCP サーバーです。Ardour
[本体に内蔵された OSC サーフェス](https://manual.ardour.org/using-control-surfaces/controlling-ardour-with-osc/)
経由でライブ接続します（AbletonOSCのような別途インストールが不要 —
Ardour自身が最初からOSCサーバーを内蔵しています）。**書き込み操作は
一切実装していません**。

## ⚠️ 動作状況（正直な報告）

このセッションには Ardour が無いため、**実機での動作確認はできて
いません**。

- 確認済み: OSCアドレス（`/strip/list` の返信フォーマット、
  `/transport_frame`、`/transport_speed`）は Ardour の公式マニュアル
  「Querying Ardour with OSC」とソースコード（`libs/surfaces/osc/osc.cc`）
  の両方で確認済み
- 確認済み: **Ardour の OSC にはテンポ取得コマンドが無い**ことを
  Ardourフォーラムで開発者自身が回答している投稿で確認（「単一の
  テンポという概念がセッション全体には存在しない」ため）。このため
  本アダプタに `get_tempo` はありません。無いものを「取得できる」と
  書くのは避けました
- 確認済み: このリポジトリのソケット通信ロジック（`osc_client.py`）と
  2ツール（`get_tracks` / `get_transport`）は、Ardourの挙動を模した
  擬似UDPサーバーで実際に往復させて検証済み（トラックとバスで返信の
  引数の数が違う仕様も含めて確認）
- 確認済み: `osc_client.py`の`query_list()`（`/strip/list`の複数返信を
  集約する処理）の`overall_timeout`予算の扱いは、自動テスト
  `tests/test_ardour_osc_client.py`（fakeソケット使用、Ardour本体不要）
  で固定済み（Issue #38 — 修正前は単発の返信間隔が`self._timeout`
  （デフォルト2.0秒、コンストラクタ引数で変更可）を超えるだけで、
  全体`overall_timeout`（デフォルト20秒）の予算が残っていても
  打ち切られていたバグ）
- **未確認**: 本物の Ardour との実際の疎通

## 前提条件

- Ardour（バージョン不問。OSCサーフェスは長く安定している機能）
- Ardour の Preferences > Control Surfaces > Open Sound Control (OSC)
  を有効化し、Port Mode は **Auto** のままにしておくこと
  （Autoモードは「リクエストが来たアドレス・ポートに返信する」仕様。
  本アダプタはこれを前提に、送信と受信を同じソケットで行います）
- Python 3.10 以上

## セットアップ

3つのアダプタの中で一番セットアップが軽いです。外部ファイルの配置が
不要で、Ardour自体の設定を1箇所変えるだけです。

```bash
cd mcp-ardour
python3 install.py
```

（`pip install -e .` を実行するだけのスクリプトです。）

その上で、Ardour側で1回だけ:

- Preferences > Control Surfaces > **Open Sound Control (OSC)** を有効化
  （Port Mode は Auto のまま）

これはArdourの外からは変更できないため、手動が必要です。

## 起動

```bash
python -m ardour_mcp.server
```

MCP クライアント（Claude Code など）の設定で、このコマンドを stdio MCP
サーバーとして登録してください。

## 提供ツール（すべて読み取り専用）

| ツール | 内容 |
|---|---|
| `get_tracks` | トラック/バス/VCA一覧（`/strip/list`経由）。type・name・index・inputs・outputs・muted・soloed・record_enabled（バス/VCAはnull） |
| `get_transport` | 再生位置（サンプル）・速度・再生中か |

`get_tempo` はありません（上記「動作状況」参照）。書き込み系ツール
（トラック追加、テンポ変更、保存など）も実装していません。

## 参考にした一次情報

- Ardour OSC マニュアル: https://manual.ardour.org/using-control-surfaces/controlling-ardour-with-osc/
- Ardour OSCクエリ仕様: https://manual.ardour.org/using-control-surfaces/controlling-ardour-with-osc/querying-ardour-with-osc/
- Ardour OSCセットアップダイアログ（Port Mode Auto の挙動）: https://manual.ardour.org/using-control-surfaces/controlling-ardour-with-osc/osc-setup-dialog/
- Ardour OSCソースコード: https://github.com/Ardour/ardour/blob/master/libs/surfaces/osc/osc.cc
- テンポ取得が無いことの確認: https://discourse.ardour.org/t/changing-tempo-through-osc/86755

いずれも2026-09-07時点で確認した内容です。
