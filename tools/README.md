# tools/ — v0.2 の補助スクリプト

ROADMAP.md v0.2 の項目3・4を実装したものです。すべて Python 標準
ライブラリのみで動作し、追加の依存パッケージは不要です（`mcp-reaper/`
とは独立しています）。どれも**補助・警告用**であり、`policy/` の
正本を置き換えるものではありません。

## `deny_check.py` — Computer Use 前の機械チェック（v0.2 項目3）

意図した操作の説明文を `policy/deny.txt` の各行とキーワード一致で
突き合わせ、引っかかりそうな場合に警告します。

```bash
python3 tools/deny_check.py "download a midi file from bitmidi.com"
# => WARNING: ...(該当ルールと共有キーワードを表示、終了コード1)

python3 tools/deny_check.py "read the current tempo and track list via MCP"
# => OK: ...(終了コード0)
```

**これはヒューリスティックです。** キーワードの重なりで判定しているだけ
なので、見逃し（false negative）も誤検知（false positive）もあります。
`checklists/during.md` の代わりにはなりません。迷ったら禁止扱いにして
ください。

## `record_source.py` / `sources/` — ライセンス記録（v0.2 項目2）

`policy/license-allowlist.txt` にあるホストからの取得だけを
`sources.json`（リポジトリ直下）に記録します。スキーマは
`sources/README.md` を参照してください。

```bash
python3 tools/record_source.py \
  --url "https://mutopiaproject.org/ftp/.../piece.mid" \
  --license "Public Domain (Mutopia)" \
  --track "GEN-piano-ref"
```

許可リスト外のホストは既定で拒否されます。

## `refusal_messages.json` / `refusal_message.py` — 拒否メッセージ辞書（v0.2 項目4）

`policy/deny.txt` の10ルールそれぞれに対応する、日本語/英語の定型拒否文
です。`policy/deny.txt` と1対1で対応していることを確認済みです
（ルール数・文言の一致をスクリプトで検証済み）。

```bash
python3 tools/refusal_message.py --list
python3 tools/refusal_message.py no_scrape_midi_dumps
python3 tools/refusal_message.py no_overwrite_save --lang ja
```

`policy/deny.txt` の文言を変更した場合、`refusal_messages.json` 内の
対応するエントリも手動で更新してください（自動生成ではありません）。

## 動作確認について

このセッションで実際に Python 3 で実行し、想定通りの入出力になることを
確認しています（誤検知が出たケースはキーワード除外リストを調整済み）。
DAW実機・実際のエージェント運用フローでの確認はまだです。
